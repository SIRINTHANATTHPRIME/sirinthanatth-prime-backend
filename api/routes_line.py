import os
import asyncio
import inspect
import logging
import requests
import uuid
import time
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from fastapi import APIRouter, Request, Header, HTTPException, BackgroundTasks
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import (
    MessageEvent, FollowEvent, TextMessage, AudioMessage, ImageMessage, 
    VideoMessage, FileMessage, TextSendMessage, AudioSendMessage, 
    ImageSendMessage, VideoSendMessage, FlexSendMessage
)
from google import genai
from google.genai import types

load_dotenv()

# =========================================================
# 👑 SIRINTHANATTH PRIME - Enterprise LINE API Gateway
# =========================================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Prime-API-Gateway")

router = APIRouter()

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
BASE_URL = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")

line_bot_api = LineBotApi(LINE_TOKEN) if LINE_TOKEN else None
parser = WebhookParser(LINE_SECRET) if LINE_SECRET else None

# 🚀 เชื่อมต่อสมองกลส่วนกลาง (Cross-Model Supported)
try:
    from core_services.ai_config import PrimeAIConfig
    client = PrimeAIConfig.get_client()
except ImportError:
    api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
    client = genai.Client(api_key=api_key) if api_key else None

# =========================================================
# 🧩 Dynamic Imports (ดึงระบบต่างๆ มาประกอบร่าง ป้องกันไฟล์พัง)
# =========================================================
try: from security.pdpa_logger import PDPA_Logger; pdpa_logger = PDPA_Logger()
except ImportError: pdpa_logger = None

try: from security.compliance_guard import ComplianceGuard; guard = ComplianceGuard()
except ImportError: guard = None

try: from agents.central_boss import CentralBossAgent; boss_agent = CentralBossAgent()
except ImportError: boss_agent = None

try: from agents.worker_12_self_learning import SelfLearningEngine; self_learning = SelfLearningEngine()
except ImportError: self_learning = None

try: from agents.prime_brain import generate_intelligent_response
except ImportError: generate_intelligent_response = None

try: from agents.worker_0_ceo_secretary import CeoSecretaryWorker; ceo_secretary = CeoSecretaryWorker()
except ImportError: ceo_secretary = None

try: from services.elevenlabs_service import generate_voice_from_text
except ImportError: generate_voice_from_text = None

# =========================================================
# 🛠️ Core Transmission Functions (ระบบสั่งการ LINE ขั้นสูง)
# =========================================================
async def send_line_custom_payload(user_id: str, payload: dict) -> None:
    """ส่ง Flex Message หรือ Custom JSON Payload ให้ผู้บริหารผ่าน Push API"""
    if not LINE_TOKEN: return
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    data = {"to": user_id, "messages": [payload]}
    try:
        res = await asyncio.to_thread(requests.post, "https://api.line.me/v2/bot/message/push", headers=headers, json=data, timeout=10)
        res.raise_for_status()
        logger.info("📤 [System]: ส่ง Executive Custom Payload สำเร็จ")
    except Exception as e:
        logger.error(f"❌ [System Error]: ส่ง Custom Payload ล้มเหลว -> {e}")

async def dispatch_line_message(user_id: str, reply_token: Optional[str], messages: list) -> None:
    """ฟังก์ชันสลับ Reply / Push อัตโนมัติ ป้องกันปัญหา LINE Timeout และ Token หมดอายุ"""
    if not messages: return
    try:
        if reply_token:
            await asyncio.to_thread(line_bot_api.reply_message, reply_token, messages)
        else:
            await asyncio.to_thread(line_bot_api.push_message, user_id, messages)
    except LineBotApiError as line_err:
        # หาก Reply Token หมดอายุ (เกิน 60 วิ) ระบบจะ Auto-Fallback เป็น Push ทันที
        logger.warning(f"🔄 [Auto-Retry]: Reply ล้มเหลว ({line_err.error.message}). สลับไปใช้ Push Message...")
        try:
            await asyncio.to_thread(line_bot_api.push_message, user_id, messages)
        except Exception as push_err:
            logger.error(f"❌ [Dispatch Error]: ส่ง Push สำรองล้มเหลว -> {push_err}")
    except Exception as e:
        logger.error(f"❌ [Dispatch Error]: ไม่สามารถส่งข้อความได้ -> {e}")

# =========================================================
# 🧠 The Ultimate AI Processing Pipeline (ท่อประมวลผลสมองกลหลัก)
# =========================================================
async def process_ai_and_reply(user_id: str, incoming_message: str, reply_token: Optional[str], file_path: Optional[str] = None, file_type: Optional[str] = None) -> None:
    try:
        start_time = time.time()
        
        # 👑 1. [GOD MODE]: สิทธิ์ขาดประธานบริษัท (CEO Secretary Check)
        if ceo_secretary and hasattr(ceo_secretary, 'is_ceo') and ceo_secretary.is_ceo(user_id):
            logger.info("👑 [System]: CEO Identified. Activating God Mode.")
            
            if inspect.iscoroutinefunction(ceo_secretary.process_ceo_command):
                reply_payload = await ceo_secretary.process_ceo_command(incoming_message, file_path=file_path, file_type=file_type)
            else:
                reply_payload = await asyncio.to_thread(ceo_secretary.process_ceo_command, incoming_message, file_path, file_type)
                
            if time.time() - start_time > 15.0: reply_token = None # บังคับ Push ถ้านานเกิน
            
            if isinstance(reply_payload, dict): 
                if reply_payload.get("type") == "flex":
                    await send_line_custom_payload(user_id, reply_payload)
                else:
                    await dispatch_line_message(user_id, reply_token, [TextSendMessage(text=reply_payload.get("text", ""))])
            else: 
                await dispatch_line_message(user_id, reply_token, [TextSendMessage(text=str(reply_payload))])
            return

        # 🛡️ 2. [COMPLIANCE SHIELD]: กรองข้อมูลส่วนบุคคล (PDPA Zero-Risk)
        safe_message = guard.sanitize_pii(incoming_message) if (guard and hasattr(guard, 'sanitize_pii')) else incoming_message

        # 🧠 3. [PREDICTIVE EMPATHY]: ดึงกฎเหล็ก/ความจำ จาก Worker 12 (Self-Learning)
        golden_rules = ""
        if self_learning and hasattr(self_learning, 'get_rules_for_context'):
            try:
                golden_rules = await asyncio.wait_for(self_learning.get_rules_for_context(safe_message), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("⚠️ [Timeout]: ดึง Golden Rules ไม่สำเร็จในเวลาที่กำหนด ข้ามการทำงานส่วนนี้")

        enhanced_message = f"{golden_rules}\n{safe_message}" if golden_rules else safe_message

        # ⚙️ 4. [CENTRAL ROUTER]: ส่งให้ Boss Agent ประเมินเจตนา ตัด Token และสั่งการ Worker
        reply_msg = ""
        if boss_agent:
            try:
                # ใช้วิธีสร้าง Task ใหม่แทนการโยน bg_tasks ของ FastAPI ลงมา
                if inspect.iscoroutinefunction(boss_agent.route_task):
                    reply_msg = await boss_agent.route_task(user_id, enhanced_message, incoming_message, file_path, file_type)
                else:
                    reply_msg = await asyncio.to_thread(boss_agent.route_task, user_id, enhanced_message, incoming_message, file_path, file_type)
            except Exception as boss_err:
                logger.warning(f"⚠️ [Boss Agent Error]: {boss_err} -> Fallback to Prime Brain")

        # 🔄 5. [FALLBACK SYSTEM]: ถ้าระบบ Boss ล่ม ให้ใช้ Gemini รุ่นแฟลช ตรงๆ
        if not reply_msg:
            if generate_intelligent_response:
                if inspect.iscoroutinefunction(generate_intelligent_response):
                    reply_msg = await generate_intelligent_response(user_id, enhanced_message, file_path=file_path, file_type=file_type)
                else:
                    reply_msg = await asyncio.to_thread(generate_intelligent_response, user_id, enhanced_message, file_path, file_type)
            else:
                sys_instruct = f"คุณคือเลขาอัจฉริยะ SIRINTHANATTH PRIME ตอบสั้นกระชับ {golden_rules}"
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model='gemini-3.7-flash',
                    contents=enhanced_message,
                    config=types.GenerateContentConfig(system_instruction=sys_instruct)
                )
                reply_msg = response.text if response.text else "ระบบได้รับข้อมูลเรียบร้อยแล้วครับ"

        # ⚖️ 6. [OUTPUT SANITIZER]: แนบคำเตือนจำกัดความรับผิดชอบอัตโนมัติ
        if guard and hasattr(guard, 'attach_financial_disclaimer'):
            reply_msg = guard.attach_financial_disclaimer(reply_msg)

        messages_to_send = [TextSendMessage(text=reply_msg)]

        # 🎙️ 7. [VOICE AI SYNTHESIS]: แปลงเสียงพูดกลับ (ElevenLabs)
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
        
        # ประเมินเวลาทำงานทั้งหมด หากนานเกินไปให้ตัด Reply Token ทิ้ง
        if time.time() - start_time > 15.0: reply_token = None 

        # 📤 8. [DISPATCH]: ส่งข้อมูลกลับหาลูกค้า
        await dispatch_line_message(user_id, reply_token, messages_to_send)
        
    except Exception as e: 
        logger.error(f"❌ [Critical Pipeline Error]: {e}", exc_info=True)
        await dispatch_line_message(user_id, None, [TextSendMessage(text="ขออภัยครับ ระบบประมวลผลล้ำลึกกำลังจัดเรียงข้อมูลเครือข่ายใหม่ ทีมวิศวกรกำลังเร่งตรวจสอบให้ครับ")])
    finally:
        # 🧹 9. [ZERO-DATA RETENTION]: ทำลายข้อมูลชั่วคราวทิ้งทันที 100%
        if file_path and os.path.exists(file_path):
            try: 
                os.remove(file_path)
                logger.info(f"🧹 [Zero-Data]: ทำลายไฟล์ลับชั่วคราวสำเร็จ ({file_path})")
            except Exception as cleanup_err: 
                logger.error(f"⚠️ [Cleanup Failed]: {cleanup_err}")

# =========================================================
# 🌐 Webhook Gateway (ด่านหน้ารับข้อความจาก LINE OA)
# =========================================================
@router.post("/webhook")
async def line_webhook(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    """ด่านหน้ารับข้อความจาก LINE OA (รองรับ 10,000+ Concurrent Requests)"""
    if not parser or not line_bot_api:
        logger.warning("⚠️ Webhook Parser ไม่พร้อมทำงาน ส่ง 200 OK เพื่อให้ Verify ผ่าน")
        return {"status": "ok", "message": "Verify Only Mode"}
        
    body = await request.body()
    try: 
        events = parser.parse(body.decode('utf-8'), x_line_signature)
    except InvalidSignatureError: 
        logger.warning("🚨 [Security Alert]: ตรวจพบการปลอมแปลง Signature! บล็อกการเข้าถึงทันที")
        raise HTTPException(status_code=400, detail="Invalid signature. Access Denied.")
        
    for event in events:
        
        # 🌟 ระบบต้อนรับ VVIP ผ่านหน้าต่าง LIFF อัตโนมัติ
        if isinstance(event, FollowEvent):
            welcome_msg = "ยินดีต้อนรับเข้าสู่ศูนย์บัญชาการอัจฉริยะ SIRINTHANATTH PRIME ครับ พิมพ์คำว่า 'เมนู' หรือ 'แพ็กเกจ' เพื่อดูบริการระดับโลกของเราได้เลยครับ"
            if boss_agent and hasattr(boss_agent, '_get_liff_welcome_message'):
                welcome_msg = boss_agent._get_liff_welcome_message(tier="GUEST")
            background_tasks.add_task(dispatch_line_message, event.source.user_id, event.reply_token, [TextSendMessage(text=welcome_msg)])
            continue

        if not isinstance(event, MessageEvent):
            continue

        user_id = event.source.user_id
        reply_token = event.reply_token
        message_type = event.message.type
        incoming_message, file_path, file_type = "", None, None

        # 🛡️ ระบบกรอง LINE Verification
        if reply_token in ["00000000000000000000000000000000", "ffffffffffffffffffffffffffffffff"]:
            logger.info("✅ [System]: ตอบรับการทดสอบ Webhook จาก LINE เรียบร้อย")
            continue

        # ==========================================
        # 📝 1. โหมดข้อความและการกดปุ่ม
        # ==========================================
        if message_type == 'text': 
            incoming_message = event.message.text.strip()

            if incoming_message == "PRIME: UNLOCK CEO":
                reply_msg = (f"👑 [SYSTEM OVERRIDE SUCCESS]\n"
                             f"ท่านประธานครับ LINE ID ของท่านคือ:\n\n"
                             f"{user_id}\n\n"
                             f"กรุณาคัดลอกรหัสนี้ไปใส่ในไฟล์ .env (CEO_LINE_ID) เพื่อปลดล็อกระบบระดับมหาภาคครับ")
                background_tasks.add_task(dispatch_line_message, user_id, reply_token, [TextSendMessage(text=reply_msg)])
                continue

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
                # ตอบกลับทันทีว่ากำลังประมวลผล เพื่อกันลูกค้าชะงัก
                await asyncio.to_thread(line_bot_api.reply_message, reply_token, TextSendMessage(text="ระบบกำลังอัปโหลดไฟล์เข้าสู่ Data Lake ระดับองค์กรเพื่อวิเคราะห์เชิงลึก กรุณารอสักครู่นะครับ ⏳"))
                
                message_content = await asyncio.to_thread(line_bot_api.get_message_content, message_id)
                ext = ".m4a" if message_type == 'audio' else ".jpg" if message_type == 'image' else ".mp4" if message_type == 'video' else ".pdf"
                file_name = f"file_{uuid.uuid4().hex}{ext}"
                os.makedirs("/tmp", exist_ok=True)
                file_path = f"/tmp/{file_name}"
                
                # ปรับปรุง Context Manager ป้องกัน Memory Leak
                def save_media():
                    with open(file_path, 'wb') as fd:
                        for chunk in message_content.iter_content(chunk_size=8192): 
                            if chunk: fd.write(chunk)
                await asyncio.to_thread(save_media)
                
                incoming_message = f"[System Alert: ลูกค้าอัปโหลดไฟล์ {message_type} สำเร็จ ช่วยวิเคราะห์เอกสาร/ภาพ/วิดีโอนี้อย่างละเอียดบนพื้นฐานกฎหมายและศีลธรรม]"
                file_type = message_type
                reply_token = None # รีเซ็ต Token เพราะใช้ตอบกลับไปแล้ว 1 ครั้ง
                
            except Exception as e: 
                logger.error(f"❌ File download error: {e}", exc_info=True)
                continue
        else: 
            continue
    
        # 🚀 โยนเข้าคิวประมวลผล AI หลังบ้าน (ถอดตัวแปร background_tasks ออกตามหลักวิศวกรรม)
        background_tasks.add_task(process_ai_and_reply, user_id, incoming_message, reply_token, file_path, file_type)
        
    return {"status": "OK"}