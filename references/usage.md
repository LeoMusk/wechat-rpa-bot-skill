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

While the Agent handles the backend logic, **WeChat requires a physical login (QR Code scan) and some configurations (SOPs, Activations) are easier via the UI.**

Once the service is started successfully, you MUST tell the user:

> "The RPA Backend is running successfully. Please open your browser and navigate to the Frontend UI: **http://127.0.0.1:9922/** to scan the WeChat QR Code or configure any missing settings. Let me know when you are done so I can proceed."

## 3. Handling API "Action Required"

When making API calls (e.g., sending a message), you might receive a `401`/`403` or a specific payload indicating WeChat is offline:
```json
{
  "success": false,
  "error_code": "WECHAT_NOT_LOGGED_IN",
  "action_required": "OPEN_UI"
}
```

If you receive this, **do not retry automatically**. Stop your current task and instruct the user to open the UI (`http://127.0.0.1:9922/`) to resolve the issue.

## 4. Activation Code

The RPA service has a built-in Activation Code (License Key) mechanism. 
- If the initialization fails due to license errors, the user must enter their Activation Code in the Frontend UI (`http://127.0.0.1:9922/`).
- The Agent should simply point the user to the UI for activation.

## 5. Using the API

After successful login and activation, you can use the REST APIs defined in `references/openapi.json`.
- **Authentication**: All API requests must include the header `X-API-Key: <WEBOT_API_KEY>`.
- **Base URL**: `http://127.0.0.1:9922`
