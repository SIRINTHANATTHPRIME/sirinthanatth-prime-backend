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
        EXECUTIVE_MODEL = "gemini-3.1-pro" # ใช้รุ่นเรือธงสำหรับตรรกะข้อมูลและ Excel
        @staticmethod
        def get_client():
            PrimeAIConfig.self.client = genai.Client(
                vertexai=True, 
                project="swift-area-503915-a1", 
                location="asia-southeast3"
            )
            return PrimeAIConfig.self.client

try:
    from supabase import create_client, Client
except ImportError:
    Client = None

logger = logging.getLogger("Worker1-Report")

class ReportWorker:
    """
    📊 Worker 1: Chief Data Officer (CDO) & Executive Report Specialist
    อัปเกรด: [Gemini 2.5 Pro] ระบบสร้างเอกสาร, ตารางคำนวณ, งานวิจัย และ Smart Wallet Tokenomics
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = PrimeAIConfig.EXECUTIVE_MODEL
        
        # เชื่อมต่อ Supabase สำหรับระบบ Token & Package Tiers
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        self.topup_link = "https://buy.stripe.com/YOUR_TOPUP_LINK" # เปลี่ยนเป็นลิงก์ Stripe เติมเงินจริง

    async def _deduct_token(self, user_id: str, tokens_needed: int) -> dict:
        """💳 ตรวจสอบแพ็กเกจและหัก PRIME CREDITS อัจฉริยะ สำหรับงานจัดการเอกสารและข้อมูล"""
        if not self.db:
            return {"authorized": True, "tier": "ESSENTIAL"} # Fallback โหมด Offline
        
        try:
            user_data = await asyncio.to_thread(
                lambda: self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
            )
            
            if not user_data.data:
                return {"authorized": False, "msg": "⚠️ ไม่พบข้อมูลบัญชี กรุณาลงทะเบียนหรือรับสิทธิ์ใช้งานระบบวิเคราะห์ข้อมูลขั้นสูงครับ"}
                
            balance = float(user_data.data[0].get("token_balance", 0.0))
            tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
            
            # 👑 VIP_FOUNDER และ ENTERPRISE ใช้งานระบบวิเคราะห์ข้อมูลได้ไม่จำกัด หรือตามระดับพิเศษ
            if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]:
                return {"authorized": True, "tier": tier}
                
            if balance >= tokens_needed:
                new_balance = balance - tokens_needed
                await asyncio.to_thread(
                    lambda: self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                )
                logger.info(f"🪙 [Token Engine]: หัก {tokens_needed} Credits จาก {user_id} (บริการ Data & Report)")
                return {"authorized": True, "tier": tier}
            else:
                return {"authorized": False, "msg": f"⚠️ PRIME CREDITS ของท่านไม่เพียงพอสำหรับการวิเคราะห์และสร้างเอกสาร (ต้องการ {tokens_needed} Credits)\n👉 เติมเครดิตได้ที่: {self.topup_link}"}
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return {"authorized": True, "tier": "ESSENTIAL"}

    # รองรับการเรียกจาก Router เก่าที่ใช้ชื่อฟังก์ชัน process()
    async def process(self, user_id: str, message: str, file_path: str = None) -> str:
        return await self.process_task(user_id, message, file_path)

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """ทำงานเบื้องหลัง: วิเคราะห์ข้อมูล สร้างโครงสร้างเอกสาร Excel/PPT และงานวิจัย"""
        if not self.client:
            return "⚠️ [Worker 1]: ระบบวิเคราะห์ข้อมูลออฟไลน์ (ไม่พบ API Key)"

        # 🪙 ตรวจสอบค่าใช้จ่าย: ถาม-ตอบสูตร Excel = 10 Credits, วิเคราะห์ Big Data / PDF = 100 Credits
        tokens_needed = 100 if file_path else 10
        auth_status = await self._deduct_token(user_id, tokens_needed)
        
        if not auth_status["authorized"]:
            return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "ESSENTIAL")
        logger.info(f"📊 [Document Engineering]: สร้างรายงานให้ User {user_id} (Tier: {package_tier})")

        # 🧠 System Prompt ปรับแต่งระดับโลกและปรับตาม Tier
        system_instruction = f"""
        คุณคือ 'Chief Data Officer (CDO)' และ 'Executive Administrator' ของ SIRINTHANATTH PRIME
        ลูกค้ารายนี้อยู่ในแพ็กเกจระดับ: {package_tier}
        
        หน้าที่และแนวทางการทำงาน:
        1. 📊 ตารางและการคำนวณ: ร่างโครงสร้าง Excel, สร้างสูตร (Formulas), หรือเขียน VBA/Python สำหรับจัดการ Big Data หากมีการสร้างตาราง ให้ใช้ Markdown Table เสมอ เพื่อให้ลูกค้าคัดลอกไปลง Excel ได้ทันที
        2. 📑 การจัดการเอกสาร (Filing) & งานวิจัย: ร่างหนังสือราชการ, โครงสร้างงานวิจัย, แผนงานการศึกษา, หรือโครงสร้าง Presentation (PowerPoint) อย่างมืออาชีพ
        3. 🔍 การย่อยข้อมูล (Data Extraction): สกัดข้อมูลสำคัญจากข้อความหรือไฟล์ที่แนบมา นำเสนอแบบ Executive Summary
        
        การยกระดับตามแพ็กเกจ:
        - {package_tier} (SMEs/บุคคล): เน้นความถูกต้อง เข้าใจง่าย ช่วยลดเวลาทำงาน Office รายวัน
        - หากเป็น ENTERPRISE / VIP: เน้นกลยุทธ์การเชื่อมต่อ API, Database Architecture, ระบบ ERP, BI Dashboard และการวิเคราะห์สถิติขั้นสูง
        
        *หมายเหตุความปลอดภัย*: อย่าลืมคำนึงถึงหลักความถูกต้องทางลิขสิทธิ์ และ PDPA หากข้อมูลดูเป็นความลับขององค์กร
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 📂 1. จัดการระบบวิเคราะห์ไฟล์ (Data Parser & File Upload)
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"📊 [Worker 1]: กำลังอัปโหลด Data File เพื่อวิเคราะห์เชิงลึก...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith('.xlsx'): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif file_path.lower().endswith('.xls'): mime_type = "application/vnd.ms-excel"
                elif file_path.lower().endswith('.csv'): mime_type = "text/csv"
                elif file_path.lower().endswith('.pdf'): mime_type = "application/pdf"
                if not mime_type: mime_type = "application/octet-stream"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    return f"⚠️ [Worker 1]: ไม่สามารถประมวลผลไฟล์นี้ได้โดยตรงครับ รบกวนแปลงเป็น PDF หรือ CSV เพื่อประสิทธิภาพสูงสุดในการวิเคราะห์ครับ"

                # ⏳ Async Sync รอ Google ย่อยข้อมูล (Crash-Proof)
                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 1]: เกิดข้อผิดพลาดในกระบวนการถอดรหัสเอกสารบนเซิร์ฟเวอร์ครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดวิเคราะห์ข้อมูล สกัดตัวเลขสำคัญ และจัดทำรายงานสรุปตามคำสั่งนี้: {message}")
            else:
                content_to_send.append(f"โปรดออกแบบโครงสร้างเอกสาร ตารางคำนวณ หรืองานวิจัย ตามคำสั่งนี้: {message}")

            # ==========================================
            # 🧠 2. สั่งรัน Gemini 3.1 Pro (Asynchronous)
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2 # ใช้อุณหภูมิ 0.2 เพื่อให้การคำนวณและโครงสร้างตารางมีความแม่นยำทางวิศวกรรมสูงสุด ไม่ผิดเพี้ยน
                )
            )
            
            return response.text if response.text else "✅ วิเคราะห์และจัดทำโครงร่างเอกสารเสร็จสิ้นครับ"

        except Exception as e:
            logger.error(f"❌ [Worker 1 Error]: {e}")
            return f"⚠️ [Worker 1]: ระบบจัดการเอกสารขัดข้องชั่วคราว ทีมวิศวกรกำลังเข้าตรวจสอบครับ (Error: {str(e)[:50]})"

        finally:
            # ==========================================
            # 🧹 3. Zero-Data Retention Policy (PDPA Shield)
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🗑️ [Worker 1]: ทำลายไฟล์ Data ของลูกค้าออกจากระบบคลาวด์เรียบร้อย (Data Privacy Shield)")
                except:
                    pass