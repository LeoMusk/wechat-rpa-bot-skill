---
name: wechat-rpa-bot
description: Control and automate WeChat operations via RPA. Use this skill when the user wants to start the RPA server, complete WeChat login, open the UI, send WeChat messages, or manage the RPA service lifecycle.
---

# WeChat RPA Bot Skill

This skill allows any Agent (like OpenClaw) to act as a WeChat assistant by hooking into the YokoWebot RPA backend. It provides autonomous installation, startup, activation, initialization, and API-based control over WeChat Desktop.

---

## 1. Installation & Setup (For the Agent)

If the user wants to install this skill or hasn't set it up yet:
1. Ensure the user is on **Windows** and has **WeChat Desktop 4.1.7** installed (not newer, not older).
   - Version check: open WeChat → Help (帮助) → About (关于) → confirm version is **4.1.7**
   - If wrong version, download from: https://n2b8xxdgjx.feishu.cn/wiki/Nbauw9HWsihsQ7kgjYPcfZSCnKb
2. Download the core binary `service.exe` from the [GitHub Releases page](https://github.com/LeoMusk/wechat-rpa-bot-skill/releases) and place it in the root directory of this skill.
   ```bash
   curl -L -o service.exe https://github.com/LeoMusk/wechat-rpa-bot-skill/releases/download/v1.7.0/service.exe
   ```
3. Install Python dependencies (if running from source):
   ```bash
   pip install psutil requests
   ```
4. The project uses an **Activation Code** system — no `.env` file needed. Activation codes are obtained from: **www.yokoagi.com**

---

## 2. Service Lifecycle

### 2.1 Starting the RPA Service

**Architecture Note — Sandbox Isolation:**
If you are running inside a restricted sandbox (e.g., QClaw), you cannot access the user's interactive desktop (Session 1). Spawning `service.exe` directly from the sandbox will place it in an isolated session where it cannot see WeChat.

**The correct SOP (Standard Operating Procedure) is:**

**Step 1 — Check if already running:**
Always ping `http://127.0.0.1:9922/docs` first (disable proxy for localhost). If it responds, the service is already running — skip to Section 2.2 (Initialization).

**Step 2 — Generate desktop launcher scripts:**
If the service is not running, generate **both** `启动微信RPA.bat` AND `停止微信RPA.bat` on the user's Desktop. Generate both at the same time so the user has both tools ready.

> **IMPORTANT: Only GENERATE these files — do NOT execute them yourself.**

*Python code to generate both scripts (run this code, do not execute the bat files):*
```python
import os

desktop = os.path.join(os.path.expanduser("~"), "Desktop")
skill_dir = os.path.abspath(".")  # adjust to the actual skill directory path

# --- Start bat ---
start_bat = os.path.join(desktop, "启动微信RPA.bat")
if not os.path.exists(start_bat):
    with open(start_bat, "w", encoding="gbk") as f:
        f.write(
            "@echo off\n"
            "chcp 65001\n"
            "echo 正在清理旧的 RPA 进程...\n"
            f"cd /d {skill_dir}\n"
            "python scripts\\stop_server.py\n"
            "echo 正在启动微信 RPA 服务，请稍候...\n"
            "set WEBOT_BACKEND_MODE=1\n"
            "set HEADLESS_MODE=1\n"
            "set DISABLE_WEBVIEW=1\n"
            "set NO_BROWSER=1\n"
            "python scripts\\start_server.py\n"
            "pause\n"
        )
    print(f"Created: {start_bat}")

# --- Stop bat ---
stop_bat = os.path.join(desktop, "停止微信RPA.bat")
if not os.path.exists(stop_bat):
    with open(stop_bat, "w", encoding="gbk") as f:
        f.write(
            "@echo off\n"
            "chcp 65001\n"
            "echo 正在停止微信 RPA 服务...\n"
            f"cd /d {skill_dir}\n"
            "python scripts\\stop_server.py\n"
            "echo 服务已停止！\n"
            "pause\n"
        )
    print(f"Created: {stop_bat}")
```

**Step 3 — Prompt the user:**
> "由于沙箱隔离限制，我已在您的桌面生成了两个脚本：
> - `启动微信RPA.bat` — 启动服务（已内置自动清理旧进程逻辑）
> - `停止微信RPA.bat` — 服务使用完毕后关闭
>
> **请先双击桌面上的 `启动微信RPA.bat` 来启动服务**，启动成功后请回复我"已启动"。"

**Step 4 — Verify and proceed:**
After the user confirms, ping `http://127.0.0.1:9922/docs` (with proxy disabled for localhost) to verify the service is reachable, then proceed to Section 2.2.

---

### 2.2 WeChat Initialization (Two-Step SOP)

**CRITICAL RULES — read carefully:**
- `auto_config` is a **destructive operation** (it kills WeChat and restarts it). **NEVER** call `POST /api/system/wechat41/auto_config` unless Step 1 below explicitly returns `ENV_NOT_CONFIGURED`.
- Always call `POST /api/init/multi` **without** auto_config first (Step 1).

**Standard initialization flow:**

```
Step 1: POST /api/init/multi
        Headers: X-API-Key: yoko_test
        Body: {}

        → success (instances returned)       → Done. WeChat is initialized.
        → error_code: UNAUTHORIZED           → Go to Section 3 (Activation).
        → code: ENV_NOT_CONFIGURED           → Go to Step 2 below.
        → other error                        → Report to user, suggest restarting service.

Step 2: (Only if ENV_NOT_CONFIGURED)
        Ask user: "微信环境尚未配置，我需要短暂关闭并重启您的微信来完成配置，是否继续？"
        
        If user agrees:
          a. POST /api/system/wechat41/auto_config
             (WeChat will be killed and restarted — this is expected)
          b. Wait 5 seconds for WeChat to restart
          c. Warn the user:
             "配置过程中 Windows 讲述人（屏幕阅读器）可能会短暂启动并发出声音，
              这是正常现象。配置完成后如果仍有声音，请告诉我"关闭讲述人"，
              我会帮您关闭。"
          d. POST /api/init/multi again → should return success now.
```

### 2.3 Heartbeat Setup — MANDATORY After Every Service Start

**This step is required.** Without it, real-time events (AI config errors, task failures, WeChat disconnects) will pile up silently and no agent will process them.

Call `POST /setup/heartbeat` immediately after the service starts:

```python
import requests

r = requests.post(
    "http://127.0.0.1:9923/setup/heartbeat",
    json={"intervalSeconds": 60},   # adjust to your platform's minimum interval
    proxies={"http": None, "https": None},
    timeout=5,
)
cfg = r.json()
print(cfg["heartbeatPrompt"])   # ← paste this into your agent's heartbeat config
print(cfg["setupGuide"])        # ← step-by-step instructions for your platform
```

**What the response contains:**

```json
{
  "registered": true,
  "intervalSeconds": 60,
  "heartbeatPrompt": "...",   ← the full prompt your heartbeat should run
  "setupGuide": "..."         ← how to configure it in OpenClaw / QClaw
}
```

**How to configure in OpenClaw / QClaw:**

1. Open Agent Settings → Heartbeat (心跳)
2. Set interval to `60` seconds (or whatever `intervalSeconds` you registered)
3. Paste the `heartbeatPrompt` value as the heartbeat trigger prompt
4. Save and enable

Once configured, the agent will automatically wake up every 60 seconds, check for pending events, process them (notify the user, send commands), and go back to sleep — **no user intervention needed**.

**Check registration status at any time:**

```python
r = requests.get("http://127.0.0.1:9923/setup/heartbeat",
                 proxies={"http": None, "https": None})
print(r.json())
# {"configured": true, "intervalSeconds": 60, "registeredAt": "2025-04-24T10:00:00"}
```

---

### 2.4 Stopping the Service

The RPA service runs as a background daemon — it keeps running even after the Agent conversation ends or the browser UI is closed. This is by design, but you should help the user stop it when appropriate.

**When to suggest stopping the service:**
- The user explicitly says they're done with WeChat / don't need it anymore.
- The user says the service is using too much memory or wants to free up resources.
- Before a planned system shutdown or restart.

#### ⚠️ Sandbox Cannot Kill User-Session Processes — CRITICAL

**If you are running inside a sandbox (e.g., QClaw), you CANNOT kill `service.exe` processes that were started by the user interactively (via the desktop `.bat` file).**

This is a Windows Session Isolation security boundary:
- Desktop `.bat` → `service.exe` runs in **Session 1** (user's interactive desktop)
- Sandbox agent → runs in **Session 0** or a restricted session
- `taskkill /F /PID <pid>` across sessions = **Access Denied** — this will ALWAYS fail silently

**Therefore:**
- **NEVER attempt to kill `service.exe` using `taskkill`, `stop_server.py`, or PowerShell `Stop-Process` from within the sandbox.** It will fail and waste time.
- The **only reliable way to stop the service** is to ask the user to run `停止微信RPA.bat` on their desktop (which runs in Session 1 and has the correct permissions).

**How to guide the user when stop is needed:**
> "由于沙箱权限限制，我无法直接关闭在您桌面上启动的 RPA 服务。请双击桌面上的 `停止微信RPA.bat` 来安全关闭服务，完成后请告诉我。"

**If the stop bat doesn't exist on the desktop** (e.g., first time), regenerate it using the Python code in Section 2.1 Step 2.

#### Avoid Running Two Instances

Two `service.exe` instances can arise when the agent mistakenly believes the service is down (due to API blocking during a task — see Section 5) and starts a second one. **Always check the port first before starting a new instance.** If two instances exist and both are unkillable from sandbox, instruct the user to open Task Manager, end both `service.exe` tasks, then re-run `启动微信RPA.bat`.

**If the user is experiencing port 9922 occupied on next startup:**
The start bat already handles this — it calls `stop_server.py` before starting, which cleans up any orphaned processes. Just ask the user to run `启动微信RPA.bat` again.

---

## 3. Activation

If `POST /api/init/multi` returns `UNAUTHORIZED`, the software needs to be activated.

1. Call `GET /api/license/machine-code` to retrieve the device's machine code.
2. Tell the user:
   > "软件尚未激活。请前往 **www.yokoagi.com** 获取激活码，获取后告诉我，我将为您完成自动激活。"
3. After the user provides the Activation Code, call `POST /api/license/activate` with:
   ```json
   { "activation_code": "<user_provided>", "machine_code": "<from_step_1>" }
   ```
4. On success, call `POST /api/init/multi` again to complete initialization.

---

## 4. Opening the Frontend UI

The skill includes a pre-built frontend UI served at `http://127.0.0.1:9922/`.

**Open UI only after WeChat is successfully initialized** (Section 2.2 must return success first). Before initialization, the UI shows "微信掉线" and is non-functional.

When the user asks to open the UI:
```python
import webbrowser
webbrowser.open('http://127.0.0.1:9922/')
```

Always also provide a fallback link in the response:
> "可视化控制台已为您准备好：👉 [打开微信 RPA 控制台](http://127.0.0.1:9922/)
> 若浏览器未自动弹出，请手动点击上方链接。"

### Handling "Close Narrator" (关闭讲述人)
When the user reports hearing Narrator (屏幕阅读器) sounds and wants it closed:
```bat
taskkill /F /IM Narrator.exe /T
```

---

## 5. API Usage

Once initialized, control WeChat via HTTP REST APIs.

- **Base URL**: `http://127.0.0.1:9922`
- **Auth Header**: `X-API-Key: yoko_test` (required on all requests)
- **API Reference**: See `references/openapi.json` for all endpoints.

### Bypass System Proxy for localhost
If the user has a system proxy (VPN on port 33210, 7890, etc.), localhost calls may be intercepted. Always disable proxy when calling `127.0.0.1`.

### Chinese Encoding in API Requests
**Recommended — Python requests (auto UTF-8, proxy disabled):**
```bash
# 单微信实例（常见场景）
python -c "import requests; requests.post('http://127.0.0.1:9922/api/chat/send_message', headers={'X-API-Key':'yoko_test'}, json={'user':'联系人昵称','message':'消息内容'}, proxies={'http': None, 'https': None})"

# 多微信实例（指定发送方账号）
python -c "import requests; requests.post('http://127.0.0.1:9922/api/chat/send_message', headers={'X-API-Key':'yoko_test'}, json={'user':'联系人昵称','message':'消息内容','account_id':'wxid_xxx'}, proxies={'http': None, 'https': None})"
```

> `user` 是**接收方**联系人的备注名/昵称；`account_id` 是**发送方**微信实例标识，仅多实例时需要传入。

**Alternative — curl.exe:**
```bash
chcp 65001
curl.exe --noproxy "*" -X POST http://127.0.0.1:9922/api/chat/send_message -H "Content-Type: application/json" -H "X-API-Key: yoko_test" -d "{\"user\":\"联系人昵称\",\"message\":\"消息内容\"}"
```

**Avoid PowerShell `Invoke-RestMethod`** for Chinese content — it defaults to ISO-8859-1 encoding and will cause garbled characters.

### Send Message Best Practices

**⚠️ CRITICAL: 发送消息时直接使用用户提供的联系人名称（备注名、昵称或微信号），无需提前查询联系人或获取wxid。RPA服务会自动在通讯录中查找匹配的好友。**

**正确做法：**
- 用户说"给Charlie发消息" → 直接使用 `"user": "Charlie"` 调用发送接口
- 用户说"给张三发消息" → 直接使用 `"user": "张三"` 调用发送接口

**常见错误（务必避免）：**
- ❌ 不要先调用任何接口查询联系人列表来获取wxid
- ❌ 不要因为没有完全匹配的名称就使用相似名称替代（如把"Charlie"换成"charry"）
- ❌ 不要假设必须知道微信号才能发送消息

RPA的`send_message`接口支持模糊匹配，只要通讯录中有这个好友，直接使用用户提供的名称即可。

### Long-Running Tasks & API Blocking — CRITICAL

**The RPA service runs all automation tasks on the main thread. This means the HTTP server is completely unresponsive while a task is executing. This is NORMAL, not a bug.**

**Two very different states that look similar:**

| Symptom | What it means | What to do |
|---|---|---|
| `Connection refused` / `port not listening` | Service is DOWN | Safe to restart |
| `Request hangs / times out` | Service is BUSY executing a task | **Wait — do NOT restart** |

**How to distinguish them in Python:**
```python
import socket, requests

def service_state():
    """Returns 'down', 'busy', or 'ready'."""
    s = socket.socket()
    s.settimeout(2)
    try:
        s.connect(('127.0.0.1', 9922))
        s.close()
    except ConnectionRefusedError:
        return 'down'   # Port not listening → service truly crashed
    except Exception:
        return 'down'
    finally:
        s.close()
    # Port is open, now try a quick HTTP check
    try:
        r = requests.get('http://127.0.0.1:9922/docs',
                         timeout=5, proxies={'http': None, 'https': None})
        return 'ready'
    except requests.exceptions.Timeout:
        return 'busy'   # Port open but HTTP hung → task in progress
    except Exception:
        return 'busy'
```

**Expected wait times for common tasks (do NOT interrupt):**

| Task | Expected duration |
|---|---|
| Send message | 5–30 seconds |
| Auto-config (`auto_config`) | 30–90 seconds |
| Add friend / pass friend request | 30–120 seconds |
| Post Moment | 30–120 seconds |
| Mass send / batch operations | Up to 10 minutes |

**Rules:**
- **NEVER kill or restart the service solely because an API call hangs or times out.** Check the port first.
- Only restart if `service_state()` returns `'down'` (connection refused).
- If `'busy'`, wait and retry after the expected duration has passed. Inform the user that a task is in progress.
- If a task has been running longer than **15 minutes** and the port is still open, only then should you ask the user whether to force-stop.

### Error Handling
If an API returns `WECHAT_NOT_LOGGED_IN`, open the UI (`http://127.0.0.1:9922/`) and ask the user to log in.

---

## 6. Progressive Documentation (Agent Knowledge Base)

For complex tasks (auto-add friends, mass sending, moment posting, config schemas):
- **Read `docs/index.md`** first to discover available SOPs.
- Follow the specific `docs/*.md` file before calling related APIs.

---

## 7. Real-time Event Listener (WebSocket)

### Overview

When `start_server.py` completes successfully, it automatically starts a background WebSocket listener (`scripts/ws_listener.py`). This listener:

- Connects to `ws://127.0.0.1:9922/ws` and registers as a named Agent (`yoko-skill-agent`)
- Receives real-time events from the RPA backend (task failures, WeChat disconnects, AI config errors, login alerts, etc.)
- Stores actionable events locally
- Exposes a lightweight HTTP API on **port 9923** so you can query and acknowledge them

**The listener starts and stops automatically** alongside the RPA service — no manual management needed.

> **Reminder**: After the listener starts, you must call `POST /setup/heartbeat` (Section 2.3) so your agent platform knows to poll for events periodically. Without this step, events are captured but never acted on.

---

### 7.1 Checking Listener Health

```python
import requests
r = requests.get("http://127.0.0.1:9923/health", proxies={"http": None, "https": None})
print(r.json())
# {
#   "status": "running",
#   "connected": true,        ← WebSocket connection to backend
#   "pendingEvents": 2,       ← unacknowledged events in queue
#   "urgentEvents": 1,        ← urgent-severity events needing immediate attention
#   "timestamp": 1715000000000
# }
```

If `connected` is `false`, the listener is running but has temporarily lost the WebSocket connection to the RPA backend (auto-reconnect is in progress).

---

### 7.2 Polling for Events

**Always check for pending events at the start of any task**, especially after the service has been running unattended.

```python
import requests

proxies = {"http": None, "https": None}

# Get all pending events
r = requests.get("http://127.0.0.1:9923/events", proxies=proxies)
data = r.json()
# { "events": [...], "count": 3 }

# Filter by severity (info | warning | error | urgent)
r = requests.get("http://127.0.0.1:9923/events?severity=urgent", proxies=proxies)
```

**Each event object:**
```json
{
  "id": "a1b2c3d4e5f6",
  "event": "task.failed",
  "severity": "warning",
  "context": { "taskId": "mass_sending_xyz", "taskType": "mass_sending" },
  "payload": {
    "errorCode": "ERR_TASK_FAILED",
    "errorMessage": "群发任务失败：微信频率限制",
    "isRetryable": true
  },
  "actions": [
    { "actionId": "retry", "command": "task.retry", "params": { "taskId": "mass_sending_xyz" } },
    { "actionId": "abort", "command": "task.abort", "params": { "taskId": "mass_sending_xyz" } }
  ],
  "correlationId": "corr_mass_sending_xyz_run1",
  "receivedAt": "2025-04-24T10:30:00.000",
  "acknowledged": false
}
```

**Severity levels:**

| Severity | Events | What to do |
|----------|--------|------------|
| `info` | `task.started`, `task.completed` | Log; no action required |
| `warning` | `task.failed`, `wechat.disconnected`, `ai.service_error` | Notify user; may need action |
| `error` | `wechat.error`, `ai.config_error` | Notify user; must be fixed |
| `urgent` | `wechat.manual_action_required`, `action.required` | Act immediately |

---

### 7.3 Acknowledging Events

After processing an event, acknowledge it to remove it from the queue:

```python
event_id = "a1b2c3d4e5f6"
r = requests.post(
    f"http://127.0.0.1:9923/events/{event_id}/ack",
    proxies={"http": None, "https": None}
)
# { "success": true, "eventId": "a1b2c3d4e5f6" }
```

---

### 7.4 Handling Each Event Type

#### `urgent` — Act immediately

**`wechat.manual_action_required`** (10-second window):
```
→ Tell the user IMMEDIATELY: "微信登录需要手动操作！请在10秒内点击微信头像"
→ The listener has already shown a Windows toast notification.
→ Acknowledge the event after notifying the user.
→ Do NOT send any WebSocket command — just wait for the user.
```

**`action.required`** (timeoutSeconds window, usually 25 s):
```
→ Read payload.pendingContent (the AI-generated reply)
→ Read payload.userQuestion (what the user asked)
→ Decide: approve or reject
→ Send the command via POST /ws/command (see 7.5)
→ Acknowledge the event
```

#### `error` — User must fix the configuration

**`ai.config_error`**:
```
→ Tell the user the error: payload.errorMessage
→ Tell the user how to fix it: payload.configKey
→ Acknowledge the event
→ Note: related AI features will keep failing until the user fixes the config
```

**`wechat.error`**:
```
→ Tell the user: "账号 {context.accountNickname} 出现严重错误，请检查微信"
→ Optionally send query.accounts command (see 7.5) to get current account states
→ Acknowledge the event
```

#### `warning` — Notify user; decide on action

**`task.failed`**:
```
→ Read payload.errorMessage and payload.isRetryable
→ If isRetryable: ask user whether to retry or abort
  → User says retry: send task.retry command (see 7.5)
  → User says abort: send task.abort command (see 7.5)
→ If NOT isRetryable: inform user the task has permanently failed
→ Acknowledge the event
```

**`wechat.disconnected`**:
```
→ Tell the user: "账号 {context.accountNickname} 已掉线，服务正在自动重连"
→ No command needed — auto-reconnect is in progress
→ Wait for wechat.reconnected (severity=info) to confirm it's back
→ Acknowledge the event
```

#### `info` — Log and acknowledge

**`task.started`**, **`task.completed`**:
```
→ Log the event for your own tracking
→ Acknowledge immediately (no further action needed)
```

---

### 7.5 Sending Commands via WebSocket

Use `POST /ws/command` to send instructions to the RPA backend through the listener's WebSocket connection. This is the **only way** to respond to `action.required` events.

```python
import requests

proxies = {"http": None, "https": None}

# Approve an action.required event
requests.post("http://127.0.0.1:9923/ws/command", proxies=proxies, json={
    "command": "action.approve",
    "correlationId": "<event.correlationId>",   # from the event
    "params": {
        "eventId": "<event.payload.eventId>",   # from the event payload
        "taskId": "<event.context.taskId>",
        "sessionName": "<event.payload.targetSession>"
    }
})

# Reject an action.required event
requests.post("http://127.0.0.1:9923/ws/command", proxies=proxies, json={
    "command": "action.reject",
    "correlationId": "<event.correlationId>",
    "params": {
        "eventId": "<event.payload.eventId>",
        "taskId": "<event.context.taskId>",
        "sessionName": "<event.payload.targetSession>"
    }
})

# Abort a failed task
requests.post("http://127.0.0.1:9923/ws/command", proxies=proxies, json={
    "command": "task.abort",
    "params": { "taskId": "<context.taskId>" }
})

# Retry a failed task
requests.post("http://127.0.0.1:9923/ws/command", proxies=proxies, json={
    "command": "task.retry",
    "params": { "taskId": "<context.taskId>" }
})

# Query all current account states
requests.post("http://127.0.0.1:9923/ws/command", proxies=proxies, json={
    "command": "query.accounts",
    "params": {}
})
```

**Response:**
```json
{ "success": true, "commandId": "cmd_a1b2c3d4" }
```
If `success` is `false`, the WebSocket is not connected — retry after a few seconds.

---

### 7.6 Recommended Event-Check Workflow

**At the start of any agent session** (or after returning from a long wait):

```python
import requests

proxies = {"http": None, "https": None}

def handle_pending_events():
    """Process all pending events before proceeding with user tasks."""
    try:
        r = requests.get("http://127.0.0.1:9923/events", proxies=proxies, timeout=3)
    except Exception:
        return  # Listener not running (service not started yet)

    events = r.json().get("events", [])
    if not events:
        return

    for ev in events:
        event_type = ev["event"]
        severity = ev["severity"]
        payload = ev.get("payload", {})
        context = ev.get("context", {})

        if severity == "urgent":
            if event_type == "wechat.manual_action_required":
                # ← CRITICAL: tell the user immediately
                print(f"⚠️ 紧急：{payload.get('message')}")

            elif event_type == "action.required":
                session = payload.get("targetSession", "?")
                content = payload.get("pendingContent", "")
                # ← Present to user or auto-decide based on riskLevel
                print(f"待审核回复 [{session}]: {content[:100]}")

        elif severity == "error":
            if event_type == "ai.config_error":
                print(f"❌ AI配置错误: {payload.get('errorMessage')}")
                print(f"   修复方式: {payload.get('configKey')}")
            elif event_type == "wechat.error":
                print(f"❌ 账号异常: {context.get('accountNickname')}")

        elif severity == "warning":
            if event_type == "task.failed":
                print(f"⚠️ 任务失败: {context.get('taskId')} — {payload.get('errorMessage')}")
            elif event_type == "wechat.disconnected":
                print(f"⚠️ 账号掉线: {context.get('accountNickname')}（自动重连中）")

        # Acknowledge processed event
        requests.post(
            f"http://127.0.0.1:9923/events/{ev['id']}/ack",
            proxies=proxies, timeout=3
        )
```

---

### 7.7 Listener Not Running?

If port 9923 is not accessible:

1. **Service not started yet** — Run `启动微信RPA.bat` first (Section 2.1).
2. **Listener crashed** — The service is still running but the listener died. Run this once to restart it:
   ```python
   import subprocess, sys, os
   skill_dir = os.path.abspath(".")  # adjust to actual skill directory
   subprocess.Popen(
       [sys.executable, os.path.join(skill_dir, "scripts", "ws_listener.py")],
       creationflags=0x00000008  # DETACHED_PROCESS
   )
   ```
3. **Port conflict** — Another process is using 9923. Check with `netstat -ano | findstr 9923`.
