import os
import time
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

# =========================================================
# 🌐 1. นำเข้าศูนย์บัญชาการ AI และฐานข้อมูล (Vertex AI / Zero Downtime)
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.1-pro" # 🚀 อัปเกรดเป็นรุ่นเรือธงเพื่อความเข้าใจด้านภาษาศาสตร์และดนตรีที่ลึกซึ้ง
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
    อัปเกรด: Vertex AI (Gemini 2.5 Pro) + ElevenLabs ระบบวิเคราะห์เสียง, แต่งเพลง, และผลิตเสียงพากย์ 4K
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.1-pro")
        
        self.base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
        
        # เชื่อมต่อ Supabase สำหรับระบบ Token
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        self.topup_link = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")

    async def _deduct_token(self, user_id: str, tokens_needed: int) -> dict:
        """💳 ตรวจสอบแพ็กเกจและหัก PRIME CREDITS อัจฉริยะ สำหรับสตูดิโอเสียง"""
        if not self.db:
            return {"authorized": True, "tier": "ESSENTIAL"} # Fallback โหมด Offline
        
        try:
            def _check_and_deduct():
                user_data = self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
                
                if not user_data.data:
                    return {"authorized": False, "msg": "⚠️ ไม่พบข้อมูลบัญชี กรุณาลงทะเบียนผ่านเมนูเพื่อเปิดใช้งานระบบ Audio Studio ครับ"}
                    
                balance = float(user_data.data[0].get("token_balance", 0.0))
                tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
                
                # 👑 VIP_FOUNDER และ ENTERPRISE ใช้งานระบบ Audio ได้เต็มประสิทธิภาพ
                if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]:
                    return {"authorized": True, "tier": tier}
                    
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

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """ทำงานเบื้องหลัง: ถอดรหัสคลื่นเสียง, วิเคราะห์อารมณ์, แต่งเพลง, และสั่งการ ElevenLabs"""
        if not self.client:
            return "⚠️ [Worker 3]: ระบบประมวลผลเสียงและดนตรีออฟไลน์ (ไม่พบ API Key ส่วนกลาง)"

        # 🪙 ตรวจสอบค่าใช้จ่าย:
        # - วิเคราะห์ข้อความ/แต่งเพลง/ถอดเสียง = 50 Credits
        # - ถ้ามีการสั่ง 'พากย์' (ElevenLabs) = 150 Credits
        is_voice_generation = ("พากย์" in message or "สร้างเสียง" in message)
        tokens_needed = 150 if is_voice_generation else 50
        
        auth_status = await self._deduct_token(user_id, tokens_needed)
        if not auth_status["authorized"]:
            return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "ESSENTIAL")
        logger.info(f"🎙️ [Audio Studio]: เริ่มโปรดักชันให้ User {user_id} (Tier: {package_tier})")

        # 🧠 System Prompt ปรับแต่งระดับ Global Audio & Music Producer
        system_instruction = f"""
        คุณคือ 'Executive Audio & Music Producer' ระดับโลก ประจำสตูดิโอ SIRINTHANATTH PRIME
        ลูกค้ารายนี้อยู่ในแพ็กเกจระดับ: {package_tier}
        
        หน้าที่ของคุณ (Audio Intelligence & Composition):
        1. 🎙️ ถอดรหัสเสียง (Transcription) & วิเคราะห์อารมณ์ (Sentiment): หากได้รับไฟล์เสียง ให้ถอดสคริปต์ สรุปใจความ และบอกว่าผู้พูดมีอารมณ์ความรู้สึกอย่างไร (เช่น รีบร้อน, ยินดี, ไม่พอใจ)
        2. 🎵 การแต่งเพลงและทำนอง (Music Composition): หากลูกค้าสั่งให้แต่งเพลง ให้คุณเขียนเนื้อร้อง (Lyrics) ที่สัมผัสคล้องจองระดับมืออาชีพ พร้อมระบุ [Verse], [Chorus], [Bridge] และเขียน Prompt แนวเพลง (เช่น Synthwave, Acoustic Pop, Cinematic Orchestral) สำหรับนำไปใช้กับ AI Music Generator (เช่น Suno/Udio)
        3. 🗣️ การเตรียมสคริปต์พากย์เสียง: หากลูกค้าสั่งทำเสียงพากย์ ให้คุณปรับเกลาภาษาให้เป็น "ภาษาพูด" ที่เป็นธรรมชาติที่สุด มีจังหวะเว้นวรรค (Pacing) ที่เหมาะสม เพื่อส่งต่อให้ระบบ Voice AI พากย์ออกมาได้เนียนเหมือนมนุษย์ที่สุด
        
        *ตอบกลับอย่างมืออาชีพ ทรงพลัง และมีศิลปะ*
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 📂 1. จัดการไฟล์เสียงและการอัปโหลด (Voice Recognition)
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"🎙️ [Worker 3]: กำลังอัปโหลดไฟล์เสียงสู่ Secure AI Engine เพื่อถอดรหัสคลื่นเสียง...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = "audio/mp4" # ค่าเริ่มต้นสำหรับไฟล์เสียง LINE (.m4a)

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    logger.error(f"⚠️ [File Upload Error]: {e}")
                    return f"⚠️ [Worker 3]: ระบบไม่รองรับไฟล์เสียงประเภทนี้ครับ กรุณาส่งเป็นไฟล์ .mp3 หรือ .m4a ขนาดไม่เกิน 20MB ครับ"

                # ⏳ Async Sync รอการถอดรหัสเสียง พร้อมระบบ Anti-Freeze (Timeout 60s)
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
            # 🧠 2. ประมวลผลขั้นสูงด้วย Gemini 3.1 Pro (Asynchronous)
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7 # อุณหภูมิ 0.7 เหมาะสมที่สุดสำหรับงานเขียนเนื้อเพลงและการปรับโทนภาษา
                )
            )
            
            reply_text = response.text.strip() if response.text else "✅ วิเคราะห์และจัดเตรียมสคริปต์เสียงเสร็จสิ้นครับ"
            
            # ==========================================
            # 🎙️ 3. ผสมผสานขุมพลัง ElevenLabs API (สร้างเสียงมนุษย์จริงทันที)
            # ==========================================
            if is_voice_generation and generate_voice_from_text:
                if package_tier in ["ENTERPRISE", "VIP_FOUNDER", "VIP", "ADMIN"]:
                    logger.info("🎙️ [ElevenLabs]: ได้รับคำสั่งให้สร้างเสียงพากย์ 4K กำลังเชื่อมต่อ API...")
                    # ส่งข้อความไปให้ ElevenLabs สังเคราะห์เสียงแบบ Asynchronous
                    filename, duration_ms = await asyncio.to_thread(generate_voice_from_text, reply_text)
                    if filename:
                        audio_link = f"{self.base_url}/static/audio/{filename}"
                        reply_text += f"\n\n🎧 [High-Fidelity Audio] ระบบได้สร้างเสียงพากย์ระดับสตูดิโอเรียบร้อยแล้ว:\n👉 {audio_link}"
                    else:
                        reply_text += "\n\n⚠️ ระบบพากย์เสียงขัดข้องชั่วคราว แต่สคริปต์พร้อมใช้งานแล้วครับ"
                else:
                    reply_text += f"\n\n💡 [Upsell]: อัปเกรดเป็นแพ็กเกจ ENTERPRISE หรือ VIP วันนี้ เพื่อปลดล็อกฟีเจอร์พากย์เสียงระดับสตูดิโอ (ElevenLabs AI) ช่วยให้โฆษณาของคุณดูแพงและทรงพลังขึ้น 300%!"
            
            return reply_text

        except TimeoutError:
            logger.error("❌ [Worker 3 Timeout]: ไฟล์เสียงมีความยาวหรือซับซ้อนเกินไป")
            return "ขออภัยครับ ไฟล์เสียงมีความยาวเกินกำหนดทำให้ใช้เวลาถอดรหัสนานกว่าปกติ รบกวนส่งไฟล์เสียงที่สั้นลงเพื่อการประมวลผลที่รวดเร็วขึ้นครับ"
        except Exception as e:
            logger.error(f"❌ [Worker 3 Error]: {e}")
            return f"⚠️ [Worker 3]: สตูดิโอเสียงขัดข้องชั่วคราว ทีมวิศวกรกำลังเข้าแก้ไขครับ"

        finally:
            # ==========================================
            # 🧹 4. Zero-Data Retention Policy (PDPA Audio Shield)
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🗑️ [Worker 3]: ทำลายไฟล์เสียงลับของลูกค้าออกจากระบบเซิร์ฟเวอร์คลาวด์เรียบร้อย (Data Privacy Shield)")
                except Exception as e:
                    logger.error(f"⚠️ [File Deletion Failed]: {e}")