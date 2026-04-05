# WeChat RPA Skill Installation Guide (For OpenClaw & Agents)

This document provides instructions for an autonomous agent (like OpenClaw) to install and configure the WeChat RPA bot.

## 1. Environment Requirements
- **OS**: Windows (Required for WeChat UIAutomation).
- **Dependencies**: Python 3.10+ (if running from source).
- **WeChat**: The user must have WeChat Desktop installed.

## 2. Agent Installation Steps

If you (the Agent) are asked to install this skill from GitHub:
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-repo/wechat-rpa-bot-skill.git
   cd wechat-rpa-bot-skill
   ```
2. **Download the RPA Core Service (`service.exe`)**:
   The Python startup script expects the compiled RPA service binary in the project root.
   The Agent MUST download `service.exe` from the GitHub [Releases page](https://github.com/LeoMusk/wechat-rpa-bot-skill/releases) (e.g., `wechat rpa bot service-v1.7.0`) and save it to the root of this skill directory.

   ```bash
   curl -L -o service.exe https://github.com/LeoMusk/wechat-rpa-bot-skill/releases/download/v1.7.0/service.exe
   ```

3. **Install Python Dependencies** (for the startup script):
   ```bash
   pip install psutil requests
   ```

## 3. Configuration & Activation
The RPA service is activated via a License Code (Activation Code) rather than a static API key.
There is no need to create a `.env` file or configure `WEBOT_API_KEY`. 

Instead, the Agent will ask the user for an Activation Code at runtime and use the API to activate the service automatically.

## 4. Next Steps
Once installed, you can start the service. Refer to `references/usage.md` or `SKILL.md` for instructions on how to start the RPA backend and bind the activation code.
