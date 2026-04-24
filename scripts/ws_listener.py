"""
WebSocket agent client for yokowebot.

Connects to ws://127.0.0.1:9922/ws as a registered Agent, handles all events,
stores actionable events locally, and exposes a simple HTTP API on port 9923
so the AI Agent can query and acknowledge pending events.

HTTP API (port 9923):
  GET  /health                    – listener health + connection status
  GET  /events[?severity=<s>]     – list pending (unacknowledged) events
  POST /events/<id>/ack           – acknowledge an event (removes from queue)
  POST /ws/command                – forward a command to yokowebot via WebSocket
  POST /setup/heartbeat           – register heartbeat monitoring; returns prompt template
  GET  /setup/heartbeat           – current heartbeat registration status
  POST /debug/inject              – inject a fake event for local testing
"""

import asyncio
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

# ─────────────── constants ───────────────

WS_URL = "ws://127.0.0.1:9922/ws"
CLIENT_ID = "yoko-skill-agent"
EVENT_SERVER_PORT = 9923

EVENTS_DIR = Path.home() / ".yoko"
EVENTS_FILE = EVENTS_DIR / "pending_events.json"
LISTENER_PID_FILE = EVENTS_DIR / "ws_listener.pid"
HEARTBEAT_CONFIG_FILE = EVENTS_DIR / "heartbeat_config.json"

# Default heartbeat interval if caller doesn't specify
DEFAULT_HEARTBEAT_SECONDS = 60

# The prompt template an external agent should use for each heartbeat cycle.
# {interval} is replaced at registration time.
HEARTBEAT_PROMPT_TEMPLATE = """\
[微信RPA 心跳检查 — 每{interval}秒自动执行一次]

执行以下步骤，完成后不需要等待用户回复，静默完成即可：

1. 检查监听器状态
   GET http://127.0.0.1:9923/health
   如果请求失败（端口不通），说明 RPA 服务未启动，跳过后续步骤。

2. 获取所有待处理事件
   GET http://127.0.0.1:9923/events
   如果 count == 0，本次心跳结束，不需要输出任何内容。

3. 按优先级处理每个事件（events 数组从头到尾）：

   【urgent — 必须立即告知用户】
   - wechat.manual_action_required：
       告知用户：「{payload.message}，请立即操作！」
   - action.required：
       告知用户待审核的 AI 回复内容（payload.pendingContent），
       询问是否发送，然后发送 approve 或 reject 指令：
       POST http://127.0.0.1:9923/ws/command
       Body: {"command":"action.approve","params":{"eventId":"...","taskId":"...","sessionName":"..."}}

   【error — 需要用户修复配置】
   - ai.config_error：
       告知用户：「AI 配置错误（{context.service}）：{payload.errorMessage}」
       同时告知修复方式：「{payload.configKey}」
   - wechat.error：
       告知用户：「微信账号 {context.accountNickname} 出现严重错误，请检查微信状态」

   【warning — 通知用户，可能需要操作】
   - task.failed：
       告知用户任务失败信息，询问是否重试（isRetryable=true 时才询问）：
       重试：POST http://127.0.0.1:9923/ws/command {"command":"task.retry","params":{"taskId":"..."}}
       终止：POST http://127.0.0.1:9923/ws/command {"command":"task.abort","params":{"taskId":"..."}}
   - wechat.disconnected：
       告知用户：「微信账号 {context.accountNickname} 已掉线，服务正在自动重连」

4. 处理完每个事件后立即确认（无论是否需要用户操作）：
   POST http://127.0.0.1:9923/events/{id}/ack

注意：info 级别事件（task.started、task.completed）直接静默 ack，无需通知用户。\
"""

# Events that carry no actionable information — silently dropped
DISCARD_EVENTS = {
    "task.progress",             # Too frequent, noisy
    "auto_reply.session_update", # Real-time status, agent doesn't need to poll this
    "system.health",             # Passive health snapshot
    "wechat.reconnected",        # Good news, no action required
}

# Severity mapping for the remaining queued events
SEVERITY_MAP = {
    "task.started":                    "info",
    "task.completed":                  "info",
    "task.failed":                     "warning",
    "wechat.disconnected":             "warning",
    "ai.service_error":                "warning",
    "wechat.error":                    "error",
    "ai.config_error":                 "error",
    "wechat.manual_action_required":   "urgent",
    "action.required":                 "urgent",
}

# ─────────────── event store ───────────────

class EventStore:
    """Thread-safe in-memory event store with JSON file persistence."""

    def __init__(self):
        self._events: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def load(self):
        """Load unacknowledged events from the persistence file on startup."""
        try:
            if EVENTS_FILE.exists():
                with open(EVENTS_FILE, encoding="utf-8") as f:
                    rows = json.load(f)
                with self._lock:
                    self._events = {
                        r["id"]: r for r in rows if not r.get("acknowledged")
                    }
                print(f"[EventStore] Loaded {len(self._events)} pending events from disk")
        except Exception as e:
            print(f"[EventStore] Load failed: {e}")

    def add(self, msg: dict) -> str:
        event_name = msg.get("event", "unknown")
        entry = {
            "id": uuid.uuid4().hex[:12],
            "event": event_name,
            "severity": SEVERITY_MAP.get(event_name, "info"),
            "context": msg.get("context", {}),
            "payload": msg.get("payload", {}),
            "actions": msg.get("actions", []),
            "correlationId": msg.get("correlationId", ""),
            "eventId": msg.get("eventId", ""),
            "timestamp": msg.get("timestamp", int(time.time() * 1000)),
            "receivedAt": datetime.now().isoformat(),
            "acknowledged": False,
        }
        with self._lock:
            self._events[entry["id"]] = entry
            self._persist()
        print(f"[EventStore] +{entry['event']} (id={entry['id']}, severity={entry['severity']})")
        return entry["id"]

    def get_pending(self, severity: Optional[str] = None) -> List[dict]:
        with self._lock:
            items = [e for e in self._events.values() if not e.get("acknowledged")]
        if severity:
            items = [e for e in items if e.get("severity") == severity]
        return sorted(items, key=lambda x: x.get("timestamp", 0))

    def acknowledge(self, event_id: str) -> bool:
        with self._lock:
            if event_id in self._events:
                self._events[event_id]["acknowledged"] = True
                self._persist()
                return True
        return False

    def _persist(self):
        try:
            EVENTS_DIR.mkdir(parents=True, exist_ok=True)
            with open(EVENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(list(self._events.values()), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[EventStore] Persist failed: {e}")


event_store = EventStore()


# ─────────────── heartbeat registry ───────────────

class HeartbeatRegistry:
    """Persists heartbeat registration so the listener can warn if none is configured."""

    def __init__(self):
        self._config: Optional[dict] = None
        self._lock = threading.Lock()

    def load(self):
        try:
            if HEARTBEAT_CONFIG_FILE.exists():
                with open(HEARTBEAT_CONFIG_FILE, encoding="utf-8") as f:
                    self._config = json.load(f)
                print(f"[Heartbeat] Loaded config: interval={self._config.get('intervalSeconds')}s")
        except Exception as e:
            print(f"[Heartbeat] Load failed: {e}")

    def register(self, interval_seconds: int = DEFAULT_HEARTBEAT_SECONDS,
                 agent_id: str = "") -> dict:
        prompt = HEARTBEAT_PROMPT_TEMPLATE.replace("{interval}", str(interval_seconds))
        cfg = {
            "registered": True,
            "intervalSeconds": interval_seconds,
            "agentId": agent_id,
            "registeredAt": datetime.now().isoformat(),
            "heartbeatPrompt": prompt,
            "setupGuide": (
                "在 OpenClaw / QClaw 中配置心跳：\n"
                "1. 打开 Agent 设置 → 心跳（Heartbeat）\n"
                f"2. 设置间隔为 {interval_seconds} 秒\n"
                "3. 将 heartbeatPrompt 字段的内容粘贴为心跳触发提示词\n"
                "4. 保存并启用心跳"
            ),
        }
        with self._lock:
            self._config = cfg
            self._persist(cfg)
        print(f"[Heartbeat] Registered: interval={interval_seconds}s agentId={agent_id or '(none)'}")
        return cfg

    def status(self) -> dict:
        with self._lock:
            if self._config:
                return {
                    "configured": True,
                    "intervalSeconds": self._config.get("intervalSeconds"),
                    "agentId": self._config.get("agentId"),
                    "registeredAt": self._config.get("registeredAt"),
                }
        return {"configured": False}

    def is_configured(self) -> bool:
        with self._lock:
            return self._config is not None

    def _persist(self, cfg: dict):
        try:
            EVENTS_DIR.mkdir(parents=True, exist_ok=True)
            with open(HEARTBEAT_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Heartbeat] Persist failed: {e}")


heartbeat_registry = HeartbeatRegistry()

# ─────────────── command bus ───────────────

class CommandBus:
    """
    Thread-safe bridge that lets the HTTP handler (running in a background thread)
    schedule WebSocket sends on the asyncio event loop (running in main thread).
    """

    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._ws = None
        self._ws_lock = threading.Lock()

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def set_ws(self, ws):
        with self._ws_lock:
            self._ws = ws

    @property
    def connected(self) -> bool:
        with self._ws_lock:
            return self._ws is not None

    def send_command(self, payload: dict) -> bool:
        """
        Called from the HTTP thread. Schedules an async WS send on the event loop.
        Blocks up to 5 s waiting for the result.
        """
        with self._ws_lock:
            ws = self._ws
        if not self._loop or not ws:
            return False
        future = asyncio.run_coroutine_threadsafe(
            self._send_async(ws, json.dumps(payload)), self._loop
        )
        try:
            future.result(timeout=5)
            return True
        except Exception as e:
            print(f"[CommandBus] Send failed: {e}")
            return False

    @staticmethod
    async def _send_async(ws, text: str):
        await ws.send(text)


command_bus = CommandBus()

# ─────────────── HTTP event API (port 9923) ───────────────

class EventAPIHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # silence access log spam

    def _json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/health":
            pending = event_store.get_pending()
            urgent = [e for e in pending if e["severity"] == "urgent"]
            self._json({
                "status": "running",
                "connected": command_bus.connected,
                "pendingEvents": len(pending),
                "urgentEvents": len(urgent),
                "timestamp": int(time.time() * 1000),
            })

        elif parsed.path == "/events":
            severity = params.get("severity", [None])[0]
            events = event_store.get_pending(severity)
            self._json({"events": events, "count": len(events)})

        elif parsed.path == "/setup/heartbeat":
            self._json(heartbeat_registry.status())

        else:
            self._json({"error": "Not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except Exception:
            self._json({"error": "Invalid JSON body"}, 400)
            return

        path = self.path

        # POST /events/<id>/ack
        parts = path.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "events" and parts[2] == "ack":
            event_id = parts[1]
            ok = event_store.acknowledge(event_id)
            self._json({"success": ok, "eventId": event_id})
            return

        # POST /setup/heartbeat  – register heartbeat monitoring, return prompt template
        if path == "/setup/heartbeat":
            interval = int(data.get("intervalSeconds", DEFAULT_HEARTBEAT_SECONDS))
            interval = max(30, min(interval, 3600))  # clamp 30s ~ 1h
            agent_id = str(data.get("agentId", ""))
            cfg = heartbeat_registry.register(interval, agent_id)
            self._json(cfg)
            return

        # POST /debug/inject  – inject a fake agent_event for local testing
        if path == "/debug/inject":
            event_name = data.get("event")
            if not event_name:
                self._json({"error": "Missing required field: 'event'"}, 400)
                return
            # Build a minimal agent_event envelope if caller omits wrapper fields
            envelope = {
                "type":          "agent_event",
                "eventId":       data.get("eventId") or f"dbg_{uuid.uuid4().hex[:8]}",
                "correlationId": data.get("correlationId") or f"corr_debug_{uuid.uuid4().hex[:6]}",
                "timestamp":     data.get("timestamp") or int(time.time() * 1000),
                "event":         event_name,
                "context":       data.get("context", {}),
                "payload":       data.get("payload", {}),
                "actions":       data.get("actions", []),
            }
            # Reuse the same handler as real WS events (includes urgent side-effects)
            loop = command_bus._loop
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    handle_agent_event(envelope), loop
                ).result(timeout=3)
            else:
                # Fallback: insert directly without side-effects
                event_store.add(envelope)
            event_id = list(event_store._events.keys())[-1] if event_store._events else "?"
            self._json({"injected": True, "event": event_name, "eventId": event_id})
            return

        # POST /ws/command  – forward a command to yokowebot
        if path == "/ws/command":
            command = data.get("command")
            if not command:
                self._json({"error": "Missing required field: 'command'"}, 400)
                return
            cmd_id = data.get("commandId") or f"cmd_{uuid.uuid4().hex[:8]}"
            ws_msg = {
                "type": "command",
                "commandId": cmd_id,
                "correlationId": data.get("correlationId", ""),
                "command": command,
                "params": data.get("params", {}),
            }
            if command_bus.send_command(ws_msg):
                self._json({"success": True, "commandId": cmd_id})
            else:
                self._json(
                    {"error": "WebSocket not connected or send timed out"}, 503
                )
            return

        self._json({"error": "Not found"}, 404)


def start_event_server() -> HTTPServer:
    server = HTTPServer(("127.0.0.1", EVENT_SERVER_PORT), EventAPIHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True, name="event-api")
    t.start()
    print(f"[EventServer] Listening on http://127.0.0.1:{EVENT_SERVER_PORT}")
    return server

# ─────────────── WebSocket listener ───────────────

async def handle_message(msg: dict):
    msg_type = msg.get("type")

    if msg_type == "ping":
        # yokowebot sends application-level JSON pings; reply with pong
        return  # the WS send happens in the outer loop (see _send_pong)

    if msg_type == "registered":
        print(f"[WS] Registered — sessionId={msg.get('sessionId')}")
        return

    if msg_type == "command_result":
        ok = msg.get("success")
        cid = msg.get("commandId", "?")
        err = msg.get("error")
        print(f"[WS] command_result: commandId={cid} success={ok}" +
              (f" error={err}" if err else ""))
        return

    if msg_type == "agent_event":
        await handle_agent_event(msg)


async def handle_agent_event(msg: dict):
    event = msg.get("event", "")
    payload = msg.get("payload", {})
    context = msg.get("context", {})

    # Silently drop non-actionable events
    if event in DISCARD_EVENTS:
        return

    # Queue the event
    event_store.add(msg)

    # Extra console/notification handling for time-sensitive events
    if event == "wechat.manual_action_required":
        timeout = payload.get("timeoutSeconds", 10)
        msg_text = payload.get("message", "请手动点击微信头像以继续登录")
        print(f"\n{'!'*60}")
        print(f"[URGENT] 微信登录需要手动操作！剩余 {timeout} 秒")
        print(f"[URGENT] {msg_text}")
        print(f"{'!'*60}\n")
        _try_windows_toast("微信RPA — 需要手动操作", msg_text)

    elif event == "action.required":
        session = payload.get("targetSession", "未知")
        timeout = payload.get("timeoutSeconds", 25)
        print(f"[ACTION] 等待审核: 会话「{session}」, 超时 {timeout} 秒")

    elif event == "ai.config_error":
        service = context.get("service", "AI")
        print(f"[ERROR] AI配置错误({service}): {payload.get('errorMessage')}")
        print(f"[ERROR] 修复: {payload.get('configKey', '')}")

    elif event == "task.failed":
        print(f"[WARN] 任务失败: {context.get('taskId')} — {payload.get('errorMessage')}")

    elif event == "wechat.disconnected":
        nick = context.get("accountNickname") or context.get("accountId", "未知")
        print(f"[WARN] 微信账号掉线: {nick}")


def _try_windows_toast(title: str, body: str):
    """Best-effort Windows toast notification via PowerShell."""
    try:
        # Escape single quotes for PowerShell string
        t = title.replace("'", "\\'")
        b = body.replace("'", "\\'")
        ps = (
            "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications,"
            " ContentType = WindowsRuntime] | Out-Null; "
            "$tpl = [Windows.UI.Notifications.ToastNotificationManager]"
            "::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
            f"$tpl.SelectSingleNode(\"//text[@id='1']\").InnerText = '{t}'; "
            f"$tpl.SelectSingleNode(\"//text[@id='2']\").InnerText = '{b}'; "
            "$toast = [Windows.UI.Notifications.ToastNotification]::new($tpl); "
            "[Windows.UI.Notifications.ToastNotificationManager]"
            "::CreateToastNotifier('YokoWebot').Show($toast)"
        )
        subprocess.run(
            ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-Command", ps],
            timeout=4, capture_output=True,
        )
    except Exception:
        pass  # Notification is best-effort


async def ws_listener_loop():
    """Main WebSocket listener with automatic reconnection."""
    delay = 5  # initial reconnect delay (seconds)

    while True:
        try:
            print(f"[WS] Connecting to {WS_URL} …")
            async with websockets.connect(WS_URL) as ws:
                command_bus.set_ws(ws)
                delay = 5  # reset backoff on success

                # Register as an agent
                await ws.send(json.dumps({
                    "type": "register",
                    "clientType": "agent",
                    "clientId": CLIENT_ID,
                    "subscribe": [
                        "task.*",
                        "wechat.*",
                        "auto_reply.*",
                        "ai.*",
                        "action.required",
                        "system.health",
                    ],
                }))

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        print(f"[WS] Bad JSON: {raw[:80]}")
                        continue

                    # Application-level ping/pong
                    if msg.get("type") == "ping":
                        await ws.send(json.dumps({"type": "pong"}))
                        continue

                    await handle_message(msg)

        except Exception as e:
            command_bus.set_ws(None)
            print(f"[WS] Disconnected: {e}. Reconnecting in {delay}s …")
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)  # exponential backoff, cap at 60 s


async def _warn_if_no_heartbeat():
    """Warn once after 5 minutes if no agent has registered a heartbeat."""
    await asyncio.sleep(300)
    if not heartbeat_registry.is_configured():
        print(
            "\n" + "!"*60 +
            "\n[Heartbeat] WARNING: No heartbeat has been registered in 5 minutes."
            "\nExternal agents may miss real-time events."
            "\nTell your agent to call: POST http://127.0.0.1:9923/setup/heartbeat"
            "\n" + "!"*60 + "\n"
        )


async def async_main():
    command_bus.set_loop(asyncio.get_event_loop())
    event_store.load()
    heartbeat_registry.load()
    start_event_server()
    asyncio.create_task(_warn_if_no_heartbeat())
    await ws_listener_loop()


# ─────────────── entry point ───────────────

if __name__ == "__main__":
    # Install websockets if missing
    try:
        import websockets
    except ImportError:
        print("[WS Listener] Installing websockets …")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "websockets"],
            check=True
        )
        import websockets

    # Write PID so stop_server.py can clean us up
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)
    LISTENER_PID_FILE.write_text(str(os.getpid()))

    print(f"[WS Listener] Starting (PID={os.getpid()})")
    print(f"[WS Listener] Event API → http://127.0.0.1:{EVENT_SERVER_PORT}")

    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("[WS Listener] Stopped.")
    finally:
        try:
            LISTENER_PID_FILE.unlink()
        except Exception:
            pass
