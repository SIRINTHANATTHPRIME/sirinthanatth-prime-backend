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

# Load Environment Variables
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
BASE_URL = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
GEMINI_KEY = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""

# Initialize APIs
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None
line_bot_api = LineBotApi(LINE_TOKEN)
parser = WebhookParser(LINE_SECRET)
router = APIRouter()

# 2. Import Agents (Dynamic Import เพื่อป้องกัน Error กรณีไฟล์อื่นกำลังปรับปรุง)
try:
    from agents.central_boss import CentralBossAgent
    boss_agent = CentralBossAgent()
except ImportError as e:
    logger.error(f"⚠️ ไม่สามารถโหลด CentralBossAgent ได้: {e}")
    boss_agent = None

try:
    from agents.worker_0_ceo_secretary import CeoSecretaryWorker
    ceo_secretary = CeoSecretaryWorker()
except ImportError:
    ceo_secretary = None

try: 
    from services.elevenlabs_service import generate_voice_from_text
except ImportError: 
    generate_voice_from_text = None


# 3. Utility Functions (ฟังก์ชันพิเศษสำหรับ LINE)
def send_line_custom_payload(reply_token: str, payload: dict):
    """ส่ง Custom Payload (เช่น Flex Message จาก JSON ตรงๆ สำหรับโหมด CEO)"""
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
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0F172A",
            "paddingAll": "20px",
            "contents": [
                {"type": "text", "text": "SIRINTHANATTH PRIME", "weight": "bold", "color": "#D4AF37", "size": "sm", "letterSpacing": "2px"},
                {"type": "text", "text": "VIP Executive Onboarding", "weight": "bold", "color": "#FFFFFF", "size": "lg", "margin": "xs"}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#FFFFFF",
            "spacing": "md",
            "contents": [
                {"type": "text", "text": "เอกสิทธิ์การดูแลระดับพรีเมียม", "weight": "bold", "size": "md", "color": "#1E293B"},
                {"type": "text", "text": "ระบบผู้ช่วยอัจฉริยะพร้อมดูแลและบริหารจัดการข้อมูลของคุณอย่างละเอียดอ่อน กรุณาเลือกรูปแบบคู่มือที่คุณสะดวกรับชมได้ทันทีครับ", "wrap": True, "color": "#64748B", "size": "sm", "lineSpacing": "4px"}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
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
        logger.info("✅ [System]: Onboarding sent successfully.")
    except LineBotApiError as e:
        logger.error(f"❌ [Onboarding Error]: {e}")


# 4. Core AI Processing Function (ประมวลผลพื้นหลัง ป้องกันการ Timeout)
async def process_ai_and_reply(user_id: str, incoming_message: str, reply_token: str, bg_tasks: BackgroundTasks, file_path: str = None, file_type: str = None):
    try:
        # 4.1 ตรวจสอบคำสั่งลัด (Quick Commands)
        if incoming_message.strip() in ["เมนู", "ฟังคู่มือ", "ฟังคำแนะนำเสียง"]:
            guide_audio_url = f"{BASE_URL}/static/audio/user_guide_audio.mp3"
            # ใช้ asyncio.to_thread เพื่อป้องกัน Sync Block ໃນ Async Loop
            await asyncio.to_thread(
                line_bot_api.reply_message,
                reply_token,
                [
                    TextSendMessage(text="🎧 กำลังส่งคลิปเสียงคำแนะนำการใช้งานสำหรับท่านครับ..."),
                    AudioSendMessage(original_content_url=guide_audio_url, duration=90000)
                ]
            )
            return

        # 4.2 โหมดผู้บริหารสูงสุด (CEO God Mode)
        if ceo_secretary and ceo_secretary.is_ceo(user_id):
            # ตรวจสอบว่าเป็น async function หรือไม่
            if asyncio.iscoroutinefunction(ceo_secretary.process_ceo_command):
                reply_payload = await ceo_secretary.process_ceo_command(incoming_message)
            else:
                reply_payload = await asyncio.to_thread(ceo_secretary.process_ceo_command, incoming_message)
                
            if isinstance(reply_payload, dict): 
                await asyncio.to_thread(send_line_custom_payload, reply_token, reply_payload)
            else: 
                await asyncio.to_thread(line_bot_api.reply_message, reply_token, TextSendMessage(text=str(reply_payload)))
            return

        # 4.3 โหมดประมวลผลลูกค้าทั่วไป (ประสานงาน Central Boss Agent)
        reply_msg = ""
        if boss_agent:
            try:
                # โยนงานให้ Boss ตัดสินใจ (ดึงความสามารถจากทั้งสองเวอร์ชันมาผสานกัน)
                # เช็กก่อนว่า route_task รองรับแบบ Async หรือไม่
                if asyncio.iscoroutinefunction(boss_agent.route_task):
                    reply_msg = await boss_agent.route_task(
                        user_id=user_id, 
                        message=incoming_message, 
                        bg_tasks=bg_tasks, 
                        incoming_message=incoming_message,
                        file_path=file_path,
                        file_type=file_type
                    )
                else:
                    reply_msg = await asyncio.to_thread(
                        boss_agent.route_task,
                        user_id, incoming_message, bg_tasks, incoming_message, file_path, file_type
                    )
            except Exception as boss_e:
                logger.error(f"❌ [Boss Agent Error]: {boss_e}")
                reply_msg = "ขออภัยครับ ขณะนี้ระบบบริหารจัดการคิวกำลังหนาแน่น ท่านสามารถพิมพ์ 'เมนู' เพื่อดูบริการของเราได้ครับ"
        else:
            # Fallback ป้องกันระบบพัง กรณีหา Boss ไม่เจอ
            if client:
                try:
                    prompt = f"คุณคือ AI ผู้ช่วยระดับบริหารของระบบ 'SIRINTHANATTH PRIME'\nลูกค้าสอบถามว่า: {incoming_message}"
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model='gemini-1.5-pro', # อัปเดตใช้ชื่อโมเดลล่าสุดที่เสถียรบน Google API
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.7)
                    )
                    reply_msg = response.text
                except Exception as e:
                    logger.error(f"⚠️ [Gemini Engine Error]: {e}")
                    reply_msg = "ขออภัยครับ ขณะนี้ระบบประมวลผลหลักกำลังปรับปรุง ท่านสามารถทิ้งข้อความไว้ได้เลยครับ"

        # 4.4 จัดเตรียมข้อความและเสียงตอบกลับ
        messages_to_send = [TextSendMessage(text=str(reply_msg))]
        
        # 🎙️ ระบบแปลงเสียงพูด (Voice AI)
        if file_type == 'audio' and generate_voice_from_text:
            try:
                filename, duration_ms = await asyncio.to_thread(generate_voice_from_text, reply_msg)
                if filename: 
                    audio_url = f"{BASE_URL}/static/audio/{filename}"
                    messages_to_send.append(AudioSendMessage(original_content_url=audio_url, duration=duration_ms))
            except Exception as voice_e:
                logger.error(f"❌ [Voice Generation Error]: {voice_e}")
        
        # 4.5 ส่งมอบข้อความกลับหาลูกค้า
        await asyncio.to_thread(line_bot_api.reply_message, reply_token, messages_to_send)
        
    except Exception as e: 
        logger.error(f"❌ [System Critical Error]: {e}")
        # ด่านสุดท้ายเพื่อไม่ให้บอทเงียบ
        try:
            await asyncio.to_thread(line_bot_api.reply_message, reply_token, TextSendMessage(text="ระบบขัดข้องชั่วคราว โปรดพิมพ์ 'เมนู' เพื่อดำเนินการต่อครับ"))
        except:
            pass
    finally:
        # 4.6 ทำความสะอาดระบบลบไฟล์ชั่วคราวทิ้ง (Zero-Data Retention)
        if file_path and os.path.exists(file_path):
            try: 
                os.remove(file_path)
                logger.info(f"🧹 [System]: ลบไฟล์ชั่วคราว {file_path} สำเร็จ")
            except Exception as cleanup_e: 
                logger.error(f"❌ [Cleanup Error]: {cleanup_e}")


# 5. Webhook Endpoint (ด่านหน้าประตูรับลูกค้าจาก LINE)
@router.post("/webhook")
async def line_webhook(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    body = await request.body()
    body_str = body.decode('utf-8')
    
    try: 
        events = parser.parse(body_str, x_line_signature)
    except InvalidSignatureError: 
        logger.error("❌ Invalid Signature: โปรดเช็ก LINE_CHANNEL_SECRET ใน .env")
        raise HTTPException(status_code=400, detail="Invalid signature.")
        
    for event in events:
        
        # 🌟 ลูกค้าใหม่กดเพิ่มเพื่อน (Onboarding Flow)
        if isinstance(event, FollowEvent):
            background_tasks.add_task(send_onboarding_sequence, event.reply_token)
            continue

        # 💬 ลูกค้าส่งข้อความแชท
        if isinstance(event, MessageEvent):
            user_id = event.source.user_id
            reply_token = event.reply_token
            message_type = event.message.type
            incoming_message, file_path, file_type = "", None, None

            # 5.1 ตรวจสอบว่าเป็นข้อความตัวอักษร
            if message_type == 'text': 
                incoming_message = event.message.text.strip()

                # 👑 คำสั่งลับ ปลดล็อก CEO (Override)
                if incoming_message == "PRIME: UNLOCK CEO":
                    reply_msg = (f"👑 [SYSTEM OVERRIDE SUCCESS]\n"
                                 f"ท่านประธานครับ LINE ID ของท่านคือ:\n\n"
                                 f"{user_id}\n\n"
                                 f"กรุณาคัดลอกรหัสนี้ไปใส่ในไฟล์ .env ตัวแปร CEO_LINE_ID และ MASTER_ADMIN_LINE_ID ครับ")
                    # ส่งข้อความทันที ไม่ต้องผ่าน AI
                    background_tasks.add_task(line_bot_api.reply_message, reply_token, TextSendMessage(text=reply_msg))
                    continue

            # 5.2 ตรวจสอบว่าเป็นข้อความมัลติมีเดีย/ไฟล์
            elif message_type in ['audio', 'image', 'video', 'file']:
                message_id = event.message.id
                try:
                    # ใช้ thread เพื่อไม่ให้การดาวน์โหลดไฟล์บล็อกระบบ
                    message_content = await asyncio.to_thread(line_bot_api.get_message_content, message_id)
                    ext = ".m4a" if message_type == 'audio' else ".jpg" if message_type == 'image' else ".mp4" if message_type == 'video' else ""
                    file_name = getattr(event.message, 'file_name', f"file_{message_id}") if message_type == 'file' else f"{message_id}{ext}"
                    
                    # ป้องกัน Error หากไม่มีโฟลเดอร์ /tmp ใน Cloud Run
                    os.makedirs("/tmp", exist_ok=True)
                    file_path = f"/tmp/{file_name}"
                    
                    def save_file(path, content):
                        with open(path, 'wb') as fd:
                            for chunk in content.iter_content(): 
                                fd.write(chunk)
                                
                    await asyncio.to_thread(save_file, file_path, message_content)
                    incoming_message = f"[System Alert: อัปโหลดไฟล์ {message_type} สำเร็จ]"
                    file_type = message_type
                except Exception as e: 
                    logger.error(f"❌ [File Download Error]: {e}")
                    continue
            else: 
                continue # ข้ามประเภทข้อความที่ไม่รองรับ
            
            # 5.3 ส่งต่องานให้ AI ประมวลผลแบบเบื้องหลัง (Background Task) 
            background_tasks.add_task(process_ai_and_reply, user_id, incoming_message, reply_token, background_tasks, file_path, file_type)
            
    # ตอบกลับ LINE ทันที (ป้องกัน Timeout)
    return {"status": "OK"}