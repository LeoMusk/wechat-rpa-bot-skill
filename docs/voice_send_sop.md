# 发送微信语音消息 SOP (Standard Operating Procedure)

当用户要求「用语音回复」「发条语音消息」「用我的声音说一段话」「克隆音色发语音」等场景时,Agent 应通过 `POST /api/agent/chat/send_voice` 接口发送**真实的微信语音气泡**(不是 mp3 文件附件)。本 SOP 说明:何时该用、入参怎么选、环境怎么校验、失败怎么回退。

> ⚠️ **本接口发的是语音气泡,不是文件**。和 `/api/chat/send_file` 完全不同:前者走 VB-Cable + RPA 流程,接收方看到的是绿色语音气泡;后者只是把 mp3 当文件发,接收方看到的是文件下载链接。

---

## 0. 环境前置(硬要求)

调用本接口**必须**同时满足:

| 条件 | 缺失后果 | 备注 |
| :--- | :--- | :--- |
| 微信客户端版本 ≥ 4.1.9 | 接口返回 `success:false` | 旧版微信不支持本路径 |
| VB-Cable 虚拟音频驱动已安装 | 接口返回 `success:false` | 用户需手动从 https://vb-audio.com/Cable/ 下载并装好 + 重启 |
| 已有可用的克隆音色 (S_xxx) | 模式 3 (text+voiceId) 不可用 | 用户需在 RPA 端 UI「AI 语音配置 → 我的音色」添加并校验通过 |

**Agent 不应主动尝试安装 VB-Cable**,这是用户在 RPA 客户端 UI 中完成的一次性配置。

---

## 1. 决策总览:何时用语音?

```
用户请求场景
  │
  ├─ 明确说「用语音」「语音消息」「克隆音色发」 → 用 /api/agent/chat/send_voice
  ├─ 模糊请求「回复客户某条话术」 → 默认用 /api/chat/send_message(文本)
  │     ⤷ 除非上下文清楚开启了语音回复偏好
  ├─ 群发场景 → 走 /api/agent/mass_sending + 话术组,**不要**直接循环调 send_voice
  │     ⤷ 话术组可在 RPA UI 中预存语音素材
  └─ 内容含图片/链接/复杂混排 → 用 /api/chat/send_message(语音不适合非纯文本)
```

> **本质判断**:文本路径默认更稳;语音是有特定情境(温度感、个性化营销、客户专属)才用的进阶手段。

---

## 2. 三种输入模式:怎么挑?

| 模式 | 入参 | 适用场景 | 优先级 |
| :--- | :--- | :--- | :---: |
| **1. audioPath** | `"audioPath": "D:/xxx.mp3"` | Agent 已经预生成了 mp3,有现成文件 | 高 |
| **2. audioFilename** | `"audioFilename": "abc.mp3"` | 用户已在 RPA UI 里上传/录制好素材,要发预录内容 | 中 |
| **3. text + voiceId** | `"text": "...", "voiceId": "S_xxx"` | **最常用**:动态内容,用克隆音色现合现发 | 默认 |

**优先级规则**(同时传时按序选):`audioPath > audioFilename > (text + voiceId)`。

> 大多数场景都用 **模式 3**:你已经知道要说什么,直接给文字和音色 id 就行,后端会合成 + 发送 + 清理临时文件。

---

## 3. voiceId 怎么拿(模式 3 必看)

**绝对不要编造 voiceId,也不要让用户去翻 Speaker ID。** 正确做法是查接口:

### 标准流程

```python
import requests

proxies = {"http": None, "https": None}
headers = {"X-API-Key": "yoko_test"}

# 1. 拉可用音色列表
r = requests.get("http://127.0.0.1:9922/api/agent/voice/voices",
                 headers=headers, proxies=proxies)
result = r.json()
# → { "success": true, "data": [
#       { "voiceId": "S_xxx", "displayName": "小目温柔女声", "language": "zh", "createdAt": ... },
#       { "voiceId": "S_yyy", "displayName": "Leo 本人声音", "language": "zh", "createdAt": ... },
#     ], "count": 2 }

# 2. 把 displayName 列表呈现给用户挑选
# 3. 用户选定后,把对应的 voiceId 传进 send_voice
```

### 用户已经指定了某个音色的情况

如果用户说「用我那个『小目』的音色」,你仍然要先调 `GET /api/agent/voice/voices`,然后**在结果里按 displayName 模糊匹配**「小目」,拿到真实的 `voiceId` 再调用。不要凭空编 id。

### 返回结果的三种情况(务必区分)

⚠️ **不要把"接口失败"和"没有音色"混为一谈**:

| 返回 | 含义 | 该怎么告诉用户 |
| :--- | :--- | :--- |
| `success: true, count: N > 0` | 正常,有 N 个可用音色 | 列出 displayName 让用户选 |
| `success: true, count: 0` | **用户真的还没克隆过音色** | 「您还没有克隆音色,请先到 RPA 设置 → AI 语音配置 → 我的音色 添加一个」 |
| HTTP 4xx/5xx | **RPA 后端缺少这个端点或服务异常** | 「音色查询接口暂时不可用,请确认 RPA 服务是最新版本」 |
| 连不上(ConnectionError) | **RPA 后端没起** | 「无法连接 RPA 后端,请确认服务正在运行」 |

判定方法:**先看 HTTP 状态码,再看 `success`** — `success:true` 时才看 `count`;否则永远不要告诉用户"没有可用音色"。

---

## 4. 完整调用流程

### Step 1 — 确定模式

按用户上下文挑模式 1/2/3,准备入参。

### Step 2 — 校验 voiceId(模式 3)

如果选了模式 3,**必须**通过 `GET /api/agent/voice/voices` 取得真实存在的 voiceId(见 Section 3)。不要让用户输入 S_xxx。

### Step 3 — 调用发送接口

```python
import requests

proxies = {"http": None, "https": None}
headers = {"X-API-Key": "yoko_test", "Content-Type": "application/json"}

payload = {
    "user": "客户张三",                  # 必填:收件人精确名称
    "text": "您好,关于您之前咨询的方案,我整理好了",
    "voiceId": "S_FcZmbgm32",
    "speed": 1.1,                        # 可选,默认 1.0
    # "accountId": "wxid_xxx",           # 多账号时才需要
}

r = requests.post("http://127.0.0.1:9922/api/agent/chat/send_voice",
                  headers=headers, json=payload, proxies=proxies, timeout=60)
result = r.json()
```

### Step 4 — 看返回结果

成功 `{ "success": true, "message": "语音发送成功", "data": ... }` → 告诉用户「已发送」。

失败 `{ "success": false, "error": "..." }` → **不要重试**,看错误信息走 Section 5。

---

## 5. 失败兜底策略

`/api/agent/chat/send_voice` 失败时,**默认应回退到文本发送**(`/api/chat/send_message`),并向用户说明。

按错误信息分类处理:

| error 关键词 | 含义 | 处理 |
| :--- | :--- | :--- |
| `版本 < 4.1.9` / `wechat_build` | 微信版本太低 | 提示用户升级微信,本次走文本回退 |
| `VB-Cable` / `未检测到` | 用户机器没装 VB-Cable | 提示用户安装(给链接),本次走文本回退 |
| `INVALID_API_KEY` / `合成失败` | 语音模型 API Key 异常 | 提示用户去 RPA 设置 → AI 语音配置 检查凭证 |
| `voice_id` / `音色不存在` | voiceId 错误 | 让用户确认音色 id,或换一个 voiceId 重试 |
| `audioPath 文件不存在` / `audioFilename` | 文件丢失 | 走模式 3 即时合成,或让用户重新提供 |
| 默认实例 / `account_id` | 多账号场景下没指定发送方 | 调 `/api/agent/instances_status` 拿 account_id 再带上 |

**回退伪代码**:
```
result = POST /api/agent/chat/send_voice { user, text, voiceId }
if (!result.success):
    告知用户「语音发送失败:<error>,已改用文本回复」
    POST /api/chat/send_message { user, message: text }
```

---

## 6. 注意事项

- **音色克隆需用户提前在 RPA UI 完成**:Agent 没有创建音色的接口,只能用已有的 `S_xxx`。
- **时长上限 60 秒**:模式 3 文本太长会被后端拒绝(返回 `时长超过 60s 上限`)。一段话术控制在 200 字以内一般稳。
- **同账号不要并发调**:VB-Cable 临时切默认麦克风时是串行的,并发会互相打架。如果要批量发,串行调用,每条之间间隔 1~2 秒。
- **群发用 mass_sending**:循环单条 send_voice 既慢又脆;批量场景用 `/api/agent/mass_sending` 配合预录语音话术组。
- **语音不适合混排消息**:如果智能体回复里有图片 / 链接 / 文件标记,**不要强转语音**,走文本路径让后端正常拆分发送。
- **接口响应时长**:本接口同步阻塞 ~5-10 秒(切麦克风 + 录音 + 发送),`timeout` 至少 30 秒,推荐 60 秒。

---

## 7. 附录:相关接口

| 操作 | 接口 (Base `http://127.0.0.1:9922`, 需 `X-API-Key`) |
| :--- | :--- |
| **列出可用克隆音色(必备前置)** | `GET /api/agent/voice/voices` |
| 发送语音 | `POST /api/agent/chat/send_voice` |
| 失败回退 | `POST /api/chat/send_message` |
| 群发场景 | `POST /api/agent/mass_sending` |

---

## 8. 反例(不要这么做)

❌ **编造 voiceId 试运气 / 让用户手输 S_xxx**
```python
# 反例 a:直接编一个
requests.post(".../send_voice", json={"user": "张三", "text": "你好", "voiceId": "S_abc123"})

# 反例 b:对话里追问"请输入 voiceId(S_xxx 格式)"
# 用户体验灾难,而且记不住会拼错

# ✅ 正确做法:先列出,让用户按名称选
voices = requests.get(".../api/agent/voice/voices").json()["data"]
# → 把 [v["displayName"] for v in voices] 呈现给用户,等用户选完拿对应 voiceId
requests.post(".../send_voice", json={"user": "张三", "text": "你好", "voiceId": voices[0]["voiceId"]})
```

❌ **把语音当兜底重试机制**
```python
result = requests.post(".../send_message", ...).json()
if not result["success"]:
    requests.post(".../send_voice", ...)  # 文本都发不了,语音更不可能成功
```

❌ **混排内容强转语音**
```python
# 智能体回复包含 ![](image.jpg) 和正文混排
requests.post(".../send_voice", json={"user": user, "text": "看下图...\n![](image.jpg)\n..."})
# 图片标记会被当成文字读出来,效果灾难
```

❌ **群发循环调用**
```python
for user in 500_users:
    requests.post(".../send_voice", json={"user": user, "text": text, "voiceId": vid})
    # 每条 5~10s,500 人需要 1 小时,且并发竞争 VB-Cable 麦克风路由
# 改用 /api/agent/mass_sending + 预录话术组
```
