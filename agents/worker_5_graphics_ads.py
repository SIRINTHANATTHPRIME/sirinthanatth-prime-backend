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
        EXECUTIVE_MODEL = "gemini-3.1-pro" # 🚀 อัปเกรดเป็นรุ่นเรือธงสำหรับงาน Creative ขั้นสูง
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

# 🎙️ นำเข้าระบบเสียงพากย์ระดับโลก (ElevenLabs API)
try:
    from services.elevenlabs_service import generate_voice_from_text
except ImportError:
    generate_voice_from_text = None

logger = logging.getLogger("Worker5-CreativeDirector")

class GraphicsAdsWorker:
    """
    🎨 Worker 5: Executive Creative Director & Media Buyer
    อัปเกรด: Vertex AI (Gemini 2.5 Pro) + ElevenLabs ระบบออกแบบกราฟิก, สิ่งพิมพ์, โฆษณา และการตลาด
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.1-pro")
        
        # เชื่อมต่อ Supabase สำหรับระบบ Token
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        self.topup_link = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4") # เชื่อมโยงเข้าสู่ Smart Wallet

    async def _deduct_token(self, user_id: str, tokens_needed: int) -> dict:
        """💳 ตรวจสอบแพ็กเกจและหัก PRIME CREDITS สำหรับงานออกแบบโปรดักชัน"""
        if not self.db:
            return {"authorized": True, "tier": "ESSENTIAL"} # Fallback โหมด Offline
        
        try:
            def _check_and_deduct():
                user_data = self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
                if not user_data.data:
                    return {"authorized": False, "msg": "⚠️ ไม่พบข้อมูลบัญชี กรุณาลงทะเบียนผ่านเมนูเพื่อรับสิทธิ์เปิดใช้งานระบบ Creative Agency ครับ"}
                    
                balance = float(user_data.data[0].get("token_balance", 0.0))
                tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
                
                # 👑 VIP_FOUNDER และ ENTERPRISE ใช้งานระบบโปรดักชันได้ไม่อั้น หรือตามข้อตกลงพิเศษ
                if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]:
                    return {"authorized": True, "tier": tier}
                    
                if balance >= tokens_needed:
                    new_balance = balance - tokens_needed
                    self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                    logger.info(f"🪙 [Token Engine]: หัก {tokens_needed} Credits จาก {user_id} (บริการงาน Graphic & Ads)")
                    return {"authorized": True, "tier": tier}
                else:
                    return {"authorized": False, "msg": f"⚠️ PRIME CREDITS ของท่านไม่เพียงพอสำหรับการออกแบบและวิเคราะห์สื่อ (ต้องการ {tokens_needed} Credits)\n👉 เติมเครดิตเพื่อผลิตสื่อ 4K ได้ที่: {self.topup_link}"}

            return await asyncio.to_thread(_check_and_deduct)
            
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return {"authorized": True, "tier": "ESSENTIAL"}

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """ทำงานเบื้องหลัง: วิเคราะห์ภาพลักษณ์แบรนด์ สร้างสรรค์สื่อ 4K และสคริปต์โฆษณา"""
        if not self.client:
            return "⚠️ [Worker 5]: ระบบ Creative Director ออฟไลน์ (ไม่พบ API Key ส่วนกลาง)"

        # 🪙 ตรวจสอบค่าใช้จ่าย: คิดไอเดียโฆษณา = 20 Credits, วิเคราะห์รูปภาพแพ็กเกจจิ้ง = 50 Credits
        tokens_needed = 50 if file_path else 20
        auth_status = await self._deduct_token(user_id, tokens_needed)
        
        if not auth_status["authorized"]:
            return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "ESSENTIAL")
        logger.info(f"🎨 [Graphics & Ads]: เริ่มกระบวนการโปรดักชันให้ User {user_id} (Tier: {package_tier})")

        # 🧠 System Prompt ปรับแต่งระดับ Global Agency
        system_instruction = f"""
        คุณคือ 'Executive Creative Director' ระดับ Global Agency ของ SIRINTHANATTH PRIME
        ลูกค้ารายนี้อยู่ในแพ็กเกจระดับ: {package_tier}
        
        หน้าที่ของคุณ (Agency Pitch Deck):
        1. 🎨 Art Direction: วิเคราะห์งานออกแบบ โทนสี Typography และ User Experience ให้หรูหรา ล้ำสมัย
        2. 🤖 4K Image Prompt: ร่าง Prompt ภาษาอังกฤษระดับมืออาชีพที่ละเอียดและทรงพลัง สำหรับนำไปใช้กับ Midjourney หรือ Imagen
        3. 🎙️ Copywriting & Voice Script: ร่างแคปชันโฆษณาที่ดึงดูด ถูกกฎหมาย (ไม่โอ้อวดเกินจริง) และสคริปต์สำหรับเสียงพากย์ (Voiceover)
        4. 🎯 Media Buying: แนะนำกลุ่มเป้าหมาย (Targeting) และช่องทางที่เหมาะสมสำหรับการยิงแอด
        
        *สำหรับลูกค้าระดับ ENTERPRISE และ VIP_FOUNDER: ให้นำเสนอโครงสร้างการทำ A/B Testing, จิตวิทยาพฤติกรรมผู้บริโภค และ Omnichannel Marketing อย่างละเอียด*
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 📂 1. จัดการระบบวิเคราะห์รูปภาพ (Image & Packaging Parser)
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"🎨 [Worker 5]: กำลังอัปโหลดภาพเข้าสู่ Secure AI Engine เพื่อถอดรหัสองค์ประกอบศิลป์...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type: mime_type = "image/jpeg"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    logger.error(f"⚠️ [Image Upload Error]: {e}")
                    return f"⚠️ [Worker 5]: ระบบไม่สามารถประมวลผลไฟล์รูปภาพนี้ได้ครับ รบกวนส่งเป็นไฟล์ .jpg หรือ .png ขนาดไม่เกิน 20MB ครับ"

                # ⏳ Async Sync และระบบ Anti-Freeze (Timeout 60 วินาที)
                timeout = 60
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        raise TimeoutError("การประมวลผลภาพใช้เวลานานเกินกำหนด")
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 5]: เกิดข้อผิดพลาดในการวิเคราะห์พิกเซลและการจัดองค์ประกอบของภาพครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดวิเคราะห์องค์ประกอบศิลป์ของภาพ/แพ็กเกจจิ้งนี้ และยกระดับงานออกแบบโฆษณาตามคำสั่ง: {message}")
            else:
                content_to_send.append(f"โปรดร่างคอนเซปต์งานกราฟิก สื่อโฆษณา และสคริปต์สำหรับโปรดักชัน ตามความต้องการนี้: {message}")

            # ==========================================
            # 🧠 2. สั่งรัน Gemini 2.5 Pro (Creative Mode)
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.8 # ใช้อุณหภูมิ 0.8 เพื่อสร้างความหลากหลายและจินตนาการระดับ Global Agency
                )
            )
            
            final_text = response.text.strip() if response.text else "✅ ออกแบบคอนเซปต์โฆษณาและประเมินแคมเปญเสร็จสิ้นครับ"

            # ==========================================
            # 🎙️ 3. Voice AI & Upsell Trigger (ElevenLabs Connection)
            # ==========================================
            trigger_keywords = ["เสียงพากย์", "ทำคลิป", "voiceover", "อ่านสคริปต์", "วิดีโอ"]
            if any(keyword in message.lower() for keyword in trigger_keywords):
                if package_tier in ["ENTERPRISE", "VIP_FOUNDER", "VIP", "ADMIN"]:
                    final_text += "\n\n🎙️ [Audio Production]: เนื่องจากท่านคือสมาชิกระดับผู้บริหาร (VIP) ระบบสตูดิโอพร้อมทำงานแล้วครับ หากท่านพอใจสคริปต์ด้านบน พิมพ์ 'ยืนยันสร้างเสียง' เพื่อให้ระบบเรนเดอร์ไฟล์ Audio 4K ส่งให้ท่านทันทีครับ"
                else:
                    final_text += f"\n\n💡 [Exclusive Feature]: อัปเกรดเป็นแพ็กเกจ ENTERPRISE วันนี้ เพื่อปลดล็อกฟีเจอร์พากย์เสียงมนุษย์ระดับสตูดิโอ (ElevenLabs AI) ช่วยเพิ่ม Conversion Rate ให้แอดของคุณทันที!"

            return final_text

        except TimeoutError:
            logger.error("❌ [Worker 5 Timeout]: ภาพมีความละเอียดหรือซับซ้อนเกินไป")
            return "ขออภัยครับคุณลูกค้า ภาพมีความละเอียดและซับซ้อนสูงทำให้ประมวลผลนานกว่าปกติ รบกวนย่อขนาดไฟล์แล้วลองใหม่อีกครั้งนะครับ"
        except Exception as e:
            logger.error(f"❌ [Worker 5 Error]: {e}")
            return f"⚠️ [Worker 5]: แผนกโปรดักชันครีเอทีฟขัดข้องชั่วคราว ทีมวิศวกรกำลังตรวจสอบระบบให้ครับ"

        finally:
            # ==========================================
            # 🧹 4. Trade Secret Protection (Zero-Data Retention)
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info(f"🗑️ [Worker 5]: ลบไฟล์ {uploaded_file.name} ออกจากเซิร์ฟเวอร์เรียบร้อย (Trade Secret Safe)")
                except Exception as e:
                    logger.error(f"⚠️ [File Deletion Failed]: {e}")