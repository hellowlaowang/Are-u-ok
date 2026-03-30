"""
最简单的测试版 - 只打印日志
"""

import os
import json
import requests
from flask import Flask, request, jsonify

os.environ.setdefault("FEISHU_APP_ID", "cli_a9426bcd88f8dbd6")
os.environ.setdefault("FEISHU_APP_SECRET", "j9afagTYAfuughw27OcfjgIfGHWXkMp2")

app_id = os.getenv("FEISHU_APP_ID")
app_secret = os.getenv("FEISHU_APP_SECRET")

flask_app = Flask(__name__)

def get_tenant_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": app_id, "app_secret": app_secret})
    data = resp.json()
    return data.get("tenant_access_token") if data.get("code") == 0 else None

def send_simple_message(receive_id: str, content: str):
    token = get_tenant_token()
    if not token:
        return False
    
    resp = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"receive_id": receive_id, "msg_type": "text", "content": json.dumps({"text": content})}
    )
    return resp.json()

@flask_app.route('/webhook', methods=['POST'])
def webhook():
    body = request.json
    print("="*60)
    print("收到完整请求：")
    print(json.dumps(body, ensure_ascii=False, indent=2))
    print("="*60)
    
    if body.get("type") == "url_verification":
        return jsonify({"challenge": body.get("challenge", "")})
    
    event_type = body.get("header", {}).get("event_type", "")
    
    if event_type == "im.message.receive_v1":
        event = body.get("event", {})
        message = event.get("message", {})
        sender = event.get("sender", {})
        sender_id = sender.get("sender_id", {}).get("open_id", "")
        
        if message.get("message_type") == "text":
            content = json.loads(message.get("content", "{}"))
            text = content.get("text", "").strip()
            
            print(f"收到消息：{text}")
            
            if "分享模型" in text or "创值分享" in text:
                print("发送回复！")
                send_simple_message(sender_id, "收到！正在处理...")
    
    return jsonify({"code": 0, "msg": "success"})

@flask_app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "version": "simple-test"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    flask_app.run(host='0.0.0.0', port=port)
