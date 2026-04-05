# 一键配置 AI 销冠 / AI 自动回复 SOP (Standard Operating Procedure)

当用户遇到 "未同步群聊" 或 "无可用AI助理" 的错误，或者用户主动要求 "帮我一键配置 RPA / AI 销冠" 时，Agent **必须严格按照以下步骤（Step-by-Step）** 执行检查与配置。

## 前置准备：理解当前状态
如果你收到来自 `/api/chat/multi-monitor/start` 接口的错误返回（例如 `VALIDATION_FAILED`），请先解析 `accounts` 数组中的报错信息，这决定了你需要执行以下哪些步骤。

---

## Step 1: 检查并同步群聊 (Sync Groups)
*如果后端提示 `未同步群聊` 或 `超7天未同步群聊`，必须执行此步。如果状态是 `已同步过群聊`，请跳过此步。*

1. **获取所有微信账号 ID**: 如果当前上下文没有 `account_id`，请先通过相关接口或本地配置获取当前登录的微信 `account_id` 列表。
2. **调用同步接口**: 对每个未同步的账号，调用同步群聊接口。
   - **Endpoint**: `POST /api/contact/sync` (注意：这是 RPA API 工具，非配置工具)
   - **Payload**: `{"type": "group", "account_id": "对应的账号ID"}`
3. 等待接口返回成功后，继续下一步。

---

## Step 2: 检查并初始化智能体 (Agents Config)
*如果后端提示 `无可用AI助理`，说明需要从头配置。*

1. **读取现有智能体**: 调用 `wechat_get_config({ config_type: "agents" })` 获取当前智能体列表。
2. **判断是否已存在**: 检查返回的数组中是否已经存在有效的fireflow平台的智能体（如 `platform: "fireflow"` 或其他）。
   - **如果有**: 记录下该智能体的 `botId`，直接跳到 **Step 4**。
   - **如果没有**: 继续执行 **Step 3** 去申请官方模板工作流。

---

## Step 3: 向工作流平台申请官方模板 (Initialize Workflow)
*仅在 Step 2 发现没有智能体时执行。*

1. **调用外部接口**: 发起网络请求 (Web Fetch) 到工作流平台申请一键初始化。
   - **Base URL**: `https://fireflow.yokoagi.com`
   - **Endpoint**: `POST /v1/agent/apps/initialize`
   - **Headers**: 必须携带用户的登录 Token（`Authorization: Bearer <User_JWT_Token>`）。*(注：请通过上下文或授权系统获取用户的登录Token)*
2. **解析返回结果**:
   - 如果 `success: true` 且 `alreadyConfigured: false`，从 `data` 数组中获取第一个工作流的 `appName` 和 `apiKey`。
   - 如果 `alreadyConfigured: true`，说明用户其实在云端有工作流，只是本地没配置。由于接口没有返回具体的 apiKey，请中止流程，并友好地提示用户："您在 Fireflow 平台已有工作流，请前往平台手动复制 API Key 并提供给我。"

---

## Step 4: 将智能体写入 RPA 配置 (Update Agents)
*将获取到的智能体 api key 写入配置文件。*

1. 构造新的 Agent 对象：
   ```json
   {
     "id": "fireflow-<时间戳>",
     "name": "<Step 3 返回的 appName 或 默认名称>",
     "botId": "<Step 3 返回的 apiKey 或 Step 2 找到的已有 botId>",
     "platform": "fireflow",
     "isDefault": false
   }
   ```
2. 将此对象追加到 Step 2 获取到的 `agents` 数组中。
3. 调用 `wechat_update_config({ config_type: "agents", data: <新数组> })` 保存配置。
4. **记住这个 `botId`**，下一步要用。

---

## Step 5: 创建默认 AI 助理 (Update Reply Strategy)
*将刚刚配置的智能体绑定到实际的业务助理上。*

1. **读取现有策略**: 调用 `wechat_get_config({ config_type: "reply_strategy_v2" })`。
2. **追加单聊与群聊助理**: 在返回数据的 `staffList` 数组中，追加一个默认助理（chatType值为all）。
   ```json
   // 默认助理示例
   {
     "id": "staff-<时间戳>",
     "name": "通用AI助理",
     "enabled": true,
     "agentId": "<Step 4 记住的 botId>",
     "chatType": "all",
     "selectedTags": [],
     "keywords": []
   }
   ```
3. 调用 `wechat_update_config({ config_type: "reply_strategy_v2", data: <更新后的完整对象> })`。

---

## Step 6: 闭环与反馈
1. 向用户汇报："已为您自动完成群聊同步、智能体绑定以及AI助理配置，可以去尝试启动AI销冠"
2. 如果已经确认按要求配置但依然报错，请将最新的错误信息呈现给用户，并提供修复建议