import os
import asyncio
import requests
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# ---------------------------------------------------------
# นำเข้าสมองกลระบบทั้งหมด
# ---------------------------------------------------------
# 1. สมองกลส่วนกลาง (ระบบเดิม)
from agents.central_boss import CentralBossAgent

# 2. สมองอัจฉริยะ (ระบบใหม่ RAG)
try:
    from agents.prime_brain import generate_intelligent_response
except ImportError:
    generate_intelligent_response = None

# 3. 👑 เลขาฯ ส่วนตัว (CEO God Mode)
try:
    from agents.worker_0_ceo_secretary import CeoSecretaryWorker
    ceo_secretary = CeoSecretaryWorker()
except ImportError:
    ceo_secretary = None

# ---------------------------------------------------------
# ตั้งค่า Router และ LINE API
# ---------------------------------------------------------
router = APIRouter()

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
line_bot_api = LineBotApi(LINE_TOKEN)
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET", ""))

boss_agent = CentralBossAgent()

# 🛠️ ฟังก์ชันพิเศษ: สำหรับส่ง Flex Message และโครงสร้างแบบ Custom (จากเลขาฯ)
def send_line_custom_payload(reply_token: str, payload: dict):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    data = {
        "replyToken": reply_token,
        "messages": [payload]
    }
    try:
        response = requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=data)
        response.raise_for_status()
        print(f"📤 [LINE API Custom Payload]: ส่งข้อความสำเร็จ")
    except Exception as e:
        print(f"❌ [LINE API Error]: ไม่สามารถส่ง Custom Payload ได้ ({e})")


# 🌟 ฟังก์ชันหลัก: ให้ AI แอบไปคิดและตอบกลับแบบไม่ให้ LINE ตัดสาย (Background Task)
async def process_ai_and_reply(user_id: str, incoming_message: str, reply_token: str):
    try:
        # ==========================================
        # 👑 [GOD MODE]: ตรวจสอบสิทธิ์ท่านประธาน (CEO)
        # ==========================================
        if ceo_secretary and ceo_secretary.is_ceo(user_id):
            print("👑 [System]: ตรวจพบคำสั่งผู้บริหาร เข้าสู่โหมดเลขาฯ ส่วนตัว (CEO God Mode)")
            # ประมวลผลผ่านเลขาฯ 
            reply_payload = await ceo_secretary.process_ceo_command(incoming_message)
            # ส่งกลับในรูปแบบ Flex Message หรือ Text อัตโนมัติ
            send_line_custom_payload(reply_token, reply_payload)
            return  # จบการทำงาน (ไม่ให้ระบบลูกค้าทั่วไปทำงานทับซ้อน)

        # ==========================================
        # 👥 โหมดปกติสำหรับลูกค้า / ตัวแทน (User Mode)
        # ==========================================
        reply_msg = ""
        
        # 1. ลองใช้สมองอัจฉริยะ (Prime Brain)
        if generate_intelligent_response:
            try:
                reply_msg = generate_intelligent_response(user_id, incoming_message)
                print(f"🧠 [Prime Brain]: ประมวลผลสำเร็จสำหรับผู้ใช้ {user_id}")
            except Exception as e:
                print(f"⚠️ [Prime Brain Error]: ขัดข้อง ({e}) สลับไปใช้ระบบบอสชั่วคราว")
                reply_msg = boss_agent.route_task(user_id, incoming_message, None)
        else:
            # 2. ถ้าระบบใหม่ไม่มี ให้ใช้บอสตัวเก่า (Rule-Based / Fallback)
            reply_msg = boss_agent.route_task(user_id, incoming_message, None)

        # 3. ส่งข้อความตอบกลับหาลูกค้า
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_msg))
        print(f"📤 [LINE AI Reply]: ตอบกลับ {user_id} สำเร็จ")
        
    except Exception as e:
        print(f"❌ [Critical Reply Error]: ไม่สามารถส่งข้อความได้ ({e})")


# 🌐 Endpoint สำหรับรับ Webhook จาก LINE
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
            
            print(f"📩 [LINE API]: ได้รับข้อความจาก {user_id} -> {incoming_message[:50]}")
            
            # 🌟 ย้ายการทำงานไปอยู่เบื้องหลัง (Background Task) ทันที เพื่อจบงานฝั่ง Webhook ภายใน 1-2 วินาที
            background_tasks.add_task(process_ai_and_reply, user_id, incoming_message, reply_token)
        
    # ตอบกลับ LINE ทันทีว่า "OK รับเรื่องแล้ว" ป้องกัน Timeout จากเซิร์ฟเวอร์ LINE
    return {"status": "OK"}