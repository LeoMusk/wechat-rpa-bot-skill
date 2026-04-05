# YokoWeBot 任务执行日志系统指南 (Task Logs Schema)

本文档描述了通过 `wechat_get_task_logs` 工具获取的 RPA 任务执行日志的数据结构，以及日志文件的存储位置和内容格式。
当你需要为用户统计任务执行数据（如“今日群发了几个人”、“加了多少好友”）时，请参考本手册。

## 1. 存储位置与文件格式

所有任务日志存储于用户家目录下的 `~/.yokowebot/task_logs/` 文件夹中。
采用 **JSON Lines (JSONL)** 格式，每行一个独立的 JSON 对象，按任务类型分文件存储：

- `add_friend.jsonl`：自动加人（加好友）执行日志
- `auto_reply.jsonl`：自动回复（单聊/群聊）执行日志
- `auto_follow.jsonl`：自动跟单（新客户跟进）执行日志
- `moment_interaction.jsonl`：朋友圈互动（点赞/评论）执行日志
- `friend_request.jsonl`：自动通过好友执行日志
- `mass_sending.jsonl`：群发/推送消息执行日志

## 2. 统一日志数据结构模型 (Base Schema)

每一行 JSON 日志都包含以下标准外壳字段：

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | String | 日志单条记录唯一主键 (UUID v4) |
| `task_id` | String | **批次任务ID**（如某次群发任务ID，用于将分散的原子日志关联为一次整体任务） |
| `account_id` | String | **微信实例账号 ID** (用于区分不同微信号的数据) |
| `task_type` | String | 任务类型枚举 (`add_friend`, `auto_reply`, `auto_follow`, `moment_interaction`, `friend_request`, `mass_sending`) |
| `timestamp` | Integer| **13位毫秒级时间戳**，方便快速按时间过滤和排序 |
| `created_at` | String | **UTC+8 可读时间** (`2024-05-20T14:30:00.000+08:00`) |
| `status` | String | 单项操作的执行状态 (`success` 或 `completed` 表示成功，`failed` 表示失败) |
| `error_msg` | String | 错误信息 (仅 `status=failed` 时存在) |
| `details` | Object | **任务专属明细**（扁平化的 JSON 对象，根据 `task_type` 不同而变化，详见下文） |

## 3. 详情字段 (Details) 完整字典

### ① 自动加人 (`add_friend`)
*场景：每发送一次添加请求，记录一行。*
- `wxid`: 被添加者的微信号或手机号
- `name`: 获取到的微信昵称（可能为空或“未知”）
- `hello_msg`: 发送的验证打招呼消息
- `remark`: 预设的好友备注名
- `tags`: 预设的好友标签列表 (Array)
- `result`: 执行结果说明（如“添加成功”、“请求已发送”等）

### ② 自动回复 (`auto_reply`)
*场景：每次回复动作记录一行。*
- `session_name`: 会话名称（群聊名称，私聊则等于发信人昵称）
- `user_name`: 发送消息的人的名称
- `chat_type`: 会话类型：`single` (单聊) 或 `group` (群聊)
- `receive_msg`: 接收到的用户问题/消息内容
- `reply_msg`: AI 生成并回复的内容
- `agent_id`: 提供回复服务的 Agent ID
- `agent_name`: 提供回复服务的 Agent 名称

### ③ 自动跟单 (`auto_follow`)
*场景：每次跟单发送记录一行。*
- `friend_wxid`: 被跟单好友的 wxid
- `friend_name`: 被跟单好友的微信昵称
- `agent_id`: 生成跟单话术的 Agent ID
- `follow_scenario`: 跟单场景（如“新客户跟进”、“未成交挽回”等）
- `generated_message`: AI 最终生成并发送给该客户的跟进内容

### ④ 朋友圈评赞 (`moment_interaction`)
*场景：每操作一条朋友圈记录一行。*
- `publisher`: 朋友圈发布人的微信昵称
- `content`: 朋友圈的文字内容
- `publish_time`: 朋友圈发布时间（如“1小时前”）
- `action_type`: 实际执行的动作，包含 `"like"`(点赞) 和/或 `"comment"`(评论) (Array)
- `comment_content`: 实际评论的文本内容（当 action_type 包含 comment 时有意义）

### ⑤ 自动通过好友 (`friend_request`)
*场景：每次批量通过好友记录一行。*
- `processed_users`: 成功通过请求并处理的好友昵称/标识列表 (Array)
- `tag`: 自动为这些新好友打上的微信标签
- `greeting_group_id`: 通过后自动发送的欢迎打招呼“话术组”名称/ID
- `target_group`: 通过后自动邀请对方加入的微信群聊名称（为空表示不拉群）

### ⑥ 推送/群发消息 (`mass_sending`)
*场景：每成功发送给一个目标（好友或群），记录一行。*
- `targetName`: 群发批次的整体名称标识
- `content`: 发送的具体文本内容 / 或话术组标识
- `tagIds`: 选定的目标好友标签 ID 列表 (Array)
- `selectedFriends`: 额外勾选的具体好友名称列表 (Array)
- `contentType`: 内容类别（通常为 `"greeting"` 等）
- `agentId`: 话术组 ID 或提供内容的 Agent ID
- `type`: 消息类型（如 `"text"`）
- `progress`: 当前这条发送成功时，该批次的总进度数字
- `total`: 该批次群发计划的总人数
- `batchIndex`: 批次号（分批发送时存在）
- `totalBatches`: 总批次数（分批发送时存在）

## 4. Agent 统计分析指南
- Agent 在进行数据统计时，建议直接利用提供的工具按需过滤日志。
- 利用 `timestamp` 字段过滤当日或指定时间段数据。
- 利用 `account_id` 过滤特定微信实例。
- 统计“成功数量”时，只计算 `status` 为 `success` 或 `completed` 的记录。
