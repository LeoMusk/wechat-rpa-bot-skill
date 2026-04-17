# WeChat RPA Skill Installation Guide (For OpenClaw & Agents)

This document provides instructions for an autonomous agent (like OpenClaw) to install and configure the WeChat RPA bot.

## 1. Environment Requirements

- **OS**: Windows (Required for WeChat UIAutomation).
- **WeChat Version**: **4.1.7 only** — this skill does NOT work with any other version (higher or lower).
- **Python**: 3.10+ (if running from source).

### Verifying WeChat Version
Ask the user to open WeChat → **帮助 (Help)** → **关于 (About)** and confirm the version reads exactly **4.1.7**.

If the version is wrong, the user must:
1. Uninstall the current WeChat.
2. Download and install WeChat 4.1.7 from: **https://n2b8xxdgjx.feishu.cn/wiki/Nbauw9HWsihsQ7kgjYPcfZSCnKb**
3. During installation, choose **not to auto-update** if prompted.

## 2. Agent Installation Steps

If you (the Agent) are asked to install this skill from GitHub:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/LeoMusk/wechat-rpa-bot-skill.git
   cd wechat-rpa-bot-skill
   ```

2. **Download the RPA Core Service (`service.exe`)**:
   The Python startup script expects the compiled RPA service binary in the project root.
   Download `service.exe` from the GitHub [Releases page](https://github.com/LeoMusk/wechat-rpa-bot-skill/releases) and save it to the root of this skill directory.

   ```bash
   curl -L -o service.exe https://github.com/LeoMusk/wechat-rpa-bot-skill/releases/download/v1.7.0/service.exe
   ```

3. **Install Python Dependencies** (for the startup scripts):
   ```bash
   pip install psutil requests
   ```

## 3. Configuration & Activation

The RPA service is activated via a **License Code (Activation Code)** — no `.env` file or API key configuration needed.

- Activation codes are obtained from: **www.yokoagi.com**
- The Agent will retrieve the device's machine code via API, ask the user for their Activation Code, and activate automatically at runtime.

## 4. Next Steps

Once installed, refer to `SKILL.md` for the complete service lifecycle SOP:
- Section 2.1: Starting the service (generating desktop bat scripts)
- Section 2.2: WeChat initialization (two-step flow)
- Section 2.3: Stopping the service
- Section 3: Activation flow
