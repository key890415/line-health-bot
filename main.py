import os
from fastapi import FastAPI, HTTPException, Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import firebase_admin
from firebase_admin import credentials, firestore

# 1. 初始化 Firebase (請確保你的 firebase 憑證檔名正確，或改為讀取環境變數)
cred = credentials.Certificate("firebase_credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# 2. 初始化 LINE Bot 憑證 (建議後續部署時改用環境變數帶入)
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "你的_Channel_Access_Token")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "你的_Channel_Secret")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Health Bot Backend is running!"}

# 3. 接收 LINE Webhook 請求
@app.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    body_str = body.decode("utf-8")

    try:
        handler.handle(body_str, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature. Please check your channel access token/secret.")
    
    return "OK"

# 4. 處理 LINE 文字訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text.strip()

    # 簡單的指令邏輯範例
    if user_message == "記錄健康":
        # 寫入 Firebase 資料庫的範例
        doc_ref = db.collection("health_data").document(user_id)
        doc_ref.set({
            "user_id": user_id,
            "status": "平安",
            "last_update": firestore.SERVER_TIMESTAMP
        }, merge=True)
        
        reply_text = "已為您記錄最新平安狀態到 Firebase！"
    elif user_message == "查詢狀態":
        # 從 Firebase 讀取資料的範例
        doc_ref = db.collection("health_data").document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            reply_text = f"您目前的狀態：{data.get('status', '未知')}"
        else:
            reply_text = "目前沒有您的健康記錄，請先輸入「記錄健康」。"
    else:
        reply_text = f"你剛剛說了：{user_message}\n輸入「記錄健康」或「查詢狀態」來測試 Firebase 互動！"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )