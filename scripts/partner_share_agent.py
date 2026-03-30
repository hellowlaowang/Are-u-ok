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
import time
import requests
from flask import Flask, request, jsonify
from typing import Dict, List, Optional, Any

# 配置
os.environ.setdefault("FEISHU_APP_ID", "cli_a9426bcd88f8dbd6")
os.environ.setdefault("FEISHU_APP_SECRET", "j9afagTYAfuughw27OcfjgIfGHWXkMp2")

workspace_path = os.getenv('COZE_WORKSPACE_PATH', '/workspace/projects')
if workspace_path not in sys.path:
    sys.path.insert(0, workspace_path)

from lark_oapi import Client, LogLevel

app_id = os.getenv("FEISHU_APP_ID")
app_secret = os.getenv("FEISHU_APP_SECRET")

client = Client.builder() \
    .app_id(app_id) \
    .app_secret(app_secret) \
    .log_level(LogLevel.INFO) \
    .build()

flask_app = Flask(__name__)

# 用户会话存储 (生产环境应该用 Redis)
user_sessions: Dict[str, Dict] = {}

def get_tenant_token():
    """获取飞书 tenant token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": app_id, "app_secret": app_secret})
    data = resp.json()
    return data.get("tenant_access_token") if data.get("code") == 0 else None

def send_message(chat_id: str, content: dict, msg_type: str = "interactive"):
    """发送消息到飞书"""
    token = get_tenant_token()
    if not token:
        return False
    
    resp = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "receive_id": chat_id,
            "msg_type": msg_type,
            "content": json.dumps(content) if isinstance(content, dict) else content
        }
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
            # Step 3 跳过
            if action_key == "step3_skip":
                session["step"] = 4
                send_message(chat_id, create_step4_card())
                return jsonify({"code": 0})
            
            # Step 3 提交
            if action_key == "step3_submit":
                form_data = action.get("form_value", {})
                session["data"]["verification"] = {
                    "method": form_data.get("verification_method", "")
                }
                session["step"] = 4
                send_message(chat_id, create_step4_card())
                return jsonify({"code": 0})
            
            # Step 4 提交 - 生成最终模型
            if action_key == "step4_submit":
                form_data = action.get("form_value", {})
                session["data"]["risk_rules"] = {
                    "low_score_threshold": form_data.get("low_score_threshold", "80"),
                    "exceed_level_limit": form_data.get("exceed_level_limit", "30"),
                    "profit_margin": form_data.get("profit_margin", "5"),
                    "budget_overrun": form_data.get("budget_overrun", "10")
                }
                session["step"] = 5
                send_message(chat_id, generate_final_card(session))
                return jsonify({"code": 0})
            
            # 重新开始
            if action_key == "restart":
                # 清除会话
                key = f"{open_id}_{chat_id}"
                if key in user_sessions:
                    del user_sessions[key]
                
                session = get_or_create_session(open_id, chat_id)
                session["step"] = 1
                send_message(chat_id, create_step1_card())
                return jsonify({"code": 0})
        
        return jsonify({"code": 0, "msg": "success"})
    
    except Exception as e:
        print(f"处理失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"code": 0, "msg": "success"})

@flask_app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "service": "partner-share-card-agent"})

def main():
    print("="*60)
    print("🚀 伙伴能力创值分享模型 Agent")
    print("="*60)
    print("发送「分享模型」或「创值分享」开始制定")
    print("")
    port = int(os.environ.get("PORT", 3000))
    flask_app.run(host='0.0.0.0', port=port, threaded=True)

if __name__ == "__main__":
    main()
