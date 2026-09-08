import os
import asyncio
import inspect
import logging
import uuid
import time
import httpx # ⚡ อัปเกรดเป็น Async HTTP ขั้นสุด
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

LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
LINE_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
BASE_URL = os.environ.get("BASE_URL") or "https://prime-core-agent-601183279633.asia-southeast3.run.app"

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
# 🌟 Advanced UI/UX: LINE Loading Animation API (ฟีเจอร์ใหม่ล่าสุด)
# =========================================================
async def show_line_loading_animation(user_id: str, loading_seconds: int = 20) -> None:
    """แสดงจุดไข่ปลา (...) อนิเมชันกำลังพิมพ์ให้ลูกค้าเห็นขณะ AI กำลังคิด ป้องกันความสับสน"""
    if not LINE_TOKEN or not user_id: return
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}"
    }
    data = {"chatId": user_id, "loadingSeconds": loading_seconds}
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post("https://api.line.me/v2/bot/chat/loading/start", headers=headers, json=data, timeout=5.0)
    except Exception as e:
        logger.warning(f"⚠️ [Loading Animation Warning]: ไม่สามารถแสดงอนิเมชันได้ -> {e}")

# =========================================================
# 🛠️ Core Transmission Functions (ระบบสั่งการ LINE ขั้นสูง)
# =========================================================
async def send_line_custom_payload(user_id: str, payload: dict) -> None:
    """⚡ ส่ง Flex Message หรือ Custom JSON Payload ให้ผู้บริหารผ่าน Push API แบบปลอดภัย (Anti-Error 400)"""
    if not LINE_TOKEN or not user_id: return
    
    # 🛡️ ระบบ Auto-Correction: ตรวจสอบและซ่อมแซมโครงสร้าง Flex Message
    if payload.get("type") == "flex":
        if "altText" not in payload:
            payload["altText"] = "SIRINTHANATTH PRIME ส่งเอกสารสำคัญให้คุณ"
        if "contents" not in payload and "body" in payload:
            payload = {
                "type": "flex",
                "altText": payload.get("altText", "ข้อความสำคัญ"),
                "contents": {
                    "type": "bubble",
                    "body": payload.get("body")
                }
            }

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"}
    data = {"to": user_id, "messages": [payload]}
    
    try:
        async with httpx.AsyncClient() as http_client:
            res = await http_client.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data, timeout=15.0)
            if res.status_code == 200:
                logger.info("📤 [System]: ส่ง Executive Custom Payload สำเร็จ")
            else:
                logger.error(f"❌ [LINE API Error {res.status_code}]: {res.text}")
    except httpx.TimeoutException:
        logger.error("❌ [System Timeout]: LINE API ไม่ตอบสนองภายในเวลาที่กำหนด")
    except Exception as e:
        logger.error(f"❌ [System Error]: ส่ง Custom Payload ล้มเหลว -> {e}", exc_info=True)

async def dispatch_line_message(user_id: str, reply_token: Optional[str], messages: list) -> None:
    """ระบบสลับ Reply / Push อัจฉริยะ (Adaptive Dispatcher) ลดการใช้ Push Quota โดยไม่จำเป็น"""
    if not messages: return
    try:
        # ถ้ามี Reply Token และอายุยังไม่เกิน (ใช้งานปกติ)
        if reply_token:
            await asyncio.to_thread(line_bot_api.reply_message, reply_token, messages)
        else:
            await asyncio.to_thread(line_bot_api.push_message, user_id, messages)
    except LineBotApiError as line_err:
        logger.warning(f"🔄 [Auto-Retry]: Reply ล้มเหลว/Token หมดอายุ สลับไปใช้ Push Message แบบไร้รอยต่อ...")
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
    """ทำงานใน Background: ใช้เวลาคิดได้เต็มที่ ไร้ข้อจำกัด Timeout 5 วินาทีของ LINE"""
    try:
        start_time = time.time()
        
        # 👑 1. [GOD MODE]: สิทธิ์ขาดประธานบริษัท (CEO Secretary Check)
        if ceo_secretary and hasattr(ceo_secretary, 'is_ceo') and ceo_secretary.is_ceo(user_id):
            logger.info("👑 [System]: CEO Identified. Activating God Mode.")
            
            if inspect.iscoroutinefunction(ceo_secretary.process_ceo_command):
                reply_payload = await ceo_secretary.process_ceo_command(incoming_message, file_path=file_path, file_type=file_type)
            else:
                reply_payload = await asyncio.to_thread(ceo_secretary.process_ceo_command, incoming_message, file_path, file_type)
                
            if time.time() - start_time > 45.0: reply_token = None # LINE Reply Token หมดอายุใน 60 วินาที
            
            if isinstance(reply_payload, dict): 
                if reply_payload.get("type") in ["flex", "template"]:
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
                golden_rules = await asyncio.wait_for(self_learning.get_rules_for_context(safe_message), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("⚠️ [Timeout]: ดึง Golden Rules ไม่สำเร็จใน 5 วิ ข้ามไปก่อนเพื่อความเร็ว")

        enhanced_message = f"{golden_rules}\n{safe_message}" if golden_rules else safe_message

        # ⚙️ 4. [CENTRAL ROUTER]: ส่งให้ Boss Agent ประเมินเจตนา ตัด Token และสั่งการ Worker
        reply_msg = ""
        if boss_agent:
            try:
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
                sys_instruct = f"คุณคือเลขาอัจฉริยะ SIRINTHANATTH PRIME ตอบสั้นกระชับ เป็นมืออาชีพ {golden_rules}"
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

        # 🚀 ฟีเจอร์พิเศษ: ถ้า AI เจน JSON ออกมา ให้โยนเข้า Custom Payload
        if isinstance(reply_msg, dict) and reply_msg.get("type") in ["flex", "template"]:
            await send_line_custom_payload(user_id, reply_msg)
            return

        messages_to_send = [TextSendMessage(text=str(reply_msg))]

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
        
        # ปรับเวลา Token Expiry ตามมาตรฐาน LINE (1 นาที)
        if time.time() - start_time > 45.0: reply_token = None 

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
    """ด่านหน้ารับข้อความจาก LINE OA ออกแบบมาเพื่อป้องกัน Timeout 100% (Event-Driven Architecture)"""
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
        # ⚡ 1. โชว์จุดไข่ปลา (Loading Animation) ทันทีที่รับข้อความ!
        # ==========================================
        background_tasks.add_task(show_line_loading_animation, user_id, 20)

        # ==========================================
        # 📝 2. โหมดข้อความและการกดปุ่ม
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
        # 🖼️ 3. โหมดมัลติมีเดีย (รูปภาพ เสียง วิดีโอ PDF)
        # ==========================================
        elif message_type in ['audio', 'image', 'video', 'file']:
            message_id = event.message.id
            try:
                message_content = await asyncio.to_thread(line_bot_api.get_message_content, message_id)
                ext = ".m4a" if message_type == 'audio' else ".jpg" if message_type == 'image' else ".mp4" if message_type == 'video' else ".pdf"
                file_name = f"file_{uuid.uuid4().hex}{ext}"
                os.makedirs("/tmp", exist_ok=True)
                file_path = f"/tmp/{file_name}"
                
                # เขียนไฟล์แบบปลอดภัย
                def save_media():
                    with open(file_path, 'wb') as fd:
                        for chunk in message_content.iter_content(chunk_size=8192): 
                            if chunk: fd.write(chunk)
                await asyncio.to_thread(save_media)
                
                incoming_message = f"[System Alert: ลูกค้าอัปโหลดไฟล์ {message_type} สำเร็จ ช่วยวิเคราะห์เอกสาร/ภาพ/วิดีโอนี้อย่างละเอียดบนพื้นฐานกฎหมายและศีลธรรม]"
                file_type = message_type
                
            except Exception as e: 
                logger.error(f"❌ File download error: {e}", exc_info=True)
                continue
        else: 
            continue
    
        # 🚀 4. โยนเข้าคิวประมวลผล AI หลังบ้าน (FastAPI คืนค่า 200 OK กลับไปหา LINE ทันที)
        background_tasks.add_task(process_ai_and_reply, user_id, incoming_message, reply_token, file_path, file_type)
        
    return {"status": "OK"}