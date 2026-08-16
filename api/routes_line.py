import os
import asyncio
import requests
import logging
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, FollowEvent, TextMessage, AudioMessage, ImageMessage, 
<<<<<<< HEAD
    VideoMessage, FileMessage, TextSendMessage, AudioSendMessage, VideoSendMessage, ImageSendMessage, FlexSendMessage
=======
    VideoMessage, FileMessage, TextSendMessage, AudioSendMessage, 
    FlexSendMessage, ImageSendMessage, VideoSendMessage
>>>>>>> 6a2e30c725309e2951341a326a1162c8a14a0e16
)
from google import genai
from google.genai import types

# =================================================================
# 👑 SIRINTHANATTH PRIME - Core API Router (World-Class Standard)
# =================================================================

# 1. System Configuration & Logging (ระบบเก็บ Log เพื่อให้ตรวจสอบข้อผิดพลาดง่ายขึ้น)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Prime-Router")

GEMINI_KEY = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

<<<<<<< HEAD
# โหลดระบบเก่าและระบบบริหารให้ทำงานร่วมกันได้อย่างสมบูรณ์
from agents.central_boss import CentralBossAgent
=======
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
BASE_URL = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")

line_bot_api = LineBotApi(LINE_TOKEN)
parser = WebhookParser(LINE_SECRET)
router = APIRouter()

# 2. Import Agents (ระบบจะยังคงทำงานได้แม้บางไฟล์กำลังปรับปรุง)
from agents.central_boss import CentralBossAgent
boss_agent = CentralBossAgent()
>>>>>>> 6a2e30c725309e2951341a326a1162c8a14a0e16

try:
    from agents.worker_0_ceo_secretary import CeoSecretaryWorker
    ceo_secretary = CeoSecretaryWorker()
<<<<<<< HEAD
except ImportError: 
    ceo_secretary = None

try: 
    from services.elevenlabs_service import generate_voice_from_text
except ImportError: 
    generate_voice_from_text = None

router = APIRouter()
LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
line_bot_api = LineBotApi(LINE_TOKEN)
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET", ""))
boss_agent = CentralBossAgent()
BASE_URL = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
=======
except ImportError:
    ceo_secretary = None

try: 
    from services.elevenlabs_service import generate_voice_from_text
except ImportError: 
    generate_voice_from_text = None
>>>>>>> 6a2e30c725309e2951341a326a1162c8a14a0e16


# 3. Utility Functions (ฟังก์ชันตัวช่วยส่งข้อความพิเศษ)
def send_line_custom_payload(reply_token: str, payload: dict):
    """ส่ง Custom Payload (เช่น Flex Message จาก JSON ตรงๆ สำหรับโหมด CEO)"""
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    data = {"replyToken": reply_token, "messages": [payload]}
    try: 
<<<<<<< HEAD
        requests.post("https://api.line.me/v2/bot/message/reply", headers=headers, json=data).raise_for_status()
    except Exception as e: 
        print(f"❌ [System Error]: {e}")

async def process_ai_and_reply(user_id: str, incoming_message: str, reply_token: str, bg_tasks: BackgroundTasks, file_path: str = None, file_type: str = None):
    try:
        # ==========================================
        # 👑 1. โหมดด่านตรวจ CEO (God Mode)
        # ==========================================
        if ceo_secretary and ceo_secretary.is_ceo(user_id):
            reply_payload = await ceo_secretary.process_ceo_command(incoming_message)
            if isinstance(reply_payload, dict): 
                send_line_custom_payload(reply_token, reply_payload)
            else: 
                line_bot_api.reply_message(reply_token, TextSendMessage(text=str(reply_payload)))
            return

        # ==========================================
        # 👥 2. โหมดลูกค้าทั่วไป (Central Boss Agent)
        # ==========================================
        # ให้ Central Boss (ที่เพิ่งอัปเกรด Gemini 3.7) ทำหน้าที่จ่ายงานและตอบกลับอัตโนมัติ
        reply_msg = boss_agent.route_task(
            user_id=user_id, 
            message=incoming_message, 
            bg_tasks=bg_tasks, 
            incoming_message=incoming_message,
            file_path=file_path,
            file_type=file_type
        )
=======
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
    except LineBotApiError as e:
        logger.error(f"❌ [Onboarding Error]: {e}")


# 4. Core AI Processing Function (แยกประมวลผลพื้นหลังเพื่อป้องกันการ Timeout)
async def process_ai_and_reply(user_id: str, incoming_message: str, reply_token: str, file_path: str = None, file_type: str = None):
    try:
        # 4.1 ตรวจสอบคำสั่งลัด (Quick Commands) เพื่อการตอบสนองทันที
        if incoming_message.strip() in ["เมนู", "ฟังคู่มือ", "ฟังคำแนะนำเสียง"]:
            guide_audio_url = f"{BASE_URL}/static/audio/user_guide_audio.mp3"
            line_bot_api.reply_message(
                reply_token,
                [
                    TextSendMessage(text="🎧 กำลังส่งคลิปเสียงคำแนะนำการใช้งานสำหรับท่านครับ..."),
                    AudioSendMessage(original_content_url=guide_audio_url, duration=90000)
                ]
            )
            return

        # 4.2 โหมดผู้บริหารสูงสุด (CEO Mode - ทำงานได้เสถียร 100%)
        if ceo_secretary and ceo_secretary.is_ceo(user_id):
            reply_payload = await ceo_secretary.process_ceo_command(incoming_message)
            if isinstance(reply_payload, dict): 
                send_line_custom_payload(reply_token, reply_payload)
            else: 
                line_bot_api.reply_message(reply_token, TextSendMessage(text=str(reply_payload)))
            return

        # 4.3 โหมดประมวลผลลูกค้าทั่วไป (ใช้ Gemini 3.7 Flash เพื่อความรวดเร็วและฉลาดสูงสุด)
        reply_msg = ""
        try:
            if client:
                prompt = f"คุณคือ AI ผู้ช่วยระดับบริหารของระบบ 'SIRINTHANATTH PRIME'\nลูกค้าสอบถามว่า: {incoming_message}"
                response = client.models.generate_content(
                    model='gemini-3.7-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.7)
                )
                reply_msg = response.text
            else: 
                reply_msg = "ขออภัยครับ ขณะนี้ระบบประมวลผลหลักกำลังเชื่อมต่อคีย์ข้อมูล ท่านสามารถทิ้งข้อความไว้ได้เลยครับ"
        except Exception as e:
            logger.warning(f"⚠️ [Gemini Engine Error]: {e} -> Fallback to Central Boss")
            
            # 4.4 ระบบแผนสำรอง: หาก Gemini 3.7 มีปัญหา จะส่งงานให้ Boss Agent
            try:
                reply_msg = boss_agent.route_task(user_id, incoming_message, file_path)
            except Exception as boss_e:
                logger.error(f"❌ [Boss Agent Error]: {boss_e}")
                reply_msg = "ขออภัยครับ ขณะนี้ระบบประมวลผลหลักกำลังปรับปรุง ท่านสามารถพิมพ์ 'เมนู' เพื่อดูบริการของเราได้ครับ"
>>>>>>> 6a2e30c725309e2951341a326a1162c8a14a0e16

        # 4.5 จัดเตรียมข้อความและเสียงตอบกลับ (ระบบ ElevenLabs เดิม)
        messages_to_send = [TextSendMessage(text=reply_msg)]
        
<<<<<<< HEAD
        # 🎙️ ระบบแปลงเสียงพูด (Voice AI)
        if file_type == 'audio' and generate_voice_from_text:
            filename, duration_ms = generate_voice_from_text(reply_msg)
            if filename: 
                audio_url = f"{BASE_URL}/static/audio/{filename}"
                messages_to_send.append(AudioSendMessage(original_content_url=audio_url, duration=duration_ms))
=======
        if file_type == 'audio' and generate_voice_from_text:
            filename, duration_ms = generate_voice_from_text(reply_msg)
            if filename: 
                messages_to_send.append(AudioSendMessage(original_content_url=f"{BASE_URL}/static/audio/{filename}", duration=duration_ms))
>>>>>>> 6a2e30c725309e2951341a326a1162c8a14a0e16
        
        # 4.6 ส่งมอบข้อความกลับหาลูกค้า
        line_bot_api.reply_message(reply_token, messages_to_send)
        
    except Exception as e: 
<<<<<<< HEAD
        print(f"❌ Error in Processing: {e}")
        # ด่านสุดท้ายเพื่อไม่ให้บอทเงียบ
        line_bot_api.reply_message(reply_token, TextSendMessage(text="ขออภัยครับ ขณะนี้ระบบประมวลผลหลักกำลังปรับปรุง ท่านสามารถพิมพ์ 'เมนู' เพื่อดูบริการของเราได้ครับ"))
=======
        logger.error(f"❌ [System Critical Error]: {e}")
>>>>>>> 6a2e30c725309e2951341a326a1162c8a14a0e16
    finally:
        # 4.7 ทำความสะอาดระบบลบไฟล์ชั่วคราวทิ้ง
        if file_path and os.path.exists(file_path):
            try: os.remove(file_path)
            except: pass


# 5. Webhook Endpoint (ด่านหน้าประตูรับลูกค้าจาก LINE)
@router.post("/webhook")
async def line_webhook(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    body = await request.body()
    try: 
        events = parser.parse(body.decode('utf-8'), x_line_signature)
    except InvalidSignatureError: 
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

<<<<<<< HEAD
            # ตรวจสอบว่าเป็นข้อความตัวอักษรหรือไม่
            if message_type == 'text': 
                incoming_message = event.message.text.strip()

                # 👑 คำสั่งลับ ปลดล็อก CEO (ย้ายมาวางตรงนี้หลังอ่านข้อความแล้ว จะทำงานได้ 100%)
                if incoming_message == "PRIME: UNLOCK CEO":
                    reply_msg = (f"👑 [SYSTEM OVERRIDE SUCCESS]\n"
                                 f"ท่านประธานครับ LINE ID ของท่านคือ:\n\n"
                                 f"{user_id}\n\n"
                                 f"กรุณาคัดลอกรหัสนี้ไปใส่ในไฟล์ .env ตัวแปร CEO_LINE_ID และ MASTER_ADMIN_LINE_ID ใน Cloud Run เพื่อปลดล็อกระดับสูงสุดครับ")
                    line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_msg))
                    continue

            # ตรวจสอบว่าเป็นข้อความมัลติมีเดีย/ไฟล์ หรือไม่
=======
            if message_type == 'text': 
                incoming_message = event.message.text
>>>>>>> 6a2e30c725309e2951341a326a1162c8a14a0e16
            elif message_type in ['audio', 'image', 'video', 'file']:
                message_id = event.message.id
                try:
                    message_content = line_bot_api.get_message_content(message_id)
                    ext = ".m4a" if message_type == 'audio' else ".jpg" if message_type == 'image' else ".mp4" if message_type == 'video' else ""
                    file_name = getattr(event.message, 'file_name', f"file_{message_id}") if message_type == 'file' else f"{message_id}{ext}"
                    
                    # ป้องกัน Error หากไม่มีโฟลเดอร์ /tmp ใน Cloud Run
                    os.makedirs("/tmp", exist_ok=True)
                    file_path = f"/tmp/{file_name}"
                    
                    with open(file_path, 'wb') as fd:
                        for chunk in message_content.iter_content(): fd.write(chunk)
<<<<<<< HEAD
                    incoming_message, file_type = f"[System Alert: อัปโหลดไฟล์ {message_type} สำเร็จ]", message_type
                except Exception as e: 
                    print(f"❌ File processing error: {e}")
                    continue
            else: 
                continue
            
            # ส่งต่องานให้ AI ประมวลผลแบบเบื้องหลัง (Background Task) เพื่อให้ LINE ไม่ติด Timeout
            background_tasks.add_task(process_ai_and_reply, user_id, incoming_message, reply_token, background_tasks, file_path, file_type)
            
    return {"status": "OK"}
=======
                    incoming_message = f"[System Alert: อัปโหลดไฟล์ {message_type} สำเร็จ]"
                    file_type = message_type
                except Exception as e: 
                    logger.error(f"❌ [File Download Error]: {e}")
                    continue
            else: 
                continue
            
            # ส่งงานให้ Background Task เพื่อให้เซิร์ฟเวอร์ตอบรับ LINE ทันที (ป้องกันอาการค้าง)
            background_tasks.add_task(process_ai_and_reply, user_id, incoming_message, reply_token, file_path, file_type)
            
    return {"status": "OK"}
>>>>>>> 6a2e30c725309e2951341a326a1162c8a14a0e16
