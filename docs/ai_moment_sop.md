# AI 朋友圈 自动配置与开启 SOP (Standard Operating Procedure)

当用户要求「开启 AI 朋友圈 / 朋友圈自动点赞评论」，或开启时报错（如缺少 `interactionMode`、`agentId`）时，Agent **必须严格按本 SOP 自动帮用户完成配置并启动任务**，而不是让用户自己去后台手动配置。

> **最终目标**：根据用户要求成功调用启动接口、开启 AI 朋友圈任务。

---

## 0. 核心前提与启动接口

**核心前提**：RPA 的「智能体列表」(`agents` 配置) 里必须存在一个**能生成朋友圈评语的智能体**。该智能体的 `botId` 就是朋友圈配置要传的 `agentId`。如果用户从未绑定过这样的智能体，开启朋友圈就会报错 `缺少必传参数 interactionMode 或 agentId，且未找到历史配置`。本 SOP 的主体工作就是自动帮用户备好这个智能体。

**启动方式**：通过本技能的 **`wechat_toggle_ai_moment`** 工具开启 / 关闭。
- 开启：`wechat_toggle_ai_moment({ enabled: true, interactionMode, agentId, ...其余可选项 })`。
- 关闭：`wechat_toggle_ai_moment({ enabled: false })`。
- **必传**：`interactionMode`、`agentId`。其余可选字段不传则使用历史配置或系统默认值。
- ⚠️ **严禁**用 `shell_exec` / `curl` 手动请求 `/api/moment/toggle-auto-comment` 接口——`X-API-Key` 由工具自动处理，手动 curl 必然失败。开启动作**只能**通过 `wechat_toggle_ai_moment` 工具完成。

---

## 1. 决策总览

```
开启 AI 朋友圈请求
  │
  ├─ Step 1  读取 RPA agents 配置，判断是否已有可用朋友圈智能体
  │            ├─ 已确认有 → 记下 botId，跳到 Step 4
  │            └─ 不确定/没有 → 继续 Step 2
  │
  ├─ Step 2  workflow_list 在用户 FireFlow 空间查找「朋友圈评语」工作流
  │
  ├─ Step 3  取得该工作流的 apiKey
  │            ├─ Step 2 找到了 → workflow_get_apikey
  │            └─ Step 2 没找到 → workflow_list_official + workflow_copy_app
  │
  ├─ Step 4  将 apiKey 绑定到 RPA agents 智能体列表
  │
  ├─ Step 5  询问用户互动模式 (interactionMode)
  │
  └─ Step 6  调用启动接口开启 AI 朋友圈
            （任一 FireFlow 步骤失败 → 走「兜底：转人工」）
```

---

## Step 1: 检查现有智能体

调用 `wechat_get_config({ config_type: "agents" })` 读取智能体列表。
- 如果用户**明确说过**某个已有智能体就是用来做朋友圈评语的，或上下文能确认 → 记下它的 `botId`，直接跳到 **Step 4**（无需重复绑定，直接用于启动）。
- 仅凭名称通常**无法可靠判断**某智能体是否擅长朋友圈评语。**默认情况下继续 Step 2**，在 FireFlow 侧按工作流确认，更可靠。

---

## Step 2: 在用户 FireFlow 空间查找朋友圈工作流

调用 `workflow_list` 获取用户当前所有 FireFlow 工作流。

在返回的工作流里**按语义匹配**「朋友圈 / 评语 / 点评 / moment」相关的工作流。
> ⚠️ **不要写死工作流名称**。官方目前的朋友圈工作流名为「微信朋友圈智能评语生成」，但名称可能调整，请根据 `name` + `description` 语义判断，不要做精确字符串匹配。

- **找到** → 记下该工作流的 `appId`，进入 **Step 3 路线 A**。
- **没找到** → 进入 **Step 3 路线 B** 从官方示例空间复制。

---

## Step 3: 取得朋友圈工作流的 apiKey

朋友圈配置要用的 `agentId` 来自工作流的 apiKey，按 Step 2 的结果走对应路线。

### 路线 A：用户空间已有该工作流（Step 2 找到了）

调用 `workflow_get_apikey({ appId: "<Step 2 的 appId>" })`：
- 该工作流已有 apiKey → 返回现有的；没有 → 自动生成一个。
- 返回 `{ appId, apiKey }`，记下 `apiKey`，进入 **Step 4**。

### 路线 B：用户空间没有（Step 2 没找到）

1. 调用 `workflow_list_official` 浏览官方示例空间，在返回结果里**按语义**找到朋友圈评语工作流（同 Step 2，不要写死名称），记下其 `appId`。
2. 调用 `workflow_copy_app({ appId: "<上一步的官方 appId>" })`：该工具会把工作流复制到用户空间、自动发布并生成 apiKey。
3. 返回 `{ appId, appName, apiKey }`，记下 `apiKey`，进入 **Step 4**。

> 任一步骤失败（找不到官方工作流、复制报错等）→ 不要反复重试，转「兜底：转人工」。

---

## Step 4: 绑定到 RPA 智能体列表

把 apiKey 写入 RPA 的 `agents` 配置（与 AI 销冠一键配置完全一致的做法）：

1. `wechat_get_config({ config_type: "agents" })` 取当前智能体数组。
2. 追加一个新智能体对象：
   ```json
   {
     "id": "fireflow-<时间戳>",
     "name": "朋友圈智能评语",
     "botId": "<Step 3 拿到的 apiKey>",
     "platform": "fireflow",
     "isDefault": false
   }
   ```
3. `wechat_update_config({ config_type: "agents", data: <追加后的完整数组> })` 保存。
4. **记住这个 `botId`**（即 apiKey），它就是下面启动接口要传的 `agentId`。

---

## Step 5: 询问互动模式 (interactionMode)

`interactionMode` 是启动的**必传参数**，直接问用户想要哪种模式：

| interactionMode | 行为 |
| :--- | :--- |
| `like_only` | 仅点赞（全部点赞，不评论） |
| `comment_only` | 仅评论（有评语才评，不点赞） |
| `like_and_comment` | 评论才点赞（有评语时才评论并点赞） |
| `like_always_and_comment` | 点赞 + 评论（必点赞，有评语再评论） |

其余参数**不必询问**，不传即用默认值；仅当用户主动提出要求时才设置（字段含义见文末附录）。

---

## Step 6: 启动 AI 朋友圈

调用 **`wechat_toggle_ai_moment`** 工具开启任务：

```
wechat_toggle_ai_moment({
  "enabled": true,
  "interactionMode": "<Step 5 用户选择的模式>",
  "agentId": "<Step 4 记住的 botId / apiKey>"
})
```

- 返回 `success: true` 即开启成功，向用户汇报：「已为您自动绑定朋友圈智能体并开启 AI 朋友圈（互动模式：xxx）」。
- ⚠️ **不要**用 `shell_exec` / `curl` 调接口；开启动作只能通过 `wechat_toggle_ai_moment` 工具完成。
- 若工具返回报错，将错误信息原样呈现给用户，并对照本 SOP 检查是哪一步未完成。

---

## 兜底：转人工接管

FireFlow 相关步骤（Step 3 取 apiKey / 复制工作流）**任一步失败**时，不要反复重试，改为引导用户手动操作：

> 「自动复制朋友圈工作流没有成功，需要您手动操作一下：
> 1. 打开 YokoAgent 左侧菜单的「FireFlow」。
> 2. 在官方示例中找到朋友圈评语相关的工作流（当前名为「微信朋友圈智能评语生成」），复制到您自己的空间。
> 3. 打开复制后的工作流，生成 / 复制它的 API Key，把 API Key 粘贴发给我。」

拿到用户粘贴的 apiKey 后，从 **Step 4** 继续（绑定 → 询问模式 → 启动）。

---

## 附录：wechat_toggle_ai_moment 参数说明

以下为 `wechat_toggle_ai_moment` 工具的参数。仅当用户主动要求调整时才设置；否则不传，走默认值。

| 参数名 | 类型 | 含义 | 默认 / 可选值 |
| :--- | :--- | :--- | :--- |
| **interactionMode** | string | **互动模式（必传）**，见 Step 5 | 见 Step 5 四种取值 |
| **agentId** | string | **生成评语的智能体（必传）**，即 RPA `agents` 中对应智能体的 `botId` | 见 Step 4 |
| **commentLimit** | int | **总评论上限**：单次任务最多评论的好友总数 | 默认 `100` |
| **perFriendLimit** | int | **单好友次数**：单次任务对同一好友最多评论几次，防刷屏 | 默认 `2` |
| **checkInterval** | int | **循环间隔(分钟)**：本次任务结束后等待多久再跑下一轮 | 默认 `120` |
| **reachLastPosition** | string | 滚动到上次已处理位置时的处理方式 | `stop`（终止本轮，推荐）/ `continue`（跳过继续） |
| **autoLike** | bool | 是否自动点赞 | 默认 `false` |
| **blacklist** | string | 黑名单（不互动的好友） | 默认空 |
| **selectedTags** | array | 只评论带选中标签的好友朋友圈 | `[]`（不限制） |
| **multiCycleEnabled** | bool | 多微信循环：登录多个微信时是否对指定账号循环评论 | 默认 `false` |
| **selectedAccounts** | array | `multiCycleEnabled=true` 时，参与循环的微信 `account_id` 数组 | `[]` |

---

## 附录：FireFlow 工作流相关接口与工具

本 SOP 用到的 `workflow` 技能工具及其对应的 FireFlow 接口（Base URL `https://fireflow.yokoagi.com`，工具会自动注入用户登录态）：

| 操作 | `workflow` 技能工具 | 底层接口 |
| :--- | :--- | :--- |
| 列出用户工作流 | `workflow_list` | `GET /v1/agent/apps` |
| 浏览官方示例空间 | `workflow_list_official` | `GET /v1/apps?type=official` |
| 复制工作流到用户空间（含发布+生成apiKey） | `workflow_copy_app({ appId })` | `POST /v1/agent/apps/copy` |
| 取/建工作流 apiKey | `workflow_get_apikey({ appId })` | `GET` / `POST /v1/apps/:id/api-tokens` |
