import os
import time
import re
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

# 🌐 นำเข้าศูนย์บัญชาการ AI และระบบเครือข่ายส่งต่องาน (Swarm)
from core_services.swarm_dispatcher import swarm_hub

try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.1-pro-preview" # 🚀 อัปเกรดเป็นรุ่นเรือธงล่าสุด
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

try:
    from supabase import create_client, Client
except ImportError:
    Client = None

# 🎙️ นำเข้าระบบเสียงระดับโลก ElevenLabs 
try:
    from services.elevenlabs_service import generate_voice_from_text
except ImportError:
    generate_voice_from_text = None

logger = logging.getLogger("Worker3-AudioStudio")

class AudioWorker:
    """
    🎙️ Worker 3: Chief Audio Producer & Voice Synthesizer
    อัปเกรด: Gemini 3.1 Pro, Swarm Delegation, ElevenLabs Integration, และ Sentiment Recognition
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.1-pro-preview")
        self.base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
        
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        self.topup_link = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")

    async def _deduct_token(self, user_id: str, tokens_needed: int) -> dict:
        """💳 ตรวจสอบแพ็กเกจและหัก PRIME CREDITS อัจฉริยะ สำหรับสตูดิโอเสียง"""
        if not self.db: return {"authorized": True, "tier": "ESSENTIAL"}
        
        try:
            def _check_and_deduct():
                user_data = self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
                if not user_data.data:
                    return {"authorized": False, "msg": "⚠️ ไม่พบข้อมูลบัญชี กรุณาลงทะเบียนผ่านเมนูเพื่อเปิดใช้งานระบบ Audio Studio ครับ"}
                    
                balance = float(user_data.data[0].get("token_balance", 0.0))
                tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
                
                if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]: return {"authorized": True, "tier": tier}
                    
                if balance >= tokens_needed:
                    new_balance = balance - tokens_needed
                    self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                    logger.info(f"🪙 [Token Engine]: หัก {tokens_needed} Credits จาก {user_id} (บริการ Audio Production)")
                    return {"authorized": True, "tier": tier}
                else:
                    return {"authorized": False, "msg": f"⚠️ PRIME CREDITS ไม่เพียงพอสำหรับโปรดักชันเสียง (ต้องการ {tokens_needed} Credits)\n👉 เติมเครดิตได้อย่างปลอดภัยที่: {self.topup_link}"}

            return await asyncio.to_thread(_check_and_deduct)
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return {"authorized": True, "tier": "ESSENTIAL"}

    async def process_command(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """สะพานเชื่อมต่อรับงานจาก Swarm Hub หรือ Central Boss"""
        return await self.process_task(user_id, message, file_path)

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """ทำงานเบื้องหลัง: ถอดรหัสคลื่นเสียง, วิเคราะห์อารมณ์, แต่งเพลง, และสั่งการ ElevenLabs"""
        if not self.client: return "⚠️ [Worker 3]: ระบบประมวลผลเสียงและดนตรีออฟไลน์"

        # 🪙 ตรวจสอบค่าใช้จ่าย: พากย์เสียง 150 Token / วิเคราะห์แต่งเพลง 50 Token
        is_voice_generation = ("พากย์" in message or "สร้างเสียง" in message)
        tokens_needed = 150 if is_voice_generation else 50
        
        auth_status = await self._deduct_token(user_id, tokens_needed)
        if not auth_status["authorized"]: return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "ESSENTIAL")
        logger.info(f"🎙️ [Audio Studio]: เริ่มโปรดักชันให้ User {user_id} (Tier: {package_tier})")

        system_instruction = f"""
        คุณคือ 'Executive Audio & Music Producer' ระดับโลก ประจำสตูดิโอ SIRINTHANATTH PRIME
        ลูกค้ารายนี้อยู่ในแพ็กเกจระดับ: {package_tier}
        
        หน้าที่ของคุณ (Audio Intelligence & Composition):
        1. 🎙️ ถอดรหัสเสียง (Transcription) & วิเคราะห์อารมณ์ (Sentiment): หากได้รับไฟล์เสียง ให้ถอดสคริปต์ สรุปใจความ และบอกว่าผู้พูดมีอารมณ์ความรู้สึกอย่างไร
        2. 🎵 การแต่งเพลงและทำนอง (Music Composition): หากถูกสั่งให้แต่งเพลง ให้เขียนเนื้อร้อง (Lyrics) ที่สัมผัสคล้องจองระดับมืออาชีพ พร้อมระบุ [Verse], [Chorus], [Bridge] และเขียน Prompt แนวเพลง (เช่น Synthwave, Cinematic)
        3. 🗣️ การเตรียมสคริปต์พากย์เสียง: ปรับเกลาภาษาให้เป็น "ภาษาพูด" ที่เป็นธรรมชาติ มีจังหวะเว้นวรรค (Pacing) ที่เหมาะสม
        
        🚨 กฎการส่งต่องาน (Swarm Delegation):
        หากลูกค้าสั่งงานที่ต้องใช้ภาพประกอบ วิดีโอ หรือการตลาด ให้คุณโยนงานให้แผนกอื่นทันทีโดยพิมพ์:
        [DELEGATE: WORKER_X_NAME] สคริปต์หรือข้อมูลที่ต้องการส่งต่อให้ทำวิดีโอ/ภาพ
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 📂 1. จัดการไฟล์เสียงและการอัปโหลด
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"🎙️ [Worker 3]: กำลังอัปโหลดไฟล์เสียงสู่ Secure AI Engine...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type: mime_type = "audio/mp4" 

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    logger.error(f"⚠️ [File Upload Error]: {e}")
                    return f"⚠️ [Worker 3]: ระบบไม่รองรับไฟล์เสียงประเภทนี้ครับ กรุณาส่งเป็นไฟล์ .mp3 หรือ .m4a ขนาดไม่เกิน 20MB"

                timeout = 60
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        raise TimeoutError("หมดเวลาการสแกนและถอดรหัสคลื่นเสียง")
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 3]: เกิดข้อผิดพลาดในการถอดรหัสคลื่นเสียงและการบีบอัดไฟล์ครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดรับฟัง ถอดรหัสข้อความ วิเคราะห์อารมณ์ และดำเนินการตามคำสั่ง: {message}")
            else:
                content_to_send.append(f"โปรดวิเคราะห์ แต่งเพลง หรือเตรียมสคริปต์สำหรับโปรดักชันเสียง ตามความต้องการนี้: {message}")

            # ==========================================
            # 🧠 2. ประมวลผลขั้นสูงด้วย Gemini 3.1 Pro 
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7 # อุณหภูมิ 0.7 เหมาะสำหรับงาน Creative และเนื้อเพลง
                )
            )
            
            reply_text = response.text.strip() if response.text else "✅ วิเคราะห์และจัดเตรียมสคริปต์เสียงเสร็จสิ้นครับ"
            
            # ==========================================
            # 🎙️ 3. ผสมผสานขุมพลัง ElevenLabs API
            # ==========================================
            if is_voice_generation and generate_voice_from_text:
                if package_tier in ["ENTERPRISE", "VIP_FOUNDER", "VIP", "ADMIN"]:
                    logger.info("🎙️ [ElevenLabs]: ได้รับคำสั่งให้สร้างเสียงพากย์ กำลังเชื่อมต่อ API...")
                    filename, duration_ms = await asyncio.to_thread(generate_voice_from_text, reply_text)
                    if filename:
                        audio_link = f"{self.base_url}/static/audio/{filename}"
                        reply_text += f"\n\n🎧 [High-Fidelity Audio] ระบบสร้างเสียงพากย์ระดับสตูดิโอเรียบร้อยแล้ว:\n👉 {audio_link}"
                    else:
                        reply_text += "\n\n⚠️ ระบบพากย์เสียงขัดข้องชั่วคราว แต่สคริปต์พร้อมใช้งานแล้วครับ"
                else:
                    reply_text += f"\n\n💡 [Upsell]: อัปเกรดเป็นแพ็กเกจ ENTERPRISE วันนี้ เพื่อปลดล็อกฟีเจอร์พากย์เสียงมนุษย์ (ElevenLabs AI) ช่วยให้โฆษณาของคุณดูแพงและทรงพลังขึ้น 300%!"
            
            # ==========================================
            # 🔄 4. ตรวจจับการส่งต่องาน (Swarm Delegation)
            # ==========================================
            delegate_match = re.search(r'\[DELEGATE:\s*(.+?)\](.*)', reply_text, re.DOTALL | re.IGNORECASE)
            if delegate_match:
                target_worker = delegate_match.group(1).strip()
                handoff_message = delegate_match.group(2).strip()
                
                clean_reply = re.sub(r'\[DELEGATE:\s*(.+?)\](.*)', '', reply_text, flags=re.DOTALL | re.IGNORECASE).strip()
                
                worker_response = await swarm_hub.delegate_task(
                    from_worker="WORKER_3_AUDIO", 
                    to_worker=target_worker, 
                    user_id=user_id, 
                    message=handoff_message, 
                    file_path=file_path
                )
                return f"{clean_reply}\n\n🔄 [สตูดิโอเสียงส่งต่อให้แผนก {target_worker}]:\n{worker_response}"

            return reply_text

        except TimeoutError:
            logger.error("❌ [Worker 3 Timeout]: ไฟล์เสียงมีความยาวเกินไป")
            return "ขออภัยครับ ไฟล์เสียงมีความยาวเกินกำหนด รบกวนส่งไฟล์เสียงที่สั้นลงเพื่อการประมวลผลที่รวดเร็วขึ้นครับ"
        except Exception as e:
            logger.error(f"❌ [Worker 3 Error]: {e}")
            return f"⚠️ [Worker 3]: สตูดิโอเสียงขัดข้องชั่วคราว ทีมวิศวกรกำลังเข้าแก้ไขครับ"

        finally:
            # ==========================================
            # 🧹 5. Zero-Data Retention Policy
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🗑️ [Worker 3]: ทำลายไฟล์เสียงลับของลูกค้าออกจากระบบคลาวด์เรียบร้อย")
                except Exception as e:
                    logger.error(f"⚠️ [File Deletion Failed]: {e}")