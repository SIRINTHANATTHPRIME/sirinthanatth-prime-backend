import os
import asyncio
import requests
import google.generativeai as genai
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, AudioMessage, ImageMessage, 
    VideoMessage, FileMessage, TextSendMessage, AudioSendMessage, ImageSendMessage, VideoSendMessage
)

# =========================================================
# 👑 SIRINTHANATTH PRIME - Enterprise API Router
# =========================================================

GEMINI_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("AI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

# 1. สมองกลส่วนกลาง (Central Routing)
from agents.central_boss import CentralBossAgent

# 2. สมองอัจฉริยะ (RAG, Vision, Data Analytics)
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

# 4. 🎙️ กล่องเสียง (Voice Module)
try:
    from services.elevenlabs_service import generate_voice_from_text
except ImportError:
    generate_voice_from_text = None

router = APIRouter()

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
line_bot_api = LineBotApi(LINE_TOKEN)
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET", ""))
boss_agent = CentralBossAgent()
BASE_URL = os.getenv("BASE_URL", "https://www.sirinthanatthprime.com")

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
    except Exception as e:
        print(f"❌ [System Error]: Custom Payload Transmission Failed -> {e}")

async def process_ai_and_reply(user_id: str, incoming_message: str, reply_token: str, file_path: str = None, file_type: str = None):
    try:
        # ตรวจสอบสิทธิ์ CEO
        if ceo_secretary and ceo_secretary.is_ceo(user_id):
            reply_payload = await ceo_secretary.process_ceo_command(incoming_message)
            if isinstance(reply_payload, dict):
                send_line_custom_payload(reply_token, reply_payload)
            else:
                line_bot_api.reply_message(reply_token, TextSendMessage(text=str(reply_payload)))
            return

        reply_msg = ""
        try:
            if GEMINI_KEY:
                model = genai.GenerativeModel('gemini-2.5-flash')
                prompt = f"คุณคือ AI ผู้ช่วยระดับผู้บริหารของระบบ 'SIRINTHANATTH PRIME' บริหารโดย คุณวีระชัย สิรินทร์ธนัตถ์...\nผู้ใช้งานส่งข้อความมาว่า: {incoming_message}"
                response = model.generate_content(prompt)
                reply_msg = response.text
            else:
                reply_msg = f"ได้รับข้อความ: '{incoming_message}' (กรุณาตั้งค่า GEMINI_API_KEY)"
        except Exception as e:
            reply_msg = boss_agent.route_task(user_id, incoming_message, None)

        messages_to_send = [TextSendMessage(text=reply_msg)]

        if file_type == 'audio' and generate_voice_from_text:
            filename, duration_ms = generate_voice_from_text(reply_msg)
            if filename:
                audio_url = f"{BASE_URL}/static/audio/{filename}"
                messages_to_send.append(AudioSendMessage(original_content_url=audio_url, duration=duration_ms))

        line_bot_api.reply_message(reply_token, messages_to_send)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if file_path and os.path.exists(file_path):
            try: os.remove(file_path)
            except: pass

# 👇 ปรับเป็น /webhook เพื่อประกอบกับ /api/v1/line ใน main.py
@router.post("/webhook")
async def line_webhook(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    body = await request.body()
    body_str = body.decode('utf-8')
    
    try:
        events = parser.parse(body_str, x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature.")
        
    for event in events:
        if isinstance(event, MessageEvent):
            user_id = event.source.user_id
            reply_token = event.reply_token
            message_type = event.message.type

            incoming_message = ""
            file_path = None
            file_type = None

            if message_type == 'text':
                incoming_message = event.message.text
            elif message_type in ['audio', 'image', 'video', 'file']:
                message_id = event.message.id
                try:
                    message_content = line_bot_api.get_message_content(message_id)
                    ext = ".m4a" if message_type == 'audio' else ".jpg" if message_type == 'image' else ".mp4" if message_type == 'video' else ""
                    if message_type == 'file':
                        file_name = getattr(event.message, 'file_name', f"file_{message_id}")
                        file_path = f"/tmp/{message_id}_{file_name}"
                    else:
                        file_path = f"/tmp/{message_id}{ext}"
                        
                    with open(file_path, 'wb') as fd:
                        for chunk in message_content.iter_content():
                            fd.write(chunk)
                    incoming_message = f"[System Alert: User uploaded a {message_type}]"
                    file_type = message_type
                except:
                    continue
            else:
                continue
            
            background_tasks.add_task(process_ai_and_reply, user_id, incoming_message, reply_token, file_path, file_type)
        
    return {"status": "OK"}