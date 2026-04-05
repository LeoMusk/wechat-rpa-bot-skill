---
name: wechat-rpa-bot
description: Control and automate WeChat operations via RPA. Use this skill when the user wants to start the RPA server, complete WeChat login, open the UI, or send WeChat messages.
---

# WeChat RPA Bot Skill

This skill allows any Agent (like OpenClaw) to act as a WeChat assistant by hooking into the YokoWebot RPA backend. It provides autonomous installation, startup, activation, and API-based control over WeChat Desktop.

## 1. Installation & Setup (For the Agent)

If the user wants to install this skill or hasn't set it up yet:
1. Ensure the user is on **Windows** and has **WeChat Desktop** installed.
2. The user must have a valid `WEBOT_API_KEY` (Token) for the Agent to authenticate. Ask the user to create a `.env` file in the project root containing:
   ```env
   WEBOT_API_KEY=your_token_here
   ```
3. If running from source, ensure `python` is installed.

## 2. Starting and Activating the RPA Service

To start the RPA backend and automatically initialize the WeChat connection, run the provided startup script:

```bash
python scripts/start_server.py
```

**What this script does:**
- Cleans up any zombie processes or port conflicts (9922).
- Starts the RPA backend in the background (`--no-ui` mode).
- Waits for the health check.
- **Automatically calls the `/api/init/multi` endpoint** to bind to WeChat and perform RPA initialization (using the `WEBOT_API_KEY`).

*Note: The script will exit once the service is running successfully in the background.*

## 3. UI Interaction & User Login

The RPA service is headless for the Agent, but requires the user to log in to WeChat manually via a QR code. 
Once the server is running, you **MUST** inform the user:

> "The WeChat RPA service has started. Please open the Frontend UI in your browser at http://127.0.0.1:9922/ to complete the WeChat login (scan the QR code) or perform any initial configurations. Let me know when you are done!"

If the `start_server.py` output mentions `ENV_NOT_CONFIGURED`, remind the user to configure the WeChat environment via the UI or let you know so you can run the auto-config API.

## 4. API Usage (Agent Control)

Once the service is running and the user is logged in, the Agent can control WeChat via HTTP REST APIs.

- **Base URL**: `http://127.0.0.1:9922`
- **Authentication**: Include header `X-API-Key: <WEBOT_API_KEY>` in all requests.
- **API Reference**: Read `references/openapi.json` for details on available endpoints (e.g., `POST /api/chat/send_message`, `POST /api/agent/mass_sending`, etc.).

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
