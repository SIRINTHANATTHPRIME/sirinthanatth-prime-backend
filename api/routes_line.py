import os
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# นำเข้าสมองกลส่วนกลาง
from agents.central_boss import CentralBossAgent

router = APIRouter()

# 🔑 ดึงกุญแจเชื่อมต่อ LINE
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""))
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET", ""))

# สร้างอินสแตนซ์ของบอส
boss_agent = CentralBossAgent()

@router.post("/webhook")
async def line_webhook(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    """รับข้อความจาก LINE และโยนให้ Central Boss จัดการ"""
    body = await request.body()
    body_str = body.decode('utf-8')
    
    try:
        events = parser.parse(body_str, x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature.")
        
    for event in events:
        # 🟢 ดึงข้อความและ User ID ของลูกค้าที่พิมพ์เข้ามาจริงๆ
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessage):
            user_id = event.source.user_id
            incoming_message = event.message.text
            
            # 1. โยนให้ Boss วิเคราะห์ และเข้าคิว Background Tasks
            reply_msg = boss_agent.route_task(user_id, incoming_message, background_tasks)
            
            # 2. ตอบกลับ LINE ทันที เพื่อไม่ให้ระบบเกิด Timeout
            print(f"📤 [LINE AI Reply]: ส่งข้อความกลับไปหา {user_id}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_msg)
            )
        
    return {"status": "OK", "message": "Received and Processing in Background"}