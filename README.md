# WeChat RPA Bot Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

这是一个专为 AI 智能体（Agent，如 [OpenClaw](https://github.com/openclaw/openclaw)、YokoAgent 等）设计的、强大且独立的微信 RPA（机器人流程自动化）技能。

该技能允许任何 AI 智能体通过 HTTP REST API 自主安装、配置、启动和控制本地微信桌面端实例。它弥合了大语言模型（LLM）推理与真实世界微信操作之间的鸿沟。

## 🌟 核心特性

- **智能体友好 (Agent-Friendly)**：从底层开始专门针对 AI 智能体的轻松安装和调用而构建。
- **无头后端 (Headless Backend)**：在后台静默运行，暴露出丰富的 REST API 接口（`http://127.0.0.1:9922`）。
- **自主初始化 (Autonomous Initialization)**：智能体可以在无需人工干预的情况下启动服务并自动绑定到微信。
- **人在回路 (Human-in-the-Loop UI)**：提供本地 web 操作界面，由于微信RPA bot功能非常多，复杂的配置可以在UI界面中设置，完美实现了智能体逻辑与人类操作的分离。

## 📦 安装指南（面向 AI 智能体）

智能体可以通过以下步骤自主安装此技能：

1. **克隆代码库**：
   ```bash
   git clone [https://github.com/YOUR_USERNAME/wechat-rpa-bot-skill.git](https://github.com/YOUR_USERNAME/wechat-rpa-bot-skill.git)
   cd wechat-rpa-bot-skill
2. **下载核心服务组件 (`service.exe`)**：
   此技能依赖 RPA 后端服务。智能体需要从本仓库的 [Releases](https://github.com/LeoMusk/wechat-rpa-bot-skill/releases) 页面下载 `service.exe`（如 `wechat rpa bot service-v1.7.0` 中的附件），并将其放置在 `wechat-rpa-bot-skill` 根目录下。

   *Agent 可以使用类似以下的命令自动下载（注意替换为最新的 release URL）：*
   ```bash
   curl -L -o service.exe https://github.com/LeoMusk/wechat-rpa-bot-skill/releases/download/v1.7.0/service.exe
   ```

3. **安装 Python 依赖（用于启动脚本）**：

```bash
pip install psutil requests
```
4. **无需额外配置认证（Token）**：
   现在项目采用**激活码 (Activation Code)**方式认证。智能体只需在服务启动后，引导用户提供激活码，并直接调用自带的激活接口完成绑定，无需用户手动修改环境变量。

## 🚀 使用指南

### 1. 启动服务
在尝试进行任何微信操作之前，智能体应该先启动 RPA 后端服务。运行提供的启动脚本：

```bash
python scripts/start_server.py
```
此脚本会自动清理旧进程，启动后端服务（service.exe 或 server.py），并等待健康检查完成。

### 2. 软件激活 (Agent 自动操作)
服务启动后，如果未激活，智能体（如 OpenClaw）可以引导用户提供**激活码**。
智能体获取到激活码后，可以直接调用自带的 REST API 工具完成设备激活：
1. 调用 `GET /api/license/machine-code` 获取当前机器码。
2. 调用 `POST /api/license/activate` 传入 `activation_code` 和 `machine_code` 激活。

> 话术参考："微信RPA服务已启动，请提供您的激活码，我将为您自动完成设备绑定。"

### 3. API 控制
激活并登录成功后，智能体即可通过 REST API 控制微信。

- 基础 URL (Base URL)：`http://127.0.0.1:9922`
- 认证请求头 (Auth Header)：所有请求必须携带 `X-API-Key: yoko_test`

示例：发送消息（⚠️ 必须注意中文编码）

> **重要提示**：Windows PowerShell 的 `Invoke-RestMethod` 默认以 ISO-8859-1 发送字符串，会导致微信发送中文乱码。智能体必须使用 `curl.exe` 或 Python `requests` 来调用接口。

```bash
curl.exe -X POST http://127.0.0.1:9922/api/chat/send_message \
     -H "Content-Type: application/json" \
     -H "X-API-Key: yoko_test" \
     -d "{\"user\": \"文件传输助手\", \"message\": \"你好，这是来自智能体的消息！\"}"
```
📚 微信RPA机器人操作文档
- <a href="https://n2b8xxdgjx.feishu.cn/wiki/DgLlwBoV4ioFbpkG8LDcz6VjnAf" target="_blank">[微信RPA机器人操作文档]</a>
- <a href="https://www.yokoagi.com/" target="_blank">微信AI销售机器人官网</a>
