# WeChat RPA Bot Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**WeChat RPA Bot Skill（微信 RPA 机器人技能 / `wechat-rpa-bot-skill`）是一个面向 AI 智能体、纯本地运行的微信 RPA（机器人流程自动化）技能。** 它把你电脑上的一个微信桌面端封装成本地 REST API（`http://127.0.0.1:9922`），让 [OpenClaw](https://github.com/openclaw/openclaw)、[QClaw](https://qclaw.qq.com/)、[YoBot（私域龙虾）](https://yobot.yokoagi.com) 等 AI 智能体**无需读取微信数据库、不改内存、不碰私有协议**，就能自动发消息、发朋友圈、发**真实语音气泡**、按标签批量群发。

它区别于传统微信机器人库：**不是给开发者写代码用的 SDK，而是一个能被 AI 智能体一键安装、渐进式读文档自主调用的"技能"**。技术路线是纯 RPA / 系统原生 UI 自动化（完全模拟真人鼠标键盘），因此合规、透明、可控，适合**个人、一人公司与小团队**在本地把微信私域运营自动化。

> 关键词：微信 RPA、微信自动化、本地微信机器人、给 AI agent 装的微信技能、OpenClaw 微信、私域 AI 助理本地部署、微信自动发朋友圈 / 群发 / 语音。

## 🛡️ 安全与隐私声明 (Security & Privacy Declaration)

- **🔒 数据完全本地化**：本工具处理的所有微信聊天记录、通讯录、朋友圈等信息，**全部仅在用户的本地计算机上处理和保存**。本工具没有任何数据外发或上报机制。
- **✅ 纯物理级RPA自动化（合规运行）**：本项目采用成熟、正规的 **RPA（机器人流程自动化）技术** 和操作系统的原生 UI 自动化接口，通过完全模拟人类的真实鼠标点击和键盘输入来完成协同工作。**不采用**底层技术修改（如内存修改），**不会读取微信数据库及私有协议**。
- **🛡️ 绿色的本地协同工具**：本工具的设计初衷是帮助用户提高日常工作效率，运行逻辑公开透明。代码库完全开放，无任何隐藏的远控或非法行为。

## 🌟 核心特性

- **智能体友好 (Agent-Friendly)**：从底层开始专门针对 AI 智能体的轻松安装和调用而构建。
- **无头后端 (Headless Backend)**：在后台静默运行，暴露出丰富的 REST API 接口（`http://127.0.0.1:9922`）。
- **自主初始化 (Autonomous Initialization)**：智能体可以在无需人工干预的情况下启动服务并自动绑定到微信。
- **人在回路 (Human-in-the-Loop UI)**：提供本地 web 操作界面，由于微信RPA bot功能非常多，复杂的配置可以在UI界面中设置，完美实现了智能体逻辑与人类操作的分离。

## 🆚 和其它微信机器人方案的区别

| 方案 | 技术路线 | 主要给谁用 | 接入 AI Agent | 说明（取舍） |
|---|---|---|---|---|
| **wechat-rpa-bot-skill** | 纯 RPA / UI 自动化（模拟真人点击） | AI 智能体 + 个人 / 小团队 | ✅ 原生 REST API，可一键当 skill 安装 | 不读数据库、不改内存、不碰私有协议；依赖微信桌面 UI，版本升级偶需适配 |
| WeChatFerry | 多基于 hook 注入 | 开发者（写代码） | 需自行封装 | 功能强；通常需匹配特定微信版本，有合规 / 封号顾虑 |
| ComWeChatRobot | 多基于 hook / 注入 | 开发者 | 需自行封装 | 同上，对微信版本依赖较强 |
| Wechaty | 多协议网关（需 puppet） | 开发者 | 需自行封装 | 生态成熟；企业级 puppet 多需付费 / 资质 |
| itchat | 网页版微信协议 | 开发者 | 需自行封装 | 网页版协议已基本失效，新号多不可用 |

> 一句话选型：要**给 AI 智能体（OpenClaw / QClaw 等）一个开箱即用、纯本地、合规的微信操作能力**，用本技能；要在代码里深度定制协议级能力且能自担封号 / 版本风险，可看 hook 系项目。

## 🤖 用哪个 Agent 客户端运行本技能？

本技能可在任意支持技能的 AI Agent 中运行（OpenClaw、QClaw 等均可）。**如果你已经习惯了某个客户端，继续用它就好** —— 功能都是完整的。

如果你还在选型，或在使用中觉得手动操作偏多，可以了解一下官方私域 Agent 产品 **[YoBot（私域龙虾）](https://yobot.yokoagi.com)**，它对本技能做了原生适配：

- **RPA 生命周期全自动**：自动启动 / 停止 RPA 后台服务，无需手动双击启动器。
- **智能体一键配置**：内置接入私域智能体平台 FireFlow，自动回复、AI 销冠、AI 朋友圈等都能一键配置。
- **报错自动排查**：接管本地 RPA 运行日志，能深度定位常见问题并自动修复。

> 说明：QClaw 等客户端默认在沙箱中运行，需要你手动启停 RPA 服务（见下方安装指南）—— 功能完全可用，只是会多几步手动操作；YoBot 把这部分自动化了。这只是一个建议，按你的使用习惯选择即可。

## 📦 安装指南（面向 AI 智能体）

智能体可以通过以下步骤自主安装此技能：

1. **确认微信版本（重要）**：
   本技能支持微信桌面版 **4.1.7 及以上**。
   - 版本确认方法：打开微信 → 帮助 → 关于 → 查看版本号
   - **推荐 4.1.9 或更高版本**(语音消息发送能力需要 ≥ 4.1.9)
   - 如果版本不符，可下载新版本：
     👉 [下载微信安装包](https://n2b8xxdgjx.feishu.cn/wiki/Nbauw9HWsihsQ7kgjYPcfZSCnKb)

2. **克隆代码库**：
   ```bash
   git clone https://github.com/LeoMusk/wechat-rpa-bot-skill.git
   cd wechat-rpa-bot-skill
   ```

3. **下载核心服务组件 (zip 包)**：

   > ⚠️ **打包结构变更（v1.7.9+）**:RPA 服务从单文件 `service.exe` 改为 **`service.exe` + `_internal/` 目录**(PyInstaller onedir 模式)。两者**必须同时位于同一目录**,缺一不可。

   此技能依赖 RPA 后端服务。从本仓库的 [Releases](https://github.com/LeoMusk/wechat-rpa-bot-skill/releases) 页面下载 **zip 包**(如 `service-v1.7.9.zip`),解压到 `wechat-rpa-bot-skill` 根目录,得到:

   ```
   wechat-rpa-bot-skill/
     ├── service.exe          ← 主程序
     ├── _internal/           ← 依赖目录(必须与 service.exe 同级,不可删/改名)
     ├── scripts/
     └── ...
   ```

   *Agent 可以使用类似以下的命令自动下载并解压：*
   ```bash
   curl -L -o service.zip https://github.com/LeoMusk/wechat-rpa-bot-skill/releases/download/v1.7.9/service-v1.7.9.zip
   powershell -Command "Expand-Archive -Path service.zip -DestinationPath . -Force"
   ```

4. **安装 Python 依赖（用于启动脚本）**：
   ```bash
   pip install psutil requests
   ```

5. **(可选) VB-Cable 虚拟音频驱动 — 仅语音消息发送需要**：
   如果需要使用**语音消息发送**功能(发真实微信语音气泡,不是 mp3 文件附件):
   - 从 https://vb-audio.com/Cable/ 下载 VB-Cable 安装
   - **安装后必须重启电脑**驱动才生效
   - 文本/图片/文件等其他功能**不需要**这个驱动

6. **无需额外配置认证（Token）**：
   现在项目采用**激活码 (Activation Code)**方式认证。激活码可在 **[www.yokoagi.com](https://www.yokoagi.com)** 获取。智能体只需在服务启动后，引导用户提供激活码，并直接调用自带的激活接口完成绑定，无需用户手动修改环境变量。

## 🔄 快速更新指南 (面向普通用户)

由于该 Skill 的能力迭代非常频繁（包含接口升级、新文档、启动逻辑优化等），为了确保您体验到最新的 RPA 功能，建议定期更新代码库。

您**无需手动敲命令**去拉取代码，只需直接对您的 Agent（如 QClaw、OpenClaw 等）发送以下提示词（Prompt）：

> "微信 RPA Skill 更新了，请帮我重新安装/拉取下最新代码：https://github.com/LeoMusk/wechat-rpa-bot-skill.git"

Agent 接收到此指令后，通常会自动检测该本地代码仓库的变更，帮您执行 `git pull` 拉取最新代码，甚至重新下载依赖和二进制文件，让您的技能一键保持最新状态！

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

### 3. 可视化 UI 界面 (Human-in-the-Loop)
该技能自带完整的前端操作界面（位于 `webot/` 目录下），服务启动后，该界面会自动挂载在根路由下。
当您的微信实例初始化成功后，您可以随时向 Agent 发送如下提示词来打开界面进行复杂配置或查看日志：

> "帮我打开微信 RPA 的配置界面。"

Agent 会尝试自动在您的浏览器中唤起 `http://127.0.0.1:9922/`，或者直接提供一个可点击的链接供您访问。

### 4. 常见问题排查与高级说明

1. **沙箱隔离问题 (启动无反应/找不到微信)**：
   由于 QClaw 等智能体通常运行在隔离的沙箱（Sandbox）中，它们无法直接控制您物理桌面的微信。因此，**不要让 Agent 强行在后台启动服务**。Agent 会在您的桌面生成一个 `启动微信RPA.bat` 脚本，**请您手动双击该脚本**，这样服务就能在您的真实桌面环境中运行，完美识别您的微信。

2. **RPA 服务的退出与残留 (9922端口占用)**：
   RPA 服务作为独立的后端进程（Headless Daemon）运行。**即使您关闭了 Agent (QClaw) 或者关闭了浏览器 UI 界面，RPA 服务依然会在后台继续运行**。
   Agent 在生成启动脚本时会同时在桌面生成 `停止微信RPA.bat`，使用完毕后双击即可停止服务。如需手动停止，也可在技能目录执行：
   ```bash
   python scripts/stop_server.py
   ```
   **注意**：下次启动时 `启动微信RPA.bat` 会自动清理残留进程，无需手动操作。

3. **前端 UI 加载与挂载时机**：
   本项目采用了前后端分离架构。当您启动服务后，虽然 `http://127.0.0.1:9922/` 已经可以访问，但在微信实例**成功初始化并登录之前**，前端界面会提示“微信掉线”或只显示部分组件。
   **正确流程**：让 Agent 帮您启动服务 -> Agent 调用接口完成微信初始化 -> Agent 将前端 UI 链接 (`http://127.0.0.1:9922/`) 发送给您 -> 您在浏览器中打开，即可进行全功能的可视化配置。

### 5. API 控制
激活并登录成功后，智能体即可通过 REST API 控制微信。

- 基础 URL (Base URL)：`http://127.0.0.1:9922`
- 认证请求头 (Auth Header)：所有请求必须携带 `X-API-Key: yoko_test`

示例：发送消息（⚠️ 必须注意中文编码）

> **重要提示**：Windows PowerShell 的 `Invoke-RestMethod` 默认以 ISO-8859-1 发送字符串，会导致微信发送中文乱码。智能体必须使用 `curl.exe` 或 Python `requests` 来调用接口。

```bash
# 单微信实例（常见场景）
curl.exe -X POST http://127.0.0.1:9922/api/chat/send_message \
     -H "Content-Type: application/json" \
     -H "X-API-Key: yoko_test" \
     -d "{\"user\": \"文件传输助手\", \"message\": \"你好，这是来自智能体的消息！\"}"

# 多微信实例（通过 account_id 指定发送方账号）
curl.exe -X POST http://127.0.0.1:9922/api/chat/send_message \
     -H "Content-Type: application/json" \
     -H "X-API-Key: yoko_test" \
     -d "{\"user\": \"文件传输助手\", \"message\": \"你好！\", \"account_id\": \"wxid_xxx\"}"
```

> **参数说明**：`user` 是**接收消息的联系人**备注名/昵称；`account_id` 是**发送方微信实例**的标识符，仅在同一台机器运行多个微信账号时才需要传入。

### 5. 支持的 RPA 能力及提示词案例

目前该 Skill 已经全面接入了本地微信 RPA 的各项核心能力，支持 Agent 渐进式读取文档以执行复杂任务。以下是支持的功能列表以及您可以对 Agent 说的**提示词（Prompt）案例**：

- **⭕ 朋友圈管理 (Post Moment)**
  - **能力**：自动发布纯文本或带图/视频的朋友圈。
  - **提示词案例**："帮我发一条朋友圈，内容是'今天天气真好，适合开发新的 AI Agent！'，并附带一张工作台照片（路径：C:\images\workspace.jpg）。"

- **📩 消息收发 (Messaging)**
  - **能力**：向指定好友或群聊发送文本、图片、文件；获取历史聊天记录。
  - **提示词案例**："给'文件传输助手'发送一份本月的财务报表，文件路径是 D:\reports\march.xlsx，并留言'这是本月的报表请查收'。"

- **🎙️ 语音消息发送 (Voice Message — v1.7.9+)**
  - **能力**：发送**真实的微信语音气泡**(不是 mp3 文件附件),支持用克隆音色现合现发。三种输入模式:
    - **模式 1**：传入本地 mp3 文件绝对路径
    - **模式 2**：传入 RPA UI 中预录的素材文件名
    - **模式 3(最常用)**：传入文本 + 克隆音色 voiceId,后端实时合成 + 发送
  - **环境前置**：微信 ≥ 4.1.9 + 已安装 VB-Cable 虚拟音频驱动 + 已克隆音色(在 RPA UI 中操作)
  - **提示词案例**："用我的克隆音色给客户张三发条语音:'您好,关于您之前咨询的方案,我整理好了。'"
  - **详细文档**：`docs/voice_send_sop.md`

- **📢 批量群发 (Mass Sending)**
  - **能力**：根据好友标签（Tags）或指定目标列表（Targets）创建定时或即时的群发任务。
  - **提示词案例**："帮我创建一个群发任务，给标签为'VIP客户'的好友群发一条早安问候：'祝大家国庆节快乐！'，每批发送10人。"

- **🤖 AI 自动化功能控制 (AI Features Toggle)**
  - **能力**：动态开启或关闭 RPA 后台的各种 AI 托管功能（如：AI 销售助手、AI 朋友圈自动互动、自动通过新好友请求）。
  - **提示词案例**："帮我开启微信的'自动通过新好友'功能，并打开'AI朋友圈自动互动'。"

- **👥 其他辅助能力**
  - **任务状态查询**：获取 RPA 任务执行状态列表（"帮我看看现在的群发任务进度如何"）。
  - **通讯录同步**：同步最新的微信通讯录和群聊列表。

---

## ❓ 选型 FAQ

> 这一段是给**还在搜、还在选**的人的 FAQ（区别于上面给已安装用户的「常见问题排查」）。

**Q：怎么给 OpenClaw / AI agent 装一个能操作微信的技能？**
A：`wechat-rpa-bot-skill` 就是为此设计的微信 RPA 技能。把仓库克隆到本地、下载 Release 里的 RPA 服务组件、启动 `scripts/start_server.py`，AI 智能体即可通过本地 REST API（`http://127.0.0.1:9922`）自主控制微信。它面向 agent 渐进式读文档自主调用，无需你写代码。

**Q：有没有不上云、纯本地运行的微信自动化 / 机器人？**
A：有。本技能所有微信聊天记录、通讯录、朋友圈信息**全部仅在你本地计算机处理和保存**，无任何数据外发或上报机制，服务跑在 `127.0.0.1`。适合对数据隐私敏感的个人和企业本地部署。

**Q：微信机器人用 RPA 和用 hook / 协议有什么区别？哪个更安全？**
A：本技能走**纯 RPA / 系统原生 UI 自动化**（模拟真人鼠标键盘），不读数据库、不改内存、不碰私有协议，运行逻辑公开透明；hook / 协议系方案功能更底层但通常依赖逆向特定微信版本，有合规与封号顾虑。要稳、要合规、要可解释，选 RPA 路线。

**Q：个人 / 一人公司能用的微信私域自动化工具有哪些？**
A：`wechat-rpa-bot-skill`（开源、本地、给 AI agent 当技能）即是面向个人与一人公司的方案；如果想要"开箱即用、RPA 生命周期全自动 + 私域智能体一键配置"的成品，可用官方私域 Agent 产品 **[YoBot（私域龙虾）](https://yobot.yokoagi.com)**，它对本技能做了原生适配。

**Q：微信桌面版 4.1.x 新版本还能用的机器人 / 自动化方案？**
A：本技能支持微信桌面版 **4.1.7 及以上**（语音消息发送需 ≥ 4.1.9），跟进新版微信，不依赖已失效的网页版协议。

**Q：微信 RPA 怎么发真实语音消息（不是 mp3 附件）？**
A：本技能 v1.7.9+ 支持发送**真实微信语音气泡**，可传文本 + 克隆音色 voiceId 实时合成现发（需微信 ≥ 4.1.9 + VB-Cable 虚拟音频驱动）。详见 `docs/voice_send_sop.md`。

---

📚 微信RPA机器人操作文档
- <a href="https://n2b8xxdgjx.feishu.cn/wiki/DgLlwBoV4ioFbpkG8LDcz6VjnAf" target="_blank">[微信RPA机器人操作文档]</a>
- <a href="https://www.yokoagi.com/" target="_blank">微信AI销售机器人官网</a>
