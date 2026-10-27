# WeChat RPA Bot Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**WeChat RPA Bot Skill（微信 RPA 机器人技能 / `wechat-rpa-bot-skill`）是一个面向 AI 智能体、纯本地运行的微信 RPA（机器人流程自动化）技能。** 它把你电脑上的一个微信桌面端封装成一个**纯本地服务**（`http://127.0.0.1:9922`），通过 **MCP（Model Context Protocol）** 以及 REST API，让 [OpenClaw](https://github.com/openclaw/openclaw)、[QClaw](https://qclaw.qq.com/)、[YoBot（私域龙虾）](https://yobot.yokoagi.com) 等 AI 智能体**无需读取微信数据库、不改内存、不碰私有协议**，就能自动发消息、发朋友圈、发**真实语音气泡**、按标签批量群发。

它区别于传统微信机器人库：**不是给开发者写代码用的 SDK，而是一个能被 AI 智能体一键安装、渐进式读文档自主调用的"技能"**。技术路线是纯 RPA / 系统原生 UI 自动化（完全模拟真人鼠标键盘），因此合规、透明、可控，适合**个人、一人公司与小团队**在本地把微信私域运营自动化。

> **独立 MCP 安装包继续提供和更新**，可直接查看[安装、激活与接入步骤](#standalone-install)。首次使用，或希望在一个客户端中管理微信 RPA、智能体和任务，可以使用 [YoBot](https://yobot.yokoagi.com)：在客户端完成配置，再将 MCP 接入已有 Agent，日常使用更便捷。参见 [YoBot 使用说明](#yobot)。
>
> 开发者文档：[MCP 工具清单与参数](references/mcp-tools.md) · [企业自定义智能体 API](references/customer-agent-api.md)

> 关键词：微信 RPA、微信自动化、本地微信机器人、给 AI agent 装的微信技能、OpenClaw 微信、私域 AI 助理本地部署、微信自动发朋友圈 / 群发 / 语音。

## 🛡️ 安全与隐私声明 (Security & Privacy Declaration)

- **🔒 微信 RPA 在本机运行**：微信界面操作与 RPA 本地记录在用户电脑上完成。接入外部 Agent、模型或企业 API 后，相应功能会将所需消息或附件交给配置的服务处理；数据流向取决于实际接入配置。
- **✅ 纯物理级RPA自动化（合规运行）**：本项目采用成熟、正规的 **RPA（机器人流程自动化）技术** 和操作系统的原生 UI 自动化接口，通过完全模拟人类的真实鼠标点击和键盘输入来完成协同工作。**不采用**底层技术修改（如内存修改），**不会读取微信数据库及私有协议**。
- **🛡️ 绿色的本地协同工具**：本工具的设计初衷是帮助用户提高日常工作效率，运行逻辑公开透明。代码库完全开放，无任何隐藏的远控或非法行为。

## 🌟 核心特性

- **智能体友好 (Agent-Friendly)**：从底层开始专门针对 AI 智能体的轻松安装和调用而构建。
- **MCP 原生 + 无头后端**：后台常驻，以标准 **MCP 工具**（约 27 个）及 REST API 暴露微信能力（`http://127.0.0.1:9922`），宿主连上即原生可用。
- **生命周期自管理**：服务由安装器/开机自启在用户桌面会话常驻（崩溃自愈），智能体只作网络客户端自动绑定并驱动微信，无需手动启停。
- **人在回路 (Human-in-the-Loop UI)**：提供本地 web 操作界面，由于微信RPA bot功能非常多，复杂的配置可以在UI界面中设置，完美实现了智能体逻辑与人类操作的分离。

## 🆚 和其它微信机器人方案的区别

| 方案 | 技术路线 | 主要给谁用 | 接入 AI Agent | 说明（取舍） |
|---|---|---|---|---|
| **wechat-rpa-bot-skill** | 纯 RPA / UI 自动化（模拟真人点击） | AI 智能体 + 个人 / 小团队 | ✅ 原生 MCP + REST，可一键当 skill 安装 | 不读数据库、不改内存、不碰私有协议；依赖微信桌面 UI，版本升级偶需适配 |
| WeChatFerry | 多基于 hook 注入 | 开发者（写代码） | 需自行封装 | 功能强；通常需匹配特定微信版本，有合规 / 封号顾虑 |
| ComWeChatRobot | 多基于 hook / 注入 | 开发者 | 需自行封装 | 同上，对微信版本依赖较强 |
| Wechaty | 多协议网关（需 puppet） | 开发者 | 需自行封装 | 生态成熟；企业级 puppet 多需付费 / 资质 |
| itchat | 网页版微信协议 | 开发者 | 需自行封装 | 网页版协议已基本失效，新号多不可用 |

> 一句话选型：要**给 AI 智能体（OpenClaw / QClaw 等）一个开箱即用、纯本地、合规的微信操作能力**，用本技能；要在代码里深度定制协议级能力且能自担封号 / 版本风险，可看 hook 系项目。

## 🧩 本技能如何提供能力：一个纯本地的 MCP 服务

**本技能的微信能力，由一个纯本地运行的 MCP 服务 `yoko_rpa_mcp.exe` 对外提供。** 它在你的电脑上常驻（端口 `9922`），把「发消息 / 群发 / 发朋友圈 / 发真实语音气泡 / 读联系人 / 群聊总结 / 任务管理……」等约 27 项微信能力，以标准 **MCP（Model Context Protocol）工具**的形式暴露出来。OpenClaw / QClaw / WorkBuddy 等宿主只需连上本机的 MCP 端点（`http://127.0.0.1:9922/mcp` + 一个本地配对 token），这些微信工具就会**原生出现在你的 AI Agent 里**，像调用内置工具一样驱动微信。

> 同一个程序同时提供三个门面、共享同一套后端：**`/mcp`（MCP 工具，主通道）** + `/api/*`（REST，用于安装/激活等）+ `/`（可视化控制台，手动兜底）。你既可以**通过本技能引导安装接入 MCP**，也可以**把 MCP 端点直接接进你自己的 Agent 产品**，两种接法都行。

### 为什么走 MCP：从「Agent 直管 RPA」到「Agent 只做网络客户端」

早期版本让 AI Agent 自己管理 RPA 后端的整个生命周期（下载、启动、REST 调用、结束清理）。实践中这套体验并不好，根因有二：

1. **沙箱 / 会话隔离让"自动启动"行不通**：QClaw 等宿主会把技能子进程放进沙箱。一旦 Agent 自己 `spawn` 起 RPA 程序，这个 RPA 进程就**继承了沙箱**，与用户的微信不在同一个桌面会话里 → 它看不见微信窗口、也就操作不了微信（这是 Windows 的 UIPI / 会话隔离安全边界，无法绕过）。
2. **生命周期负担全压在用户和 Agent 身上**：手动双击启动器、关掉对话后端口 9922 还残留、崩溃了要自己排查……对普通用户很不友好。

**MCP over 本地 HTTP 从根上解决了这两点**：

- **Agent 只是 RPA 进程的「网络客户端」，绝不是它的「父进程」。** RPA 程序由用户在自己的交互桌面会话里启动（和微信同环境、同权限级别 → RPA 正常工作），Agent 只往 `127.0.0.1` 发 HTTP → 网络请求可以**干净地穿过沙箱边界**。
- **生命周期由程序自管**：`yoko_rpa_mcp.exe` 内置进程守护（崩溃自愈）+ 开机自启，用户**首次运行一次**之后基本无感，不再需要每次手动启停。

> 如果希望把 RPA 的运行管理与智能体使用放在同一个客户端中，可以使用下面的 **YoBot 集成方式**。独立 MCP 服务仍可按下文安装使用。

<a id="yobot"></a>

## 在 YoBot 中使用：集中管理 RPA、智能体与任务
<img width="1400" height="980" alt="image" src="https://github.com/user-attachments/assets/1b119ff8-f140-45cb-8d58-16ed74775f5e" />


[YoBot](https://yobot.yokoagi.com) 是集成了微信 RPA 的桌面 Agent 客户端。它将 RPA 运行管理、微信账号初始化、智能体配置和任务操作集中在一个界面中，也提供对外 MCP 接入。

独立 MCP 安装包适合已经有 Agent、只需要单独部署微信工具服务的用户。它自带进程守护和开机自启；YoBot 则进一步把服务管理和业务功能放进客户端，减少在安装器、本地控制台和 Agent 配置之间切换的步骤。**首次使用或需要长期管理客服、聊天记录与运营任务，建议从 YoBot 开始。**

### 客户端中可以完成什么

| 需求 | YoBot 中的使用方式 |
|---|---|
| 管理微信 RPA | 由客户端负责服务启停、微信初始化和插件维护，在界面中查看账号与运行状态 |
| 日常微信工作 | 使用智能体处理客户回复、跟进、资料发送、群发和朋友圈任务，具体能力取决于配置与授权 |
| 聊天回顾 | 基于运行期间已采集的私聊、群聊记录整理进展和待办 |
| 继续使用现有 Agent | 开启「对外开放」，复制 MCP 配置，让支持该传输方式的 Agent 调用微信工具 |
| 接入企业自己的智能体 | 按本文公开的 API 规范提供消息处理接口，将企业知识库、订单查询或其他业务逻辑接入回复流程 |

客户端功能与对外 MCP 工具的开放范围可能不同。例如，本文收录的 MCP 工具可以查询已有的定时朋友圈任务，但未包含创建定时朋友圈任务的接口；详细能力以客户端及连接后返回的工具清单为准。

### 将 YoBot 的 MCP 接入已有 Agent

1. **安装并运行 YoBot**：从 [官网](https://yobot.yokoagi.com) 下载并登录，在客户端确认微信 RPA 业务授权有效，目标微信已登录、初始化并处于托管状态。
2. **复制接入配置**：打开 YoBot 的「对外开放」，开启服务，复制页面生成的 MCP 配置或配置话术。连接令牌用于 MCP 鉴权，与独立安装包的激活码不同。
3. **接入并验证**：按照所用 Agent 的要求添加或重载 MCP 配置，先获取 `tools/list`，再调用 `wechat_list_instances` 查询可用微信账号。查到账号后，再执行用户需要的业务操作。

默认使用 Streamable HTTP，地址为 `http://127.0.0.1:9922/mcp`，请求头为 `Authorization: Bearer <连接令牌>`。优先使用客户端生成的配置；各 Agent 的配置文件位置和字段可能不同。

YoBot 仍需在运行微信的电脑上保持运行。`127.0.0.1` 指这台电脑，云端 Agent 不能直接用该地址访问它。无法连接时，先在客户端检查 RPA 状态和「对外开放」开关；授权问题在客户端处理，无需套用下文独立服务的激活流程。

接入演示：[YoBot MCP 视频教程](https://www.bilibili.com/video/BV1izj16wEGe)。参数、调用示例和错误处理见 [MCP 工具接口文档](references/mcp-tools.md)。

<a id="open-interfaces"></a>

## 开放接口：MCP 工具与企业智能体 API

两种接口解决不同的问题，可以按实际业务需要使用：

| 接入方式 | 调用方向 | 适用需求 | 详细文档 |
|---|---|---|---|
| MCP 工具 | 外部 Agent → YoBot 的微信 RPA → 微信 | 让现有 Agent 发消息、发文件、查记录或创建群发任务 | [工具清单、参数与示例](references/mcp-tools.md) |
| 企业智能体 API | YoBot 的微信 RPA → 企业 API，取得结果后执行回复 | 由企业自己的智能体处理微信咨询，或只接收消息用于内部业务 | [API 接入规范](references/customer-agent-api.md) |

### MCP 开放能力

下表列出参考文档已详述的 25 个工具，文档包含参数约束和调用示例。不同版本可能提供更多工具，完整清单和参数以连接后的 `tools/list` 与 `inputSchema` 为准。

| 类别 | 主要工具 | 用途 |
|---|---|---|
| 账号 | `wechat_list_instances` | 查询可执行操作的微信账号 |
| 消息 | `wechat_send_message`、`wechat_send_file`、`wechat_send_voice`、`wechat_list_voices`、`wechat_fetch_latest_messages` | 发送文字、文件和真实语音气泡，查询音色，读取当前窗口消息 |
| 联系人与群聊 | `wechat_sync_contacts`、`wechat_get_contacts`、`wechat_get_groups`、`wechat_invite_to_group` | 同步与查询通讯录、群聊，邀请已有好友入群 |
| 群发 | `wechat_mass_sending`、`wechat_list_mass_sending_tasks`、`wechat_pause_mass_sending_task`、`wechat_resume_mass_sending_task`、`wechat_cancel_mass_sending_task` | 创建立即或定时群发任务，查询进度及暂停、恢复、取消 |
| 任务 | `wechat_get_tasks` | 查询 RPA 调度任务 |
| 朋友圈 | `wechat_post_moment`、`wechat_list_moment_post_tasks`、`wechat_get_moment_post_logs` | 立即发布朋友圈，查询已有发布任务与执行记录 |
| 添加好友 | `wechat_get_friend_list`、`wechat_get_friend_remaining_count`、`wechat_toggle_auto_add_friend`、`wechat_get_add_friend_logs` | 查看名单、启停自动添加、检查执行结果 |
| 聊天记录 | `wechat_list_sessions`、`wechat_get_session_messages` | 读取已保存会话与历史，供 Agent 总结和提取事项 |

例如，可以让 Agent「给项目群发送本机的方案 PDF」「汇总已采集的客户群记录」「给指定标签的客户创建通知任务」。文件路径应属于 RPA 所在电脑；历史查询不会自动补抓全部微信历史；群发任务创建成功后，还需查询执行状态。

这份文档以 **YoBot 客户端对外 MCP** 为范围。独立 MCP 服务保留下文的安装、激活和内置手册方式；不同版本、运行方式的工具集合可能不同，不应直接混用配置、授权或服务管理工具。

### 用 API 接入企业自己的智能体

企业提供消息处理服务，并在客户端配置服务地址、鉴权令牌和对应智能体。微信收到消息后，YoBot 的 RPA 按规范请求企业 API，企业服务完成业务处理并返回回复内容，再由 RPA 发送到微信。企业可以在自己的服务中调用已有知识库、CRM、订单系统或工作流。

例如，客户询问订单进度时，企业 API 根据消息查询订单并生成结果，YoBot 负责将结果发回微信。业务查询逻辑由企业实现；已有平台需要适配下面的接口和响应格式。

| 企业侧接口 | 作用 | 何时需要 |
|---|---|---|
| `GET /v1/capabilities` | 声明协议版本、场景和可用能力 | 必需 |
| `POST /v1/chat` | 接收消息并返回回复、异步任务或接收确认 | 必需 |
| `GET /v1/jobs/{jobId}` | 查询耗时任务的处理结果 | 异步回复时 |
| `POST /v1/deliveries/{deliveryId}/ack` | 接收微信侧最终处理状态 | 可选 |

最小同步接入只需实现前两个接口，并处理鉴权和重复请求。需要较长时间的查询或生成任务可以返回异步任务，由 RPA 主动轮询；只想把消息交给内部系统处理，可以使用 `consume_only` 模式，不发送自动回复。企业侧无需向 RPA 发起公网回调。

协议还支持可选的入站图片、文档提取文本，以及回复中的图片或文件 URL。附件能力需要企业接口显式声明，并满足插件版本和大小限制。完整请求、响应、异步恢复及联调示例见 [企业自定义智能体 API 文档](references/customer-agent-api.md)。

下载客户端及查看产品说明：[YoBot 官网](https://yobot.yokoagi.com)。

---

> 下面是**独立 MCP 服务的安装与接入**方式，安装包继续提供和更新。已通过 YoBot 接入的用户无需重复安装；独立服务的激活码、REST setup 接口和内置手册按以下说明使用。

<a id="standalone-install"></a>

## 📦 安装（用户运行官方安装器）

> ⚠️ **这一步由用户本人手动完成。** 微信能力由本地程序 `yoko_rpa_mcp.exe` 提供，需通过官方安装器安装。**请务必让用户亲自运行安装器**——这样服务跑在用户自己的桌面会话（Session 1）里，能规避 AI Agent 沙箱/会话隔离导致的"看不见微信"问题（原理见上方「为什么走 MCP」）。

1. **确认微信版本**：微信桌面版 **4.1.7 及以上**（语音消息发送需 **≥ 4.1.9**）。查看：微信 → 帮助 → 关于。版本不符可 👉 [下载新版微信](https://n2b8xxdgjx.feishu.cn/wiki/Nbauw9HWsihsQ7kgjYPcfZSCnKb)。

2. **下载并运行安装器**：👉 [`yoko_rpa_mcp_setup.exe`](https://github.com/LeoMusk/wechat-rpa-bot-skill/releases/latest/download/yoko_rpa_mcp_setup.exe)（Inno Setup 安装包）。
   - 双击运行 → 弹出 UAC，点「是」授予管理员权限（装到 `C:\Program Files\yoko_rpa_mcp\`，ASCII 路径规避中文路径加载问题）。
   - 安装器自动完成：装程序 → **以普通用户身份在用户桌面会话启动服务** → 注册**开机自启**（登录计划任务 + 启动项，含崩溃自愈）→ 建桌面/开始菜单图标「微信 RPA MCP 服务」。
   - **装完即已在后台常驻运行**，之后开机自动就绪，无需每次手动启停。

3. **(可选) VB-Cable 虚拟音频驱动 — 仅语音消息发送需要**：从 https://vb-audio.com/Cable/ 下载安装，**装后必须重启电脑**驱动才生效。文本/图片/文件等功能**不需要**这个驱动。

4. **激活**：采用**激活码 (Activation Code)** 认证，激活码在 **[www.yokoagi.com](https://www.yokoagi.com)** 获取。首次接入时 Agent 会引导你提供激活码并自动完成设备绑定，无需手动改环境变量。

## 🔌 接入 MCP（把微信能力接进你的 Agent）

安装后，微信能力以约 **27 个 MCP 工具**的形式在本机 `http://127.0.0.1:9922/mcp` 暴露。接进 OpenClaw / QClaw 等宿主：

1. **取配对信息**：本机服务提供 `GET /api/mcp/token`（请求头带 `X-API-Key: yoko_test`），返回 MCP 端点与本地配对 token。Agent 可自动读取。
2. **写入宿主 `mcp.json`**（token 换成上一步的实际值）：
   ```json
   {
     "mcpServers": {
       "yoko-wechat-rpa": {
         "type": "streamableHttp",
         "url": "http://127.0.0.1:9922/mcp",
         "headers": { "Authorization": "Bearer <token>" }
       }
     }
   }
   ```
3. **重载宿主**：保存后重启/重载宿主，微信相关工具即**原生出现在你的 Agent 里**，直接对话驱动。

> 最省事的做法：把本仓库的 `SKILL.md` 交给你的 Agent（当作 skill 安装），由它一步步引导你完成上面的下载安装 + 接入 + 激活。

## 🔄 更新

- **更新 RPA 服务（exe）**：重新下载并运行最新的 [`yoko_rpa_mcp_setup.exe`](https://github.com/LeoMusk/wechat-rpa-bot-skill/releases/latest/download/yoko_rpa_mcp_setup.exe) 即可。安装器会自动关掉在跑的旧实例、覆盖安装并复位开机自启。
- **更新 skill（SKILL.md）**：对 Agent 说一句「微信 RPA Skill 更新了，帮我拉取最新：https://github.com/LeoMusk/wechat-rpa-bot-skill.git 」，它会 `git pull` 保持 `SKILL.md` 最新。

## 🖥️ 可视化控制台（Human-in-the-Loop）

服务运行时，浏览器打开 `http://127.0.0.1:9922/` 即完整可视化操作界面，与 MCP **共享同一后端状态**（Agent 改的配置在界面实时可见，反之亦然）。复杂配置可在此手动完成；Agent 也可用 `wechat_open_console` 工具把链接发给你。

> 微信实例**成功初始化并登录之前**，界面会提示"微信掉线"或只显示部分组件——先让 Agent 完成初始化，再打开界面即可全功能使用。

## 🚀 支持的能力及提示词案例

安装接入后，直接用自然语言对 Agent 说即可（它会调用对应的 MCP 工具）：

- **📩 消息收发 (Messaging)**：向好友/群聊发文本、图片、文件；拉取实时消息与历史记录。
  - "给'文件传输助手'发一份本月财务报表，路径 D:\reports\march.xlsx，留言'请查收'。"
- **🎙️ 真实语音消息 (Voice — v1.7.9+)**：发**真实微信语音气泡**（不是 mp3 附件），可传文本 + 克隆音色 voiceId 实时合成现发（需微信 ≥ 4.1.9 + VB-Cable + 已克隆音色）。
  - "用我的克隆音色给客户张三发条语音：'方案我整理好了。'"
- **⭕ 朋友圈管理 (Moments)**：定时/即时发图文朋友圈；AI 自动点赞评论好友朋友圈。
  - "帮我发一条朋友圈，配一张 C:\images\workspace.jpg。"
- **📢 批量群发 (Mass Sending)**：按好友标签或指定目标，创建定时/即时群发任务。
  - "给标签'VIP客户'的好友群发早安问候，每批 10 人。"
- **👥 联系人 / 群聊总结 / 任务**：读取与同步通讯录、按会话总结群聊记录、查询任务进度。
  - "总结一下'项目群'今天聊了啥。"

> 复杂 SOP（语音、朋友圈、群总结、加好友、配置 schema）由 MCP 工具内置的 `wechat_rpa_read_manual` 提供分步手册，Agent 会按需读取，细节无需你操心。

### 沙箱隔离说明（为什么服务由用户启动）

QClaw 等宿主常运行在隔离沙箱里，无法直接控制你物理桌面的微信。因此本方案**刻意让 RPA 服务由安装器/开机自启在你自己的桌面会话启动**，Agent 只作为 `127.0.0.1` 的网络客户端连它——请勿让 Agent 自己去后台拉起服务。服务作为后台常驻进程运行，关掉 Agent 或浏览器界面后仍会继续运行（并崩溃自愈）；如需彻底停止，走「设置 → 应用 → 卸载『微信 RPA MCP 服务』」。

---

## ❓ 选型 FAQ

> 这一段是给**还在搜、还在选**的人的 FAQ（区别于上面给已安装用户的「常见问题排查」）。

**Q：怎么给 OpenClaw / AI agent 装一个能操作微信的技能？**
A：可以安装独立的 [`yoko_rpa_mcp_setup.exe`](https://github.com/LeoMusk/wechat-rpa-bot-skill/releases/latest/download/yoko_rpa_mcp_setup.exe)，按上文完成激活和 MCP 配置。首次使用，也可以从 [YoBot](https://yobot.yokoagi.com) 开始：由客户端管理 RPA，在「对外开放」复制配置，再接入已有 Agent。两种方式都通过本机 MCP 提供微信工具，YoBot 将运行管理和业务配置集中在客户端中。

**Q：有没有不上云、纯本地运行的微信自动化 / 机器人？**
A：本项目的微信 RPA 在本机运行，默认 MCP 地址为 `127.0.0.1`。是否有数据传到外部，还取决于所用 Agent、模型服务和企业 API 的配置；启用这些接入时，应同时查看对应服务的数据处理方式。

**Q：微信机器人用 RPA 和用 hook / 协议有什么区别？哪个更安全？**
A：本技能走**纯 RPA / 系统原生 UI 自动化**（模拟真人鼠标键盘），不读数据库、不改内存、不碰私有协议，运行逻辑公开透明；hook / 协议系方案功能更底层但通常依赖逆向特定微信版本，有合规与封号顾虑。要稳、要合规、要可解释，选 RPA 路线。

**Q：个人 / 一人公司能用的微信私域自动化工具有哪些？**
A：`wechat-rpa-bot-skill`（开源、本地、给 AI agent 当技能）即是面向个人与一人公司的方案；如果想要"开箱即用、RPA 生命周期全自动 + 私域智能体一键配置"的成品，可用官方私域 Agent 产品 **[YoBot（私域龙虾）](https://yobot.yokoagi.com)**，它对本技能做了原生适配。

**Q：微信桌面版 4.1.x 新版本还能用的机器人 / 自动化方案？**
A：本技能支持微信桌面版 **4.1.7 及以上**（语音消息发送需 ≥ 4.1.9），跟进新版微信，不依赖已失效的网页版协议。

**Q：微信 RPA 怎么发真实语音消息（不是 mp3 附件）？**
A：本技能 v1.7.9+ 支持发送**真实微信语音气泡**，可传文本 + 克隆音色 voiceId 实时合成现发（需微信 ≥ 4.1.9 + VB-Cable 虚拟音频驱动）。发送前 Agent 会通过 MCP 工具内置手册 `wechat_rpa_read_manual('voice_send_sop')` 读取完整决策流程。

---

📚 微信RPA机器人操作文档
- <a href="https://n2b8xxdgjx.feishu.cn/wiki/DgLlwBoV4ioFbpkG8LDcz6VjnAf" target="_blank">[微信RPA机器人操作文档]</a>
- <a href="https://www.yokoagi.com/" target="_blank">微信AI销售机器人官网</a>
