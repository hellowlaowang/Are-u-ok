"""
纯 Webhook 服务（不带长连接）
消息和卡片都走 Webhook
"""

import os
import sys
import json
import requests
from flask import Flask, request, jsonify

os.environ["FEISHU_APP_ID"] = "cli_a9426bcd88f8dbd6"
os.environ["FEISHU_APP_SECRET"] = "j9afagTYAfuughw27OcfjgIfGHWXkMp2"

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

cached_token = None
cached_token_expire = 0

def get_tenant_token():
    global cached_token, cached_token_expire
    import time
    now = int(time.time())
    if cached_token and now < cached_token_expire - 60:
        return cached_token
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": app_id, "app_secret": app_secret})
    data = resp.json()
    if data.get("code") != 0:
        print("获取token失败：", data)
        return None
    cached_token = data.get("tenant_access_token")
    cached_token_expire = now + data.get("expire", 7200)
    return cached_token

def send_card(chat_id: str):
    """发送可交互卡片"""
    try:
        token = get_tenant_token()
        if not token:
            return False
        
        interactive_card = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "🎯 测试卡片 - 点击按钮测试"},
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"tag": "lark_md", "content": "**点击下方按钮测试交互功能**"}
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "✅ 按钮1"},
                            "type": "primary",
                            "value": {"action": "btn1"}
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "🔴 按钮2"},
                            "type": "danger",
                            "value": {"action": "btn2"}
                        }
                    ]
                }
            ]
        }
        
        resp = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "receive_id": chat_id,
                "msg_type": "interactive",
                "content": json.dumps(interactive_card)
            }
        )
        
        result = resp.json()
        print(f"发送卡片: {resp.status_code} - {json.dumps(result, ensure_ascii=False)}")
        return result.get("code") == 0
    except Exception as e:
        print(f"发送失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def update_card_with_response(token, msg_id, new_card):
    """使用回复消息的方式更新卡片"""
    try:
        resp = requests.post(
            f"https://open.feishu.cn/open-apis/im/v1/messages/{msg_id}/reply",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "msg_type": "interactive",
                "content": json.dumps(new_card)
            }
        )
        result = resp.json()
        print(f"回复卡片: {resp.status_code} - {json.dumps(result, ensure_ascii=False)}")
        return result.get("code") == 0
    except Exception as e:
        print(f"回复失败: {e}")
        return False

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    try:
        body = request.json
        print(f"\n{'='*60}")
        print(f"🔔 收到回调（完整内容）")
        print(f"{'='*60}")
        print(f"完整回调: {json.dumps(body, ensure_ascii=False, indent=2)}")
        
        # URL 验证
        if body.get("type") == "url_verification" or body.get("header", {}).get("event_type") == "url_verification":
            challenge = body.get("challenge", "") or body.get("header", {}).get("challenge", "")
            print(f"✅ URL 验证: challenge={challenge}")
            return jsonify({"challenge": challenge})
        
        # 获取事件类型（兼容新旧格式）
        event_type = body.get("type") or body.get("header", {}).get("event_type")
        
        # 消息回调
        if event_type == "im.message.receive_v1":
            event = body.get("event", {})
            message = event.get("message", {})
            msg_type = message.get("message_type")
            chat_id = message.get("chat_id")
            content_str = message.get("content", "{}")
            
            print(f"💬 收到消息: type={msg_type}, chat_id={chat_id}")
            
            if msg_type == "text":
                content = json.loads(content_str) if isinstance(content_str, str) else content_str
                text = content.get("text", "").strip()
                print(f"📝 内容: {text}")
                
                # 自动回复卡片
                if "你好" in text or "测试" in text or "卡片" in text:
                    print(f"\n🎯 自动回复卡片...")
                    success = send_card(chat_id)
                    print(f"{'✅' if success else '❌'} 卡片{'发送成功' if success else '发送失败'}")
            
            return jsonify({"code": 0, "msg": "success"})
        
        # 卡片回调
        if event_type == "card.action.trigger":
            event_data = body.get("event", {})
            action = event_data.get("action", {})  # 注意：action 在 event 里面
            
            print(f"🎯 卡片操作: {json.dumps(event_data, ensure_ascii=False)}")
            
            # 获取按钮值
            value = action.get("value", {})
            action_key = value.get("action", "unknown")
            
            # 获取消息ID: event.context.open_message_id
            context = event_data.get("context", {})
            msg_id = context.get("open_message_id", "")
            
            print(f"📍 点击的按钮: {action_key}")
            print(f"🆔 消息ID: {msg_id}")
            
            # 回复卡片
            token = get_tenant_token()
            if token and msg_id:
                new_card = {
                    "config": {"wide_screen_mode": True},
                    "header": {
                        "title": {"tag": "plain_text", "content": f"✅ 点击了：{action_key}"},
                        "template": "green"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {"tag": "lark_md", "content": f"**你点击了按钮：** `{action_key}`"}
                        },
                        {
                            "tag": "hr"
                        },
                        {
                            "tag": "div",
                            "text": {"tag": "lark_md", "content": "卡片已更新成功！🎉"}
                        }
                    ]
                }
                update_card_with_response(token, msg_id, new_card)
            
            return jsonify({"code": 0, "msg": "success"})
        
        return jsonify({"code": 0, "msg": "success"})
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"code": 0, "msg": "success"})

@flask_app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

def main():
    print("="*60)
    print("🚀 飞书纯 Webhook 服务（无长连接）")
    print("="*60)
    print("✅ 消息和卡片都走 Webhook")
    print("⚠️  请在飞书后台配置：")
    print("   1. 事件配置 → 请求地址 URL → https://你的render域名/webhook")
    print("   2. 订阅事件：im.message.receive_v1 和 card.action.trigger")
    print("")
    # Render 会提供 PORT 环境变量
    port = int(os.environ.get("PORT", 3000))
    flask_app.run(host='0.0.0.0', port=port, threaded=True)

if __name__ == "__main__":
    main()