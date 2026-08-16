import os
import asyncio
import requests
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, FollowEvent, TextMessage, AudioMessage, ImageMessage, 
    VideoMessage, FileMessage, TextSendMessage, AudioSendMessage, VideoSendMessage, ImageSendMessage, FlexSendMessage
)
# 🚀 อิมพอร์ต SDK มาตรฐานใหม่ล่าสุดของ Google
from google import genai

GEMINI_KEY = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# โหลดระบบเก่าและระบบบริหารให้ทำงานร่วมกันได้อย่างสมบูรณ์
from agents.central_boss import CentralBossAgent

try:
    from agents.worker_0_ceo_secretary import CeoSecretaryWorker
    ceo_secretary = CeoSecretaryWorker()
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

def send_line_custom_payload(reply_token: str, payload: dict):
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    data = {"replyToken": reply_token, "messages": [payload]}
    try: 
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

        messages_to_send = [TextSendMessage(text=reply_msg)]
        
        # 🎙️ ระบบแปลงเสียงพูด (Voice AI)
        if file_type == 'audio' and generate_voice_from_text:
            filename, duration_ms = generate_voice_from_text(reply_msg)
            if filename: 
                audio_url = f"{BASE_URL}/static/audio/{filename}"
                messages_to_send.append(AudioSendMessage(original_content_url=audio_url, duration=duration_ms))
        
        line_bot_api.reply_message(reply_token, messages_to_send)
        
    except Exception as e: 
        print(f"❌ Error in Processing: {e}")
        # ด่านสุดท้ายเพื่อไม่ให้บอทเงียบ
        line_bot_api.reply_message(reply_token, TextSendMessage(text="ขออภัยครับ ขณะนี้ระบบประมวลผลหลักกำลังปรับปรุง ท่านสามารถพิมพ์ 'เมนู' เพื่อดูบริการของเราได้ครับ"))
    finally:
        if file_path and os.path.exists(file_path):
            try: os.remove(file_path)
            except: pass

@router.post("/webhook")
async def line_webhook(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
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
                    incoming_message, file_type = f"[System Alert: อัปโหลดไฟล์ {message_type} สำเร็จ]", message_type
                except Exception as e: 
                    print(f"❌ File processing error: {e}")
                    continue
            else: 
                continue
            
            # ส่งต่องานให้ AI ประมวลผลแบบเบื้องหลัง (Background Task) เพื่อให้ LINE ไม่ติด Timeout
            background_tasks.add_task(process_ai_and_reply, user_id, incoming_message, reply_token, background_tasks, file_path, file_type)
            
    return {"status": "OK"}