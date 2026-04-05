# WeChat RPA Bot Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A powerful, standalone WeChat RPA (Robotic Process Automation) skill designed specifically for AI Agents (like [OpenClaw](https://github.com/openclaw/openclaw), YokoAgent, etc.). 

This skill allows any AI Agent to autonomously install, configure, start, and control a local WeChat Desktop instance via HTTP REST APIs. It bridges the gap between LLM reasoning and real-world WeChat operations.

## 🌟 Key Features
- **Agent-Friendly**: Built from the ground up to be easily installed and invoked by AI Agents.
- **Headless Backend**: Runs silently in the background, exposing a rich set of REST APIs (`http://127.0.0.1:9922`).
- **Autonomous Initialization**: The agent can start the service and auto-bind to WeChat without human intervention.
- **Human-in-the-Loop (UI)**: Provides a local web UI for users to scan the WeChat login QR code and perform initial configurations, perfectly separating Agent logic from human operations.

## 📦 Installation (For AI Agents)

Agents can autonomously install this skill by following these steps:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/wechat-rpa-bot-skill.git
   cd wechat-rpa-bot-skill
   ```

2. **Install Python Dependencies** (for the startup script):
   ```bash
   pip install psutil requests
   ```

3. **Configure Authentication**:
   Create a `.env` file in the root directory and add the `WEBOT_API_KEY`. This token is required for the Agent to authenticate API requests.
   ```env
   WEBOT_API_KEY=your_secure_token_here
   ```

## 🚀 Usage Guide

### 1. Starting the Service
The Agent should start the RPA backend before attempting any WeChat operations. Run the provided startup script:

```bash
python scripts/start_server.py
```
*This script automatically cleans up old processes, starts the backend (`service.exe` or `server.py`), waits for the health check, and calls the initialization API.*

### 2. User Login (Human Action)
Because WeChat requires a physical QR code scan, the Agent **must** instruct the user to open the UI after the service starts:

> "The WeChat RPA service has started. Please open **http://127.0.0.1:9922/** in your browser to scan the WeChat QR Code or configure settings. Let me know when you're done!"

### 3. API Control
Once the user is logged in, the Agent can control WeChat via the REST API.
- **Base URL**: `http://127.0.0.1:9922`
- **Auth Header**: `X-API-Key: <WEBOT_API_KEY>`

**Example: Sending a Message**
```bash
curl -X POST http://127.0.0.1:9922/api/chat/send_message \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your_secure_token_here" \
     -d '{"user": "File Transfer", "message": "Hello from Agent!"}'
```

## 📚 Documentation
- **[Agent Skill Definition](SKILL.md)**: How the Agent should understand and invoke this skill.
- **[Installation Guide](references/install.md)**: Detailed environment setup instructions.
- **[Usage Guide](references/usage.md)**: How the Agent should handle WeChat offline states and UI prompts.
- **[OpenAPI Spec](references/openapi.json)**: Full API reference for WeChat control (Send messages, post moments, sync contacts, etc.).

## 🖥️ System Requirements
- **OS**: Windows 10/11 (Strictly required for WeChat UIAutomation).
- **WeChat**: WeChat Desktop Client installed.
- **Python**: 3.10+ (if running the Python startup script).

## 📄 License
This project is licensed under the MIT License.