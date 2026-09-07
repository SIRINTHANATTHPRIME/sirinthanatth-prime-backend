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

logger = logging.getLogger("Worker8-Ecommerce")

# =========================================================
# 🌐 1. นำเข้าศูนย์บัญชาการ AI ส่วนกลาง (Vertex AI / Zero Downtime)
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.1-pro-preview" # 🚀 อัปเกรดเป็นรุ่นเรือธงสำหรับอ่านสลิปและ OCR ขั้นสูงสุด
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

class EcommerceWorker:
    """
    🛒 Worker 8: Chief E-Commerce & Legal Compliance Officer (CELO)
    อัปเกรด: Gemini 3.1 Pro (Vision OCR), Swarm Delegation, Flash Express Automation, และ Zero-Data Retention
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.1-pro-preview")
        
        supa_url = os.environ.get("SUPABASE_URL")
        supa_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        self.line_oa_link = "https://lin.ee/@636pgjnh/SIRINTHANATTH_PRIME"
        self.topup_link = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")
        self.vip_link = "https://buy.stripe.com/00weVf1JdeBn07t7gI6Zy00"

    async def _deduct_token(self, user_id: str, tokens_needed: int) -> dict:
        """💳 ระบบ Smart Wallet: ตรวจสอบแพ็กเกจและหัก PRIME CREDITS อัตโนมัติ"""
        if not self.db: return {"authorized": True, "tier": "ESSENTIAL"} 
        
        try:
            def _check_and_deduct():
                user_data = self.db.table("prime_clients").select("package_tier, token_balance, role").eq("line_user_id", user_id).execute()
                
                if not user_data.data:
                    return {"authorized": False, "msg": "⚠️ ไม่พบข้อมูลบัญชีของท่าน กรุณาลงทะเบียนผ่านเมนูเพื่อเปิดใช้งานระบบ E-Commerce ครับ"}
                    
                client_data = user_data.data[0]
                role = client_data.get("role", "user")
                tier = client_data.get("package_tier", "ESSENTIAL").upper()
                balance = float(client_data.get("token_balance", 0.0))
                
                # 👑 VIP_FOUNDER และ Admin ใช้ฟรีไม่จำกัด (Unlimited Quota)
                if role in ["admin", "vip"] or tier in ["VIP_FOUNDER", "VIP", "ADMIN"]:
                    return {"authorized": True, "tier": tier}
                    
                if balance >= tokens_needed:
                    new_balance = balance - tokens_needed
                    self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                    logger.info(f"🪙 [Token Engine]: หัก {tokens_needed} Credits จาก {user_id} (บริการ E-Commerce)")
                    return {"authorized": True, "tier": tier}
                else:
                    return {"authorized": False, "msg": f"⚠️ ขออภัยครับ PRIME CREDITS ไม่เพียงพอ (ต้องการ {tokens_needed} เครดิต)\n\nกรุณาเติมเครดิตเพื่อสแกนสลิปและใช้งานระบบจัดการออเดอร์ต่อได้ที่นี่ครับ:\n👉 {self.topup_link}"}

            return await asyncio.to_thread(_check_and_deduct)
        except Exception as e:
            logger.error(f"❌ [Wallet DB Error]: {e}")
            return {"authorized": True, "tier": "ESSENTIAL"} 

    async def process_command(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """สะพานเชื่อมต่อรับงานจาก Swarm Hub หรือ Central Boss"""
        return await self.process_task(user_id, message, file_path, file_type)

    async def process_task(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """การประมวลผลหลักของ Worker 8: ตรวจสลิป แกะออเดอร์ และคัดกรองกฎหมายเบื้องต้น"""
        message_lower = message.lower() if message else ""
        
        # ==========================================
        # 1. ระบบดักจับคำสั่งซื้อแพ็กเกจ / เติมเงิน (Fast-Track)
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
        # 2. ให้ AI วิเคราะห์ข้อมูลออเดอร์/สลิป/เอกสารกฎหมาย
        # ==========================================
        if not self.client:
            return "⚠️ [Worker 8]: ระบบ E-Commerce & Legal ขัดข้อง (ไม่พบ API Key ส่วนกลาง)"

        # 🪙 ตรวจสอบค่าใช้จ่าย: ข้อความ = 10 Credits, สลิป/ภาพ = 50 Credits, สัญญา/PDF = 100 Credits
        tokens_needed = 10
        if file_path:
            if file_type in ['image', 'photo']: tokens_needed = 50
            else: tokens_needed = 100
            
        auth_status = await self._deduct_token(user_id, tokens_needed)
        if not auth_status["authorized"]: return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "ESSENTIAL")
        logger.info(f"📦 [Smart E-Commerce]: เริ่มวิเคราะห์ข้อมูลให้ User {user_id} (Tier: {package_tier})")
        
        system_instruction = f"""
        คุณคือ 'Chief E-commerce & Legal Officer (CELO)' ของ SIRINTHANATTH PRIME
        ลูกค้ารายนี้อยู่ในแพ็กเกจระดับ: {package_tier}
        
        หน้าที่ของคุณ:
        1. [งาน E-Commerce]: หากได้รับภาพสลิปโอนเงิน หรือออเดอร์ ให้สกัดยอดเงิน ชื่อที่อยู่จัดส่ง และเบอร์โทรศัพท์ ให้ชัดเจนและแม่นยำ 100% ห้ามเดาตัวเลขผิดเด็ดขาด
        2. [งานกฎหมาย]: หากได้รับเอกสารสัญญา ให้ตรวจสอบข้อตกลงซื้อขาย กฎหมาย PDPA และแจ้งเตือนหากพบความเสี่ยง
        3. ตอบกลับอย่างมืออาชีพ กระชับ เป็นทางการ (ใช้คำว่า ครับ/ค่ะ เสมอ)
        
        🚨 กฎการส่งต่องาน (Swarm Delegation):
        - หากสลิปโอนเงินมีแนวโน้มปลอมแปลง หรือสัญญาเสี่ยงต่อการผิดกฎหมาย ให้โยนงานให้ฝ่ายกฎหมายตรวจสอบต่อ โดยพิมพ์:
          [DELEGATE: WORKER_2_RISK_QA] พบความเสี่ยงในเอกสาร/ออเดอร์นี้ ฝากตรวจสอบข้อกฎหมายเชิงลึกครับ: (ระบุรายละเอียด)
        - หากต้องการบันทึกยอดขายลงในงบการเงิน ให้โยนให้ CFO:
          [DELEGATE: WORKER_7_FINANCE] ฝากบันทึกยอดขายและประเมินกำไรจากออเดอร์นี้ครับ: (ระบุยอดเงิน/รายละเอียด)
        """

        uploaded_file = None
        content_to_send = []
        is_order_context = False

        try:
            # ==========================================
            # 📂 3. ระบบอัปโหลดและวิเคราะห์ไฟล์ (Vision OCR)
            # ==========================================
            if file_path and os.path.exists(file_path):
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith(('.xlsx', '.xls')): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif file_path.lower().endswith('.csv'): mime_type = "text/csv"
                elif file_path.lower().endswith('.pdf'): mime_type = "application/pdf"
                if not mime_type: mime_type = "image/jpeg"
                
                # เช็คว่าเป็นออเดอร์หรือสลิปหรือไม่
                if file_type in ['image', 'photo'] or mime_type.startswith('image/'):
                    is_order_context = True
                    content_to_send.append("ตรวจสอบรูปภาพ/สลิปโอนเงินนี้ สกัดข้อมูลยอดเงิน สินค้า ที่อยู่จัดส่ง และเช็กความถูกต้องแม่นยำ 100%")
                else:
                    content_to_send.append("ตรวจสอบข้อกำหนดในเอกสารนี้ พร้อมให้ความเห็นเพื่อปกป้องธุรกิจ E-Commerce")

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    logger.error(f"⚠️ [File Upload Error]: {e}")
                    return f"⚠️ [Worker 8]: ระบบไม่สามารถอ่านไฟล์นี้ได้ รบกวนส่งเป็นภาพสลิป (JPG/PNG) หรือ PDF ครับ"

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
                if message: content_to_send.append(message)
            else:
                if any(kw in message_lower for kw in ["ออเดอร์", "สั่ง", "ยอด", "สลิป", "ส่ง", "ที่อยู่"]):
                    is_order_context = True
                content_to_send.append(f"โปรดดำเนินการ: {message}")

            # ==========================================
            # 🧠 4. สั่งรัน Gemini 3.1 Pro (Precision OCR)
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1 # อุณหภูมิต่ำสุดเพื่อความแม่นยำของตัวเลขยอดเงินในสลิป 100%
                )
            )
            
            ai_analysis = response.text.strip() if response.text else "✅ ตรวจสอบข้อมูลเสร็จสิ้นครับ"

            # ==========================================
            # 🔄 5. ตรวจจับการส่งต่องาน (Swarm Delegation)
            # ==========================================
            delegate_match = re.search(r'\[DELEGATE:\s*(.+?)\](.*)', ai_analysis, re.DOTALL | re.IGNORECASE)
            if delegate_match:
                target_worker = delegate_match.group(1).strip()
                handoff_message = delegate_match.group(2).strip()
                
                clean_reply = re.sub(r'\[DELEGATE:\s*(.+?)\](.*)', '', ai_analysis, flags=re.DOTALL | re.IGNORECASE).strip()
                
                worker_response = await swarm_hub.delegate_task(
                    from_worker="WORKER_8_ECOMMERCE", 
                    to_worker=target_worker, 
                    user_id=user_id, 
                    message=handoff_message, 
                    file_path=file_path, 
                    file_type=file_type
                )
                ai_analysis = f"{clean_reply}\n\n🔄 [ระบบส่งต่อให้ {target_worker} บันทึกข้อมูล]:\n{worker_response}"

            # ==========================================
            # 🚚 6. Interactive Menu (Flash Express) อัตโนมัติ
            # ==========================================
            if is_order_context and "ยืนยันการสร้างคลิป" not in message_lower:
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
            # 🧹 7. Zero-Data Retention (ทำลายข้อมูลทิ้งเพื่อ PDPA)
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info(f"🧹 [Zero-Data]: ลบไฟล์สลิป/สัญญา {uploaded_file.name} ออกจากเซิร์ฟเวอร์เรียบร้อยแล้ว")
                except Exception as e:
                    logger.error(f"⚠️ [File Deletion Failed]: {e}")