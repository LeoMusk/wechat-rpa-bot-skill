---
name: wechat-rpa-bot
description: Onboard and drive the yoko WeChat RPA MCP server. Use this skill to install yoko_rpa_mcp.exe, start it, activate the license, wire its local MCP endpoint into the host (mcp.json), and then use WeChat automation through the MCP tools it exposes.
---

# WeChat RPA Bot Skill (MCP edition)

This skill turns any MCP-capable host (OpenClaw / QClaw / WorkBuddy …) into a WeChat assistant by
**onboarding the local yoko WeChat RPA MCP server** and then driving WeChat through its MCP tools.

**心智模型（务必先理解）**
- 微信自动化能力由 `yoko_rpa_mcp.exe` 在用户桌面(Session 1)常驻提供，端口 **9922**，同一进程三门面：
  - `/mcp` — Streamable-HTTP **MCP 端点**（本技能的主通道，Bearer token 鉴权）
  - `/api/*` — REST（本技能只在**安装/激活/取 token**等 setup 步骤用它）
  - `/` — 可视化控制台（手动兜底）
- **本技能不直接发微信**：它负责把 MCP server 装好、拉起、激活、把 `/mcp` + token 写进宿主的 `mcp.json`。
  一旦宿主重载配置，~27 个微信工具就**原生**出现在宿主里，之后由宿主 Agent 直接调用。
- Agent **绝不能自己 spawn 这个 exe**：被 spawn 的进程会继承沙箱/会话隔离，看不见微信桌面。exe 必须由
  用户在自己的交互会话里启动（首启一次；之后 exe 自注册开机自启，自动复活）。

---

## 0. 端到端流程总览

```
安装 exe ──▶ 用户首启(Session 1) ──▶ 健康检查(REST) ──▶ 激活 license(REST)
   └──▶ 取 MCP token(REST) ──▶ 生成 mcp.json ──▶ 用户粘贴+重载宿主 ──▶ 验活(MCP tools/list)
        ──▶ 之后所有微信能力走 MCP 工具(自带 read_manual 手册)
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
   - 安装器会自动：① 把程序装到 Program Files；② **以普通用户身份**（非管理员，落在用户交互会话 Session 1）立即启动服务 `--supervisor --no-ui`；③ 注册**三通道开机自启**（登录计划任务 + HKCU Run 键 + 启动文件夹）；④ 建桌面/开始菜单图标 **「微信 RPA MCP 服务」**。
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
> "请双击桌面上的 **「微信 RPA MCP 服务」** 图标启动它（或从开始菜单打开）。启动后**无需回复我**，我会自动检测到就绪并继续。"

然后继续轮询 `/api/health`。仍不行则问用户是否有报错弹窗，或参考 §6 恢复手段。

**开机自启**：安装器已注册三通道自启 + 崩溃自愈守护，**下次开机自动就绪**，用户日常无需手动启停。

---

## 3. 激活 License（走 REST，setup 操作）

先探一次初始化状态以判断是否已激活：
```
GET  http://127.0.0.1:9922/api/license/machine-code   → 拿本机 machine_code
```
- 若服务返回**已激活**（后续 MCP 连接不返回 403）→ 跳到 §4。
- 若**未激活**：
  1. 告诉用户：「软件尚未激活。请前往 **www.yokoagi.com** 获取激活码，拿到后发我，我来自动激活。」
  2. 用户给码后：
     ```
     POST http://127.0.0.1:9922/api/license/activate
     Body: { "activation_code": "<用户提供>", "machine_code": "<step 1>" }
     ```
  3. 成功即可继续。MCP 端点每次连接会校验 license（未激活/过期 → 403 并回传 machine_code）。

> 注：REST 的 setup 调用需带 `X-API-Key: yoko_test`（localhost 关代理）。MCP 通道用的是另一套 Bearer token，见 §4，别混。

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
- 若返回 `404 { code: "MCP_DISABLED" }`：说明当前 exe 非 MCP 版（正常应下载 `yoko_rpa_mcp.exe`）。

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

**重要**：本 skill 会话**当场无法**调用刚配好的 MCP 工具——宿主需重载配置后，工具才在**新会话**里原生可用。这是 MCP 的固有机制，不是故障。

### 4.4 验活
用户重载后，在新会话让宿主 Agent：
- 列工具：应能看到 `wechat_*` 系列 ~27 个工具（`tools/list`）。
- 调 `wechat_license_info` → 返回 `licensed / machine_code / agent_id`，确认授权与归属正常。
- 调 `wechat_rpa_read_manual` with `{ "topic": "index" }` → 拿到手册目录，确认手册可读。

---

## 5. 用 MCP 工具驱动微信（重载后）

**纪律：复杂能力先读手册再调用。** 工具描述里对 SOP 类工具设了 gate「你必须先 `wechat_rpa_read_manual({topic})`」。手册已打进 exe（`mcp_manuals/`），通过 `wechat_rpa_read_manual` 读取，**不要臆造参数**。

**能力地图（意图 → 工具 → 先读手册）**

| 意图 | MCP 工具 | 先读手册 topic |
|---|---|---|
| 发文本消息 | `wechat_send_message` | — |
| 发文件 | `wechat_send_file` | — |
| 发**真实语音气泡** | `wechat_send_voice` / `wechat_list_voices` | `voice_send_sop` |
| 发朋友圈 / 定时朋友圈 | `wechat_post_moment` / `wechat_create_moment_plan` / `wechat_create_moment_post_task` / `wechat_cancel_moment_post_task` | `moment_post_sop` |
| AI 自动朋友圈开关 | `wechat_toggle_ai_moment`（无独立手册，参数见工具描述；配 agent 参考 `config_schema`） | — |
| 群发 | `wechat_mass_sending` | — |
| 加好友 / 通过好友 SOP | （相关工具，见 tools/list） | `auto_add_friend_sop` |
| 读联系人 / 同步联系人 | `wechat_get_contacts` / `wechat_sync_contacts` | — |
| 拉最新消息 | `wechat_fetch_latest_messages` | — |
| 群聊总结 / 会话历史 | `wechat_list_sessions` / `wechat_get_session_messages` | `group_summary_sop` |
| 配置读写 | `wechat_get_config` / `wechat_update_config` | `config_schema` |
| 任务与日志 | `wechat_get_tasks` / `wechat_get_task_logs` | `task_schema` / `task_log_schema` |
| 多实例本地账号 | `wechat_list_local_users` | `multi_instance_sop` |
| 初始化微信 | `wechat_initialize` | `basic_setup_checklist` |
| 打开手动控制台 | `wechat_open_console` → 返回 `http://127.0.0.1:9922/` | — |
| 授权/归属排查 | `wechat_license_info` | — |
| 服务自愈 | `wechat_service_status` / `wechat_restart_service` / `wechat_launch_wechat` | — |

> exe 内实际手册（`wechat_rpa_read_manual` 的合法 topic）：`index`、`basic_setup_checklist`、`multi_instance_sop`、`voice_send_sop`、`moment_post_sop`、`group_summary_sop`、`auto_add_friend_sop`、`config_schema`、`task_schema`、`task_log_schema`。工具名/参数以宿主实际 `tools/list` 为准。

**发消息最佳实践（提醒宿主 Agent）**：直接用用户给的联系人备注名/昵称即可，RPA 会模糊匹配，**不要**先查 wxid，不要用相似名替代。

> **无后台事件推送**：本版不提供主动通知/心跳（不存在实时事件推送通道）。任务失败、掉线、AI 配置错误等状态请**按需查询**——需要时调 `wechat_service_status` / `wechat_get_task_logs`，或引导用户打开控制台（`wechat_open_console`）查看。**不要**向用户承诺"出问题会自动提醒"。

---

## 6. 生命周期 / 恢复 / 手动兜底

`yoko_rpa_mcp.exe` 内置 supervisor + 三通道自启，多数情况无需人工：

| 场景 | 恢复 |
|---|---|
| worker（RPA）崩溃/被杀 | supervisor 秒级自动重启（退出码/心跳/health 三重监控） |
| supervisor 被杀 | 计划任务 restart-on-failure + 周期复活 / 下次登录三通道自启 |
| 服务能连但卡住 | 宿主调 `wechat_restart_service`（经 9921 控制通道重启 worker） |
| 全停 | 用户双击桌面「启动微信RPA」，或托盘「重启服务」 |
| exe 被杀软隔离 | 引导加白名单/重装（代码签名降误报） |

**手动控制台**：服务在跑时 `http://127.0.0.1:9922/` 即完整可视化界面（与 MCP 共享同一后端状态，改动实时互通）。复杂操作可引导用户在此手动完成。

**停止服务**：沙箱内 `taskkill` 跨会话必失败（Session 隔离），别自己尝试。服务由安装器/自启常驻，正常不需要停。若确需停止/卸载，引导用户走「设置 → 应用 → 卸载『微信 RPA MCP 服务』」（卸载会清理自启并杀进程），或让用户在任务管理器结束 `yoko_rpa_mcp.exe`（注意开机自启会再次拉起，彻底停用需卸载或用 §6 的 `wechat_restart_service` 之外的手段）。

---

## 7. 维护备注

- **无宿主推送**：本版不做实时事件/心跳（无向宿主主动推送通道）。状态按需查询（§5 末尾）。
- **手册以 exe 内为准**：SOP/schema 手册打进 `yoko_rpa_mcp.exe`，经 `wechat_rpa_read_manual` 读取；本 skill 仓不再维护 REST 版 `docs/`。合法 topic 见 §5 表下的清单。
- **工具清单以运行时 `tools/list` 为准**：当前版本 27 个工具（已实测）。exe 升级由重新运行最新 `yoko_rpa_mcp_setup.exe` 完成（安装器识别升级、关旧实例、重装并复位自启）。
- **鉴权两套别混**：REST setup 调用用 `X-API-Key: yoko_test`；MCP 用 `/api/mcp/token` 拿的 Bearer pairing token。
