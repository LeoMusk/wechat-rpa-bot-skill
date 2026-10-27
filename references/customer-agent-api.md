# 企业自定义智能体 API 接入规范

[返回项目说明](../README.md#open-interfaces) · [YoBot 官网](https://yobot.yokoagi.com) · [MCP 工具接口](mcp-tools.md)

企业按本文实现消息处理 API，并在 YoBot 的 RPA 配置中接入。RPA 主动将微信消息交给企业服务，再根据返回结果执行回复或仅完成消息投递。企业可以在服务内部调用自己的知识库、CRM、订单系统或工作流；这些业务逻辑由企业实现。

本文定义的是企业侧接口，不是供外部程序调用的微信 REST 管理接口，也不等同于通用模型 API。已有智能体平台需按本规范适配请求和响应。

## 阅读导航

- [文档说明与最小接入流程](#1-文档说明)。
- [接入地址与鉴权](#2-接入地址与安全要求)、[接口清单](#3-接口清单)。
- [能力探测](#4-能力探测)、[消息结构与入站附件](#5-消息处理接口)。
- [同步回复](#6-同步回复模式)、[异步回复](#7-异步任务回复模式)、[只消费消息](#8-只消费消息模式)。
- [图片和文件回复](#9-图片和文件-url)、[投递确认](#10-回复投递确认)。
- [错误响应](#11-错误响应规范)、[幂等与可靠性](#12-幂等与可靠性要求)、[联调示例](#13-联调示例)。
- [上线验收](#14-上线验收清单)、[兼容性](#15-兼容性说明)。

## 版本信息

版本：`1.2`

协议版本：`1`

更新日期：`2026-09-18`

更新内容：支持以 Base64 携带入站图片（最多 4 张）及文档提取文本，详见第 5.8 节。文档输入需要微信 BOT 插件 v2.0.0 或以上。

## 1. 文档说明

本文档用于指导客户自建 AI 平台接收 RPA 客户端采集的会话消息，并按业务需要返回自动回复结果或仅消费消息。

接口调用方向均为：

```text
YoBot 的 RPA 客户端 → 企业平台 API
```

客户平台不需要连接 RPA 的 WebSocket，也不需要回调 RPA 或将 RPA 暴露到公网。耗时任务采用 `HTTP 202 + jobId`，由 RPA 主动轮询客户平台。

### 1.1 支持的接入模式

|模式|配置值|客户平台最低实现范围|RPA 是否发送微信回复|
|---|---|---|---|
|同步回复|`sync_reply`|`GET /v1/capabilities`、`POST /v1/chat`|是|
|异步任务回复|`async_reply`|同步模式端点及 `GET /v1/jobs/{jobId}`|任务完成后发送|
|只消费消息|`consume_only`|`GET /v1/capabilities`、`POST /v1/chat`|否|

投递确认接口 `POST /v1/deliveries/{deliveryId}/ack` 为可选增强能力，建议生产环境实现。

### 1.2 最小接入流程

1. 在企业服务中实现 `GET /v1/capabilities`，声明协议版本 `"1"` 和 `auto_reply` 场景，最小响应见第 4.4 节。
2. 实现 `POST /v1/chat`：校验鉴权和请求参数，按 `idempotencyKey` 去重，再调用企业业务逻辑。同步回复使用第 6.1 节的 `action`、`segments` 结构。
3. 在客户端的 RPA 配置页填写企业服务 Base URL、Bearer Token 和对应的智能体 ID，使用同步回复模式。若能力接口返回 `profiles`，其 ID 必须与配置一致。
4. 先使用第 13 节的示例联调接口，再在测试会话中验证微信消息接收与回复。需要异步处理、只消费消息或投递确认时，再实现相应扩展。

同一业务消息的重试必须返回已有结果，避免重复执行业务操作。远程企业服务需可从 RPA 所在电脑通过 HTTPS 访问，无需将 RPA 本机服务暴露到公网。

## 2. 接入地址与安全要求

### 2.1 Base URL

客户在 RPA 配置页填写客户平台的服务根地址，例如：

```text
https://agent-api.example.com
```

RPA 会在该地址后拼接本文档定义的标准路径。Base URL 不应包含查询参数、片段、账号或密码。

远程服务必须使用有效的 HTTPS 证书。本机环回地址可以使用 HTTP，例如 `http://127.0.0.1:3000`。

### 2.2 Bearer Token

远程客户平台必须使用 Bearer Token 鉴权。RPA 对本文档中的所有客户接口发送：

```http
Authorization: Bearer <customer-token>
```

建议每个客户、每个部署环境使用独立的高强度随机 Token，并支持定期轮换。Token 不应写入 URL、响应正文或业务日志。

### 2.3 通用格式

|项目|约定|
|---|---|
|请求与响应编码|UTF-8|
|JSON Content-Type|`application/json`|
|时间戳|Unix 时间戳，单位为秒|
|字段命名|camelCase|
|API 版本|URL 中使用 `/v1`|
|超时|RPA 配置范围为 1–300 秒|
|网络重试|同一次重试保持 `requestId` 和 `idempotencyKey` 不变|

## 3. 接口清单

|方法|路径|必需性|说明|
|---|---|---|---|
|`GET`|`/v1/capabilities`|必需|能力探测、智能体和场景校验|
|`POST`|`/v1/chat`|必需|接收消息，返回同步结果、异步任务或接收确认|
|`GET`|`/v1/jobs/{jobId}`|异步模式必需|查询异步任务状态及最终结果|
|`POST`|`/v1/deliveries/{deliveryId}/ack`|可选|接收微信侧最终投递结果|

## 4. 能力探测

### 4.1 请求

```http
GET /v1/capabilities HTTP/1.1
Host: agent-api.example.com
Accept: application/json
Authorization: Bearer <customer-token>
```

请求无正文。

### 4.2 成功响应

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "protocolVersion": "1",
  "stateless": true,
  "scenes": [
    "auto_reply"
  ],
  "profiles": [
    {
      "id": "rpa-reply",
      "name": "默认回复"
    }
  ],
  "deliveryAcknowledgement": {
    "pathTemplate": "/v1/deliveries/{deliveryId}/ack",
    "itemLevel": false
  },
  "asyncReply": {
    "statusPathTemplate": "/v1/jobs/{jobId}"
  },
  "inputAttachments": {
    "schemaVersion": "1",
    "maxRequestBytes": 4194304,
    "images": {
      "transports": [
        "inline_base64"
      ],
      "mimeTypes": [
        "image/jpeg",
        "image/png",
        "image/webp"
      ],
      "maxFiles": 4,
      "maxFileBytes": 524288,
      "maxTotalBytes": 2097152
    },
    "documents": {
      "transports": [
        "extracted_text"
      ],
      "extensions": [
        "txt",
        "md",
        "csv",
        "json",
        "xml",
        "pdf",
        "docx",
        "xlsx"
      ],
      "maxFiles": 5,
      "maxFileBytes": 10485760,
      "maxTotalBytes": 20971520,
      "maxCharsPerFile": 24000,
      "maxTotalChars": 60000
    }
  }
}
```

### 4.3 响应字段

|字段|类型|必需|说明|
|---|---|---|---|
|`protocolVersion`|string|是|当前填写 `"1"`|
|`stateless`|boolean|否|表示平台是否可以仅依赖每次请求完成处理|
|`twoPhase`|boolean|否|是否会在 `sync_reply` 的 `auto_reply` 场景返回显式 `phase: 1/2`；不需要时省略或填 `false`|
|`scenes`|string[]|否|支持的场景；返回时必须包含当前使用场景|
|`profiles`|object[]|否|平台提供的智能体或业务处理配置|
|`profiles[].id`|string|是|智能体 ID，需与 RPA 配置一致|
|`profiles[].name`|string|否|展示名称|
|`deliveryAcknowledgement`|object|否|声明支持投递确认|
|`deliveryAcknowledgement.pathTemplate`|string|是|当前固定为 `/v1/deliveries/{deliveryId}/ack`|
|`deliveryAcknowledgement.itemLevel`|boolean|否|当前版本仅回传整体状态，建议填写 `false`|
|`asyncReply`|object|异步模式是|声明支持异步任务回复|
|`asyncReply.statusPathTemplate`|string|异步模式是|当前必须严格填写 `/v1/jobs/{jobId}`|
|`inputAttachments`|object|否|声明接收入站图片或文档文本；不声明时 RPA 严格保持旧版纯文本请求|
|`inputAttachments.schemaVersion`|string|是|当前填写 `"1"`|
|`inputAttachments.maxRequestBytes`|integer|否|平台可接收的完整 JSON 请求体上限；RPA 仍受本地 4 MiB 硬上限约束|
|`inputAttachments.images`|object|否|图片内联能力，见 5.8 节|
|`inputAttachments.documents`|object|否|文档文本能力，见 5.8 节|

如果 `profiles` 非空，RPA 会验证配置的智能体 ID 是否存在。如果 `scenes` 非空，自动回复场景必须包含 `auto_reply`。

### 4.4 最小响应

同步回复或只消费模式可以返回：

```json
{
  "protocolVersion": "1",
  "scenes": ["auto_reply"]
}
```

## 5. 消息处理接口

### 5.1 请求

```http
POST /v1/chat HTTP/1.1
Host: agent-api.example.com
Content-Type: application/json
Accept: application/json
Authorization: Bearer <customer-token>
```

同步模式配置为 SSE 时，`Accept` 为 `text/event-stream`；自动识别模式可能为 `application/json, text/event-stream`。异步模式固定请求 JSON。

### 5.2 请求示例

```json
{
  "requestId": "29d29b27-314f-4ba0-ad28-d7f05c96e3d5",
  "idempotencyKey": "4b997cd81a1e5a0040a185f49e87a12c19e81491cd5de4384770c714d04cfe4f",
  "profileId": "rpa-reply",
  "scene": "auto_reply",
  "conversation": {
    "accountId": "account-001",
    "sessionId": "session-001",
    "source": "rpa",
    "scopeId": "account-001",
    "sessionName": "客户群",
    "isGroup": true,
    "stateless": false,
    "memoryMode": "conversation"
  },
  "identity": {
    "userName": "张三",
    "friendTags": "高意向"
  },
  "messages": [
    {
      "id": "message-001",
      "role": "user",
      "content": "请问今天能发货吗？",
      "contentType": "text",
      "senderName": "张三",
      "timestamp": 1787378400
    }
  ]
}
```

### 5.3 顶层字段

|字段|类型|必需|说明|
|---|---|---|---|
|`requestId`|string|是|本次调用 ID；同一次网络重试保持不变|
|`idempotencyKey`|string|自动回复是|业务幂等键；客户平台必须据此去重|
|`profileId`|string|是|RPA 配置的智能体或业务处理配置 ID|
|`scene`|string|是|业务场景，见场景枚举|
|`conversation`|object|是|会话坐标及记忆策略|
|`identity`|object|是|当前发言人及客户标签|
|`messages`|object[]|是|当前消息及可用的历史消息，至少一条|
|`attachments`|object[]|否|当前轮附件；只有平台在能力接口中显式声明后才发送|

### 5.4 scene 场景枚举

|值|说明|
|---|---|
|`auto_reply`|自动回复，当前客户接口对接的主要场景|
|`moment_comment`|朋友圈评论生成|
|`follow_up`|跟单内容生成|
|`greeting`|打招呼内容生成|

客户平台只需在能力接口中声明实际支持的场景。未声明或不支持的场景应返回明确的业务错误。

### 5.5 conversation 字段

|字段|类型|必需|说明|
|---|---|---|---|
|`accountId`|string|是|微信实例账号标识，用于账号级隔离|
|`sessionId`|string|是|当前会话标识|
|`source`|string|是|当前固定为 `rpa`|
|`scopeId`|string|是|当前与 `accountId` 一致，作为平台侧隔离范围|
|`sessionName`|string\|null|否|好友昵称或群名称|
|`isGroup`|boolean|是|`true` 表示群聊|
|`stateless`|boolean|是|`true` 表示本次请求不应写入长期会话记忆|
|`memoryMode`|string|是|`conversation` 或 `none`|

平台侧会话键建议使用：

```text
profileId + accountId + sessionId
```

不能只用 `sessionName` 作为会话键，因为不同账号可能存在同名好友或群聊。

### 5.6 identity 字段

|字段|类型|必需|说明|
|---|---|---|---|
|`userName`|string\|null|否|当前发言人名称；群聊时通常为群成员名称|
|`friendTags`|string|否|RPA 可用的好友标签，无标签时为空字符串|

### 5.7 messages 字段

|字段|类型|必需|说明|
|---|---|---|---|
|`id`|string|否|稳定消息 ID；建议用于平台侧消息去重|
|`role`|string|是|`user` 或 `assistant`|
|`content`|string|是|消息文本|
|`contentType`|string|是|当前为 `text`|
|`senderName`|string|否|消息发送者名称，群聊消息建议使用|
|`timestamp`|number|否|Unix 时间戳，单位秒|

重要约定：

- `messages` 可能只有当前一条消息，客户平台不能假设历史消息始终完整。

- 历史消息的作用是同步或冷启动上下文，不应替代客户平台自己的可靠会话存储。

- 远程客户平台当前不会收到 RPA 主机上的本地文件路径。

- 未声明入站附件能力时，图片或文件可能只有文本占位信息。启用第 5.8 节的可选能力后，图片与文档提取文本通过顶层 `attachments` 传入，原始文档文件不上传。

- `messages[].content` 永远只保存原始用户文本或原有消息占位信息；文件解析文本不会拼入该字段。

- 附件只描述当前轮输入，不会随历史消息窗口反复发送。

### 5.8 入站图片和文档附件

附件能力是 APP v1 的可选扩展。平台必须在 `GET /v1/capabilities` 中显式声明对应 transport，RPA 才会在 `POST /v1/chat` 增加顶层 `attachments`：

> 本节只适用于真正的远程客户 API。直连本机 YokoAgent（loopback 地址）继续沿用既有本地文件路径方案：图片放在 `messages[].images`，文档使用 `source.type=local_path`；本次扩展不会把本机链路改成 Base64 或本地提取文本。
>
>

- 图片 transport：`inline_base64`

- 文档 transport：`extracted_text`

- 未声明 `inputAttachments`、能力探测失败或使用旧版能力响应：完全保持升级前的请求结构，不发送 `attachments`。

- 只声明其中一种 transport：RPA 只发送该类型附件。

- 平台声明的限制大于 RPA 本地硬上限时，以本地硬上限为准；声明更小限制时，以平台限制为准。

#### 5.8.1 图片附件

```json
{
  "id": "4db74b...",
  "messageId": "message-001",
  "kind": "image",
  "name": "image.jpg",
  "mimeType": "image/jpeg",
  "sizeBytes": 932114,
  "sha256": "原始图片的 SHA-256",
  "source": {
    "type": "inline_base64",
    "encoding": "base64",
    "data": "/9j/4AAQSkZJRg...",
    "dataBytes": 428312,
    "dataSha256": "实际 Base64 解码后图片的 SHA-256"
  }
}
```

字段说明：

|字段|类型|说明|
|---|---|---|
|`id`|string|本次附件稳定标识；当前取发送载荷摘要|
|`messageId`|string|关联的当前用户消息 ID；可能省略|
|`kind`|string|固定为 `image`|
|`name`|string|文件名；实际格式以 `mimeType` 为准|
|`mimeType`|string|实际发送图片的 MIME，可能与微信原图不同|
|`sizeBytes`|integer|微信原始本地图片的字节数|
|`sha256`|string|原始图片摘要|
|`source.data`|string|纯 Base64 字符串，不包含 `data:image/...;base64,` 前缀|
|`source.dataBytes`|integer|Base64 解码后的实际载荷字节数|
|`source.dataSha256`|string|实际发送载荷摘要，可用于完整性校验和去重|

图片限制：

- 支持识别 JPG/JPEG、PNG、WEBP、GIF、BMP；平台可通过 `mimeTypes` 声明其中的子集。

- 单轮最多 4 张图片。

- 微信原始单图最大 15 MiB；超过后忽略该图片但不阻断文本消息。

- 图片最大 4,000 万像素；超过后忽略该图片，避免异常压缩图占用过多内存。

- 实际发送的单图二进制最大 512 KiB，合计最大 2 MiB。

- Base64 会增加约三分之一体积；包含消息和文档后的完整 JSON 最大 4 MiB。

- 超限图片会在本地使用现有 Pillow 能力缩放或转换，不引入新的图像依赖。

- 平台应至少允许能力响应中 `maxRequestBytes` 对应的请求体，并避免在网关层使用过小的默认 body limit。

平台需要提交给视觉模型时，可自行转换为模型常见的 data URL：

```text
data:{mimeType};base64,{source.data}
```

#### 5.8.2 文档文本附件

RPA 不上传原文件，也不依赖 OSS。文档在 RPA 本机有界解析后，以独立字段发送：

```json
{
  "id": "attachment-002",
  "messageId": "message-002",
  "kind": "document",
  "name": "报价单.xlsx",
  "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "sizeBytes": 183211,
  "sha256": "原始文档的 SHA-256",
  "source": {
    "type": "extracted_text",
    "format": "text",
    "text": "--- Sheet: 报价 ---\n产品A\t100",
    "status": "success",
    "extractedChars": 31,
    "truncated": false
  }
}
```

文档字段说明：

|字段|类型|说明|
|---|---|---|
|`kind`|string|固定为 `document`|
|`sizeBytes`|integer|原文件字节数，不是提取文本长度|
|`sha256`|string|原文件摘要|
|`source.type`|string|固定为 `extracted_text`|
|`source.format`|string|当前固定为 `text`；Excel 使用 Sheet 标记和制表符保留基础结构|
|`source.text`|string|独立的文件提取文本，可能为空|
|`source.status`|string|`success`、`truncated`、`no_text`、`unsupported` 或 `failed`|
|`source.extractedChars`|integer|实际发送的文本字符数|
|`source.truncated`|boolean|是否因上下文预算被截断|
|`source.errorCode`|string|可选诊断码，例如 `scanned_or_empty_pdf`、`parser_unavailable`、`extract_failed`|

支持的文档格式：

- 纯文本：TXT、Markdown、CSV、JSON、XML。

- 文档：PDF、DOCX。

- 表格：XLSX。

- 暂不支持旧版 XLS、DOC、PPT/PPTX、压缩包、音视频以及加密文档。

- 扫描版或纯图片 PDF 暂不执行 OCR，通常返回 `status: no_text`。

文档限制：

- 单轮最多 5 个文档。

- 单文件最大 10 MiB，原文件合计最大 20 MiB。

- 每个文档最多 24,000 字符，所有文档合计最多 60,000 字符。

- XLSX 使用只读模式并在达到字符预算时停止，不会先把整份工作簿拼入内存。

- 任一文件解析失败都不会阻断原始文本请求。

#### 5.8.3 文本隔离与安全

- 客户平台必须分别读取 `messages` 和 `attachments`，不得假设文档文本已拼入用户问题。

- `source.text` 属于不可信用户数据。拼接模型上下文时应使用明确的附件边界，不得把文档里的文字当作系统指令。

- RPA 日志不会记录 Base64 或完整文档文本；客户平台也不应把完整附件写入网关访问日志。

- 远程 Provider 必须使用 HTTPS。Bearer Token、图片和文件文本不得通过明文 HTTP 传输。

- `consume_only` 为保证断网重试，可能把完整请求加密保存在本机可靠队列，投递成功后立即删除；同步回复和异步任务坐标模式不额外持久化附件请求体。

## 6. 同步回复模式

### 6.1 JSON 回复

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "action": "reply",
  "segments": [
    "您好，可以的。",
    "今天 18:00 前会发出。"
  ],
  "deliveryId": "delivery-20260822-001"
}
```

### 6.2 回复字段

|字段|类型|必需|说明|
|---|---|---|---|
|`action`|string|是|`reply`、`no_reply` 或 `defer`|
|`segments`|string[]|`reply` 时是|按顺序返回的文本、图片 URL 或文件 URL|
|`reason`|string|否|`no_reply` 或 `defer` 的原因，仅用于诊断|
|`deliveryId`|string|否|稳定投递 ID；实现 ACK 时应提供|
|`deliveryItems`|object[]|否|预留的回复项坐标；当前 ACK 仍为整体状态|

`deliveryId` 规则：

- 长度不超过 128 个字符。

- 建议仅使用字母、数字、`-`、`_`、`.`、`:`。

- 同一业务回复必须保持稳定，不能每次重试都重新生成。

### 6.3 不回复

```json
{
  "action": "no_reply",
  "reason": "该消息只需内部归档"
}
```

### 6.4 暂缓自动回复

```json
{
  "action": "defer",
  "reason": "需要人工确认价格"
}
```

当前版本将 `defer` 按“不发送自动回复”处理，不会启动独立的人工接管流程。

### 6.5 SSE 回复

同步模式可以返回 SSE。未使用两阶段回复时，旧格式保持兼容：

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
```

```text
event: message
data: {"action":"reply","segments":["您好，可以的。"],"deliveryId":"delivery-20260822-001"}

event: done
data: {}
```

约束：

- `data:` 必须是合法的 JSON 对象。

- 未携带 `phase` 的 `message` 按旧协议处理：RPA 读取第一条后立即结束，不产生额外等待。

- JSON 回复、`async_reply` 和 `consume_only` 模式不支持下面的同连接两阶段语义。

#### 6.5.1 自动回复的两阶段回复

仅 `sync_reply` 的自动回复场景支持最多两个阶段。客户平台可先返回一条简短安抚话术，待最终答案生成后再返回第二阶段：

```text
event: message
data: {"phase":1,"action":"reply","segments":["问题已收到，正在查询，请稍候。"],"deliveryId":"delivery-001-phase-1"}

event: message
data: {"phase":2,"action":"reply","segments":["这是最终答案。"],"deliveryId":"delivery-001-phase-2"}
```

协议规则：

- `phase` 只能为数字 `1` 或 `2`，顺序必须是 `1`、可选的 `2`，每轮最多各一条 `message`。

- `phase: 1` 是简短安抚话术，只允许纯文本；不要在第一阶段返回图片、文件、话术组、转发或其他控制指令。

- 收到 `phase: 1` 后，RPA 会立即串行发送；收到 `phase: 2` 后即视为本轮终态，发送完成后结束任务，不要求再返回 `done`。

- 如果不需要第二阶段，应在 `phase: 1` 后立即发送 `done`。否则 RPA 会等待第二阶段，最长 300 秒。

- 300 秒是绝对超时，从第一阶段最后一条微信消息发送完成开始计算；SSE 注释、心跳或其他事件不会续期。

- RPA 保证第二阶段的第一条微信消息与第一阶段最后一条微信消息至少间隔 3 秒；第二阶段过快时由 RPA 补足等待。

- 开启引用回复时，只引用本轮第一条实际发送的文本。第一阶段已引用后，第二阶段不会重复引用。

- 每个阶段如需可靠 ACK，应使用各自独立且稳定的 `deliveryId`。

- 不需要两阶段能力的旧接口不要添加 `phase`，即可继续保持“首条回复后立即结束”的原行为。

只有第一阶段的完整示例：

```text
event: message
data: {"phase":1,"action":"reply","segments":["问题已收到，我们会尽快处理。"]}

event: done
data: {"status":"completed"}
```

## 7. 异步任务回复模式

### 7.1 接收任务

客户平台收到 `POST /v1/chat` 后完成可靠入队，再返回：

```http
HTTP/1.1 202 Accepted
Content-Type: application/json
```

```json
{
  "status": "accepted",
  "jobId": "job-20260822-001",
  "retryAfterSeconds": 5,
  "expiresInSeconds": 3600
}
```

|字段|类型|必需|说明|
|---|---|---|---|
|`status`|string|否|建议填写 `accepted`|
|`jobId`|string|是|客户平台任务 ID，最长 128 个字符|
|`retryAfterSeconds`|integer|否|建议的首次查询间隔，RPA 会限制在 2–300 秒|
|`expiresInSeconds`|integer|否|任务有效期；RPA 最长保存 72 小时|

同一个 `idempotencyKey` 被重复提交时，客户平台必须返回同一个 `jobId`。如果同一幂等键返回不同任务 ID，RPA 会拒绝覆盖原任务。

### 7.2 查询任务

```http
GET /v1/jobs/{jobId} HTTP/1.1
Host: agent-api.example.com
Accept: application/json
Authorization: Bearer <customer-token>
```

`jobId` 由 RPA 进行 URL 编码后放入路径。

### 7.3 处理中响应

方式一，返回 HTTP 202：

```http
HTTP/1.1 202 Accepted
Content-Type: application/json
Retry-After: 10
```

```json
{
  "status": "processing",
  "retryAfterSeconds": 10
}
```

方式二，返回 HTTP 200：

```json
{
  "status": "processing",
  "retryAfterSeconds": 10
}
```

处理中状态可使用 `pending`、`processing` 或 `accepted`。

### 7.4 完成响应

```http
HTTP/1.1 200 OK
Content-Type: application/json
```

```json
{
  "status": "completed",
  "result": {
    "action": "reply",
    "segments": [
      "处理完成，请查收结果。",
      "https://cdn.example.com/results/report.pdf"
    ],
    "deliveryId": "delivery-20260822-001"
  }
}
```

`result` 使用与同步回复完全相同的结构。客户平台也可以在 HTTP 200 响应中直接返回 `action`、`segments` 对象，但推荐使用带 `status` 和 `result` 的标准结构。

### 7.5 失败或取消

```json
{
  "status": "failed",
  "error": "模型服务暂时不可用"
}
```

或：

```json
{
  "status": "cancelled",
  "error": "任务已由操作人员取消"
}
```

`failed` 和 `cancelled` 被视为终态，RPA 不再轮询该任务。

### 7.6 RPA 恢复规则

- 任务坐标、最终结果和回复项发送进度会加密持久化。

- RPA 重启后继续轮询尚未完成的任务。

- 临时网络故障按退避策略重试，默认最多失败 12 次、最长 72 小时。

- 每个回复组件发送成功后保存进度，以减少部分成功后的重复发送。

- 用户停止自动回复或停用对应账号后，迟到结果不会继续发送。

## 8. 只消费消息模式

只消费模式用于把消息交给客户平台内部处理，但不需要 RPA 自动回复。

客户平台完成可靠接收或可靠入队后，返回任意 `2xx`：

```http
HTTP/1.1 202 Accepted
Content-Type: application/json
```

```json
{
  "accepted": true
}
```

RPA 在请求客户平台前会先把消息可靠保存到本地队列：

- 任意 `2xx`：认为客户平台已接收，结束本次流程。

- 超时、连接失败、`408`、`425`、`429` 或 `5xx`：后台继续重试。

- 其他 `4xx`：进入死信，等待修正配置后人工重试。

- 重启 RPA 后，未完成消息继续投递。

客户平台必须在可靠保存消息后再返回 `2xx`，并始终按 `idempotencyKey` 去重。

## 9. 图片和文件 URL

客户平台需要让 RPA 发送图片或文件时，将可访问的 HTTP(S) URL 作为独立元素放入 `segments`：

```json
{
  "action": "reply",
  "segments": [
    "这是您需要的文件：",
    "https://cdn.example.com/files/quotation-20260822.pdf"
  ]
}
```

URL 要求：

- 必须能从运行 RPA 的机器直接访问。

- 建议使用 HTTPS。

- 如果资源需要鉴权，请使用有效期足够长的签名 URL；RPA 不会为文件下载附加客户自定义请求头。

- 建议 URL 路径包含明确扩展名，并正确返回 `Content-Type` 和 `Content-Disposition`。

- URL 有效期应覆盖任务轮询和失败重试窗口；异步任务建议至少覆盖实际业务 SLA。

- 普通网页 URL 会作为文本发送，只有被识别为图片或文件的 URL 才会下载并发送。

当前建议使用的常见类型：

- 图片：JPG、JPEG、PNG、GIF、WEBP、BMP。

- 文件：PDF、DOC/DOCX、XLS/XLSX、PPT/PPTX、TXT、RTF。

本期不支持客户平台在回复中返回 RPA 本地路径、Base64 文件内容或自定义文件上传协议。

## 10. 回复投递确认

客户平台在能力响应中声明 `deliveryAcknowledgement`，并在同步或异步回复中提供稳定的 `deliveryId` 后，RPA 会回传最终处理状态。

### 10.1 请求

```http
POST /v1/deliveries/{deliveryId}/ack HTTP/1.1
Host: agent-api.example.com
Content-Type: application/json
Accept: application/json
Authorization: Bearer <customer-token>
```

发送成功、明确不回复或暂缓时：

```json
{
  "status": "delivered"
}
```

微信发送失败、用户取消或账号被停用时：

```json
{
  "status": "failed"
}
```

### 10.2 响应

客户平台成功记录 ACK 后返回任意 `2xx`：

```http
HTTP/1.1 204 No Content
```

### 10.3 ACK 幂等要求

- `deliveryId` 是 ACK 的幂等键。

- 同一个 `deliveryId` 可能因网络重试收到多次相同状态。

- 极端情况下，未成功投递的 `failed` 可能在业务重放成功后更新为 `delivered`，平台应以最终状态为准。

- ACK 会在 RPA 本地可靠排队；客户平台短暂不可用或 RPA 重启不会直接丢失待确认记录。

微信发送和 HTTP ACK 无法组成跨系统原子事务。客户平台仍应保留按 `idempotencyKey`、`jobId` 和 `deliveryId` 查询投递账本的能力。

## 11. 错误响应规范

业务错误建议使用统一结构：

```json
{
  "error": {
    "code": "PROFILE_NOT_FOUND",
    "message": "未找到对应智能体"
  }
}
```

推荐状态码：

|HTTP 状态码|场景|RPA 处理建议|
|---|---|---|
|`200`|同步成功、任务完成或任务仍在处理|按响应结构解析|
|`202`|只消费已接收、异步任务已接单或仍在处理|按当前配置模式处理|
|`204`|ACK 已记录|成功|
|`400`|JSON 或字段格式错误|不自动重试|
|`401`|Token 缺失或无效|不自动重试，修正配置|
|`403`|无权限访问 profile 或场景|不自动重试，修正权限|
|`404`|profile 或 job 不存在|任务查询时视为终止错误|
|`409`|幂等键冲突|不自动重试，人工检查|
|`422`|业务参数无法处理|不自动重试|
|`425`|服务尚未准备好|可重试|
|`429`|触发限流|可重试，建议提供 `Retry-After`|
|`500`|平台内部错误|可重试|
|`502`、`503`、`504`|临时服务或网关错误|可重试|

错误响应、网关日志和应用日志均不得输出 Bearer Token 或完整敏感消息正文。

## 12. 幂等与可靠性要求

客户平台至少需要维护以下三个标识：

|标识|生成方|用途|
|---|---|---|
|`requestId`|RPA|一次 HTTP 调用及其网络重试追踪|
|`idempotencyKey`|RPA|一次业务消息处理去重|
|`deliveryId`|客户平台|一次最终回复投递及 ACK 去重|

异步模式另外维护：

|标识|生成方|用途|
|---|---|---|
|`jobId`|客户平台|异步任务查询；同一 `idempotencyKey` 必须稳定|

推荐客户平台处理流程：

1. 校验 Bearer Token、JSON 结构、`profileId` 和 `scene`。

2. 使用 `idempotencyKey` 查询已有处理记录。

3. 已处理时返回原同步结果或原 `jobId`，不要重复调用模型和业务系统。

4. 未处理时先创建幂等账本，再执行同步处理或可靠入队。

5. 为最终回复生成稳定的 `deliveryId`。

6. 记录 RPA 回传的 ACK，支持人工按标识排查。

## 13. 联调示例

### 13.1 能力探测

```bash
curl -X GET "https://agent-api.example.com/v1/capabilities" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer CUSTOMER_TOKEN"
```

### 13.2 发送测试消息

```bash
curl -X POST "https://agent-api.example.com/v1/chat" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer CUSTOMER_TOKEN" \
  -d '{
    "requestId":"test-request-001",
    "idempotencyKey":"test-message-001",
    "profileId":"rpa-reply",
    "scene":"auto_reply",
    "conversation":{
      "accountId":"account-001",
      "sessionId":"session-001",
      "source":"rpa",
      "scopeId":"account-001",
      "sessionName":"测试客户",
      "isGroup":false,
      "stateless":false,
      "memoryMode":"conversation"
    },
    "identity":{
      "userName":"测试客户",
      "friendTags":""
    },
    "messages":[{
      "id":"message-001",
      "role":"user",
      "content":"你好",
      "contentType":"text"
    }]
  }'
```

### 13.3 查询异步任务

```bash
curl -X GET "https://agent-api.example.com/v1/jobs/job-20260822-001" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer CUSTOMER_TOKEN"
```

## 14. 上线验收清单

* [ ] 远程 Base URL 使用有效 HTTPS 证书。

* [ ] 所有端点正确校验 Bearer Token。

* [ ] `/v1/capabilities` 返回协议版本、场景和正确的 profile。

* [ ] 固定 `idempotencyKey` 重复请求不会重复处理。

* [ ] `sync_reply` 能正确返回文本回复。

* [ ] `no_reply` 和 `defer` 不产生微信消息。

* [ ] `consume_only` 在可靠入队后返回 `2xx`。

* [ ] 如启用异步模式，同一幂等键始终返回相同 `jobId`。

* [ ] 如启用异步模式，处理中、完成、失败和取消状态均符合本文档。

* [ ] 图片或文件 URL 能从 RPA 运行机器直接访问，且有效期满足业务 SLA。

* [ ] 如启用 ACK，重复 ACK 可幂等处理。

* [ ] `429`、`503` 和超时场景不会造成重复业务处理。

* [ ] 日志不输出 Token、完整敏感消息或不必要的个人信息。

## 15. 兼容性说明

- 未启用 `async_reply` 的现有同步 provider 不需要实现任务查询接口。

- 未声明 `deliveryAcknowledgement` 时，不要求实现 ACK 接口。

- 只消费模式可以与同步/异步回复模式使用同一套消息请求结构。

- 当前不需要 WebSocket，也没有客户平台到 RPA 的公网回调接口。

- 后续协议新增字段时，客户平台应忽略无法识别的可选字段，以保持向前兼容。
