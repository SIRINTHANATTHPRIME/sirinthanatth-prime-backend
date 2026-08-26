import os
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

# 🌐 นำเข้าศูนย์บัญชาการ AI และฐานข้อมูล
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-2.5-pro" # รุ่นเรือธงสำหรับการวิเคราะห์วิดีโอและวางโครงสร้าง
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            return genai.Client(api_key=api_key) if api_key else None

try:
    from supabase import create_client, Client
except ImportError:
    Client = None

logger = logging.getLogger("Worker4-VideoDirector")

class VideoProductionWorker:
    """
    🎬 Worker 4: Executive Video Director & Analyst
    อัปเกรด: [Gemini 2.5 Pro] ระบบวิเคราะห์วิดีโอ, ออกแบบ Storyboard 4K/HD และระบบ Approval Workflow
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = PrimeAIConfig.EXECUTIVE_MODEL
        
        # เชื่อมต่อ Supabase สำหรับระบบ Token
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        self.topup_link = "https://buy.stripe.com/YOUR_TOPUP_LINK" # เปลี่ยนเป็นลิงก์เติมเงินจริง

    async def _deduct_token(self, user_id: str, tokens_needed: int) -> dict:
        """💳 ตรวจสอบแพ็กเกจและหัก PRIME CREDITS อัจฉริยะ สำหรับงานวิดีโอ"""
        if not self.db:
            return {"authorized": True, "tier": "ESSENTIAL"} # Fallback โหมด Offline
        
        try:
            user_data = await asyncio.to_thread(
                lambda: self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
            )
            
            if not user_data.data:
                return {"authorized": False, "msg": "⚠️ ไม่พบข้อมูลบัญชี กรุณาลงทะเบียนเพื่อเปิดใช้งานระบบ Video Production ครับ"}
                
            balance = float(user_data.data[0].get("token_balance", 0.0))
            tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
            
            # 👑 VIP_FOUNDER และ ENTERPRISE ใช้งานระบบวิเคราะห์สื่อได้ตามสิทธิพิเศษ
            if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]:
                return {"authorized": True, "tier": tier}
                
            if balance >= tokens_needed:
                new_balance = balance - tokens_needed
                await asyncio.to_thread(
                    lambda: self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                )
                logger.info(f"🪙 [Token Engine]: หัก {tokens_needed} Credits จาก {user_id} (บริการ Video Production)")
                return {"authorized": True, "tier": tier}
            else:
                return {"authorized": False, "msg": f"⚠️ PRIME CREDITS ของท่านไม่เพียงพอสำหรับการวิเคราะห์หรือสร้างสคริปต์วิดีโอ (ต้องการ {tokens_needed} Credits)\n👉 เติมเครดิตได้ที่: {self.topup_link}"}
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return {"authorized": True, "tier": "ESSENTIAL"}

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """ทำงานเบื้องหลัง: วิเคราะห์วิดีโอ สร้าง Storyboard และผูกระบบส่งเรนเดอร์"""
        if not self.client:
            return "⚠️ [Worker 4]: ระบบ Video Director ออฟไลน์ (ไม่พบ API Key)"

        # 🪙 ตรวจสอบค่าใช้จ่าย: อัปโหลดวิดีโอให้ AI วิเคราะห์ = 100 Credits, คิดบทสคริปต์โฆษณา = 20 Credits
        tokens_needed = 100 if file_path else 20
        auth_status = await self._deduct_token(user_id, tokens_needed)
        
        if not auth_status["authorized"]:
            return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "ESSENTIAL")
        logger.info(f"🎬 [Video Production]: วางแผนวิดีโอให้ User {user_id} (Tier: {package_tier})")

        # 🧠 System Prompt ปรับแต่งตามระดับ Agency มืออาชีพ
        system_instruction = f"""
        คุณคือ 'Executive Video Director' ระดับโลก ของ SIRINTHANATTH PRIME
        ลูกค้ารายนี้อยู่ในแพ็กเกจระดับ: {package_tier}
        
        หน้าที่ของคุณ:
        1. 🎞️ การวิเคราะห์วิดีโอ (Video Analysis): หากได้รับไฟล์วิดีโอ ให้ถอดรหัสองค์ประกอบภาพ เสียง อารมณ์ และชี้จุดที่ควรปรับปรุงเพื่อเพิ่ม Conversion Rate
        2. 📝 การออกแบบ Storyboard: หากลูกค้าให้คิดคอนเซปต์ ให้แบ่งฉากอย่างเป็นระบบ:
           - Scene 1: Hook (ดึงดูดสายตาใน 3 วินาทีแรก)
           - Scene 2: Pain Point (ขยี้ปัญหา/อารมณ์)
           - Scene 3: Solution (นำเสนอทางออกของโปรดักส์)
           - Scene 4: Call-to-Action (ปิดการขาย)
        3. 🗣️ บทพากย์ (Voiceover Script): เขียนคำพูดที่สละสลวย เตรียมไว้ให้ AI พากย์เสียง
        
        ⚠️ ข้อบังคับสำคัญสูงสุด (Approval Workflow): 
        ตบท้ายข้อความของคุณด้วยประโยคนี้เสมอ เพื่อเข้าสู่ระบบ Automation ให้ลูกค้าอนุมัติ:
        "📝 [ตรวจสอบสคริปต์]: หากพึงพอใจกับโครงสร้างนี้ โปรดพิมพ์คำว่า 'ยืนยันการสร้างคลิป' เพื่อให้ระบบประเมินราคา ตัดเครดิตจาก Smart Wallet และส่งเข้าสู่กระบวนการเรนเดอร์ 4K ทันทีครับ"
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 📂 1. จัดการอัปโหลดไฟล์วิดีโอ (Deep Video Parsing)
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"🎞️ [Worker 4]: กำลังอัปโหลดวิดีโอขึ้น Cloud เพื่อการวิเคราะห์เฟรมต่อเฟรม...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = "video/mp4" # ค่าเริ่มต้นสำหรับวิดีโอ

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    return f"⚠️ [Worker 4]: โครงสร้างไฟล์วิดีโอไม่รองรับหรือใหญ่เกินไปครับ รบกวนส่งเป็นไฟล์ .mp4 ขนาดไม่เกิน 50MB ครับ"

                # ⏳ Async Sync: วิดีโอจะใช้เวลาประมวลผลนานกว่าปกติ ระบบจะรออย่างใจเย็น
                while uploaded_file.state.name == "PROCESSING":
                    logger.info("⏳ [Worker 4]: AI กำลังแยกเฟรมภาพและเสียงในวิดีโอ (Processing)...")
                    await asyncio.sleep(4) # เช็กทุกๆ 4 วินาทีเพื่อลดภาระเซิร์ฟเวอร์
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 4]: ขออภัยครับ AI ไม่สามารถถอดรหัสวิดีโอนี้ได้ อาจมีความซับซ้อนเกินไป"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดวิเคราะห์วิดีโอนี้อย่างละเอียด และให้คำแนะนำตามคำสั่ง: {message}")
            else:
                content_to_send.append(f"โปรดออกแบบและวางแผนสคริปต์วิดีโอโฆษณา (Storyboard) สำหรับหัวข้อนี้: {message}")

            # ==========================================
            # 🧠 2. ประมวลผลขั้นสูงด้วย Gemini 2.5 Pro
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7 # ใช้อุณหภูมิ 0.7 เพื่อดึงความคิดสร้างสรรค์ระดับผู้กำกับออกมา
                )
            )
            
            return response.text if response.text else "✅ ออกแบบสคริปต์และวางแผนวิดีโอเสร็จสิ้นครับ"

        except Exception as e:
            logger.error(f"❌ [Worker 4 Error]: {e}")
            return f"⚠️ [Worker 4]: สตูดิโอวิดีโอขัดข้องชั่วคราว ทีมวิศวกรกำลังตรวจสอบครับ (Error: {str(e)[:50]})"

        finally:
            # ==========================================
            # 🧹 3. Zero-Data Retention Policy (PDPA Video Shield)
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🗑️ [Worker 4]: ลบไฟล์วิดีโอ Footage ลับของลูกค้าออกจากคลาวด์เรียบร้อย (Data Privacy Shield)")
                except:
                    pass