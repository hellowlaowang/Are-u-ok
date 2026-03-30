"""
伙伴能力创值分享模型 Agent
支持四步引导流程：
1. 业务场景定位
2. 分享策略制定
3. 验证策略制定
4. 示险规则确认
"""

import os
import sys
import json
import requests
from flask import Flask, request, jsonify
from typing import Dict

# 配置
os.environ.setdefault("FEISHU_APP_ID", "cli_a9426bcd88f8dbd6")
os.environ.setdefault("FEISHU_APP_SECRET", "j9afagTYAfuughw27OcfjgIfGHWXkMp2")

app_id = os.getenv("FEISHU_APP_ID")
app_secret = os.getenv("FEISHU_APP_SECRET")

flask_app = Flask(__name__)
user_sessions: Dict[str, Dict] = {}

def get_tenant_token():
    """获取飞书 tenant token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": app_id, "app_secret": app_secret})
    data = resp.json()
    return data.get("tenant_access_token") if data.get("code") == 0 else None

def send_message(chat_id: str, content: dict):
    """发送消息到飞书"""
    token = get_tenant_token()
    if not token:
        return False
    resp = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"receive_id": chat_id, "msg_type": "interactive", "content": json.dumps(content)}
    )
    return resp.json().get("code") == 0

def get_or_create_session(user_id: str, chat_id: str) -> Dict:
    """获取或创建用户会话"""
    key = f"{user_id}_{chat_id}"
    if key not in user_sessions:
        user_sessions[key] = {
            "user_id": user_id,
            "chat_id": chat_id,
            "step": 0,
            "data": {
                "business_line": "",
                "customer_type": "",
                "demand_type": "",
                "capability": {},
                "applicable_levels": [],
                "applicability_note": "",
                "share_strategies": [],
                "verification": {},
                "risk_rules": {}
            },
            "temp": {}
        }
    return user_sessions[key]

def create_step1_card() -> dict:
    """创建 Step 1 业务场景定位卡片"""
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "🎯 Step 1: 业务场景定位"},
            "template": "blue"
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**请填写业务场景信息，制定伙伴能力创值分享模型**"}
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**📋 业务线**"}
            },
            {
                "tag": "input",
                "placeholder": {"tag": "plain_text", "content": "请输入业务线名称，如：泛能"},
                "value": {"key": "business_line"},
                "width": "default"
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**👥 客户类型**"}
            },
            {
                "tag": "input",
                "placeholder": {"tag": "plain_text", "content": "请输入客户类型，如：造纸"},
                "value": {"key": "customer_type"},
                "width": "default"
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**📦 需求类型**"}
            },
            {
                "tag": "input",
                "placeholder": {"tag": "plain_text", "content": "请输入需求类型，如：储能"},
                "value": {"key": "demand_type"},
                "width": "default"
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**💪 能力名称**"}
            },
            {
                "tag": "input",
                "placeholder": {"tag": "plain_text", "content": "请输入能力名称，如：客户需求识别"},
                "value": {"key": "capability_name"},
                "width": "default"
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**🎯 适用伙伴等级**（多选）"}
            },
            {
                "tag": "checkbox",
                "options": [
                    {"text": {"tag": "plain_text", "content": "入门"}, "value": "入门"},
                    {"text": {"tag": "plain_text", "content": "基础"}, "value": "基础"},
                    {"text": {"tag": "plain_text", "content": "中级"}, "value": "中级"},
                    {"text": {"tag": "plain_text", "content": "高级"}, "value": "高级"},
                    {"text": {"tag": "plain_text", "content": "资深"}, "value": "资深"},
                    {"text": {"tag": "plain_text", "content": "专家"}, "value": "专家"},
                    {"text": {"tag": "plain_text", "content": "首席"}, "value": "首席"}
                ],
                "value": {"key": "applicable_levels"}
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**📝 适用性说明**（适用前提、限制条件）"}
            },
            {
                "tag": "input",
                "placeholder": {"tag": "plain_text", "content": "请描述模型适用性说明"},
                "value": {"key": "applicability_note"},
                "width": "default"
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✅ 下一步：制定分享策略"},
                        "type": "primary",
                        "value": {"action": "step1_submit"}
                    }
                ]
            }
        ]
    }

def create_step2_card(strategy_num: int = 1) -> dict:
    """创建 Step 2 分享策略制定卡片"""
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"💰 Step 2: 分享策略 #{strategy_num}"},
            "template": "green"
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**配置分享依据、分享水平和兑现节奏**"}
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**📊 分享依据类型**"}
            },
            {
                "tag": "select",
                "placeholder": {"tag": "plain_text", "content": "选择分享依据类型"},
                "options": [
                    {"text": {"tag": "plain_text", "content": "财务类"}, "value": "财务类"},
                    {"text": {"tag": "plain_text", "content": "业务类"}, "value": "业务类"},
                    {"text": {"tag": "plain_text", "content": "里程碑类"}, "value": "里程碑类"},
                    {"text": {"tag": "plain_text", "content": "交付物类"}, "value": "交付物类"},
                    {"text": {"tag": "plain_text", "content": "投入量类"}, "value": "投入量类"}
                ],
                "value": {"key": "share_basis_type"}
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**📝 分享依据名称**"}
            },
            {
                "tag": "input",
                "placeholder": {"tag": "plain_text", "content": "如：项目回款"},
                "value": {"key": "share_basis_name"},
                "width": "default"
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**📏 计量单位**"}
            },
            {
                "tag": "select",
                "placeholder": {"tag": "plain_text", "content": "选择计量单位"},
                "options": [
                    {"text": {"tag": "plain_text", "content": "元"}, "value": "元"},
                    {"text": {"tag": "plain_text", "content": "万元"}, "value": "万元"},
                    {"text": {"tag": "plain_text", "content": "次"}, "value": "次"},
                    {"text": {"tag": "plain_text", "content": "天"}, "value": "天"}
                ],
                "value": {"key": "unit"}
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**💵 分享水平**"}
            },
            {
                "tag": "input",
                "placeholder": {"tag": "plain_text", "content": "如：5% 或 3000"},
                "value": {"key": "share_default"},
                "width": "default"
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**⏱️ 兑现节奏**"}
            },
            {
                "tag": "select",
                "placeholder": {"tag": "plain_text", "content": "选择兑现节奏"},
                "options": [
                    {"text": {"tag": "plain_text", "content": "月度"}, "value": "月度"},
                    {"text": {"tag": "plain_text", "content": "季度"}, "value": "季度"},
                    {"text": {"tag": "plain_text", "content": "年度"}, "value": "年度"}
                ],
                "value": {"key": "payment_rhythm"}
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "➕ 添加更多"},
                        "type": "default",
                        "value": {"action": "step2_add_more"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✅ 下一步"},
                        "type": "primary",
                        "value": {"action": "step2_next"}
                    }
                ]
            }
        ]
    }

def create_step3_card() -> dict:
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "✅ Step 3: 验证策略"},
            "template": "orange"
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**验证策略是对分享水平的系数修正**"}
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**📊 折算方式**"}
            },
            {
                "tag": "select",
                "placeholder": {"tag": "plain_text", "content": "选择折算方式"},
                "options": [
                    {"text": {"tag": "plain_text", "content": "线性折算"}, "value": "线性"},
                    {"text": {"tag": "plain_text", "content": "区间对应"}, "value": "区间"},
                    {"text": {"tag": "plain_text", "content": "函数计算"}, "value": "函数"}
                ],
                "value": {"key": "verification_method"}
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "🔄 跳过"},
                        "type": "default",
                        "value": {"action": "step3_skip"}
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✅ 下一步"},
                        "type": "primary",
                        "value": {"action": "step3_submit"}
                    }
                ]
            }
        ]
    }

def create_step4_card() -> dict:
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "🛡️ Step 4: 示险规则"},
            "template": "red"
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "**三层熔断保护体系**"}
            },
            {"tag": "hr"},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "✅ 生成模型"},
                        "type": "primary",
                        "value": {"action": "step4_submit"}
                    }
                ]
            }
        ]
    }

def generate_final_card(session: Dict) -> dict:
    """生成最终的分享模型卡片"""
    data = session["data"]
    strategies_text = ""
    for i, strategy in enumerate(data.get("share_strategies", []), 1):
        strategies_text += f"\\n策略{i}: {strategy.get('basis_type', '')} - {strategy.get('share_default', '')}\\n"
    
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": "📋 伙伴能力创值分享模型"},
            "template": "blue"
        },
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**业务场景：** {data.get('business_line', '')} · {data.get('customer_type', '')} · {data.get('demand_type', '')}"}
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**目标能力：** {data.get('capability', {}).get('name', '')}"}
            },
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**适用等级：** {' / '.join(data.get('applicable_levels', []))}"}
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**💰 分享策略：**{strategies_text if strategies_text else '未配置'}"}
            },
            {"tag": "hr"},
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": "*角享群开发*"}
            }
        ]
    }

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    """飞书 webhook 回调处理"""
    try:
        body = request.json
        print(f"收到回调: {json.dumps(body, ensure_ascii=False)}")
        
        # URL 验证
        if body.get("type") == "url_verification":
            return jsonify({"challenge": body.get("challenge", "")})
        
        event_type = body.get("header", {}).get("event_type", "")
        
        # 消息事件
        if event_type == "im.message.receive_v1":
            event = body.get("event", {})
            message = event.get("message", {})
            chat_id = message.get("chat_id", "")
            sender = event.get("sender", {}).get("sender_id", {}).get("user_id", "")
            
            if message.get("message_type") == "text":
                content = json.loads(message.get("content", "{}"))
                text = content.get("text", "").strip()
                
                if "分享模型" in text or "创值分享" in text:
                    session = get_or_create_session(sender, chat_id)
                    session["step"] = 1
                    send_message(chat_id, create_step1_card())
        
        # 卡片回调
        if event_type == "card.action.trigger":
            event = body.get("event", {})
            action = event.get("action", {})
            action_value = action.get("value", {})
            action_key = action_value.get("action", "")
            
            context = event.get("context", {})
            open_id = context.get("open_id", "")
            chat_id = context.get("open_chat_id", "")
            
            session = get_or_create_session(open_id, chat_id)
            
            if action_key == "step1_submit":
                form_data = action.get("form_value", {})
                session["data"]["business_line"] = form_data.get("business_line", "")
                session["data"]["customer_type"] = form_data.get("customer_type", "")
                session["data"]["demand_type"] = form_data.get("demand_type", "")
                session["data"]["capability"] = {"name": form_data.get("capability_name", "")}
                session["data"]["applicable_levels"] = form_data.get("applicable_levels", [])
                session["data"]["applicability_note"] = form_data.get("applicability_note", "")
                session["step"] = 2
                send_message(chat_id, create_step2_card(1))
            
            elif action_key == "step2_add_more":
                form_data = action.get("form_value", {})
                strategy = {
                    "basis_type": form_data.get("share_basis_type", ""),
                    "share_default": form_data.get("share_default", "")
                }
                session["data"]["share_strategies"].append(strategy)
                count = session["temp"].get("strategy_count", 1) + 1
                session["temp"]["strategy_count"] = count
                send_message(chat_id, create_step2_card(count))
            
            elif action_key == "step2_next":
                form_data = action.get("form_value", {})
                strategy = {
                    "basis_type": form_data.get("share_basis_type", ""),
                    "share_default": form_data.get("share_default", "")
                }
                session["data"]["share_strategies"].append(strategy)
                session["step"] = 3
                send_message(chat_id, create_step3_card())
            
            elif action_key == "step3_skip":
                session["step"] = 4
                send_message(chat_id, create_step4_card())
            
            elif action_key == "step3_submit":
                form_data = action.get("form_value", {})
                session["data"]["verification"] = {"method": form_data.get("verification_method", "")}
                session["step"] = 4
                send_message(chat_id, create_step4_card())
            
            elif action_key == "step4_submit":
                session["step"] = 5
                send_message(chat_id, generate_final_card(session))
        
        return jsonify({"code": 0, "msg": "success"})
    
    except Exception as e:
        print(f"处理失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"code": 0, "msg": "success"})

@flask_app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "partner-share-card-agent"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    flask_app.run(host='0.0.0.0', port=port, threaded=True)
