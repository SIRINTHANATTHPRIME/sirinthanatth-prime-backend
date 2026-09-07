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

# 🎙️ นำเข้าระบบเสียงพากย์ระดับโลก (ElevenLabs API)
try:
    from services.elevenlabs_service import generate_voice_from_text
except ImportError:
    generate_voice_from_text = None

logger = logging.getLogger("Worker5-CreativeDirector")

class GraphicsAdsWorker:
    """
    🎨 Worker 5: Executive Creative Director & Media Buyer
    อัปเกรด: Gemini 3.1 Pro, Swarm Delegation, 4K Image Generation Bridge
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
        """💳 ตรวจสอบแพ็กเกจและหัก PRIME CREDITS สำหรับงานออกแบบโปรดักชัน"""
        if not self.db: return {"authorized": True, "tier": "ESSENTIAL"} 
        
        try:
            def _check_and_deduct():
                user_data = self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
                if not user_data.data:
                    return {"authorized": False, "msg": "⚠️ ไม่พบข้อมูลบัญชี กรุณาลงทะเบียนผ่านเมนูเพื่อรับสิทธิ์เปิดใช้งานระบบ Creative Agency ครับ"}
                    
                balance = float(user_data.data[0].get("token_balance", 0.0))
                tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
                
                if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]: return {"authorized": True, "tier": tier}
                    
                if balance >= tokens_needed:
                    new_balance = balance - tokens_needed
                    self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                    logger.info(f"🪙 [Token Engine]: หัก {tokens_needed} Credits จาก {user_id} (บริการงาน Graphic & Ads)")
                    return {"authorized": True, "tier": tier}
                else:
                    return {"authorized": False, "msg": f"⚠️ PRIME CREDITS ไม่เพียงพอสำหรับการออกแบบ (ต้องการ {tokens_needed} Credits)\n👉 เติมเครดิตเพื่อผลิตสื่อ 4K ได้ที่: {self.topup_link}"}

            return await asyncio.to_thread(_check_and_deduct)
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return {"authorized": True, "tier": "ESSENTIAL"}

    async def process_command(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """สะพานเชื่อมต่อรับงานจาก Swarm Hub หรือ Central Boss"""
        return await self.process_task(user_id, message, file_path)

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """ทำงานเบื้องหลัง: วิเคราะห์ภาพลักษณ์แบรนด์ สร้างสรรค์สื่อ และสคริปต์โฆษณา"""
        if not self.client: return "⚠️ [Worker 5]: ระบบ Creative Director ออฟไลน์"

        # 🪙 ตรวจสอบค่าใช้จ่าย: ไอเดียโฆษณา = 20 Credits, วิเคราะห์แพ็กเกจจิ้ง = 50 Credits
        tokens_needed = 50 if file_path else 20
        auth_status = await self._deduct_token(user_id, tokens_needed)
        if not auth_status["authorized"]: return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "ESSENTIAL")
        logger.info(f"🎨 [Graphics & Ads]: เริ่มกระบวนการโปรดักชันให้ User {user_id} (Tier: {package_tier})")

        system_instruction = f"""
        คุณคือ 'Executive Creative Director' ระดับ Global Agency ของ SIRINTHANATTH PRIME
        ลูกค้ารายนี้อยู่ในแพ็กเกจระดับ: {package_tier}
        
        หน้าที่ของคุณ:
        1. 🎨 Art Direction: วิเคราะห์งานออกแบบ โทนสี Typography
        2. 🤖 4K Image Prompt: ร่าง Prompt ภาษาอังกฤษระดับสูง สำหรับให้ AI วาดรูป (เช่น Imagen/Midjourney)
        3. 🎙️ Copywriting: ร่างแคปชันโฆษณาที่ดึงดูด ถูกกฎหมาย (ไม่โอ้อวดเกินจริง)
        4. 🎯 Media Buying: แนะนำกลุ่มเป้าหมาย (Targeting) และช่องทางที่เหมาะสมสำหรับการยิงแอด
        
        🚨 กฎการส่งต่องาน (Swarm Delegation):
        - หากลูกค้าต้องการ 'ให้เรนเดอร์ภาพประกอบจริงๆ' หรือ 'สร้างภาพ 4K' ตาม Prompt ที่คุณร่างไว้ ให้โยนงานให้แผนก Media Engine โดยพิมพ์:
          [DELEGATE: WORKER_11_MEDIA] ช่วยนำ Prompt วาดภาพต่อไปนี้ไปเรนเดอร์ภาพ 4K: (ใส่ Prompt ภาษาอังกฤษ)
        - หากลูกค้าต้องการสคริปต์วิดีโอ (Storyboard) หรือพากย์เสียง ให้โยนให้ WORKER_4_VIDEO หรือ WORKER_3_AUDIO
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 📂 1. จัดการระบบวิเคราะห์รูปภาพ (Image & Packaging Parser)
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"🎨 [Worker 5]: กำลังอัปโหลดภาพเข้าสู่ Secure AI Engine เพื่อวิเคราะห์องค์ประกอบศิลป์...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type: mime_type = "image/jpeg"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    logger.error(f"⚠️ [Image Upload Error]: {e}")
                    return f"⚠️ [Worker 5]: ระบบไม่สามารถประมวลผลไฟล์รูปภาพนี้ได้ครับ รบกวนส่งเป็นไฟล์ .jpg หรือ .png ขนาดไม่เกิน 20MB ครับ"

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
                content_to_send.append(f"โปรดวิเคราะห์องค์ประกอบศิลป์ของภาพนี้ และยกระดับงานออกแบบโฆษณาตามคำสั่ง: {message}")
            else:
                content_to_send.append(f"โปรดร่างคอนเซปต์งานกราฟิก สื่อโฆษณา และสคริปต์สำหรับโปรดักชัน ตามความต้องการนี้: {message}")

            # ==========================================
            # 🧠 2. สั่งรัน Gemini 3.1 Pro (Creative Mode)
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.8 # ใช้อุณหภูมิ 0.8 เพื่อสร้างความหลากหลายและจินตนาการ
                )
            )
            
            reply_text = response.text.strip() if response.text else "✅ ออกแบบคอนเซปต์โฆษณาและประเมินแคมเปญเสร็จสิ้นครับ"

            # ==========================================
            # 🔄 3. ตรวจจับการส่งต่องาน (Swarm Delegation Logic)
            # ==========================================
            delegate_match = re.search(r'\[DELEGATE:\s*(.+?)\](.*)', reply_text, re.DOTALL | re.IGNORECASE)
            if delegate_match:
                target_worker = delegate_match.group(1).strip()
                handoff_message = delegate_match.group(2).strip()
                
                clean_reply = re.sub(r'\[DELEGATE:\s*(.+?)\](.*)', '', reply_text, flags=re.DOTALL | re.IGNORECASE).strip()
                
                worker_response = await swarm_hub.delegate_task(
                    from_worker="WORKER_5_GRAPHICS", 
                    to_worker=target_worker, 
                    user_id=user_id, 
                    message=handoff_message, 
                    file_path=file_path, 
                    file_type=None
                )
                return f"{clean_reply}\n\n🔄 [Creative Director ส่งต่อแผนก {target_worker}]:\n{worker_response}"

            return reply_text

        except TimeoutError:
            logger.error("❌ [Worker 5 Timeout]: ภาพมีความละเอียดหรือซับซ้อนเกินไป")
            return "ขออภัยครับ ภาพมีความละเอียดหรือขนาดใหญ่ทำให้ประมวลผลนานกว่าปกติ รบกวนย่อขนาดไฟล์แล้วลองใหม่อีกครั้งนะครับ"
        except Exception as e:
            logger.error(f"❌ [Worker 5 Error]: {e}")
            return f"⚠️ [Worker 5]: แผนกโปรดักชันครีเอทีฟขัดข้องชั่วคราว ทีมวิศวกรกำลังตรวจสอบระบบให้ครับ"

        finally:
            # ==========================================
            # 🧹 4. Trade Secret Protection (Zero-Data)
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info(f"🗑️ [Worker 5]: ลบไฟล์ภาพลับออกจากเซิร์ฟเวอร์เรียบร้อย (Trade Secret Safe)")
                except Exception as e:
                    logger.error(f"⚠️ [File Deletion Failed]: {e}")