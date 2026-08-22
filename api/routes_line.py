import os
import asyncio
import logging
import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    AudioMessage, ImageMessage, VideoMessage, FileMessage, AudioSendMessage, ImageSendMessage, VideoSendMessage
)
from google import genai
from google.genai import types

load_dotenv()
# ตั้งค่าระบบ Logging ระดับองค์กร
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Enterprise-Router")

# =========================================================
# 👑 SIRINTHANATTH PRIME - Enterprise API Router
# =========================================================
router = APIRouter()
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
line_bot_api = LineBotApi(LINE_TOKEN) if LINE_TOKEN else None
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET", "")) if os.getenv("LINE_CHANNEL_SECRET") else None
BASE_URL = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
GEMINI_KEY = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# 1. สมองกลส่วนกลาง (Central Routing)
try:
    from agents.central_boss import CentralBossAgent
    boss_agent = CentralBossAgent()
except ImportError:
    boss_agent = None

# 2. สมองอัจฉริยะ (RAG, Vision, Data Analytics)
try:
    from agents.prime_brain import generate_intelligent_response
except ImportError:
    generate_intelligent_response = None

# 3. 👑 เลขาฯ ส่วนตัว (CEO God Mode - Executive Privilege)
try:
    from agents.worker_0_ceo_secretary import CeoSecretaryWorker
    ceo_secretary = CeoSecretaryWorker()
except ImportError:
    ceo_secretary = None

# 4. 🎙️ กล่องเสียง (Voice Module - ElevenLabs Executive Voices)
try:
    from services.elevenlabs_service import generate_voice_from_text
except ImportError:
    generate_voice_from_text = None


# 🛠️ ฟังก์ชันพิเศษ: สำหรับส่ง Flex Message หรือ Custom JSON Payload ให้ CEO
def send_line_custom_payload(reply_token: str, payload: dict):
    if not LINE_TOKEN: return
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
        logger.info("📤 [System Info]: Transmitted Executive Custom Payload Successfully.")
    except Exception as e:
        logger.error(f"❌ [System Error]: Custom Payload Transmission Failed -> {e}")


# 🌟 ฟังก์ชันหลัก: ประมวลผล AI และตอบกลับแบบไม่ให้ LINE ตัดสาย (Background Task)
async def process_ai_and_reply(user_id: str, incoming_message: str, reply_token: str, file_path: str = None, file_type: str = None):
    try:
        # ==========================================
        # 👑 [GOD MODE]: สิทธิ์ขาดประธานบริษัท (Bypass Token & All Limits)
        # ==========================================
        if ceo_secretary and ceo_secretary.is_ceo(user_id):
            logger.info("👑 [System]: CEO Identified. Activating God Mode & Bypassing Token Checks.")
            
            # โยนงานให้เลขาฯ แบบ Asynchronous 100% (ส่ง PDF, รูป, คำสั่งเสียง ได้ทั้งหมด)
            if asyncio.iscoroutinefunction(ceo_secretary.process_ceo_command):
                reply_payload = await ceo_secretary.process_ceo_command(incoming_message, file_path=file_path, file_type=file_type)
            else:
                reply_payload = await asyncio.to_thread(ceo_secretary.process_ceo_command, incoming_message, file_path, file_type)
                
            # หากตอบกลับเป็น Flex Message (3 ปุ่ม อนุมัติ/แก้ไข/ปฏิเสธ)
            if isinstance(reply_payload, dict):
                await asyncio.to_thread(send_line_custom_payload, reply_token, reply_payload)
            else:
                await asyncio.to_thread(line_bot_api.reply_message, reply_token, TextSendMessage(text=str(reply_payload)))
            return # จบการทำงานทันที ไม่ให้ไปรันระบบลูกค้าทั่วไป

        # ==========================================
        # 👥 โหมดปกติสำหรับลูกค้า / ผู้ใช้ทั่วไป (User Mode & Token Managed)
        # ==========================================
        reply_msg = ""
        
        # 1. พยายามเรียกใช้สมองอัจฉริยะ (Prime Brain - RAG & Vision)
        if generate_intelligent_response:
            try:
                if asyncio.iscoroutinefunction(generate_intelligent_response):
                    reply_msg = await generate_intelligent_response(user_id, incoming_message, file_path=file_path, file_type=file_type)
                else:
                    reply_msg = await asyncio.to_thread(generate_intelligent_response, user_id, incoming_message, file_path, file_type)
                logger.info(f"🧠 [Prime Brain]: ประมวลผลสำเร็จสำหรับผู้ใช้ {user_id}")
            except Exception as e:
                logger.warning(f"⚠️ [Prime Brain Error]: ขัดข้อง ({e}) สลับไปใช้ Central Boss")
                if boss_agent:
                    reply_msg = await asyncio.to_thread(boss_agent.route_task, user_id, incoming_message, None)
                else:
                    reply_msg = "ขออภัยครับ ขณะนี้ระบบประมวลผลกำลังปรับปรุงชั่วคราว"
        elif boss_agent:
            # ใช้ Boss Agent เป็นคนจ่ายงาน
            reply_msg = await asyncio.to_thread(boss_agent.route_task, user_id, incoming_message, None)
        else:
            # Fallback หากระบบ AI หลักขัดข้อง
            if client:
                try:
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model='gemini-1.5-flash',
                        contents=f"คุณคือ AI ผู้ช่วยระดับบริหาร 'SIRINTHANATTH PRIME'\nลูกค้าส่งข้อความมาว่า: {incoming_message}"
                    )
                    reply_msg = response.text
                except Exception as ex:
                    logger.error(f"⚠️ [Gemini Engine Error]: {ex}")
                    reply_msg = f"ได้รับข้อความ: '{incoming_message}' (ระบบกำลังปรับปรุงคีย์การเชื่อมต่อ)"
            else:
                reply_msg = f"ได้รับข้อความ: '{incoming_message}' (ระบบออฟไลน์)"

        messages_to_send = [TextSendMessage(text=reply_msg)]
        
        # 🎙️ ระบบแปลงเสียงพูด (Voice AI - ElevenLabs)
        if file_type == 'audio' and generate_voice_from_text:
            filename, duration_ms = await asyncio.to_thread(generate_voice_from_text, reply_msg)
            if filename: 
                audio_url = f"{BASE_URL}/static/audio/{filename}"
                messages_to_send.append(AudioSendMessage(original_content_url=audio_url, duration=duration_ms))
        
        await asyncio.to_thread(line_bot_api.reply_message, reply_token, messages_to_send)
        
    except Exception as e: 
        logger.error(f"❌ Error in Processing: {e}")
        try:
            await asyncio.to_thread(line_bot_api.reply_message, reply_token, TextSendMessage(text="ขออภัยครับ ขณะนี้ระบบประมวลผลหลักกำลังอัปเดตข้อมูล ท่านสามารถพิมพ์ 'เมนู' เพื่อดูบริการของเราได้ครับ"))
        except:
            pass
    finally:
        # 🧹 ทำความสะอาดลบไฟล์ชั่วคราว (Zero-Data Retention)
        if file_path and os.path.exists(file_path):
            try: 
                os.remove(file_path)
            except Exception as clean_e: 
                logger.error(f"⚠️ [Cleanup Warning]: {clean_e}")


# 🌐 Endpoint รับสัญญาณจาก LINE (Webhook Gateway)
@router.post("/webhook")
async def line_webhook(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    """Webhook Gateway ด่านหน้ารับข้อความจาก LINE OA"""
    if not parser:
        raise HTTPException(status_code=500, detail="Webhook Parser is not initialized.")
        
    body = await request.body()
    try: 
        events = parser.parse(body.decode('utf-8'), x_line_signature)
    except InvalidSignatureError: 
        raise HTTPException(status_code=400, detail="Invalid signature.")
        
    for event in events:
        if isinstance(event, MessageEvent):
            user_id = event.source.user_id
            reply_token = event.reply_token
            message_type = event.message.type
            incoming_message, file_path, file_type = "", None, None

            # ตรวจสอบว่าเป็นข้อความตัวอักษร
            if message_type == 'text': 
                incoming_message = event.message.text.strip()

                # 👑 คำสั่งลับ ปลดล็อก CEO 
                if incoming_message == "PRIME: UNLOCK CEO":
                    reply_msg = (f"👑 [SYSTEM OVERRIDE SUCCESS]\n"
                                 f"ท่านประธานครับ LINE ID ของท่านคือ:\n\n"
                                 f"{user_id}\n\n"
                                 f"กรุณาคัดลอกรหัสนี้ไปใส่ในไฟล์ .env ตัวแปร CEO_LINE_ID และ MASTER_ADMIN_LINE_ID ใน Cloud Run เพื่อปลดล็อกระบบเลขาฯ ส่วนตัวครับ")
                    background_tasks.add_task(line_bot_api.reply_message, reply_token, TextSendMessage(text=reply_msg))
                    continue

            # ตรวจสอบว่าเป็นข้อความมัลติมีเดีย/ไฟล์ (รูป, วิดีโอ, เสียง, PDF)
            elif message_type in ['audio', 'image', 'video', 'file']:
                message_id = event.message.id
                try:
                    # โหลดไฟล์แบบ Async ไม่ให้เซิร์ฟเวอร์โดนบล็อก
                    message_content = await asyncio.to_thread(line_bot_api.get_message_content, message_id)
                    ext = ".m4a" if message_type == 'audio' else ".jpg" if message_type == 'image' else ".mp4" if message_type == 'video' else ""
                    file_name = getattr(event.message, 'file_name', f"file_{message_id}") if message_type == 'file' else f"{message_id}{ext}"
                    
                    os.makedirs("/tmp", exist_ok=True)
                    file_path = f"/tmp/{file_name}"
                    
                    def save_media():
                        with open(file_path, 'wb') as fd:
                            for chunk in message_content.iter_content(): fd.write(chunk)
                            
                    await asyncio.to_thread(save_media)
                    
                    incoming_message = f"[System Alert: อัปโหลดไฟล์ {message_type} สำเร็จ]"
                    file_type = message_type
                except Exception as e: 
                    logger.error(f"❌ File processing error: {e}")
                    continue
            else: 
                continue
            
            # 🚀 ส่งต่องานให้ AI ประมวลผลแบบเบื้องหลัง (Background Task)
            background_tasks.add_task(process_ai_and_reply, user_id, incoming_message, reply_token, file_path, file_type)
            
    return {"status": "OK"}