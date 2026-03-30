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
