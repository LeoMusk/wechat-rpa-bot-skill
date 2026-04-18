# WeChat RPA 任务说明手册 (Task Schema)

本文档描述了通过 `wechat_get_tasks` 获取的调度器任务数据结构。
当你需要分析当前系统中有哪些任务、任务的状态是什么时，请参考本手册。

## 1. 整体返回结构示例

```json
{
  "success": true,
  "message": "获取任务列表成功",
  "data": {
    "total": 2,
    "tasks": [
      {
        "task_id": "auto_follow_wxid_xxx_20231025",
        "task_type": "auto_follow",
        "status": "scheduled",
        "next_run_time": "2023-10-25T10:00:00",
        "created_at": "2023-10-24T10:00:00",
        "updated_at": "2023-10-25T09:00:00",
        "core_params": {
           "friend_wxid": "wxid_xxx",
           "friend_name": "张三",
           "account_id": "xxx",
           "follow_scenario": "新好友",
           "start_date": "2023-10-24",
           "end_date": "2023-10-31",
           "time_range": "09:00 - 12:00",
           "agent_id": "agent_123",
           "execution_count": 1
        },
        "raw_params": { ... },
        "metadata": { ... }
      }
    ]
  }
}
```

## 2. 单个任务 (Task) 的通用字段说明

| 字段名 | 类型 | 说明 |
| --- | --- | --- |
| `task_id` | string | 任务的唯一标识符 |
| `task_type` | string | 任务的类型（详见下文） |
| `status` | string | 任务当前的执行状态（详见下文） |
| `next_run_time` | string \| null | 下一次计划执行的时间 (ISO格式)。如果为 null，可能是一次性任务已结束。 |
| `created_at` | string | 任务创建时间 (ISO格式) |
| `updated_at` | string | 任务最后更新时间 (ISO格式) |
| `core_params` | object | **[核心]** 经过清洗和提取的关键业务参数，Agent 分析任务时**应优先读取此字段**（详见下文说明）。 |
| `raw_params` | object | 原始任务执行参数兜底。 |
| `metadata` | object | 任务的调度原始元数据兜底。 |

## 3. `core_params` 提取规则说明

系统针对核心任务类型进行了参数扁平化处理，提取到 `core_params` 中：

*   **`auto_follow` (自动跟单)**：
    展平了 `friend_info` 和 `execution_strategy` 里的重要信息。
    *   `friend_wxid`: 好友微信ID
    *   `friend_name`: 好友昵称
    *   `follow_scenario`: 场景 (如"新好友")
    *   `start_date` / `end_date`: 生命周期日期
    *   `time_range`: 每天允许执行的时间段 (如 "09:00 - 12:00")
    *   `agent_id`: 绑定的跟进智能体
    *   `execution_count`: 当前已执行次数

*   **`sync_contacts` (同步通讯录)**：
    展平了 `sync_config`。
    *   `sync_items`: 同步项列表 (如群聊)
    *   `sync_frequency`: 频率
    *   `time_range`: 允许执行的时间段

*   **`auto_reply` (自动回复)**：
    从 `task_data.params` 提取。
    *   `session_id`: 会话ID
    *   `session_name`: 会话名称 (好友或群名)
    *   `account_id`: 微信号ID
    *   `is_group`: boolean，是否群聊
    *   `message_num`: 消息数量

*   **`mass_sending` (群发任务)**：
    从 `task_params` 提取并计算。
    *   `greetingGroupId`: 使用的话术组
    *   `agentId`: 关联的智能体
    *   `timeType`: 发送时间类型
    *   `tagIds`: 选中的标签ID
    *   `selectedFriends_count`: 自动计算出的选中好友总数量

## 4. 枚举值说明

### 4.1 任务类型 (`task_type`)
*   `mass_sending` - 群发任务
*   `auto_follow` - 自动跟进任务
*   `auto_reply` - 自动回复任务
*   `sync_contacts` - 同步通讯录任务

### 4.2 任务状态 (`status`)
*   `scheduled` - **已调度**，等待触发。这是正常的排队状态。
*   `running` - **执行中**，任务正在执行。
*   `pending` - **排队中**，由于并发限制正在等待资源。
*   `paused` - **已暂停**，被用户手动暂停。
*   `completed` - **已完成**，任务所有流程已结束。
*   `failed` - **失败**，任务执行过程中发生错误。

## 5. 示例分析

如果你需要判断**“哪些是等待执行的群发任务”**，你应该在 `tasks` 数组中寻找符合以下两个条件的对象：
1. `task_type` === 'mass_sending'
2. `status` === 'scheduled' 或者 `status` === 'pending'

在分析 `auto_follow`（自动跟单）任务时，你应该优先读取 `task.core_params` 里的 `friend_name` 和 `follow_scenario`，而不是去遍历 `raw_params` 里的深层嵌套结构。
