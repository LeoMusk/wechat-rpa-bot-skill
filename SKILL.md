---
name: wechat-rpa-bot
description: Control and automate WeChat operations via RPA. Use this skill when the user wants to start the RPA server, complete WeChat login, open the UI, or send WeChat messages.
---

# WeChat RPA Bot Skill

This skill allows any Agent (like OpenClaw) to act as a WeChat assistant by hooking into the YokoWebot RPA backend. It provides autonomous installation, startup, activation, and API-based control over WeChat Desktop.

## 1. Installation & Setup (For the Agent)

If the user wants to install this skill or hasn't set it up yet:
1. Ensure the user is on **Windows** and has **WeChat Desktop** installed.
2. The Agent MUST download the core binary `service.exe` from the [GitHub Releases page](https://github.com/LeoMusk/wechat-rpa-bot-skill/releases) (e.g., `v1.7.0`) and place it in the root directory of this skill.
   ```bash
   curl -L -o service.exe https://github.com/LeoMusk/wechat-rpa-bot-skill/releases/download/v1.7.0/service.exe
   ```
3. If running from source, ensure `python` is installed.
4. The project uses an **Activation Code (License Code)** system instead of tokens. You do NOT need to configure a `.env` file.

## 2. Starting and Activating the RPA Service

**⚠️ CRITICAL ARCHITECTURE NOTE FOR SANDBOXED AGENTS (like QClaw):**
If you are running inside a restricted sandbox, you **CANNOT** see or control the user's interactive desktop (Session 1). If you try to start `service.exe` using a Python script directly, Windows will isolate it in your sandbox (Session 0). It will launch a *new, hidden* WeChat instance that loses user configurations and requires re-login every time. 

**Therefore, the standard operating procedure (SOP) for elegantly starting the service is:**

1. **Check Connection First:** Always try to ping `http://127.0.0.1:9922/api/agent/backend_status` first. If it succeeds, the service is already running on the host desktop. Skip to Step 4.
2. **Generate Desktop Launcher (`.bat`):** If the connection fails, generate a batch script directly on the user's Windows Desktop so they can launch it interactively.
   *Example Python snippet to run (ONLY GENERATE, DO NOT EXECUTE):*
   ```python
   import os
   desktop = os.path.join(os.path.expanduser("~"), "Desktop")
   bat_path = os.path.join(desktop, "启动微信RPA.bat")
   skill_dir = os.path.abspath(".")
   with open(bat_path, "w", encoding="gbk") as f:
       f.write(f"@echo off\nchcp 65001\necho 正在启动微信 RPA 服务，请稍候...\ncd /d {skill_dir}\npython scripts\\start_server.py\npause")
   ```
   
   🛑 **ABSOLUTE RULE FOR AGENT**: You are **STRICTLY FORBIDDEN** from executing `start_server.py`, the `.bat` file, or the `.ps1` file yourself using your shell tools. Do NOT use `subprocess`, `os.system`, or `powershell -Command` to start the server. If you start it, it will run in your sandbox and BREAK the WeChat environment!

3. **Prompt User & YIELD:** Tell the user:
   > "由于沙箱隔离限制，我无法直接在后台启动服务。我已在您的桌面生成了 `启动微信RPA.bat`。**请您手动双击桌面上的 `启动微信RPA.bat` 来启动服务**。启动成功后，请回复我 '已启动'。"
   
   **STOP HERE.** You MUST yield the conversation back to the user. Do NOT write a polling loop. Do NOT proceed until the user replies that they have started it.

4. **Proceed:** Once the user confirms they started it, verify the API is reachable, then continue with the user's request. **Crucially**, after the service successfully starts, you MUST proactively inform the user that a Visual UI is available:
   > "微信 RPA 服务已成功启动。如果您需要进行复杂配置或查看历史记录，我也可以帮您打开可视化前端 UI 界面。需要现在打开吗？"

## 3. UI Interaction & Software Activation

### 3.1 Software Activation
If the user has not activated the software yet, the Agent can autonomously activate it by asking the user for their **Activation Code**:
1. The Agent calls `GET /api/license/machine-code` to retrieve the device's machine code.
2. The Agent asks the user for their Activation Code.
3. The Agent calls `POST /api/license/activate` with the `activation_code` and `machine_code`.

### 3.2 Mounting and Opening the Frontend UI
The skill includes a pre-built frontend UI (located in the `webot/` directory) that is automatically served by the backend at `http://127.0.0.1:9922/`.
When the user asks to "打开UI", "配置界面", or "使用前端":

1. **Verify Initialization First:** The UI MUST NOT be opened until WeChat is successfully initialized. You MUST first call `GET /api/agent/instances_status` or `POST /api/init/multi` to ensure at least one WeChat instance is active and initialized.
   - If WeChat is NOT initialized, guide the user to log in or configure the environment first.
2. **Provide a Clickable Link ONLY:** Once initialized, you MUST provide a clickable Markdown link to the user so they can open it in their own normal browser. 
   🛑 **CRITICAL FOR SANDBOX:** Do NOT use Python (`webbrowser.open()`) or any shell commands to open the URL. If you do, it will trigger the sandbox's broken internal browser which will CRASH the entire Agent client and kill the RPA service!
   
   Always respond exactly like this:
   > "我已经为您准备好了可视化配置界面，请直接点击下方链接在您的独立浏览器中打开：
   > 👉 [打开微信 RPA 控制台](http://127.0.0.1:9922/)"

Alternatively, the Agent can inform the user:
> "The WeChat RPA service has started. Please provide your Activation Code, and I will activate the device for you. You can also open http://127.0.0.1:9922/ to enter it manually."

If the `start_server.py` output or any API returns `ENV_NOT_CONFIGURED`, the Agent MUST automatically fix it by:
1. Asking the user: "WeChat environment is not configured. Can I close your WeChat and automatically configure it?"
2. If approved, call `POST /api/system/wechat41/auto_config`.
3. Wait 5 seconds, then call `POST /api/init/multi` again.

## 4. API Usage (Agent Control)

Once the service is running, activated, and the user is logged in, the Agent can control WeChat via HTTP REST APIs.

- **Base URL**: `http://127.0.0.1:9922`
- **Authentication**: You MUST include the header `X-API-Key: yoko_test` in all API requests.
- **API Reference**: Read `references/openapi.json` for details on available endpoints (e.g., `POST /api/chat/send_message`, `POST /api/agent/mass_sending`, etc.).

### ⚠️ CRITICAL: Bypass System Proxy for localhost

If the user's machine has a system proxy enabled (e.g., VPNs running on ports like `33210` or `7890`), Agent API calls to `127.0.0.1` might be intercepted and fail!
You MUST explicitly tell your HTTP client to bypass proxies for `127.0.0.1`.

### ⚠️ CRITICAL: Chinese Encoding in API Requests (Mojibake/乱码)

If you use Windows PowerShell to call the API (e.g., `Invoke-RestMethod`), it will CORRUPT Chinese characters because PowerShell 5.1 defaults to ISO-8859-1 for string bodies, resulting in mojibake (乱码) in WeChat.

**You MUST use one of the following methods for API calls containing Chinese to ensure UTF-8 AND Proxy Bypass:**

1. **Method 1 (Recommended)**: Use Python `requests` inline (explicitly disabling proxies):
   ```bash
   python -c "import requests; requests.post('http://127.0.0.1:9922/api/chat/send_message', headers={'X-API-Key':'yoko_test'}, json={'user':'中文','message':'测试'}, proxies={'http': None, 'https': None})"
   ```
2. **Method 2**: Use `curl.exe` explicitly and set `--noproxy`:
   ```bash
   chcp 65001
   curl.exe --noproxy "*" -X POST http://127.0.0.1:9922/api/chat/send_message -H "Content-Type: application/json" -H "X-API-Key: yoko_test" -d "{\"user\":\"中文\",\"message\":\"测试\"}"
   ```
3. **Method 3**: If you must use `Invoke-RestMethod` in PowerShell, you MUST encode the body as UTF-8 bytes first:
   ```powershell
   $body = [System.Text.Encoding]::UTF8.GetBytes('{"user":"中文","message":"测试"}')
   Invoke-RestMethod -Uri "http://127.0.0.1:9922/api/chat/send_message" -Method POST -Headers @{"X-API-Key"="yoko_test"; "Content-Type"="application/json"} -Body $body
   ```

### Handling Errors
If an API returns:
```json
{
  "success": false,
  "error_code": "WECHAT_NOT_LOGGED_IN",
  "action_required": "OPEN_UI"
}
```
Stop your execution and tell the user to open the UI (`http://127.0.0.1:9922/`) to resolve the issue.

## 5. Progressive Documentation (Agent Knowledge Base)

This skill provides a set of progressive disclosure documents to help you understand complex operational scenarios (like auto-adding friends, posting moments, config schemas, etc.).
**Do NOT guess how complex features work.** When a user asks you to perform a specific task (e.g., "帮我开启自动通过好友" or "设置群发任务"), you MUST read the index document first to find the relevant SOP or schema:

- **Read `docs/index.md`** to discover available SOPs and configuration schemas for advanced features.
- Follow the instructions in the specific `docs/*.md` file before calling the related APIs.
