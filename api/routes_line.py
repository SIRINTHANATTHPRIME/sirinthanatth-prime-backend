import os
import asyncio
import inspect
import logging
import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, AudioMessage, ImageMessage, VideoMessage, FileMessage, 
    TextSendMessage, AudioSendMessage, ImageSendMessage, VideoSendMessage, FileSendMessage
)
from google import genai

load_dotenv()

# =========================================================
# 👑 SIRINTHANATTH PRIME - Enterprise LINE API Gateway
# =========================================================

# ตั้งค่าระบบ Logging ระดับองค์กร
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("RoutesLine")

router = APIRouter()

# 🔑 โหลดตัวแปรสภาพแวดล้อม (Environment Variables)
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
BASE_URL = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")

line_bot_api = LineBotApi(LINE_TOKEN) if LINE_TOKEN else None
parser = WebhookParser(LINE_SECRET) if LINE_SECRET else None

# โหลด Agents และ Services แบบ Graceful Degradation (กันระบบล่มถ้าไฟล์ย่อยมีปัญหา)
try: from agents.central_boss import CentralBossAgent; boss_agent = CentralBossAgent()
except ImportError: boss_agent = None

try: from agents.prime_brain import generate_intelligent_response
except ImportError: generate_intelligent_response = None

try: from agents.worker_0_ceo_secretary import CeoSecretaryWorker; ceo_secretary = CeoSecretaryWorker()
except ImportError: ceo_secretary = None

try: from services.elevenlabs_service import generate_voice_from_text
except ImportError: generate_voice_from_text = None

# =========================================================
# 🛠️ Core Functions (ระบบสั่งการ LINE ขั้นสูง)
# ==========================================

async def send_line_custom_payload(user_id: str, payload: dict):
    """ส่ง Flex Message หรือ Custom JSON Payload ให้ผู้บริหารผ่าน Push API"""
    if not LINE_TOKEN: return
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    data = {
        "to": user_id,
        "messages": [payload]
    }
    try:
        response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data)
        response.raise_for_status()
        logger.info("📤 [System]: ส่ง Executive Custom Payload สำเร็จ")
    except Exception as e:
        logger.error(f"❌ [System Error]: ส่ง Custom Payload ล้มเหลว -> {e}")

async def dispatch_line_message(user_id: str, reply_token: str, messages: list):
    """
    ฟังก์ชันสลับ Reply / Push อัตโนมัติ (Enterprise Best Practice)
    หากมี reply_token จะตอบกลับฟรี หากถูกใช้ไปแล้วจะดันเข้าระบบ Push อัตโนมัติ
    """
    try:
        if reply_token:
            await asyncio.to_thread(line_bot_api.reply_message, reply_token, messages)
        else:
            await asyncio.to_thread(line_bot_api.push_message, user_id, messages)
    except Exception as e:
        logger.error(f"❌ [Dispatch Error]: ไม่สามารถส่งข้อความได้ -> {e}")

# =========================================================
# 🧠 AI Processing Pipeline (ท่อประมวลผลสมองกลหลัก)
# =========================================================

async def process_ai_and_reply(user_id: str, incoming_message: str, reply_token: str = None, file_path: str = None, file_type: str = None):
    try:
        # 👑 [GOD MODE]: สิทธิ์ขาดประธานบริษัท (CEO)
        if ceo_secretary and ceo_secretary.is_ceo(user_id):
            logger.info("👑 [System]: CEO Identified. Activating God Mode.")
            if inspect.iscoroutinefunction(ceo_secretary.process_ceo_command):
                reply_payload = await ceo_secretary.process_ceo_command(incoming_message, file_path=file_path, file_type=file_type)
            else:
                reply_payload = await asyncio.to_thread(ceo_secretary.process_ceo_command, incoming_message, file_path, file_type)
                
            if isinstance(reply_payload, dict): 
                await send_line_custom_payload(user_id, reply_payload)
            else: 
                await dispatch_line_message(user_id, reply_token, [TextSendMessage(text=str(reply_payload))])
            return

        # 👥 [USER MODE]: ลูกค้าทั่วไป (AI Brain Processing)
        reply_msg = ""
        if generate_intelligent_response:
            try:
                if inspect.iscoroutinefunction(generate_intelligent_response):
                    reply_msg = await generate_intelligent_response(user_id, incoming_message, file_path=file_path, file_type=file_type)
                else:
                    reply_msg = await asyncio.to_thread(generate_intelligent_response, user_id, incoming_message, file_path, file_type)
            except Exception as e:
                logger.warning(f"⚠️ [Prime Brain Error]: {e}")
                reply_msg = "ขออภัยครับ ขณะนี้ระบบประมวลผลหลักมีผู้ใช้งานหนาแน่น กำลังดำเนินการปรับเสถียรภาพครับ"
        else:
            reply_msg = "ได้รับข้อความแล้ว (ระบบ AI หลักออฟไลน์ชั่วคราว)"

        messages_to_send = [TextSendMessage(text=reply_msg)]
        
        # 🎙️ ระบบแปลงเสียงพูด (ElevenLabs Voice Synthesis)
        if file_type == 'audio' and generate_voice_from_text:
            try:
                if inspect.iscoroutinefunction(generate_voice_from_text):
                    filename, duration_ms = await generate_voice_from_text(reply_msg)
                else:
                    filename, duration_ms = await asyncio.to_thread(generate_voice_from_text, reply_msg)
                    
                if filename: 
                    audio_url = f"{BASE_URL}/static/audio/{filename}"
                    messages_to_send.append(AudioSendMessage(original_content_url=audio_url, duration=duration_ms))
            except Exception as audio_err:
                logger.error(f"⚠️ [Voice Module Error]: {audio_err}")
        
        # ส่งข้อมูลกลับหาลูกค้า
        await dispatch_line_message(user_id, reply_token, messages_to_send)
        
    except Exception as e: 
        logger.error(f"❌ Error in Processing: {e}")
    finally:
        # 🧹 ระบบทำลายข้อมูล (Zero-Data Retention Policy)
        if file_path and os.path.exists(file_path):
            try: os.remove(file_path)
            except Exception as cleanup_err: logger.error(f"⚠️ Cleanup failed: {cleanup_err}")

# =========================================================
# 🌐 Endpoint Webhook Gateway (ด่านหน้าสกัดแฮกเกอร์)
# =========================================================

@router.post("/webhook")
async def line_webhook(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    """Webhook Gateway ด่านหน้ารับข้อความจาก LINE OA (ระบบป้องกันแฮกเกอร์ 100%)"""
    if not parser or not line_bot_api:
        logger.warning("⚠️ Webhook Parser หรือ API ไม่พร้อมทำงาน (ขาด Secret/Token) แต่ส่ง 200 OK เพื่อให้ Verify ผ่าน")
        return {"status": "ok", "message": "Verify Only Mode"}
        
    body = await request.body()
    try: 
        events = parser.parse(body.decode('utf-8'), x_line_signature)
    except InvalidSignatureError: 
        logger.warning("🚨 [Security Alert]: ตรวจพบการปลอมแปลง Signature! บล็อกการเข้าถึงทันที")
        raise HTTPException(status_code=400, detail="Invalid signature. Access Denied.")
        
    for event in events:
        if not isinstance(event, MessageEvent):
            continue

        user_id = event.source.user_id
        reply_token = event.reply_token
        message_type = event.message.type
        incoming_message, file_path, file_type = "", None, None

        # 🛡️ ระบบกรอง LINE Verification (กันระบบพังตอนกด Verify)
        if reply_token == "00000000000000000000000000000000" or reply_token == "ffffffffffffffffffffffffffffffff":
            logger.info("✅ [System]: ตอบรับการทดสอบ Webhook จาก LINE เรียบร้อย")
            continue

        # ==========================================
        # 📝 1. โหมดข้อความและการกดปุ่ม
        # ==========================================
        if message_type == 'text': 
            incoming_message = event.message.text.strip()

            # 👑 คำสั่งลับ ปลดล็อก CEO
            if incoming_message == "PRIME: UNLOCK CEO":
                reply_msg = (f"👑 [SYSTEM OVERRIDE SUCCESS]\n"
                             f"ท่านประธานครับ LINE ID ของท่านคือ:\n\n"
                             f"{user_id}\n\n"
                             f"กรุณาคัดลอกรหัสนี้ไปใส่ในไฟล์ .env (CEO_LINE_ID) เพื่อปลดล็อกระบบครับ")
                background_tasks.add_task(dispatch_line_message, user_id, reply_token, [TextSendMessage(text=reply_msg)])
                continue

            # 🛍️ จัดการระบบปุ่มกดโปรโมชันแบบ Real-Time
            if incoming_message.startswith("ACTION:PROMO_ACCEPT:"):
                promo_id = incoming_message.split(":")[-1]
                background_tasks.add_task(dispatch_line_message, user_id, reply_token, [TextSendMessage(text=f"✅ แคมเปญรหัส [{promo_id}] ถูกส่งไปยังระบบเผยแพร่แล้วครับ!")])
                continue
            if incoming_message.startswith("ACTION:PROMO_MODIFY:"):
                promo_id = incoming_message.split(":")[-1]
                background_tasks.add_task(dispatch_line_message, user_id, reply_token, [TextSendMessage(text=f"📝 รับทราบครับ! แคมเปญ [{promo_id}] ต้องการปรับปรุงส่วนไหน พิมพ์บอกผมได้เลยครับ!")])
                continue

        # ==========================================
        # 🖼️ 2. โหมดมัลติมีเดีย (รูปภาพ เสียง วิดีโอ PDF)
        # ==========================================
        elif message_type in ['audio', 'image', 'video', 'file']:
            message_id = event.message.id
            try:
                # ตอบกลับทันทีว่ากำลังประมวลผล (ใช้ Reply Token ให้หมดไป)
                await asyncio.to_thread(line_bot_api.reply_message, reply_token, TextSendMessage(text="ระบบกำลังสแกนและประมวลผลไฟล์ กรุณารอสักครู่นะครับ ⏳"))
                
                # ดาวน์โหลดไฟล์
                message_content = await asyncio.to_thread(line_bot_api.get_message_content, message_id)
                ext = ".m4a" if message_type == 'audio' else ".jpg" if message_type == 'image' else ".mp4" if message_type == 'video' else ""
                file_name = getattr(event.message, 'file_name', f"file_{message_id}") if message_type == 'file' else f"{message_id}{ext}"
                
                os.makedirs("/tmp", exist_ok=True)
                file_path = f"/tmp/{file_name}"
                
                def save_media():
                    with open(file_path, 'wb') as fd:
                        for chunk in message_content.iter_content(): fd.write(chunk)
                await asyncio.to_thread(save_media)
                
                incoming_message = f"[System Alert: อัปโหลดไฟล์ {message_type} สำเร็จ ช่วยวิเคราะห์ไฟล์นี้ให้ลูกค้าหน่อยครับ]"
                file_type = message_type
                reply_token = None # เซ็ตเป็น None เพื่อให้ระบบสลับไปใช้ Push Message ตอนตอบกลับไฟล์สำเร็จ
                
            except Exception as e: 
                logger.error(f"❌ File download error: {e}")
                continue
        else: 
            continue
    
        # 🚀 โยนเข้าคิวประมวลผล AI หลังบ้านเพื่อไม่ให้ LINE ตัดสาย
        background_tasks.add_task(process_ai_and_reply, user_id, incoming_message, reply_token, file_path, file_type)
        
    return {"status": "OK"}