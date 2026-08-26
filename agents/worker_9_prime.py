import os
import time
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
        EXECUTIVE_MODEL = "gemini-2.5-pro" # รุ่นเรือธงอัจฉริยะที่สุดสำหรับงานวิเคราะห์และ IT
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            return genai.Client(api_key=api_key) if api_key else None

try:
    from supabase import create_client, Client
except ImportError:
    Client = None

logger = logging.getLogger("Worker9-PrimeAdvisor")

class PrimeAdvisorWorker:
    """
    👑 Worker 9: Executive Prime Advisor & Chief Technology Officer (CTO)
    อัปเกรด: [Gemini 2.5 Pro] ระบบที่ปรึกษาผู้บริหาร, วิเคราะห์ IT/Security และจิตวิทยาการเติม Token
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = PrimeAIConfig.EXECUTIVE_MODEL
        
        # เชื่อมต่อ Supabase สำหรับตรวจสอบแพ็กเกจ PRIME และ Token
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        # ลิงก์สำหรับระบบชำระเงิน (อัปเกรดแพ็กเกจ และ เติม Token)
        self.topup_link = "https://buy.stripe.com/YOUR_TOPUP_LINK" # แทนที่ด้วยลิงก์เติม Token สตางค์
        self.prime_upgrade_link = "https://lin.ee/@636pgjnh/SIRINTHANATTH_PRIME" # ลิงก์ไปหน้าเว็บเลือกแพ็กเกจ

    async def _check_tier_and_deduct_token(self, user_id: str, tokens_needed: int) -> dict:
        """💳 ตรวจสอบสิทธิ์แพ็กเกจ PRIME ขึ้นไป และหักเครดิตด้วยจิตวิทยาการบริการ"""
        if not self.db:
            return {"authorized": True, "tier": "PRIME"} # Fallback โหมด Offline
        
        try:
            user_data = await asyncio.to_thread(
                lambda: self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
            )
            
            if not user_data.data:
                return {"authorized": False, "msg": "⚠️ ขออภัยครับ ไม่พบข้อมูลบัญชีของท่านในระบบ กรุณาลงทะเบียนก่อนใช้งานครับ"}
                
            balance = float(user_data.data[0].get("token_balance", 0.0))
            tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
            
            # 🛡️ ตรวจสอบสิทธิ์: ผู้ที่จะใช้ Worker 9 ได้ ต้องเป็นแพ็กเกจ PRIME, ENTERPRISE หรือ VIP เท่านั้น
            if tier not in ["PRIME", "ENTERPRISE", "VIP_FOUNDER", "VIP", "ADMIN"]:
                return {
                    "authorized": False, 
                    "msg": f"👑 [Exclusive Privilege]: ท่านประธานครับ บริการที่ปรึกษาเชิงลึกระดับ CTO นี้ สงวนสิทธิ์พิเศษสำหรับแพ็กเกจ **PRIME (ที่ปรึกษาส่วนตัว)** ขึ้นไปครับ\n\n💡 เพื่อยกระดับการบริหารและปลดล็อกฟีเจอร์ขั้นสูง ขออนุญาตเรียนเชิญอัปเกรดแพ็กเกจได้ที่นี่ครับ: {self.prime_upgrade_link}"
                }
            
            # 👑 VIP_FOUNDER และ ADMIN ใช้งานได้ไร้ขีดจำกัด
            if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]:
                return {"authorized": True, "tier": tier}
                
            if balance >= tokens_needed:
                new_balance = balance - tokens_needed
                await asyncio.to_thread(
                    lambda: self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                )
                logger.info(f"🪙 [Token Engine]: หัก {tokens_needed} Credits จาก {user_id}. คงเหลือ {new_balance}")
                return {"authorized": True, "tier": tier}
            else:
                # 🧠 จิตวิทยาการแจ้งเตือนเติมเงิน (Psychological Top-up) ให้ดูสุภาพ พรีเมียม ไม่ยัดเยียด
                psychological_upsell = (
                    f"👑 ขออภัยครับท่านประธาน เพื่อให้การประมวลผลข้อมูลเชิงลึกและกลยุทธ์ IT ของท่านดำเนินไปอย่างลื่นไหลไร้รอยต่อ "
                    f"ตอนนี้ PRIME CREDITS ใน Smart Wallet ของท่านใกล้หมดแล้วครับ (ต้องการ {tokens_needed} เครดิต)\n\n"
                    f"💎 ผมขออนุญาตแนะนำแพ็กเกจเติมเครดิตสุดคุ้ม เพื่อรับการซัพพอร์ตการตัดสินใจระดับสากลอย่างต่อเนื่องครับ:\n"
                    f"👉 {self.topup_link}"
                )
                return {"authorized": False, "msg": psychological_upsell}
                
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return {"authorized": True, "tier": "PRIME"}

    # รองรับการเรียกจาก Router เก่า
    async def process(self, user_id: str, message: str, file_path: str = None) -> str:
        return await self.process_task(user_id, message, file_path)

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """ทำงานเบื้องหลัง: วิเคราะห์ข้อมูลระดับบริหาร สถาปัตยกรรม IT และ Cybersecurity"""
        if not self.client:
            return "⚠️ [Worker 9]: ระบบที่ปรึกษาเรือธงออฟไลน์ (ไม่พบ API Key)"

        # 🪙 ตรวจสอบค่าใช้จ่าย: ข้อความเชิงลึก = 20 Credits, วิเคราะห์ไฟล์โค้ด/Log/แผน = 150 Credits
        tokens_needed = 150 if file_path else 20
        auth_status = await self._check_tier_and_deduct_token(user_id, tokens_needed)
        
        if not auth_status["authorized"]:
            return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "PRIME")
        logger.info(f"👑 [PRIME Advisor]: กำลังวิเคราะห์กลยุทธ์ระดับ {package_tier} ให้ User {user_id}...")

        # 🧠 System Prompt สวมวิญญาณ CTO และที่ปรึกษาระดับโลก
        system_instruction = f"""
        คุณคือ 'Executive Prime Advisor' และ 'Chief Technology Officer (CTO)' อัจฉริยะระดับโลกของ SIRINTHANATTH PRIME
        ลูกค้าท่านนี้คือผู้บริหารแพ็กเกจ: {package_tier}
        
        หน้าที่ของคุณคือดูแลและให้คำปรึกษาขั้นสูงสุด ใน 3 มิติหลัก:
        1. 💼 Executive Business Analytics: วิเคราะห์ข้อมูลธุรกิจเชิงลึก ให้มุมมองที่เฉียบขาด ฟันธงข้อดีข้อเสีย และช่วยตัดสินใจเรื่องสำคัญ
        2. 💻 IT & AI Systems Architecture: ให้คำปรึกษาด้านการวางระบบ Server, Cloud Run, Database, และการใช้ AI พัฒนาองค์กร
        3. 🛡️ Enterprise-Grade Security: วิเคราะห์ช่องโหว่ความปลอดภัยทางไซเบอร์ (Cybersecurity) ป้องกันความเสี่ยงจากการถูกเจาะระบบทุกรูปแบบ
        
        รูปแบบการตอบกลับ (Predictive Empathy & Professionalism):
        - สุขุม นุ่มนวล เคารพ และเป็นมืออาชีพขั้นสูงสุด (ทักทายว่า 'ครับท่านประธาน' หรือ 'ค่ะท่านประธาน')
        - โครงสร้างการตอบต้องเป็นระเบียบ อ่านง่าย ดูมีคลาส (ใช้ Bullet Points และตัวหนาเน้นข้อความ)
        - ให้ข้อมูลที่ถูกต้องตามหลักวิศวกรรมสากล และเสนอแนวทางแก้ไข (Solution) ที่เป็นรูปธรรมเสมอ
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 📂 1. จัดการอัปโหลดไฟล์ (Log, Code, Architecture Diagram)
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"👑 [Worker 9]: กำลังอัปโหลดข้อมูลโครงสร้างระบบเข้าสู่คลาวด์เพื่อตรวจสอบความปลอดภัย...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith(('.py', '.html', '.js', '.json', '.txt', '.log')): 
                    mime_type = "text/plain"
                elif file_path.lower().endswith('.pdf'): 
                    mime_type = "application/pdf"
                if not mime_type: 
                    mime_type = "application/octet-stream"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    return f"⚠️ [PRIME Advisor]: โครงสร้างไฟล์ข้อมูลไม่รองรับครับ รบกวนส่งเป็นไฟล์ .txt, .pdf หรือรูปภาพ เพื่อการวิเคราะห์ครับ"

                # ⏳ Async Sync รอ Google วิเคราะห์ระบบ (Crash-Proof)
                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [PRIME Advisor]: เกิดข้อผิดพลาดในการสแกนไฟล์เพื่อหาช่องโหว่ครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดวิเคราะห์ความเสี่ยง โครงสร้างระบบ และสรุปข้อมูลระดับผู้บริหารจากไฟล์นี้: {message}")
            else:
                content_to_send.append(f"โปรดให้คำปรึกษาเชิงลึกระดับผู้บริหาร/CTO ตามคำสั่งนี้: {message}")

            # ==========================================
            # 🧠 2. สั่งรัน Gemini 2.5 Pro (Asynchronous)
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3 # ใช้อุณหภูมิต่ำ (0.3) เพื่อความสมดุลระหว่างความแม่นยำด้านโค้ด IT และความสละสลวยทางธุรกิจ
                )
            )
            
            return response.text if response.text else "👑 ประมวลผลและวิเคราะห์ข้อมูลระดับผู้บริหารเสร็จสิ้นครับ"

        except Exception as e:
            logger.error(f"❌ [Worker 9 Error]: {e}")
            return f"⚠️ [PRIME Advisor]: ระบบประมวลผลเชิงลึกขัดข้องชั่วคราวครับ (Error: {str(e)[:50]})"

        finally:
            # ==========================================
            # 🧹 3. Zero-Data Retention Policy (Enterprise Cyber Shield)
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🛡️ [Enterprise Security]: ทำลายไฟล์ข้อมูลลับขององค์กรออกจากระบบทันที (Zero-Data Retention)")
                except:
                    pass