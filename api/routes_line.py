import os
import asyncio
import requests
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, AudioMessage, ImageMessage, 
    VideoMessage, FileMessage, TextSendMessage, AudioSendMessage, ImageSendMessage, VideoSendMessage, FileSendMessage
)

# ---------------------------------------------------------
# นำเข้าสมองกลระบบทั้งหมด
# ---------------------------------------------------------
# 1. สมองกลส่วนกลาง (ระบบเดิม)
from agents.central_boss import CentralBossAgent

# 2. สมองอัจฉริยะ (ระบบใหม่ RAG & Vision)
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

# 4. 🎙️ กล่องเสียง (Voice Module - ElevenLabs)
try:
    from services.elevenlabs_service import generate_voice_from_text
except ImportError:
    generate_voice_from_text = None

# ---------------------------------------------------------
# ตั้งค่า Router และ LINE API
# ---------------------------------------------------------
router = APIRouter()

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
line_bot_api = LineBotApi(LINE_TOKEN)
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET", ""))

boss_agent = CentralBossAgent()

# 🌐 โดเมนหลักของระบบ (ดึงจาก env หรือใช้ค่าเริ่มต้นสำหรับส่ง URL ไฟล์เสียงให้ LINE)
BASE_URL = os.getenv("BASE_URL", "https://www.sirinthanatthprime.com")

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


# 🌟 ฟังก์ชันหลัก: ให้ AI แอบไปคิดและตอบกลับแบบไม่ให้ LINE ตัดสาย
async def process_ai_and_reply(user_id: str, incoming_message: str, reply_token: str, file_path: str = None, file_type: str = None):
    try:
        # ==========================================
        # 👑 [GOD MODE]: ตรวจสอบสิทธิ์ท่านประธาน (CEO)
        # ==========================================
        if ceo_secretary and ceo_secretary.is_ceo(user_id):
            print("👑 [System]: ตรวจพบคำสั่งผู้บริหาร เข้าสู่โหมดเลขาฯ ส่วนตัว (CEO God Mode)")
            reply_payload = await ceo_secretary.process_ceo_command(incoming_message)
            send_line_custom_payload(reply_token, reply_payload)
            return

        # ==========================================
        # 👥 โหมดปกติสำหรับลูกค้า / ตัวแทน (User Mode)
        # ==========================================
        reply_msg = ""
        
        # 1. ให้สมองอัจฉริยะ (Prime Brain) คิดคำตอบ
        if generate_intelligent_response:
            try:
                reply_msg = generate_intelligent_response(user_id, incoming_message, file_path=file_path, file_type=file_type)
                print(f"🧠 [Prime Brain]: ประมวลผลสำเร็จสำหรับผู้ใช้ {user_id}")
            except Exception as e:
                print(f"⚠️ [Prime Brain Error]: ขัดข้อง ({e}) สลับไปใช้ระบบบอสชั่วคราว")
                reply_msg = boss_agent.route_task(user_id, incoming_message, None)
        else:
            reply_msg = boss_agent.route_task(user_id, incoming_message, None)

        # 2. จัดเตรียมแพ็กเกจข้อความที่จะส่งกลับ (เริ่มด้วย Text เสมอ)
        messages_to_send = [TextSendMessage(text=reply_msg)]

        # 3. 🎙️ ระบบ Smart Walkie-Talkie: ถ้าลูกค้าส่ง "เสียง" มา ให้ตอบกลับเป็น "เสียง" ด้วย
        if file_type == 'audio' and generate_voice_from_text:
            print("🎙️ [Voice Routing]: ตรวจพบข้อความเสียงจากลูกค้า กำลังสร้างเสียงตอบกลับ...")
            filename, duration_ms = generate_voice_from_text(reply_msg)
            
            if filename:
                audio_url = f"{BASE_URL}/static/audio/{filename}"
                # แนบไฟล์เสียงไปพร้อมกับข้อความตัวอักษรเลย!
                messages_to_send.append(AudioSendMessage(
                    original_content_url=audio_url,
                    duration=duration_ms
                ))
                print(f"✅ [Voice Routing]: แนบไฟล์เสียงลงในแพ็กเกจการตอบกลับเรียบร้อย")

        # 4. ส่งข้อความตอบกลับหาลูกค้า (LINE อนุญาตให้ส่งทีละหลายรูปแบบพร้อมกันได้)
        line_bot_api.reply_message(reply_token, messages_to_send)
        print(f"📤 [LINE AI Reply]: ตอบกลับ {user_id} สำเร็จ")
        
    except Exception as e:
        print(f"❌ [Critical Reply Error]: ไม่สามารถส่งข้อความได้ ({e})")
    finally:
        # 🧹 ระบบลบไฟล์ขยะอัตโนมัติ (Cleanup Temp Files)
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"🗑️ [Cleanup]: ลบไฟล์ชั่วคราว {file_path} เรียบร้อยแล้ว")
            except Exception as e:
                print(f"⚠️ [Cleanup Error]: ลบไฟล์ {file_path} ไม่สำเร็จ ({e})")


# 🌐 Endpoint สำหรับรับ Webhook จาก LINE
@router.post("/webhook")
async def line_webhook(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    """รับข้อความและไฟล์ทุกประเภทจาก LINE"""
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
                print(f"📩 [LINE API]: ได้รับข้อความจาก {user_id} -> {incoming_message[:50]}")
                
            elif message_type in ['audio', 'image', 'video', 'file']:
                message_id = event.message.id
                print(f"📩 [LINE API]: ได้รับไฟล์ประเภท [{message_type}] จาก {user_id} (ID: {message_id})")
                
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
                    
                    incoming_message = f"[System: ผู้ใช้ส่งไฟล์ประเภท {message_type}]"
                    file_type = message_type
                    print(f"💾 [LINE API]: บันทึกไฟล์ชั่วคราวสำเร็จที่ {file_path}")
                    
                except Exception as e:
                    print(f"❌ [LINE API Error]: ดาวน์โหลดไฟล์จาก LINE ไม่สำเร็จ ({e})")
                    continue
            else:
                print(f"⚠️ [LINE API]: ไม่รองรับข้อความประเภท {message_type} ในขณะนี้")
                continue
            
            # ส่งให้ Background Task ไปคิด วิเคราะห์ และสร้างเสียง
            background_tasks.add_task(process_ai_and_reply, user_id, incoming_message, reply_token, file_path, file_type)
        
    return {"status": "OK"}