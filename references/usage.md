# Usage & Operation Guide (For Agents)

This document provides instructions on how to start the WeChat RPA bot and how to interact with its frontend UI.

## 1. Starting the Service

The agent must start the RPA backend before making any WeChat API calls. The backend acts as a bridge between the agent and WeChat Desktop.

Run the provided script:
```bash
python scripts/start_server.py
```

This script will:
- Clean up any zombie processes from previous runs.
- Start the RPA service (`service.exe` or `server.py`).
- Wait for the API to become responsive on `http://127.0.0.1:9922`.
- Automatically initialize the WeChat connection via `POST /api/init/multi`.

## 2. Directing the User to the UI

While the Agent handles the backend logic, **the software must be activated via an Activation Code, and some configurations (SOPs) are easier via the UI.**

Once the service is started successfully, you MUST tell the user:

> "The RPA Backend is running successfully. Please open your browser and navigate to the Frontend UI: **http://127.0.0.1:9922/** to enter your Activation Code or configure any missing settings. Let me know when you are done so I can proceed."

## 3. Handling API "Action Required"

When making API calls, you might receive a payload indicating WeChat is offline:
```json
{
  "success": false,
  "error_code": "WECHAT_NOT_LOGGED_IN",
  "action_required": "OPEN_UI"
}
```
If you receive this, **do not retry automatically**. Stop your current task and instruct the user to open the UI (`http://127.0.0.1:9922/`) to resolve the issue.

### 3.1 Handling `ENV_NOT_CONFIGURED`
If the initialization or any API returns `{"code": "ENV_NOT_CONFIGURED"}`:
1. The WeChat debug environment variables are missing.
2. The Agent **must** ask the user: "Can I automatically configure your WeChat environment? This will restart your WeChat."
3. Once the user approves, the Agent MUST call `POST /api/system/wechat41/auto_config` to inject variables.
4. Wait 5 seconds for WeChat to restart, then call `POST /api/init/multi` to bind the instance.

## 4. Activation Code

The RPA service has a built-in Activation Code (License Key) mechanism. 
- If the software is not activated, the Agent can directly ask the user for their Activation Code.
- Once provided, the Agent can automatically activate it by calling `GET /api/license/machine-code` and then `POST /api/license/activate` with the `activation_code` and `machine_code`.
- Alternatively, the user can enter their Activation Code in the Frontend UI (`http://127.0.0.1:9922/`).

## 5. Using the API

After successful login and activation, you can use the REST APIs defined in `references/openapi.json`.
- **Authentication**: All API requests MUST include the header `X-API-Key: yoko_test`.
- **Base URL**: `http://127.0.0.1:9922`
