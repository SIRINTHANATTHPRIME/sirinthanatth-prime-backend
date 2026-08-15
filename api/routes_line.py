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

# ตั้งค่า Gemini AI API Key (รองรับทุกลักษณะตัวแปร)
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

# 3. 👑 เลขาฯ ส่วนตัว (CEO God Mode - Executive Privilege & VVIP Management)
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

# =========================================================
# System Initialization (ตั้งค่าระบบ)
# =========================================================
router = APIRouter()

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
line_bot_api = LineBotApi(LINE_TOKEN)
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET", ""))

boss_agent = CentralBossAgent()
BASE_URL = os.getenv("BASE_URL", "https://www.sirinthanatthprime.com")

# 🛠️ ฟังก์ชันพิเศษ: ส่ง Flex Message หรือ Custom JSON Payload จากเลขาฯ
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
        print(f"📤 [System Info]: Transmitted Custom Payload Successfully.")
    except Exception as e:
        print(f"❌ [System Error]: Custom Payload Transmission Failed -> {e}")


# 🌟 ฟังก์ชันหลัก: การประมวลผลคู่ขนานแบบไร้รอยต่อ (Background Task Processor)
async def process_ai_and_reply(user_id: str, incoming_message: str, reply_token: str, file_path: str = None, file_type: str = None):
    try:
        # ---------------------------------------------------------
        # 👑 [GOD MODE & VVIP CONTROL]: ตรวจสอบสิทธิ์ผู้บริหารสูงสุด
        # ---------------------------------------------------------
        if ceo_secretary and ceo_secretary.is_ceo(user_id):
            print(f"👑 [Security Auth]: CEO Access Granted for {user_id}. Routing to God Mode.")
            reply_payload = await ceo_secretary.process_ceo_command(incoming_message)
            
            if isinstance(reply_payload, dict):
                send_line_custom_payload(reply_token, reply_payload)
            else:
                line_bot_api.reply_message(reply_token, TextSendMessage(text=str(reply_payload)))
            return

        # ---------------------------------------------------------
        # 👥 [USER & VVIP TOKEN MODE]: ประมวลผลด้วย Gemini AI อัจฉริยะ
        # ---------------------------------------------------------
        reply_msg = ""
        
        try:
            if GEMINI_KEY:
                # เรียกใช้งาน Gemini AI โดยตรง เพื่อตอบคำถามเชิงลึกเรื่อง VVIP, Token และบริการ
                model = genai.GenerativeModel('gemini-2.5-flash')
                prompt = f"""
                คุณคือ AI ผู้ช่วยระดับผู้บริหารของระบบ 'SIRINTHANATTH PRIME' ซึ่งบริหารโดย คุณวีระชัย สิรินทร์ธนัตถ์ (ผู้เชี่ยวชาญด้านอสังหาริมทรัพย์และที่ปรึกษาทางการเงิน/ประกันชีวิต)
                ผู้ใช้งานส่งข้อความมาว่า: "{incoming_message}"
                
                คำแนะนำในการตอบ:
                - ให้คำตอบอย่างมืออาชีพ สุภาพ ชัดเจน และตรงประเด็น
                - หากผู้ใช้สอบถามเกี่ยวกับการกำหนดสิทธิ์ VVIP หรือการตั้งค่า Token ให้แนะนำแนวทางปฏิบัติที่เป็นระบบ (เช่น การจัดการสิทธิ์ผ่านฐานข้อมูล, การจำกัดโควตา, หรือการให้สิทธิพิเศษผู้บริหาร)
                - ห้ามใช้ข้อความจำลองเดิมๆ แต่ให้วิเคราะห์และตอบคำถามจริงๆ อย่างชาญฉลาด
                """
                response = model.generate_content(prompt)
                reply_msg = response.text
            else:
                reply_msg = f"SIRINTHANATTH PRIME ได้รับข้อความของคุณแล้ว: '{incoming_message}' (กรุณาตั้งค่า GEMINI_API_KEY ในระบบเพื่อเปิดใช้งานสมองกลเต็มรูปแบบ)"
        except Exception as e:
            print(f"⚠️ [Gemini Error]: {e} -> Fallback to Central Boss.")
            reply_msg = boss_agent.route_task(user_id, incoming_message, None)

        # 2. เตรียมแพ็กเกจข้อความ
        messages_to_send = [TextSendMessage(text=reply_msg)]

        # 3. 🎙️ ระบบ Smart Walkie-Talkie (หากส่งเสียงมา จะตอบกลับเป็นเสียงพากย์)
        if file_type == 'audio' and generate_voice_from_text:
            print("🎙️ [Voice Synthesizer]: Audio input detected. Generating Executive Voice Reply...")
            filename, duration_ms = generate_voice_from_text(reply_msg)
            
            if filename:
                audio_url = f"{BASE_URL}/static/audio/{filename}"
                messages_to_send.append(AudioSendMessage(
                    original_content_url=audio_url,
                    duration=duration_ms
                ))

        # 4. ส่งข้อความกลับหาผู้ใช้ทาง LINE
        line_bot_api.reply_message(reply_token, messages_to_send)
        print(f"📤 [Delivery Success]: Payload delivered to User: {user_id}")
        
    except Exception as e:
        print(f"❌ [Critical Failure]: Process halted during AI response -> {e}")
    finally:
        # 🛡️ [PDPA COMPLIANCE]: Zero-Data Retention Protocol (ลบไฟล์ชั่วคราวทิ้งทันที)
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🗑️ [Security Clean-up]: Local temporary file shredded ({file_path}).")
            except Exception as e:
                print(f"⚠️ [Clean-up Warning]: Failed to shred file {file_path} -> {e}")


# 🌐 Endpoint รับสัญญาณจาก LINE (Webhook Gateway)
@router.post("/api/v1/line/webhook")
async def line_webhook(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    """รับสัญญาณทุกรูปแบบจากผู้ใช้งานและกระจายงานเข้า Background Task อย่างปลอดภัย"""
    body = await request.body()
    body_str = body.decode('utf-8')
    
    # 🛡️ ตรวจสอบลายเซ็นความปลอดภัย (Signature Validation)
    try:
        events = parser.parse(body_str, x_line_signature)
    except InvalidSignatureError:
        print("❌ [Security Alert]: Invalid LINE Signature detected. Access Denied.")
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
                print(f"📩 [Incoming Traffic]: TEXT from {user_id} -> {incoming_message[:30]}...")
                
            # [CASE 2]: มัลติมีเดียและเอกสาร
            elif message_type in ['audio', 'image', 'video', 'file']:
                message_id = event.message.id
                print(f"📩 [Incoming Traffic]: MEDIA [{message_type.upper()}] from {user_id} (ID: {message_id})")
                
                try:
                    message_content = line_bot_api.get_message_content(message_id)
                    ext = ""
                    if message_type == 'audio': ext = ".m4a"
                    elif message_type == 'image': ext = ".jpg"
                    elif message_type == 'video': ext = ".mp4"
                    
                    if message_type == 'file':
                        file_name = getattr(event.message, 'file_name', f"file_{message_id}")
                        file_path = f"/tmp/{message_id}_{file_name}"
                    else:
                        file_path = f"/tmp/{message_id}{ext}"
                        
                    with open(file_path, 'wb') as fd:
                        for chunk in message_content.iter_content():
                            fd.write(chunk)
                    
                    incoming_message = f"[System Alert: User uploaded a {message_type} file for analysis]"
                    file_type = message_type
                    print(f"💾 [Storage Allocation]: File cached temporarily at {file_path}")
                    
                except Exception as e:
                    print(f"❌ [Network Error]: Failed to retrieve media from LINE Server -> {e}")
                    continue
            else:
                print(f"⚠️ [Unsupported Format]: Received unhandled type -> {message_type}")
                continue
            
            # 🚀 กระจายงานเข้าสู่ Background Worker
            background_tasks.add_task(process_ai_and_reply, user_id, incoming_message, reply_token, file_path, file_type)
        
    return {"status": "OK"}