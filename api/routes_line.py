import os
import asyncio
import requests
import logging
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, FollowEvent, TextMessage, AudioMessage, ImageMessage, 
    VideoMessage, FileMessage, TextSendMessage, AudioSendMessage, 
    VideoSendMessage, ImageSendMessage, FlexSendMessage
)
from google import genai
from google.genai import types

# =================================================================
# 👑 SIRINTHANATTH PRIME - Core API Router (World-Class Standard)
# =================================================================

# 1. System Configuration & Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Prime-Router")

# โหลด API Key ล่าสุด (ให้ความสำคัญกับ AI_API_KEY ก่อน)
GEMINI_KEY = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
BASE_URL = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")

router = APIRouter()
line_bot_api = LineBotApi(LINE_TOKEN) if LINE_TOKEN else None
parser = WebhookParser(LINE_SECRET) if LINE_SECRET else None

# 2. นำเข้าสมองกลระบบทั้งหมด (Try-Except ป้องกันระบบแครชหากไฟล์อื่นกำลังแก้ไข)
try:
    from agents.central_boss import CentralBossAgent
    boss_agent = CentralBossAgent()
except ImportError as e:
    logger.error(f"⚠️ [System Alert]: ไม่สามารถโหลด CentralBossAgent ได้: {e}")
    boss_agent = None

try:
    from agents.prime_brain import generate_intelligent_response
except ImportError:
    generate_intelligent_response = None

try:
    from agents.worker_0_ceo_secretary import CeoSecretaryWorker
    ceo_secretary = CeoSecretaryWorker()
except ImportError:
    ceo_secretary = None

try: 
    from services.elevenlabs_service import generate_voice_from_text
except ImportError: 
    generate_voice_from_text = None

# =================================================================
# 🛠️ Utility Functions (ตัวช่วยตอบกลับแบบพิเศษ)
# =================================================================
def send_line_custom_payload(reply_token: str, payload: dict):
    """ส่ง Custom Payload (เช่น Flex Message จาก JSON ตรงๆ สำหรับโหมด CEO)"""
    if not LINE_TOKEN: return
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    data = {"replyToken": reply_token, "messages": [payload]}
    try: 
        res = requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=data)
        res.raise_for_status()
    except Exception as e: 
        logger.error(f"❌ [Custom Payload Error]: {e}")

def get_vip_guide_flex():
    """สร้างการ์ด Flex Message สไตล์หรูหราสำหรับคู่มือ VIP"""
    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box", "layout": "vertical", "backgroundColor": "#0F172A", "paddingAll": "20px",
            "contents": [
                {"type": "text", "text": "SIRINTHANATTH PRIME", "weight": "bold", "color": "#D4AF37", "size": "sm", "letterSpacing": "2px"},
                {"type": "text", "text": "VIP Executive Onboarding", "weight": "bold", "color": "#FFFFFF", "size": "lg", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box", "layout": "vertical", "backgroundColor": "#FFFFFF", "spacing": "md",
            "contents": [
                {"type": "text", "text": "เอกสิทธิ์การดูแลระดับพรีเมียม", "weight": "bold", "size": "md", "color": "#1E293B"},
                {"type": "text", "text": "ระบบผู้ช่วยอัจฉริยะพร้อมดูแลและบริหารจัดการข้อมูลของคุณอย่างละเอียดอ่อน กรุณาเลือกรูปแบบคู่มือที่คุณสะดวกรับชมได้ทันทีครับ", "wrap": True, "color": "#64748B", "size": "sm", "lineSpacing": "4px"}
            ]
        },
        "footer": {
            "type": "box", "layout": "vertical", "spacing": "sm",
            "contents": [
                {"type": "button", "style": "primary", "color": "#D4AF37", "height": "sm", "action": {"type": "uri", "label": "📖 อ่านคู่มือฉบับเต็ม", "uri": f"{BASE_URL}/docs"}},
                {"type": "button", "style": "secondary", "height": "sm", "action": {"type": "message", "label": "🎧 ฟังคำแนะนำเสียง (Audio)", "text": "ฟังคู่มือ"}}
            ]
        }
    }

def send_onboarding_sequence(reply_token: str):
    """ฟังก์ชันส่งข้อความต้อนรับ + คลิปเสียง + การ์ดคู่มือ VIP เมื่อลูกค้ากดเพิ่มเพื่อน"""
    welcome_audio_url = f"{BASE_URL}/static/audio/welcome_greeting.mp3"
    try:
        messages = [
            TextSendMessage(text="🌟 ยินดีต้อนรับสู่ SIRINTHANATTH PRIME\nผู้ช่วยอัจฉริยะส่วนตัวระดับผู้บริหาร พร้อมดูแลคุณตลอด 24 ชั่วโมงครับ"),
            AudioSendMessage(original_content_url=welcome_audio_url, duration=20000),
            FlexSendMessage(alt_text="VIP Executive Onboarding Guide", contents=get_vip_guide_flex())
        ]
        line_bot_api.reply_message(reply_token, messages)
        logger.info("✅ [System]: Onboarding sequence sent successfully.")
    except LineBotApiError as e:
        logger.error(f"❌ [Onboarding Error]: {e}")

# =================================================================
# 🌟 Core Engine: ท่อประมวลผลสมองกล (Background Task)
# =================================================================
async def process_ai_and_reply(user_id: str, incoming_message: str, reply_token: str, bg_tasks: BackgroundTasks, file_path: str = None, file_type: str = None):
    try:
        # 1. 🛡️ โหมดด่านตรวจ CEO (God Mode)
        if ceo_secretary and ceo_secretary.is_ceo(user_id):
            logger.info(f"👑 [God Mode]: รับคำสั่งจากท่านประธาน User: {user_id}")
            
            # ตรวจสอบว่าเป็น Asynchronous Function หรือไม่
            if asyncio.iscoroutinefunction(ceo_secretary.process_ceo_command):
                reply_payload = await ceo_secretary.process_ceo_command(incoming_message, file_path=file_path, file_type=file_type)
            else:
                reply_payload = await asyncio.to_thread(ceo_secretary.process_ceo_command, incoming_message, file_path, file_type)
                
            if isinstance(reply_payload, dict): 
                await asyncio.to_thread(send_line_custom_payload, reply_token, reply_payload)
            else: 
                await asyncio.to_thread(line_bot_api.reply_message, reply_token, TextSendMessage(text=str(reply_payload)))
            return

        # 2. 👥 โหมดลูกค้าทั่วไป (Prime Brain & Central Boss)
        reply_msg = ""
        
        # ตรวจจับคำสั่งลัดด่วน (Quick Commands)
        if incoming_message.strip() in ["เมนู", "ฟังคู่มือ", "ฟังคำแนะนำเสียง"]:
            guide_audio_url = f"{BASE_URL}/static/audio/user_guide_audio.mp3"
            await asyncio.to_thread(
                line_bot_api.reply_message, reply_token, [
                    TextSendMessage(text="🎧 กำลังส่งคลิปเสียงคำแนะนำการใช้งานสำหรับท่านครับ..."),
                    AudioSendMessage(original_content_url=guide_audio_url, duration=90000)
                ]
            )
            return

        # เข้าสู่สมองอัจฉริยะ Prime Brain (RAG & Vision)
        if generate_intelligent_response:
            try:
                if asyncio.iscoroutinefunction(generate_intelligent_response):
                    reply_msg = await generate_intelligent_response(user_id, incoming_message, file_path=file_path, file_type=file_type)
                else:
                    reply_msg = await asyncio.to_thread(generate_intelligent_response, user_id, incoming_message, file_path, file_type)
                logger.info(f"🧠 [Prime Brain]: ประมวลผลสำเร็จสำหรับผู้ใช้ {user_id}")
            except Exception as prime_err:
                logger.warning(f"⚠️ [Prime Brain Error]: สะดุด ({prime_err}) สลับไปใช้ Central Boss")
                if boss_agent:
                    reply_msg = await asyncio.to_thread(boss_agent.route_task, user_id, incoming_message, bg_tasks, incoming_message, file_path, file_type)
        else:
            # Fallback ไปหา Boss หรือใช้ Gemini เพียวๆ
            if boss_agent:
                reply_msg = await asyncio.to_thread(boss_agent.route_task, user_id, incoming_message, bg_tasks, incoming_message, file_path, file_type)
            elif client:
                try:
                    prompt = f"คุณคือ AI ผู้ช่วยระดับบริหารของระบบ 'SIRINTHANATTH PRIME'\nลูกค้าส่งข้อความมาว่า: {incoming_message}"
                    # 🚀 ใช้ขุมพลัง gemini-1.5-pro (หรือรุ่นล่าสุดที่เสถียร เพื่อกัน Error 404)
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model='gemini-1.5-pro',
                        contents=prompt
                    )
                    reply_msg = response.text
                except Exception as e:
                    logger.error(f"❌ [Gemini Raw Engine Error]: {e}")
                    reply_msg = f"ได้รับข้อความ: '{incoming_message}' (ระบบกำลังปรับปรุงคีย์)"
            else:
                reply_msg = f"ได้รับข้อความ: '{incoming_message}' (ระบบประมวลผลออฟไลน์)"

        # 3. จัดเตรียมกล่องข้อความตอบกลับ
        messages_to_send = [TextSendMessage(text=str(reply_msg))]
        
        # 🎙️ ระบบเสียง Voice AI (ElevenLabs) ยังคงทำงานได้สมบูรณ์
        if file_type == 'audio' and generate_voice_from_text:
            try:
                filename, duration_ms = await asyncio.to_thread(generate_voice_from_text, reply_msg)
                if filename: 
                    messages_to_send.append(AudioSendMessage(original_content_url=f"{BASE_URL}/static/audio/{filename}", duration=duration_ms))
            except Exception as voice_err:
                logger.error(f"❌ [Voice AI Error]: {voice_err}")
        
        # ส่งข้อความกลับหาลูกค้าผ่าน Thread เพื่อไม่ให้บล็อกระบบ
        await asyncio.to_thread(line_bot_api.reply_message, reply_token, messages_to_send)
        
    except Exception as e: 
        logger.error(f"❌ [Critical Reply Error]: {e}")
        try:
            await asyncio.to_thread(line_bot_api.reply_message, reply_token, TextSendMessage(text="ขออภัยครับ ขณะนี้ระบบประมวลผลหลักกำลังปรับปรุง ท่านสามารถพิมพ์ 'เมนู' เพื่อดูบริการของเราได้ครับ"))
        except:
            pass
    finally:
        # 🧹 ทำความสะอาดลบไฟล์ขยะ (Zero-Data Retention)
        if file_path and os.path.exists(file_path):
            try: 
                os.remove(file_path)
            except: 
                pass

# =================================================================
# 🌐 Webhook Gateway (ด่านหน้ารับข้อมูลจาก LINE)
# =================================================================
@router.post("/webhook")
async def line_webhook(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    """รับข้อความและไฟล์จาก LINE OA อย่างปลอดภัยไร้รอยต่อ"""
    if not parser:
        raise HTTPException(status_code=500, detail="Webhook Parser is not initialized (Missing LINE_CHANNEL_SECRET).")
        
    body = await request.body()
    try: 
        events = parser.parse(body.decode('utf-8'), x_line_signature)
    except InvalidSignatureError: 
        raise HTTPException(status_code=400, detail="Invalid signature.")
        
    for event in events:
        # 🌟 แจกคู่มือ VIP เมื่อมีการ Add Friend เข้ามาใหม่
        if isinstance(event, FollowEvent):
            background_tasks.add_task(send_onboarding_sequence, event.reply_token)
            continue

        if isinstance(event, MessageEvent):
            user_id = event.source.user_id
            reply_token = event.reply_token
            message_type = event.message.type
            incoming_message, file_path, file_type = "", None, None

            # [Case 1]: ข้อความตัวอักษร
            if message_type == 'text': 
                incoming_message = event.message.text.strip()
                
                # 👑 คำสั่งลับ ปลดล็อก CEO 
                if incoming_message == "PRIME: UNLOCK CEO":
                    reply_msg = (f"👑 [SYSTEM OVERRIDE SUCCESS]\n"
                                 f"ท่านประธานครับ LINE ID ของท่านคือ:\n\n"
                                 f"{user_id}\n\n"
                                 f"กรุณาคัดลอกโค้ดนี้ไปใส่ในไฟล์ .env ในตัวแปร CEO_LINE_ID และ MASTER_ADMIN_LINE_ID เพื่อปลดล็อกระบบทั้งหมดครับ!")
                    background_tasks.add_task(line_bot_api.reply_message, reply_token, TextSendMessage(text=reply_msg))
                    continue

            # [Case 2]: ไฟล์ภาพ เสียง วิดีโอ หรือเอกสาร
            elif message_type in ['audio', 'image', 'video', 'file']:
                message_id = event.message.id
                try:
                    # โหลด Content แบบ Asynchronous
                    message_content = await asyncio.to_thread(line_bot_api.get_message_content, message_id)
                    ext = ".m4a" if message_type == 'audio' else ".jpg" if message_type == 'image' else ".mp4" if message_type == 'video' else ""
                    file_name = getattr(event.message, 'file_name', f"file_{message_id}") if message_type == 'file' else f"{message_id}{ext}"
                    
                    os.makedirs("/tmp", exist_ok=True)
                    file_path = f"/tmp/{file_name}"
                    
                    def save_file_to_disk(path, content):
                        with open(path, 'wb') as fd:
                            for chunk in content.iter_content(): 
                                fd.write(chunk)
                                
                    await asyncio.to_thread(save_file_to_disk, file_path, message_content)
                    incoming_message = f"[System Alert: อัปโหลดไฟล์ {message_type} สำเร็จ]"
                    file_type = message_type
                except Exception as e:
                    logger.error(f"❌ [File Download Error]: {e}")
                    continue
            else: 
                continue
            
            # โยนเข้าท่อประมวลผล (Non-blocking I/O)
            background_tasks.add_task(process_ai_and_reply, user_id, incoming_message, reply_token, background_tasks, file_path, file_type)
            
    # แจ้งสถานะกลับ LINE ทันที เพื่อป้องกัน 504 Gateway Timeout
    return {"status": "OK"}