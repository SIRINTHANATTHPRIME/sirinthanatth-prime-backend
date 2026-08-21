import os
from dotenv import load_dotenv
import asyncio
import logging
import requests
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    AudioMessage, ImageMessage, VideoMessage, FileMessage, AudioSendMessage, ImageSendMessage, VideoSendMessage,
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

# โหลดตัวแปรและตั้งค่า API Keys
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
BASE_URL = os.getenv("BASE_URL", "https://www.sirinthanatthprime.com")
GEMINI_KEY = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""

line_bot_api = LineBotApi(LINE_TOKEN) if LINE_TOKEN else None
parser = WebhookParser(LINE_SECRET) if LINE_SECRET else None
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


# 🛠️ ฟังก์ชันพิเศษ: สำหรับส่ง Flex Message หรือ Custom JSON Payload
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
        logger.info("📤 [System Info]: Transmitted Custom Payload Successfully.")
    except Exception as e:
        logger.error(f"❌ [System Error]: Custom Payload Transmission Failed -> {e}")


# 🌟 ฟังก์ชันหลัก: ประมวลผล AI และตอบกลับแบบไม่ให้ LINE ตัดสาย (Background Task)
async def process_ai_and_reply(user_id: str, incoming_message: str, reply_token: str, file_path: str = None, file_type: str = None):
    try:
        # ==========================================
        # 👑 [GOD MODE]: ตรวจสอบสิทธิ์ท่านประธาน (CEO)
        # ==========================================
        if ceo_secretary and ceo_secretary.is_ceo(user_id):
            logger.info("👑 [System]: ตรวจพบคำสั่งผู้บริหาร เข้าสู่โหมดเลขาฯ ส่วนตัว (CEO God Mode)")
            if asyncio.iscoroutinefunction(ceo_secretary.process_ceo_command):
                reply_payload = await ceo_secretary.process_ceo_command(incoming_message, file_path=file_path, file_type=file_type)
            else:
                reply_payload = await asyncio.to_thread(ceo_secretary.process_ceo_command, incoming_message, file_path, file_type)
                
            if isinstance(reply_payload, dict):
                send_line_custom_payload(reply_token, reply_payload)
            else:
                line_bot_api.reply_message(reply_token, TextSendMessage(text=str(reply_payload)))
            return

        # ==========================================
        # 👥 โหมดปกติสำหรับลูกค้า / ผู้ใช้ทั่วไป (User Mode)
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
        
        # 🎙️ ระบบเสียง Voice AI (ElevenLabs) ยังคงทำงานได้สมบูรณ์
        if file_type == 'audio' and generate_voice_from_text:
            try:
                filename, duration_ms = await asyncio.to_thread(generate_voice_from_text, reply_msg)
                if filename:
                    messages_to_send.append(AudioSendMessage(original_content_url=f"{BASE_URL}/static/audio/{filename}", duration=duration_ms))
            except Exception as voice_err:
                logger.error(f"❌ [Voice AI Error]: {voice_err}")
        
        await asyncio.to_thread(line_bot_api.reply_message, reply_token, messages_to_send)
        logger.info(f"📤 [LINE AI Reply]: ตอบกลับ {user_id} สำเร็จ")
        
    except Exception as e:
        logger.error(f"❌ [Critical Reply Error]: ไม่สามารถส่งข้อความได้ ({e})")
        try:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="ขออภัยครับ ระบบขัดข้องชั่วคราว โปรดพิมพ์ 'เมนู' เพื่อดำเนินการต่อครับ"))
        except:
            pass
    finally:
        # 🧹 4. ระบบลบไฟล์ขยะอัตโนมัติ (Cleanup Temp Files) เพื่อไม่ให้เซิร์ฟเวอร์เต็ม
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"🗑️ [Cleanup]: ลบไฟล์ชั่วคราว {file_path} เรียบร้อยแล้ว")
            except Exception as e:
                logger.warning(f"⚠️ [Cleanup Error]: ลบไฟล์ไม่สำเร็จ ({e})")


# 🌐 Endpoint รับสัญญาณจาก LINE (Webhook Gateway)
@router.post("/webhook")
async def line_webhook(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    """รับสัญญาณทุกรูปแบบจากผู้ใช้งานและกระจายงานเข้า Background Task"""
    if not parser:
        raise HTTPException(status_code=500, detail="Webhook Parser is not initialized.")
        
    body = await request.body()
    body_str = body.decode('utf-8')
    
    # 🛡️ ตรวจสอบลายเซ็นความปลอดภัย (Signature Validation)
    try:
        events = parser.parse(body_str, x_line_signature)
    except InvalidSignatureError:
        logger.error("❌ [Security Alert]: Invalid LINE Signature detected. Access Denied.")
        raise HTTPException(status_code=400, detail="Invalid signature.")
        
    for event in events:
        if isinstance(event, MessageEvent):
            user_id = event.source.user_id
            reply_token = event.reply_token
            message_type = event.message.type

            incoming_message = ""
            file_path = None
            file_type = None

            # [CASE 1]: ข้อความตัวอักษร
            if message_type == 'text':
                incoming_message = event.message.text
                logger.info(f"📩 [Incoming Traffic]: TEXT from {user_id} -> {incoming_message[:30]}...")
                
            # [CASE 2]: มัลติมีเดียและเอกสาร (Visual & Audio Data)
            elif message_type in ['audio', 'image', 'video', 'file']:
                message_id = event.message.id
                logger.info(f"📩 [Incoming Traffic]: MEDIA [{message_type.upper()}] from {user_id} (ID: {message_id})")
                
                try:
                    message_content = await asyncio.to_thread(line_bot_api.get_message_content, message_id)
                    ext = ""
                    if message_type == 'audio': ext = ".m4a"
                    elif message_type == 'image': ext = ".jpg"
                    elif message_type == 'video': ext = ".mp4"
                    
                    if message_type == 'file':
                        file_name = getattr(event.message, 'file_name', f"file_{message_id}")
                        file_path = f"/tmp/{message_id}_{file_name}"
                    else:
                        file_path = f"/tmp/{message_id}{ext}"
                        
                    def save_media_file(path, content):
                        with open(path, 'wb') as fd:
                            for chunk in content.iter_content():
                                fd.write(chunk)
                                
                    await asyncio.to_thread(save_media_file, file_path, message_content)
                    
                    incoming_message = f"[System Alert: User uploaded a {message_type} file for analysis]"
                    file_type = message_type
                    logger.info(f"💾 [Storage Allocation]: File cached temporarily at {file_path}")
                    
                except Exception as e:
                    logger.error(f"❌ [Network Error]: Failed to retrieve media from LINE Server -> {e}")
                    continue
            else:
                logger.warning(f"⚠️ [Unsupported Format]: Received unhandled type -> {message_type}")
                continue
            
            # 🚀 กระจายงานเข้าสู่ CPU Background Worker (ป้องกัน LINE ตัดสายกรณีโหลดนาน)
            background_tasks.add_task(process_ai_and_reply, user_id, incoming_message, reply_token, file_path, file_type)
        
    return {"status": "OK"}