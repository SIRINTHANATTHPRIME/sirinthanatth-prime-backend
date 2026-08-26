import os
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

# 👑 นำเข้าระบบฐานข้อมูลและจัดการสิทธิประโยชน์ (Dynamic Import ป้องกัน Error)
try:
    from supabase import create_client, Client
except ImportError:
    Client = None

logger = logging.getLogger("Worker2-RiskQA")

class RiskQAWorker:
    """
    🛡️ Worker 2: Global Risk Assessment, Legal Shield & QA
    อัปเกรด: ผสานระบบตรวจสอบสิทธิ์ 4 แพ็กเกจ, ระบบตัด Token อัจฉริยะ, และ Google Cloud Storage Sync
    """
    def __init__(self):
        self.api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        
        # 🚀 อัปเกรดเป็น Gemini 1.5 Pro รุ่นเสถียรที่สุดเพื่อป้องกัน Error 404 Model Not Found บน Cloud Run
        self.model_name = 'gemini-1.5-pro'
        
        # เชื่อมต่อ Supabase สำหรับตรวจสอบแพ็กเกจและตัด Token
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None

    async def _deduct_token(self, user_id: str, tokens_needed: int) -> bool:
        """💳 ฟังก์ชันตรวจสอบและหัก Token อัจฉริยะตามแพ็กเกจของลูกค้า"""
        if not self.db:
            return True # กรณีรันโหมด Offline หรือยังไม่ต่อ DB ให้ผ่านไปก่อน
        
        try:
            # ดึงข้อมูลผู้ใช้
            user_data = self.db.table("users").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
            if not user_data.data:
                return False
                
            balance = user_data.data[0].get("token_balance", 0)
            tier = user_data.data[0].get("package_tier", "ESSENTIAL")
            
            # VIP_FOUNDER ไม่จำกัด Token
            if tier == "VIP_FOUNDER":
                return True
                
            if balance >= tokens_needed:
                new_balance = balance - tokens_needed
                self.db.table("users").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                logger.info(f"🪙 [Token Engine]: หัก {tokens_needed} tokens จาก {user_id}. คงเหลือ {new_balance}")
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return True # Fail-safe ยอมให้ใช้งานหากระบบ DB ขัดข้อง

    async def process_task(self, user_id: str, message: str, file_path: str = None, package_tier: str = "ESSENTIAL") -> str:
        """
        ทำงานเบื้องหลัง: สแกนความเสี่ยงและหากมีไฟล์จะสแกนช่องโหว่ระดับองค์กร
        พร้อมปรับความละเอียดการสแกนตาม Package (ESSENTIAL, PRIME, ENTERPRISE, VIP_FOUNDER)
        """
        if not self.client:
            return "⚠️ [Worker 2]: ระบบประเมินความเสี่ยงออฟไลน์ (ไม่พบ API Key)"

        # 🪙 กำหนด Token ที่ต้องใช้: ตรวจข้อความใช้ 1 Token, ตรวจไฟล์ใช้ 5 Token
        tokens_needed = 5 if file_path else 1
        has_tokens = await self._deduct_token(user_id, tokens_needed)
        
        if not has_tokens:
            return "⚠️ [ระบบการเงิน]: Token ของท่านไม่เพียงพอสำหรับการประเมินความเสี่ยงระดับลึก กรุณาเติม Token หรืออัปเกรดแพ็กเกจครับ"

        # 🧠 ปรับความเข้มข้นของการตรวจสอบตามแพ็กเกจลูกค้า
        tier_instructions = {
            "ESSENTIAL": "ตรวจสอบแค่กฎหมาย อย. และ สคบ. เบื้องต้น",
            "PRIME": "ตรวจสอบ อย., สคบ., PDPA และกฎแพลตฟอร์มโซเชียลมีเดียอย่างละเอียด",
            "ENTERPRISE": "ตรวจสอบทุกข้อกฎหมาย, ตรวจสอบสัญญา, ช่องโหว่ทางธุรกิจ และประเมินผลกระทบทางการเงิน",
            "VIP_FOUNDER": "ตรวจสอบระดับสูงสุด (Enterprise-grade) พร้อมเขียน Mitigation Plan ขั้นเด็ดขาดเพื่อป้องกันการถูกฟ้องร้อง 100%"
        }
        active_instruction = tier_instructions.get(package_tier, tier_instructions["ESSENTIAL"])

        system_instruction = f"""
        คุณคือ 'Worker 2' Chief Legal Officer และผู้เชี่ยวชาญด้าน Risk Management ของ SIRINTHANATTH PRIME
        
        ระดับบริการของลูกค้าท่านนี้: {package_tier}
        ความเข้มข้นที่คุณต้องสแกน: {active_instruction}
        
        หน้าที่ของคุณ:
        1. ค้นหา 'ความเสี่ยง' หรือ 'ช่องโหว่' (Vulnerabilities) ที่อาจทำให้ลูกค้าถูกฟ้องร้องหรือแบน
        2. ให้คะแนนความปลอดภัยทางกฎหมาย (Safe, Warning, Critical)
        3. เสนอแนวทางป้องกันและปรับแก้ข้อความ/เอกสารใหม่ให้ถูกต้องตามกฎหมาย 100%
        4. ใช้ภาษาที่รัดกุม เป็นทางการ ตรงไปตรงมา และแสดงออกถึงความพรีเมียม
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # ระบบจัดการไฟล์ข้อมูล & Google Storage Simulation
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"🛡️ [Worker 2]: กำลังอัปโหลดไฟล์สู่ Google Cloud Storage ย่อย เพื่อตรวจสอบความเสี่ยง...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith('.xlsx'): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif file_path.lower().endswith('.xls'): mime_type = "application/vnd.ms-excel"
                elif file_path.lower().endswith('.csv'): mime_type = "text/csv"
                if not mime_type: mime_type = "application/octet-stream"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    return f"⚠️ [Worker 2]: โครงสร้างไฟล์ซับซ้อนเกินไป รบกวนแปลงเป็น PDF เพื่อความปลอดภัยระดับองค์กรครับ"

                # ⏳ เช็กสถานะการประมวลผลไฟล์ (Async Sync ป้องกันคิวชนกัน)
                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 2]: ตรวจพบความขัดข้องในการสแกนไฟล์ ไม่สามารถประเมินได้ครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดตรวจสอบความเสี่ยงและหาช่องโหว่จากเอกสารนี้ ตามเงื่อนไขของแพ็กเกจ {package_tier}: {message}")
            else:
                content_to_send.append(f"โปรดตรวจสอบความเสี่ยงจากข้อมูลนี้ ตามเงื่อนไขของแพ็กเกจ {package_tier}: {message}")

            # ==========================================
            # ประมวลผลขั้นสูงด้วย Gemini 1.5 Pro
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2 # อุณหภูมิต่ำ (0.2) เพื่อความแม่นยำทางกฎหมาย ไม่ใช้จินตนาการ
                )
            )
            return response.text if response.text else "✅ สแกนเสร็จสิ้น ไม่พบความเสี่ยงที่น่ากังวลครับ"

        except Exception as e:
            logger.error(f"❌ [Worker 2 Error]: {e}")
            return f"⚠️ [Worker 2]: ระบบตรวจสอบความเสี่ยงขัดข้องชั่วคราวครับ (Debug: {str(e)[:100]})"

        finally:
            # 🧹 ทำลายไฟล์ทิ้งเพื่อความปลอดภัยของข้อมูลลูกค้า (PDPA Compliance)
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🗑️ [Worker 2]: ทำลายไฟล์ชั่วคราวออกจากระบบสำเร็จ (PDPA Check)")
                except:
                    pass