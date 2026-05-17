# WeChat RPA 实时事件监听 (WebSocket Event Listener)

## 概述

When `start_server.py` completes successfully, it automatically starts a background WebSocket listener (`scripts/ws_listener.py`). This listener:

- Connects to `ws://127.0.0.1:9922/ws` and registers as a named Agent (`yoko-skill-agent`)
- Receives real-time events from the RPA backend (task failures, WeChat disconnects, AI config errors, login alerts, etc.)
- Stores actionable events locally
- Exposes a lightweight HTTP API on **port 9923** so you can query and acknowledge them

**The listener starts and stops automatically** alongside the RPA service — no manual management needed.

> **Reminder**: After the listener starts, you must call `POST /setup/heartbeat` (Section 2.3) so your agent platform knows to poll for events periodically. Without this step, events are captured but never acted on.

---

## 1. Checking Listener Health

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

## 2. Polling for Events

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

## 3. Acknowledging Events

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

## 4. Handling Each Event Type

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

## 5. Sending Commands via WebSocket

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

## 6. Recommended Event-Check Workflow

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

## 7. Listener Not Running?

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
