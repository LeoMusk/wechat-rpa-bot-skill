# WeChat RPA 智能体与 AI 助理配置说明 (Config Schema)

当你需要通过 `wechat_get_config` 读取配置或通过 `wechat_update_config` 修改配置时，请严格参考本手册。
RPA 服务的配置分为多种类型（`config_type`），目前支持 `agents` 和 `reply_strategy_v2`。

## 1. 整体修改原则
**强烈建议使用“覆盖式写入（Read-Modify-Write）”模式**：
在调用 `wechat_update_config` 前，必须先调用 `wechat_get_config` 获取当前的全量配置，在内存中修改对应字段后，将**整个 JSON 对象**通过 `wechat_update_config` 写回。

**⚠️ 【极其重要：防止结构嵌套】**
当调用 `wechat_get_config` 时，如果返回结果包含 `"success": true, "data": {...}` 的外层包裹，你在调用 `wechat_update_config` 写入数据时，**绝对不要**把外层的 `{"success": true, "data": ...}` 结构写进去！
你传递给 `data` 参数的值，必须是**直接的业务配置对象/数组**。
- 正确的 `data` 值（以 agents 为例）：`[{"id": "...", "name": "..."}]`
- 错误的 `data` 值：`{"success": true, "data": [{"id": "...", "name": "..."}]}`
- 正确的 `data` 值（以 reply_strategy_v2 为例）：`{"staffList": [...], "commonConfig": {...}}`
- 错误的 `data` 值：`{"success": true, "data": {"staffList": [...], "commonConfig": {...}}}`

---

## 2. 写入智能体 (`config_type: "agents"`)

此配置用于保存底层大模型平台的 API Token 或 Bot ID。

### 2.1 字段说明 (数组元素 `agents[i]`)
*   `id` (string): 智能体唯一 ID。推荐自生成唯一值（如 `fireflow-时间戳-随机数`）。
*   `name` (string): 智能体展示名称（必填）。
*   `botId` (string): 平台的 API Token 或 Bot ID（必填，后续将作为 `agentId` 使用）。
*   `platform` (enum): 平台类型，必须是 `"fireflow"`, `"coze"`, 或 `"dify"`。
*   `isDefault` (boolean): 是否默认接待。建议全局仅一个 `true`。

### 2.2 示例
```json
[
  {
    "id": "fireflow-1732527272-abcd1234",
    "name": "销冠助理",
    "botId": "YOUR_FIREFLOW_API_TOKEN",
    "platform": "fireflow",
    "isDefault": true
  }
]
```

---

## 3. 启用 AI 助理 (`config_type: "reply_strategy_v2"`)

此配置用于将上述定义的智能体绑定到具体的业务场景中（如自动回复、AI 销冠）。
它的顶层结构包含 `commonConfig` 和 `staffList` 两个字段。你需要重点修改的是 `staffList`。

### 3.1 核心字段 (`staffList[i]`)
*   `id` (string): 助理唯一 ID。
*   `name` (string): 助理名称（展示）。
*   `enabled` (boolean): 是否启用该助理（设为 `true` 即可生效）。
*   `agentId` (string): **[关键]** 引用智能体的标识，**必须完全等于** `agents` 配置中对应智能体的 `botId`！
*   `chatType` (enum): 生效的聊天类型：`"all" | "private" | "group"`。
*   `prompt` (string): 可选的自定义系统提示词。
*   `targetType` (enum): 目标类型：`"all" | "include" | "exclude"`。
*   `targetList` (string[]): 结合 `targetType` 使用（指定/排除微信备注）。
*   `targetTags` (string[]): 按标签生效。
*   `targetGroups` (string[]): 按群聊生效。

### 3.2 示例结构
```json
{
  "commonConfig": {
    "autoGreeting": { "enabled": false, "greetingGroupId": "" },
    "whitelist": { "enabled": false, "names": "", "list": [] },
    "filterWords": [],
    "fileRecognition": { "enabled": false, "fileTypes": [], "filePath": "" }
  },
  "staffList": [
    {
      "id": "1773016655938",//生成ID
      "name": "个人助理",
      "enabled": true,
      "agentId": "YOUR_FIREFLOW_API_TOKEN",//fireflow平台工作流的api token
      "chatType": "single",//single表示单聊AI助理，group表示群聊AI助理
      "selectedTags": [],//好友标签
      "keywords": [],
      "readGroupMember": false,
      "quoteReply": false
    }
  ]
}
```

---

## 4. Agent 执行完整链路建议
如果你接到任务：“帮我配置一个 Fireflow 的 AI 助理，Token 是 XXXX”：
1. **获取 Agents**: 调用 `wechat_get_config({ config_type: "agents" })`。
2. **追加 Agent**: 将新的 Fireflow 智能体（`platform: "fireflow"`, `botId: "XXXX"`）追加到数组中，调用 `wechat_update_config({ config_type: "agents", data: <新数组> })`。
3. **获取 Strategy**: 调用 `wechat_get_config({ config_type: "reply_strategy_v2" })`。
4. **追加/启用 Staff**: 在 `staffList` 中追加一个新助理，确保其 `agentId` 字段等于刚才的 `"XXXX"`，并且 `enabled: true`。然后调用 `wechat_update_config({ config_type: "reply_strategy_v2", data: <新对象> })`。
5. **(可选) 启动功能**: 如果用户要求开启 AI 销冠，配置完成后，可引导用户或自动调用启动 API。