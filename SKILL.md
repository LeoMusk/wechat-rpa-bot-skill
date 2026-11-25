---
name: wechat-rpa-bot
description: Connect an AI Agent to WeChat automation through YoBot or the standalone yoko WeChat RPA MCP server. Use for MCP setup, standalone installation and activation, tool usage, or integrating a custom enterprise agent through the documented customer API.
---

# WeChat RPA Bot Skill (MCP edition)

This skill turns any MCP-capable host (OpenClaw / QClaw / WorkBuddy …) into a WeChat assistant by
**connecting to YoBot or onboarding the standalone yoko WeChat RPA MCP server** and then driving WeChat through its MCP tools.

## 接入方式与参考文档

已有可用 MCP 连接时，直接复用。用户已选择独立安装包时，继续按下文的独立服务流程操作；安装包继续提供和更新。首次使用且未指定方式时，推荐 [YoBot](https://yobot.yokoagi.com)：客户端集中管理 RPA 启停、微信初始化、插件维护和业务配置，可减少单独管理服务的步骤。

- **通过 YoBot 接入**：按下一节操作，按需读取 [MCP 工具接口文档](references/mcp-tools.md)，其中包含客户端对外工具清单、参数、示例与结果处理。
- **使用独立 MCP 安装包**：按第 0–7 节操作，完成独立服务的激活、微信初始化和配对。
- **企业自己的智能体处理微信消息**：读取 [企业自定义智能体 API](references/customer-agent-api.md)。由企业实现消息处理接口，YoBot 的 RPA 主动调用；不要把这份规范当成独立服务的 REST setup API。

## 通过 YoBot 接入 MCP

1. 引导用户从 [YoBot 官网](https://yobot.yokoagi.com) 安装并运行客户端，确认微信 RPA 业务授权有效、微信已登录并由客户端初始化和托管。
2. 在「对外开放」开启服务，使用客户端生成的 MCP 配置或配置话术。默认端点是 `http://127.0.0.1:9922/mcp`，传输为 Streamable HTTP，鉴权为 `Authorization: Bearer <连接令牌>`。
3. 按宿主支持的方式添加或重载 MCP 配置，保留宿主已有的其他服务配置。连接令牌与激活码不同；不要对 YoBot 执行下文独立服务的激活、取 token 或进程恢复步骤。
4. 获取 `tools/list` 与实际 `inputSchema`，调用 `wechat_list_instances` 验证可用微信账号。连接失败时检查客户端运行状态、对外开放开关和令牌；业务授权问题回到客户端处理。
5. 根据用户任务按需读取 [接口文档](references/mcp-tools.md)，调用实际存在的工具。YoBot 与独立安装包的默认 MCP 都可参考这份工具文档。

YoBot 需在微信所在电脑上保持运行；云端 Agent 不能直接访问另一台电脑的 `127.0.0.1`。群发等后台任务应继续查询状态，发送结果不确定时先核对消息，避免重复发送。历史记录查询只能反映已采集并保存的范围。

## 独立 MCP 服务接入

以下心智模型及第 0–7 节适用于独立的 `yoko_rpa_mcp.exe`。

**心智模型（务必先理解）**
- 微信自动化能力由 `yoko_rpa_mcp.exe` 在用户桌面(Session 1)常驻提供，端口 **9922**，同一进程三门面：
  - `/mcp` — Streamable-HTTP **MCP 端点**（本技能的主通道，Bearer token 鉴权）
  - `/api/*` — REST（本技能只在**安装/激活/取 token**等 setup 步骤用它）
  - `/` — 可视化控制台（手动兜底）
- **本技能不直接发微信**：它负责把 MCP server 装好、拉起、激活、把 `/mcp` + token 写进宿主的 `mcp.json`。
  一旦宿主重载配置，默认 28 个微信工具就**原生**出现在宿主里，之后由宿主 Agent 直接调用。
- Agent **绝不能自己 spawn 这个 exe**：被 spawn 的进程会继承沙箱/会话隔离，看不见微信桌面。exe 必须由
  用户在自己的交互会话里启动（首启一次；之后 exe 自注册开机自启，自动复活）。

---

## 0. 端到端流程总览

```
安装 exe ──▶ 用户首启(Session 1) ──▶ 健康检查(REST) ──▶ 激活 license(REST)
   └──▶ 取 MCP token(REST) ──▶ 生成 mcp.json ──▶ 用户粘贴+重载宿主 ──▶ 验活(MCP tools/list)
        ──▶ 在控制台登录并初始化微信 ──▶ 查询可用账号 ──▶ 使用 MCP 工具
```

---

## 1. 安装（用户运行安装器，Agent 只做引导）

> **⚠️ 这一步由用户本人完成，不是自动的。** 微信能力由一个桌面程序提供，通过官方安装器 **`yoko_rpa_mcp_setup.exe`** 安装。
> Agent 只负责把步骤讲清楚、给出下载链接；**不要**替用户静默安装，也**不要**自己去运行安装器或 exe——原因见 §2（沙箱/会话隔离会让自动拉起的进程操作不了微信）。
> 请一次性、清楚地告诉用户：「微信自动化需要在您电脑上装一个本地程序，下面我把下载和安装步骤发给您，需要您亲自运行一次安装器（会弹管理员确认）。」

1. 确认环境：**Windows** + **微信桌面版 ≥ 4.1.7**（语音发送需 **≥ 4.1.9**）。
   - 版本查看：微信 → 帮助 → 关于；版本不对从官方渠道升级。
2. **下载并运行安装器 `yoko_rpa_mcp_setup.exe`**（Inno Setup 安装包）：
   - 下载地址：<https://github.com/LeoMusk/wechat-rpa-bot-skill/releases/latest/download/yoko_rpa_mcp_setup.exe>
   - *Agent 可代下载到用户的下载目录，再请用户双击运行（Agent 不要自己运行安装器）：*
     ```bash
     curl -L -o "$HOME/Downloads/yoko_rpa_mcp_setup.exe" https://github.com/LeoMusk/wechat-rpa-bot-skill/releases/latest/download/yoko_rpa_mcp_setup.exe
     ```
   - 用户双击运行 → **弹出 UAC，需点「是」授予管理员权限**（装到 `C:\Program Files\yoko_rpa_mcp\`，ASCII 路径规避中文路径加载问题）。
   - 安装器会自动：① 把程序装到 Program Files；② **以普通用户身份**（非管理员，落在用户交互会话 Session 1）立即启动服务 `--supervisor --no-ui`；③ 注册**三通道开机自启**（登录计划任务 + HKCU Run 键 + 启动文件夹）；④ 建桌面/开始菜单图标 **「YoBot私域AI-MCP」**。
   - **装完即已在运行**，无需再手动启动。exe 本体在 `C:\Program Files\yoko_rpa_mcp\yoko_rpa_mcp.exe`（skill 本身不再附带 exe）。
3. **VB-Cable 虚拟音频驱动**（仅"语音消息发送"需要）：从 https://vb-audio.com/Cable/ 下载安装，**装后重启电脑**。文本/图片/文件等功能不需要。
4. 无需 `.env`：采用**激活码**体系，激活码从 **www.yokoagi.com** 获取。

---

## 2. 确认服务在运行（安装器已自动启动，通常无需手动）

**为什么不能你来 spawn**：微信自动化靠在用户**可见桌面**上模拟真实鼠标键盘。若 Agent（尤其在沙箱内）自己拉起 exe，它落在隔离会话里看不见微信。**由设计如此**——服务由安装器/自启在用户会话里跑，你只做网络客户端。

**Step 1 — 健康检查。**
GET `http://127.0.0.1:9922/api/health`（localhost 关代理）。有响应说明服务就绪 → 跳到 §3 检查激活。
装完安装器后一般会在数秒内起来；可每 ~3s 轮询，最多 ~2 分钟，**不要等用户打字**。

**Step 2 — 若没起来（少数情况）。**
安装器装完会自动启动、且已注册开机自启，正常无需手动。若 `/api/health` 始终无响应，引导用户：
> "请双击桌面上的 **「YoBot私域AI-MCP」** 图标启动它（或从开始菜单打开）。启动后**无需回复我**，我会自动检测到就绪并继续。"

然后继续轮询 `/api/health`。仍不行则问用户是否有报错弹窗，或参考 §6 恢复手段。

**开机自启**：安装器已注册三通道自启 + 崩溃自愈守护，**下次开机自动就绪**，用户日常无需手动启停。

---

## 3. 激活独立服务

打开本机控制台 `http://127.0.0.1:9922/`。如果已经激活，继续配对。如果页面提示需要激活，从 [YokoAI 官网](https://www.yokoagi.com) 获取激活码，并在本机控制台输入。服务健康检查、激活和微信账号是否已初始化可以分别验证。

需要通过 REST 核对时，先调用 `GET /api/license/verify?force=false` 检查 `valid`。`GET /api/license/machine-code` 只提供绑定所需的机器码。REST 请求使用 `X-API-Key`，MCP 配对使用下一节的 Bearer 令牌。

---

## 4. 接入 MCP（本技能核心）

### 4.1 取 MCP token
token 是本地随机密钥（**不等于激活码**，激活码不外泄），首次运行落盘 `~/.yokowebot/mcp_token.dat`。
沙箱里 agent 通常读不到该文件，因此从后端专用端点取（已实现）：
```
GET http://127.0.0.1:9922/api/mcp/token
Headers: X-API-Key: yoko_test          (localhost 关代理)
```
成功返回：
```json
{
  "success": true,
  "endpoint": "http://127.0.0.1:9922/mcp",
  "token": "<随机 pairing token>",
  "server_name": "wechat-bot-mcp",
  "transport": "streamable-http",
  "auth_header": "Authorization: Bearer <token>"
}
```
- 需带 `X-API-Key`（此端点不在 api_key 豁免名单内）；未激活也能取（已加入 license 豁免），方便先配好再激活。
- 若返回 `MCP_DISABLED`，检查当前运行的是独立 MCP 版，或在 YoBot 的「对外开放」开启服务。

### 4.2 生成 mcp.json 片段
把下面片段给用户（token 换成实际值）。Streamable-HTTP 传输，Bearer 鉴权：
```json
{
  "mcpServers": {
    "yoko-wechat-rpa": {
      "type": "streamableHttp",
      "url": "http://127.0.0.1:9922/mcp",
      "headers": { "Authorization": "Bearer yoko_mcp_xxxxxxxx" }
    }
  }
}
```
> 不同宿主字段略有差异（有的用 `"transport": "http"` / `"url"` 顶层 / 或 `X-Yoko-Token` 头代替 Bearer）。
> 若宿主支持「配置话术」，可让宿主 Agent 依据上面 URL + token 自行写入。

### 4.3 指导用户装配并重载
> "请把这段配置加入您宿主的 `mcp.json`（或用宿主的 MCP 添加入口填入 URL 和 token），保存后**重启/重载宿主**。重载后微信相关工具会自动出现，之后我们就能直接用了。"

在宿主重载配置后检查工具是否已注册。当前会话看不到新工具时，开启一个新会话。

### 4.4 验证连接和微信账号

1. 重载宿主，在 `tools/list` 中确认微信工具已出现。安装包默认提供 28 个工具。
2. 打开本机控制台 `http://127.0.0.1:9922/`，确认微信已登录，按页面提示刷新或初始化微信实例。
3. 调用 `wechat_list_instances`。出现已托管账号后，就能用该账号执行微信任务。列表为空时，回到控制台完成微信登录或初始化，再查询一次。

---

## 5. 用 MCP 工具驱动微信

工具的参数、使用场景和回执见 [MCP 工具文档](references/mcp-tools.md)。

**按好友标签群发**

1. 用 `wechat_list_instances` 确认发送账号。多号时由用户选定，并把账号 ID 填入 `account_id`。
2. 标签或话术组名称不清楚时，在控制台查看。已知标签时可用 `wechat_get_contacts` 带 `tag` 核对好友。群聊使用准确群名作为 `targets`。
3. 先向用户展示发送账号、目标、文案或话术组、执行时间和间隔，等用户明确确认，再调用 `wechat_mass_sending`。提交成功后用 `wechat_list_mass_sending_tasks` 查批次进度。提交结果未知时先查任务，避免重复群发。

任务状态和掉线信息可在本机控制台查看。联系人的备注名或昵称应尽量准确。

---

## 6. 生命周期 / 恢复 / 手动兜底

`yoko_rpa_mcp.exe` 内置 supervisor + 三通道自启，多数情况无需人工：

| 场景 | 恢复 |
|---|---|
| worker（RPA）崩溃/被杀 | supervisor 秒级自动重启（退出码/心跳/health 三重监控） |
| supervisor 被杀 | 计划任务 restart-on-failure + 周期复活 / 下次登录三通道自启 |
| 服务能连但卡住 | 在托盘菜单重启服务 |
| 全停 | 用户双击桌面「YoBot私域AI-MCP」，或托盘「重启服务」 |
| exe 被杀软隔离 | 引导加白名单/重装（代码签名降误报） |

**手动控制台**：服务在跑时 `http://127.0.0.1:9922/` 即完整可视化界面（与 MCP 共享同一后端状态，改动实时互通）。复杂操作可引导用户在此手动完成。

**停止服务**：沙箱内 `taskkill` 跨会话必失败（Session 隔离），别自己尝试。服务由安装器/自启常驻，正常不需要停。若确需停止/卸载，引导用户走「设置 → 应用 → 卸载『微信 RPA MCP 服务』」（卸载会清理自启并杀进程），或通过托盘菜单退出。

---

## 7. 维护备注

- **无宿主推送**：本版不做实时事件/心跳（无向宿主主动推送通道）。状态按需查询（§5 末尾）。
- **工具和场景文档**见 [MCP 工具文档](references/mcp-tools.md)。初始化、业务配置和服务管理在本机控制台或托盘完成。
- **升级**时重新运行最新的 `yoko_rpa_mcp_setup.exe`。安装器会关闭旧进程、覆盖安装并恢复开机自启。
- **鉴权两套别混**：REST setup 调用用 `X-API-Key: yoko_test`；MCP 用 `/api/mcp/token` 拿的 Bearer pairing token。
