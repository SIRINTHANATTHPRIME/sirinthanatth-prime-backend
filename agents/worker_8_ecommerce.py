import os
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types
from supabase import create_client, Client

logger = logging.getLogger("Worker8-Ecommerce")

# =========================================================
# 🌐 นำเข้าศูนย์บัญชาการ AI ส่วนกลาง
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.1-pro"
        @staticmethod
        def get_client():
            PrimeAIConfig.self.client = genai.Client(
                vertexai=True, 
                project="swift-area-503915-a1", 
                location="asia-southeast3"
            )

class EcommerceWorker:
    """
    🛒 Worker 8: Chief E-Commerce & Legal Compliance Officer (CELO)
    หน้าที่: ตรวจสลิป, จัดการออเดอร์ (Flash Express), ตรวจสอบกฎหมายธุรกิจ และระบบ Smart Wallet
    """
    def __init__(self):
        # 🚀 โหลด Client และโมเดลรุ่นท็อป
        self.client = PrimeAIConfig.get_client()
        self.model_name = PrimeAIConfig.EXECUTIVE_MODEL
        
        # 💾 เชื่อมต่อฐานข้อมูล Supabase สำหรับเช็คยอด Token และ Wallet
        supa_url = os.environ.get("SUPABASE_URL")
        supa_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
        self.supabase: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        # 🔗 ลิงก์ระบบชำระเงิน (อ้างอิงจาก Master Plan)
        self.line_oa_link = "https://lin.ee/@636pgjnh/SIRINTHANATTH_PRIME"
        self.topup_link = "https://buy.stripe.com/YOUR_TOPUP_LINK" # เปลี่ยนเป็นลิงก์ Stripe เติมเงินจริง
        self.vip_link = "https://buy.stripe.com/00weVf1JdeBn07t7gI6Zy00"

        self.system_instruction = """
        คุณคือ 'Chief E-commerce & Legal Officer (CELO)' ของ SIRINTHANATTH PRIME
        หน้าที่ของคุณ:
        1. [งาน E-Commerce]: ตรวจสอบข้อมูลออเดอร์ หรือสลิปโอนเงิน สรุปยอดให้ชัดเจน พร้อมให้คำแนะนำเพิ่มยอดขาย (Upsell)
        2. [งานกฎหมาย]: ตรวจสอบข้อตกลง สัญญา ซื้อขาย PDPA หรือ OIC ให้คำปรึกษาทางกฎหมายอย่างรัดกุม
        3. ตอบกลับอย่างมืออาชีพ กระชับ เป็นทางการ (ใช้คำว่า ครับ/ค่ะ เสมอ)
        4. หากพบความเสี่ยงทางกฎหมาย ให้ตักเตือนและเสนอแนะทางแก้ไขทันที
        """

    async def _authorize_and_deduct_token(self, user_id: str, file_type: str) -> dict:
        """
        💳 ระบบ Smart Wallet: ตรวจสอบและหัก PRIME CREDITS อัตโนมัติ
        """
        if not self.supabase:
            return {"authorized": True, "message": "Bypass (DB Offline)"}
            
        # กำหนดราคา Token ตามประเภทงาน
        cost = 1 # ข้อความแชททั่วไป
        if file_type in ['image', 'photo']: cost = 50 # สแกนสลิป/ภาพออเดอร์
        elif file_type in ['file', 'pdf', 'document']: cost = 100 # สแกนเอกสารสัญญา
        
        try:
            # 1. ดึงข้อมูลกระเป๋าเงินลูกค้า (รันแบบ Asynchronous)
            def fetch_wallet():
                return self.supabase.table("prime_clients").select("token_balance, role").eq("line_user_id", user_id).execute()
            
            res = await asyncio.to_thread(fetch_wallet)
            
            if not res.data:
                return {"authorized": False, "message": f"⚠️ ไม่พบข้อมูลบัญชีของท่าน กรุณาลงทะเบียนผ่านเมนูเพื่อรับโบนัส Token ฟรีครับ"}
                
            client_data = res.data[0]
            role = client_data.get("role", "user")
            balance = float(client_data.get("token_balance", 0.0))
            
            # 👑 VIP และ Admin ใช้ฟรีไม่จำกัด (Unlimited Quota)
            if role in ["admin", "vip", "founder"]:
                return {"authorized": True, "message": "Unlimited VIP"}
                
            # 2. ตรวจสอบยอดและหักเงิน
            if balance >= cost:
                new_balance = balance - cost
                # หักเงินออกจากฐานข้อมูล
                await asyncio.to_thread(self.supabase.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute)
                return {"authorized": True, "message": f"Transaction Success (Remaining: {new_balance:,.2f} Credits)"}
            else:
                return {"authorized": False, "message": f"⚠️ ขออภัยครับ PRIME CREDITS ของท่านคงเหลือไม่เพียงพอ (ต้องการ {cost} เครดิต)\n\nกรุณาเติมเครดิตเพื่อใช้งานระบบ AI ขั้นสูงต่อได้ที่นี่ครับ:\n👉 {self.topup_link}"}
                
        except Exception as e:
            logger.error(f"❌ [Wallet DB Error]: {e}")
            return {"authorized": True, "message": "Bypass due to error"} # ป้องกันระบบล่มแล้วลูกค้าโวยวาย

    async def process_task(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """การประมวลผลหลักของ Worker 8"""
        message_lower = message.lower()
        
        # ==========================================
        # 1. ระบบดักจับคำสั่งซื้อแพ็กเกจ / เติมเงิน (Backward Compatibility)
        # ==========================================
        if any(kw in message_lower for kw in ["vip", "founders", "4490"]):
            return (f"👑 [100 VIP Founders Presale Offer]\n"
                    f"ชำระ 4,490 บาท/ปี การันตีล็อกราคานี้ตลอดชีพ (Lifetime Price Lock)\n"
                    f"รับเครดิต 49,000 Tokens และปลดล็อกเรทส่ง Flash 12฿\n\n"
                    f"จองสิทธิ์ด่วนได้ที่นี่ครับ:\n👉 {self.vip_link}")
                    
        if any(kw in message_lower for kw in ["สมัคร", "แพ็กเกจ", "อัปเกรด"]):
            return (f"ยินดีต้อนรับสู่ระบบนิเวศของ SIRINTHANATTH PRIME ครับ! 🚀\n"
                    f"ตรวจสอบแพ็กเกจและชำระเงินผ่านระบบอัตโนมัติได้ที่เมนูบนหน้าเว็บ หรือลิงก์นี้ครับ:\n👉 {self.line_oa_link}")
                    
        if any(kw in message_lower for kw in ["เติมเงิน", "wallet", "เติมกระเป๋า", "token", "เครดิต"]):
            return (f"💰 เติม PRIME CREDITS เข้า Smart Wallet เพื่อใช้งานระบบประมวลผล AI ขั้นสูง\n"
                    f"และสิทธิพิเศษค่าส่งพัสดุ Flash Express ได้ที่นี่ครับ:\n👉 {self.topup_link}")

        # ==========================================
        # 2. ระบบ Smart Wallet (Tokenomics Engine)
        # ==========================================
        auth_status = await self._authorize_and_deduct_token(user_id, file_type)
        if not auth_status["authorized"]:
            return auth_status["message"] # คืนค่าแจ้งเตือนให้เติมเงินทันที

        # ==========================================
        # 3. ให้ AI วิเคราะห์ข้อมูลออเดอร์/สลิป/เอกสารกฎหมาย
        # ==========================================
        if not self.client:
            return "⚠️ [Worker 8]: ระบบ E-Commerce & Legal ขัดข้อง (ไม่พบ API Key)"

        logger.info(f"📦 [Smart E-Commerce]: กำลังวิเคราะห์ข้อมูลให้ User {user_id}...")
        uploaded_file = None
        content_to_send = []
        is_order_context = False

        try:
            if file_path and os.path.exists(file_path):
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type: mime_type = "application/octet-stream"
                
                # เช็คว่าเป็นออเดอร์หรือสลิปหรือไม่
                if file_type in ['image', 'photo']:
                    is_order_context = True
                    content_to_send.append("ตรวจสอบรูปภาพ/สลิปโอนเงินนี้ สกัดข้อมูลยอดเงิน/สินค้า และแนะนำการอัปเซลล์")
                else:
                    content_to_send.append("ตรวจสอบสัญญาหรือข้อกำหนดในเอกสารนี้ พร้อมให้ความเห็นทางกฎหมายเพื่อปกป้องธุรกิจ")

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    return f"⚠️ [Worker 8]: ไม่สามารถอ่านไฟล์นี้ได้ รบกวนส่งเป็นภาพ (JPG/PNG) หรือ PDF ครับ"

                # รอจนกว่าไฟล์จะพร้อม (รองรับไฟล์ขนาดใหญ่)
                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(1.5)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 8]: เกิดข้อผิดพลาดในการประมวลผลไฟล์สลิป/เอกสารครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(message)
            else:
                if any(kw in message_lower for kw in ["ออเดอร์", "สั่ง", "ยอด", "สลิป", "ส่ง"]):
                    is_order_context = True
                content_to_send.append(f"โปรดดำเนินการ: {message}")

            # สั่งการ Gemini 3.1 Pro (รันแบบ Thread ไม่บล็อกเซิร์ฟเวอร์หลัก)
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.2 # อุณหภูมิต่ำเพื่อความแม่นยำของตัวเลขและกฎหมาย
                )
            )
            
            ai_analysis = response.text if response.text else "✅ วิเคราะห์เสร็จสิ้นครับ"

            # ==========================================
            # 4. Interactive Menu (Flash Express) อัตโนมัติ
            # ==========================================
            if is_order_context:
                ai_analysis += (
                    "\n\n-------------------------\n"
                    "📦 [Logistics Management]:\n"
                    "ท่านผู้บริหารโปรดเลือกรายการสั่งการจัดส่ง Flash Express:\n"
                    "👉 [พิมพ์ 1] จัดส่งทันที (ออกใบปะหน้า Flash 12฿/ชิ้น หักผ่าน Smart Token)\n"
                    "👉 [พิมพ์ 2] นัดเวลารถเข้ารับพัสดุ (ขั้นต่ำ 5 ชิ้น/วัน เข้ารับฟรี)\n"
                    "👉 [พิมพ์ 3] พักออเดอร์ไว้ก่อนเพื่อรวมบิล\n"
                    "-------------------------"
                )

            return ai_analysis

        except Exception as e:
            logger.error(f"❌ [Worker 8 Error]: {e}")
            return f"⚠️ [Worker 8]: ระบบประมวลผลการค้าและกฎหมายขัดข้องชั่วคราวครับ (Error: {str(e)[:50]})"

        finally:
            # 🧹 5. Zero-Data Retention (ทำลายข้อมูลทิ้งเพื่อ PDPA)
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🧹 [Zero-Data]: ลบไฟล์สลิป/สัญญาออกจากเซิร์ฟเวอร์เรียบร้อยแล้ว")
                except:
                    pass