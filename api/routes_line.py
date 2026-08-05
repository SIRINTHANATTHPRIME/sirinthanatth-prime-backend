import os
import asyncio
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# นำเข้าสมองกลส่วนกลาง (ระบบเดิม)
from agents.central_boss import CentralBossAgent

# นำเข้าสมองอัจฉริยะ (ระบบใหม่)
try:
    from agents.prime_brain import generate_intelligent_response
except ImportError:
    generate_intelligent_response = None

router = APIRouter()

# 🔑 ดึงกุญแจเชื่อมต่อ LINE
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN", ""))
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET", ""))

boss_agent = CentralBossAgent()

# 🌟 ฟังก์ชันใหม่: ให้ AI แอบไปคิดและตอบกลับแบบไม่ให้ LINE ตัดสาย
def process_ai_and_reply(user_id: str, incoming_message: str, reply_token: str):
    try:
        reply_msg = ""
        # 1. ลองใช้สมองอัจฉริยะ (Prime Brain)
        if generate_intelligent_response:
            try:
                reply_msg = generate_intelligent_response(user_id, incoming_message)
                print(f"🧠 [Prime Brain]: ประมวลผลสำเร็จ")
            except Exception as e:
                print(f"⚠️ [Prime Brain Error]: ขัดข้อง ({e}) สลับไปใช้ระบบบอส")
                reply_msg = boss_agent.route_task(user_id, incoming_message, None)
        else:
            # 2. ถ้าไม่มีสมองอัจฉริยะ ให้ใช้บอสตัวเก่า
            reply_msg = boss_agent.route_task(user_id, incoming_message, None)

        # 3. ส่งข้อความตอบกลับ
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_msg))
        print(f"📤 [LINE AI Reply]: ตอบกลับ {user_id} สำเร็จ")
        
    except Exception as e:
        print(f"❌ [Critical Reply Error]: ไม่สามารถส่งข้อความได้ ({e})")


@router.post("/webhook")
async def line_webhook(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    """รับข้อความจาก LINE"""
    body = await request.body()
    body_str = body.decode('utf-8')
    
    try:
        events = parser.parse(body_str, x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature.")
        
    for event in events:
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessage):
            user_id = event.source.user_id
            incoming_message = event.message.text
            reply_token = event.reply_token
            
            print(f"📩 [LINE API]: ได้รับข้อความ -> {incoming_message}")
            
            # 🌟 ย้ายการทำงานไปอยู่เบื้องหลัง (Background Task) ทันที เพื่อจบงานฝั่ง Webhook ให้เร็วที่สุด
            background_tasks.add_task(process_ai_and_reply, user_id, incoming_message, reply_token)
        
    # ตอบกลับ LINE ทันทีว่า "OK รับเรื่องแล้ว" ป้องกัน Timeout
    return {"status": "OK"}