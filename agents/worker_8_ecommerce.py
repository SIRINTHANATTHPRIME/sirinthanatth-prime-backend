import os
import time
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types
from supabase import create_client, Client

logger = logging.getLogger("Worker8-Ecommerce")

# =========================================================
# 🌐 1. นำเข้าศูนย์บัญชาการ AI ส่วนกลาง (Vertex AI / Zero Downtime)
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-2.5-pro" # 🚀 อัปเกรดเป็นรุ่นเรือธงสำหรับอ่านสลิปและสกัดข้อมูล OCR ขั้นสูง
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

class EcommerceWorker:
    """
    🛒 Worker 8: Chief E-Commerce & Legal Compliance Officer (CELO)
    อัปเกรด: Vertex AI (Gemini 2.5 Pro) ตรวจสลิปแม่นยำสูง, จัดการ Flash Express, และ Zero-Data Retention
    """
    def __init__(self):
        # 🚀 โหลด Client และโมเดลรุ่นท็อป
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-2.5-pro")
        
        # 💾 เชื่อมต่อฐานข้อมูล Supabase สำหรับเช็คยอด Token และ Wallet
        supa_url = os.environ.get("SUPABASE_URL")
        supa_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
        self.supabase: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        # 🔗 ลิงก์ระบบชำระเงิน
        self.line_oa_link = "https://lin.ee/@636pgjnh/SIRINTHANATTH_PRIME"
        self.topup_link = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")
        self.vip_link = "https://buy.stripe.com/00weVf1JdeBn07t7gI6Zy00"

        self.system_instruction = """
        คุณคือ 'Chief E-commerce & Legal Officer (CELO)' ของ SIRINTHANATTH PRIME
        หน้าที่ของคุณ:
        1. [งาน E-Commerce]: ตรวจสอบข้อมูลออเดอร์ หรือสลิปโอนเงิน สกัดตัวเลข ยอดเงิน และชื่อที่อยู่จัดส่งให้ชัดเจน แม่นยำ 100% พร้อมให้คำแนะนำเพิ่มยอดขาย (Upsell) อย่างแนบเนียน
        2. [งานกฎหมาย]: ตรวจสอบข้อตกลง สัญญา ซื้อขาย PDPA หรือ OIC ให้คำปรึกษาทางกฎหมายอย่างรัดกุม
        3. ตอบกลับอย่างมืออาชีพ กระชับ เป็นทางการ (ใช้คำว่า ครับ/ค่ะ เสมอ)
        4. หากพบความเสี่ยงทางกฎหมาย หรือสลิปโอนเงินมีแนวโน้มปลอมแปลง ให้ตักเตือนและเสนอแนะทางแก้ไขทันที
        """

    async def _authorize_and_deduct_token(self, user_id: str, file_type: str) -> dict:
        """💳 ระบบ Smart Wallet: ตรวจสอบและหัก PRIME CREDITS อัตโนมัติ (Thread-Safe)"""
        if not self.supabase:
            return {"authorized": True, "message": "Bypass (DB Offline)"}
            
        # กำหนดราคา Token ตามประเภทงาน
        cost = 10 # ข้อความแชททั่วไปเกี่ยวกับออเดอร์
        if file_type in ['image', 'photo']: cost = 50 # สแกนสลิป/ภาพออเดอร์
        elif file_type in ['file', 'pdf', 'document']: cost = 100 # สแกนเอกสารสัญญา
        
        try:
            def fetch_wallet():
                return self.supabase.table("prime_clients").select("token_balance, package_tier, role").eq("line_user_id", user_id).execute()
            
            res = await asyncio.to_thread(fetch_wallet)
            
            if not res.data:
                return {"authorized": False, "message": f"⚠️ ไม่พบข้อมูลบัญชีของท่าน กรุณาลงทะเบียนผ่านเมนูเพื่อเปิดใช้งานระบบ E-Commerce ครับ"}
                
            client_data = res.data[0]
            role = client_data.get("role", "user")
            tier = client_data.get("package_tier", "ESSENTIAL").upper()
            balance = float(client_data.get("token_balance", 0.0))
            
            # 👑 VIP_FOUNDER และ Admin ใช้ฟรีไม่จำกัด (Unlimited Quota)
            if role in ["admin", "vip"] or tier in ["VIP_FOUNDER", "VIP", "ADMIN"]:
                return {"authorized": True, "message": "Unlimited VIP"}
                
            # ตรวจสอบยอดและหักเงิน
            if balance >= cost:
                new_balance = balance - cost
                await asyncio.to_thread(self.supabase.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute)
                logger.info(f"🪙 [Token Engine]: หัก {cost} Credits จาก {user_id} (บริการ E-Commerce)")
                return {"authorized": True, "message": f"Transaction Success"}
            else:
                return {"authorized": False, "message": f"⚠️ ขออภัยครับ PRIME CREDITS ของท่านคงเหลือไม่เพียงพอ (ต้องการ {cost} เครดิต)\n\nกรุณาเติมเครดิตเพื่อสแกนสลิปและใช้งานระบบจัดการออเดอร์ต่อได้ที่นี่ครับ:\n👉 {self.topup_link}"}
                
        except Exception as e:
            logger.error(f"❌ [Wallet DB Error]: {e}")
            return {"authorized": True, "message": "Bypass due to error"} 

    async def process_task(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """การประมวลผลหลักของ Worker 8"""
        message_lower = message.lower()
        
        # ==========================================
        # 1. ระบบดักจับคำสั่งซื้อแพ็กเกจ / เติมเงิน
        # ==========================================
        if any(kw in message_lower for kw in ["vip", "founders", "4490"]):
            return (f"👑 [100 VIP Founders Presale Offer]\n"
                    f"ชำระ 4,490 บาท/ปี การันตีล็อกราคานี้ตลอดชีพ (Lifetime Price Lock)\n"
                    f"รับเครดิต 49,000 Tokens และปลดล็อกเรทส่ง Flash ขั้นต่ำ 12฿\n\n"
                    f"จองสิทธิ์ด่วนได้ที่นี่ครับ:\n👉 {self.vip_link}")
                    
        if any(kw in message_lower for kw in ["สมัคร", "แพ็กเกจ", "อัปเกรด"]):
            return (f"ยินดีต้อนรับสู่ระบบนิเวศของ SIRINTHANATTH PRIME ครับ! 🚀\n"
                    f"ตรวจสอบแพ็กเกจและชำระเงินผ่านระบบอัตโนมัติได้ที่เมนูบนหน้าเว็บ หรือลิงก์นี้ครับ:\n👉 {self.line_oa_link}")
                    
        if any(kw in message_lower for kw in ["เติมเงิน", "wallet", "เติมกระเป๋า", "token", "เครดิต"]):
            return (f"💰 เติม PRIME CREDITS เข้า Smart Wallet เพื่อใช้งานระบบประมวลผล AI ขั้นสูง\n"
                    f"และเปิดใช้งานสิทธิพิเศษค่าส่งพัสดุ Flash Express ได้ที่นี่ครับ:\n👉 {self.topup_link}")

        # ==========================================
        # 2. ระบบ Smart Wallet (Tokenomics Engine)
        # ==========================================
        auth_status = await self._authorize_and_deduct_token(user_id, file_type)
        if not auth_status["authorized"]:
            return auth_status["message"]

        # ==========================================
        # 3. ให้ AI วิเคราะห์ข้อมูลออเดอร์/สลิป/เอกสารกฎหมาย
        # ==========================================
        if not self.client:
            return "⚠️ [Worker 8]: ระบบ E-Commerce & Legal ขัดข้อง (ไม่พบ API Key ส่วนกลาง)"

        logger.info(f"📦 [Smart E-Commerce]: เริ่มวิเคราะห์ออเดอร์/สลิปให้ User {user_id}...")
        uploaded_file = None
        content_to_send = []
        is_order_context = False

        try:
            if file_path and os.path.exists(file_path):
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith('.xlsx'): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif file_path.lower().endswith('.xls'): mime_type = "application/vnd.ms-excel"
                elif file_path.lower().endswith('.csv'): mime_type = "text/csv"
                elif file_path.lower().endswith('.pdf'): mime_type = "application/pdf"
                if not mime_type: mime_type = "application/octet-stream"
                
                # เช็คว่าเป็นออเดอร์หรือสลิปหรือไม่
                if file_type in ['image', 'photo']:
                    is_order_context = True
                    content_to_send.append("ตรวจสอบรูปภาพ/สลิปโอนเงินนี้ สกัดข้อมูลยอดเงิน/สินค้า และเช็กความถูกต้องอย่างแม่นยำ 100%")
                else:
                    content_to_send.append("ตรวจสอบข้อกำหนดในเอกสารนี้ พร้อมให้ความเห็นทางกฎหมายเพื่อปกป้องธุรกิจ")

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    logger.error(f"⚠️ [File Upload Error]: {e}")
                    return f"⚠️ [Worker 8]: ระบบไม่สามารถอ่านไฟล์นี้ได้ รบกวนส่งเป็นภาพ (JPG/PNG) หรือ PDF ครับ"

                # ⏳ เช็กสถานะการประมวลผลไฟล์ พร้อมระบบ Anti-Freeze (Timeout 60s)
                timeout = 60
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        raise TimeoutError("หมดเวลาการสแกนสลิป/เอกสาร")
                    await asyncio.sleep(1.5)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 8]: เกิดข้อผิดพลาดในการถอดรหัสไฟล์สลิป/เอกสารครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(message)
            else:
                if any(kw in message_lower for kw in ["ออเดอร์", "สั่ง", "ยอด", "สลิป", "ส่ง"]):
                    is_order_context = True
                content_to_send.append(f"โปรดดำเนินการ: {message}")

            # สั่งการ Gemini 2.5 Pro (รันแบบ Thread ไม่บล็อกเซิร์ฟเวอร์หลัก)
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.1 # อุณหภูมิต่ำสุดเพื่อความแม่นยำของตัวเลขยอดเงินในสลิป ไม่มโนข้อมูล
                )
            )
            
            ai_analysis = response.text.strip() if response.text else "✅ ตรวจสอบข้อมูลเสร็จสิ้นครับ"

            # ==========================================
            # 4. Interactive Menu (Flash Express) อัตโนมัติ
            # ==========================================
            if is_order_context:
                ai_analysis += (
                    "\n\n-------------------------\n"
                    "📦 [Logistics Management]:\n"
                    "ท่านผู้บริหารโปรดเลือกรายการสั่งการจัดส่ง Flash Express:\n"
                    "👉 [พิมพ์ 1] จัดส่งทันที (ออกใบปะหน้า Flash เริ่มต้น 12฿ หักผ่าน Smart Token)\n"
                    "👉 [พิมพ์ 2] นัดเวลารถเข้ารับพัสดุ (ขั้นต่ำ 5 ชิ้น/วัน เข้ารับฟรี)\n"
                    "👉 [พิมพ์ 3] พักออเดอร์ไว้ก่อนเพื่อรวมบิล\n"
                    "-------------------------"
                )

            return ai_analysis

        except TimeoutError:
            logger.error("❌ [Worker 8 Timeout]: ไฟล์ภาพสลิปหรือเอกสารขนาดใหญ่เกินไป")
            return "ขออภัยครับ รูปภาพมีความละเอียดสูงเกินไปทำให้ใช้เวลาสแกนนานกว่าปกติ รบกวนส่งใหม่อีกครั้งนะครับ"
        except Exception as e:
            logger.error(f"❌ [Worker 8 Error]: {e}")
            return f"⚠️ [Worker 8]: ระบบประมวลผลการค้าและกฎหมายขัดข้องชั่วคราวครับ ทีมงานกำลังตรวจสอบ"

        finally:
            # ==========================================
            # 🧹 5. Zero-Data Retention (ทำลายข้อมูลทิ้งเพื่อ PDPA)
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info(f"🧹 [Zero-Data]: ลบไฟล์สลิป/สัญญา {uploaded_file.name} ออกจากเซิร์ฟเวอร์เรียบร้อยแล้ว")
                except Exception as e:
                    logger.error(f"⚠️ [File Deletion Failed]: {e}")