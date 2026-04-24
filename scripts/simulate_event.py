"""
simulate_event.py — 向 ws_listener 注入模拟事件，用于本地测试。

用法：
  python scripts/simulate_event.py                  # 交互式菜单
  python scripts/simulate_event.py ai_config_coze   # 直接注入指定场景
  python scripts/simulate_event.py list             # 打印所有可用场景

可用场景：
  ai_config_coze        Coze token 失效 (ai.config_error)
  ai_config_fireflow    Fireflow 401 认证失败 (ai.config_error)
  ai_service_error      Fireflow 服务调用失败 (ai.service_error)
  task_failed           群发任务失败 (task.failed)
  task_completed        群发任务完成 (task.completed)
  wechat_disconnected   微信账号掉线 (wechat.disconnected)
  wechat_error          微信账号严重错误 (wechat.error)
  manual_action         登录需手动点击头像 (wechat.manual_action_required)
  action_required       AI 回复等待审核 (action.required)
"""

import json
import sys
import time
import uuid
import requests

LISTENER_URL = "http://127.0.0.1:9923"
PROXIES = {"http": None, "https": None}

# ─────────────── event templates ───────────────

def _corr():
    return f"corr_debug_{uuid.uuid4().hex[:6]}"

def _evt():
    return f"dbg_{uuid.uuid4().hex[:8]}"

SCENARIOS = {

    "ai_config_coze": {
        "_desc": "Coze token 失效 → ai.config_error",
        "event": "ai.config_error",
        "correlationId": _corr(),
        "context": {
            "service": "coze",
            "agentId": "bot_7412345678901234567",
        },
        "payload": {
            "errorCode": "COZE_4100",
            "errorMessage": "身份验证无效",
            "configKey": "token 无效，请在 coze.cn → 个人设置 → API 密钥中重新生成并更新",
            "isRetryable": False,
        },
        "actions": [],
    },

    "ai_config_fireflow": {
        "_desc": "Fireflow 401 认证失败 → ai.config_error",
        "event": "ai.config_error",
        "correlationId": _corr(),
        "context": {
            "service": "fireflow",
        },
        "payload": {
            "errorCode": "HTTP_401",
            "errorMessage": "Unauthorized",
            "configKey": "token 无效或已过期，请检查 Fireflow 配置",
            "isRetryable": False,
        },
        "actions": [],
    },

    "ai_service_error": {
        "_desc": "Fireflow 服务调用失败 → ai.service_error",
        "event": "ai.service_error",
        "correlationId": _corr(),
        "context": {
            "service": "fireflow",
        },
        "payload": {
            "errorCode": "FIREFLOW_1001",
            "errorMessage": "工作流执行超时，请稍后重试",
            "configKey": "请检查 Fireflow 智能体配置",
            "isRetryable": False,
        },
        "actions": [],
    },

    "task_failed": {
        "_desc": "群发任务失败（可重试）→ task.failed",
        "event": "task.failed",
        "correlationId": "corr_mass_sending_test001_run1",
        "context": {
            "taskId": "mass_sending_test001",
            "taskType": "mass_sending",
        },
        "payload": {
            "status": "failed",
            "errorCode": "ERR_TASK_FAILED",
            "errorCategory": "transient",
            "errorMessage": "群发任务执行失败：微信频率限制，建议等待后重试",
            "isRetryable": True,
        },
        "actions": [
            {
                "actionId": "retry",
                "label": "重试任务",
                "command": "task.retry",
                "params": {"taskId": "mass_sending_test001"},
            },
            {
                "actionId": "abort",
                "label": "终止任务",
                "command": "task.abort",
                "params": {"taskId": "mass_sending_test001"},
            },
        ],
    },

    "task_completed": {
        "_desc": "群发任务完成 → task.completed",
        "event": "task.completed",
        "correlationId": "corr_mass_sending_test002_run1",
        "context": {
            "taskId": "mass_sending_test002",
            "taskType": "mass_sending",
        },
        "payload": {
            "status": "completed",
            "current": 50,
            "total": 50,
        },
        "actions": [],
    },

    "wechat_disconnected": {
        "_desc": "微信账号掉线 → wechat.disconnected",
        "event": "wechat.disconnected",
        "correlationId": _corr(),
        "context": {
            "accountId": "wxid_test123456",
            "accountNickname": "营销号01（测试）",
        },
        "payload": {
            "disconnectReason": "unknown",
            "accountId": "wxid_test123456",
            "nickname": "营销号01（测试）",
            "autoReconnectEnabled": True,
        },
        "actions": [
            {
                "actionId": "check_accounts",
                "label": "查询账号状态",
                "command": "query.accounts",
                "params": {},
            }
        ],
    },

    "wechat_error": {
        "_desc": "微信账号严重错误 → wechat.error",
        "event": "wechat.error",
        "correlationId": _corr(),
        "context": {
            "accountId": "wxid_test123456",
            "accountNickname": "营销号01（测试）",
        },
        "payload": {
            "status": "error",
            "errorCode": "ERR_INSTANCE_ERROR",
            "errorMessage": "账号 营销号01（测试）报告错误，需要检查",
            "isFatal": True,
        },
        "actions": [
            {
                "actionId": "check_accounts",
                "label": "查询账号状态",
                "command": "query.accounts",
                "params": {},
            }
        ],
    },

    "manual_action": {
        "_desc": "登录需手动点击头像（紧急，10秒窗口）→ wechat.manual_action_required",
        "event": "wechat.manual_action_required",
        "correlationId": _corr(),
        "context": {},
        "payload": {
            "action": "click_avatar",
            "message": "【测试】未找到微信个人信息窗口，请在10秒内手动点击微信头像以继续登录",
            "timeoutSeconds": 10,
        },
        "actions": [
            {
                "actionId": "notify_user",
                "label": "提醒用户",
                "description": "请用户在微信中手动点击头像",
            }
        ],
    },

    "action_required": {
        "_desc": "AI 回复等待 Agent 审核 → action.required",
        "event": "action.required",
        "eventId": f"evt_req_{uuid.uuid4().hex[:12]}",
        "correlationId": _corr(),
        "context": {
            "accountId": "wxid_test123456",
            "accountNickname": "客服号01（测试）",
            "taskId": "auto_reply_test789",
            "taskType": "auto_reply",
        },
        "payload": {
            "question": "AI 已为会话「测试用户」生成回复，是否发送？",
            "pendingContent": "您好，感谢您的咨询！我们的产品功能丰富，可以满足您的需求。请问您具体关注哪方面呢？",
            "userQuestion": "你们产品怎么样？",
            "targetSession": "测试用户",
            "riskLevel": "low",
            "timeoutSeconds": 25,
            "defaultAction": "approve",
        },
        "actions": [
            {
                "actionId": "approve",
                "label": "批准发送",
                "command": "action.approve",
                "params": {
                    "eventId": "evt_req_simulated",
                    "taskId": "auto_reply_test789",
                    "sessionName": "测试用户",
                },
            },
            {
                "actionId": "reject",
                "label": "拒绝跳过",
                "command": "action.reject",
                "params": {
                    "eventId": "evt_req_simulated",
                    "taskId": "auto_reply_test789",
                    "sessionName": "测试用户",
                },
            },
        ],
    },
}

# ─────────────── helpers ───────────────

def check_listener():
    try:
        r = requests.get(f"{LISTENER_URL}/health", proxies=PROXIES, timeout=3)
        h = r.json()
        connected = h.get("connected", False)
        pending = h.get("pendingEvents", 0)
        status = "✓ 已连接到 yokowebot" if connected else "⚠ 未连接到 yokowebot（事件仍可注入）"
        print(f"[Listener] 状态: {status}")
        print(f"[Listener] 当前待处理事件数: {pending}")
        return True
    except Exception as e:
        print(f"[错误] 无法连接到 ws_listener (http://127.0.0.1:9923): {e}")
        print("请确认 ws_listener.py 正在运行。")
        return False


def inject(scenario_key: str) -> bool:
    scenario = SCENARIOS.get(scenario_key)
    if not scenario:
        print(f"[错误] 未知场景: {scenario_key}")
        return False

    desc = scenario.pop("_desc", scenario_key)
    try:
        r = requests.post(
            f"{LISTENER_URL}/debug/inject",
            json=scenario,
            proxies=PROXIES,
            timeout=5,
        )
        result = r.json()
        if result.get("injected"):
            print(f"\n✓ 注入成功")
            print(f"  场景   : {desc}")
            print(f"  事件   : {result.get('event')}")
            print(f"  事件ID : {result.get('eventId')}")
        else:
            print(f"[失败] {result}")
        return result.get("injected", False)
    except Exception as e:
        print(f"[错误] 注入请求失败: {e}")
        return False


def show_events():
    try:
        r = requests.get(f"{LISTENER_URL}/events", proxies=PROXIES, timeout=3)
        events = r.json().get("events", [])
        if not events:
            print("\n[队列] 暂无待处理事件")
            return
        print(f"\n[队列] 当前待处理事件 ({len(events)} 条):")
        for ev in events:
            sev = ev.get("severity", "?")
            sev_icon = {"urgent": "🔴", "error": "🟠", "warning": "🟡", "info": "🔵"}.get(sev, "⚪")
            print(f"  {sev_icon} [{sev:7s}] {ev['event']:<35s} id={ev['id']}")
    except Exception as e:
        print(f"[错误] 获取事件失败: {e}")


def interactive_menu():
    print("\n" + "="*55)
    print("  yokowebot WebSocket 事件模拟器")
    print("="*55)
    items = list(SCENARIOS.items())
    for i, (key, val) in enumerate(items, 1):
        desc = val.get("_desc", key)
        print(f"  {i:2d}. {desc}")
    print("   q. 退出")
    print("-"*55)

    while True:
        show_events()
        print()
        choice = input("请输入序号注入事件 (或 q 退出): ").strip()
        if choice.lower() == "q":
            break
        try:
            idx = int(choice) - 1
            key = items[idx][0]
            # Re-fetch fresh scenario (avoid mutation on repeated inject)
            fresh = json.loads(json.dumps(SCENARIOS[key]))
            fresh.pop("_desc", None)
            r = requests.post(
                f"{LISTENER_URL}/debug/inject",
                json=fresh,
                proxies=PROXIES,
                timeout=5,
            )
            result = r.json()
            desc = items[idx][1].get("_desc", key)
            if result.get("injected"):
                print(f"\n✓ 已注入: {desc} (eventId={result.get('eventId')})")
            else:
                print(f"[失败] {result}")
        except (ValueError, IndexError):
            print("无效输入，请重新选择。")
        except Exception as e:
            print(f"[错误] {e}")

        time.sleep(0.3)


# ─────────────── entry point ───────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if not check_listener():
        sys.exit(1)

    if not args:
        interactive_menu()
        sys.exit(0)

    if args[0] == "list":
        print("\n可用场景：")
        for key, val in SCENARIOS.items():
            print(f"  {key:<25s} {val.get('_desc', '')}")
        sys.exit(0)

    # 直接注入指定场景
    key = args[0]
    fresh = json.loads(json.dumps(SCENARIOS.get(key, {})))
    fresh.pop("_desc", None)
    if not fresh:
        print(f"[错误] 未知场景: {key}")
        print("运行 `python scripts/simulate_event.py list` 查看可用场景")
        sys.exit(1)

    ok = inject(key)
    if ok:
        time.sleep(0.3)
        show_events()
    sys.exit(0 if ok else 1)
