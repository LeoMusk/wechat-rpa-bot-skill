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

### 2.3 Stopping the Service

The RPA service runs as a background daemon — it keeps running even after the Agent conversation ends or the browser UI is closed. This is by design, but you should help the user stop it when appropriate.

**When to suggest stopping the service:**
- The user explicitly says they're done with WeChat / don't need it anymore.
- The user says the service is using too much memory or wants to free up resources.
- Before a planned system shutdown or restart.

**How to guide the user:**
> "微信 RPA 服务目前仍在后台运行。如果您已使用完毕，可以双击桌面上的 `停止微信RPA.bat` 来关闭服务，释放系统资源。"

**If the stop bat doesn't exist on the desktop** (e.g., first time), regenerate it using the Python code in Section 2.1 Step 2.

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
python -c "import requests; requests.post('http://127.0.0.1:9922/api/chat/send_message', headers={'X-API-Key':'yoko_test'}, json={'user':'联系人昵称','message':'消息内容'}, proxies={'http': None, 'https': None})"
```

**Alternative — curl.exe:**
```bash
chcp 65001
curl.exe --noproxy "*" -X POST http://127.0.0.1:9922/api/chat/send_message -H "Content-Type: application/json" -H "X-API-Key: yoko_test" -d "{\"user\":\"联系人昵称\",\"message\":\"消息内容\"}"
```

**Avoid PowerShell `Invoke-RestMethod`** for Chinese content — it defaults to ISO-8859-1 encoding and will cause garbled characters.

### Error Handling
If an API returns `WECHAT_NOT_LOGGED_IN`, open the UI (`http://127.0.0.1:9922/`) and ask the user to log in.

---

## 6. Progressive Documentation (Agent Knowledge Base)

For complex tasks (auto-add friends, mass sending, moment posting, config schemas):
- **Read `docs/index.md`** first to discover available SOPs.
- Follow the specific `docs/*.md` file before calling related APIs.
