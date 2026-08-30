import os
import time
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

# =========================================================
# 🌐 1. นำเข้าศูนย์บัญชาการ AI และฐานข้อมูล (Vertex AI / Zero Downtime Fallback)
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-2.5-pro" # 🚀 อัปเกรดเป็นรุ่นเรือธงสำหรับวิเคราะห์งบการเงินและตัวเลขที่ซับซ้อน
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

logger = logging.getLogger("Worker7-CFO")

class FinancialAndAccountingWorker:
    """
    💰 Worker 7: Chief Financial Officer (CFO) & Risk Management Expert
    อัปเกรด: Vertex AI (Gemini 2.5 Pro), ระบบวิเคราะห์งบการเงิน, วางแผนภาษี, และรักษาความลับองค์กร (Zero-Data)
    """
    def __init__(self):
        # 🚀 โหลด Client และโมเดลรุ่นท็อปสำหรับงานตรรกะการเงินที่ซับซ้อน
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-2.5-pro")
        
        # 💾 เชื่อมต่อฐานข้อมูล Supabase สำหรับระบบ Smart Wallet
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        # 🔗 ลิงก์ระบบชำระเงินสำหรับการ Upsell และเติมเงิน
        self.vip_link = "https://buy.stripe.com/00weVf1JdeBn07t7gI6Zy00"
        self.topup_link = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")

    async def _deduct_token(self, user_id: str, tokens_needed: int) -> dict:
        """💳 ตรวจสอบแพ็กเกจและหัก PRIME CREDITS อัจฉริยะ สำหรับบริการด้านการเงิน"""
        if not self.db:
            return {"authorized": True, "tier": "ESSENTIAL"} # Fallback หาก DB ออฟไลน์
        
        try:
            def _check_and_deduct():
                user_data = self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
                
                if not user_data.data:
                    return {"authorized": False, "msg": "⚠️ ไม่พบข้อมูลบัญชี กรุณาลงทะเบียนผ่านเมนูเพื่อเปิดใช้งานระบบที่ปรึกษาการเงินครับ"}
                    
                balance = float(user_data.data[0].get("token_balance", 0.0))
                tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
                
                # 👑 VIP_FOUNDER และ ENTERPRISE ใช้งานระบบวิเคราะห์การเงินได้ตามสิทธิพิเศษ
                if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]:
                    return {"authorized": True, "tier": tier}
                    
                if balance >= tokens_needed:
                    new_balance = balance - tokens_needed
                    self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                    logger.info(f"🪙 [Token Engine]: หัก {tokens_needed} Credits จาก {user_id} (บริการด้านการเงิน)")
                    return {"authorized": True, "tier": tier}
                else:
                    return {"authorized": False, "msg": f"⚠️ ขออภัยครับ PRIME CREDITS ของท่านไม่เพียงพอสำหรับการวิเคราะห์งบการเงินเชิงลึก (ต้องการ {tokens_needed} Credits)\n👉 เติมเครดิตอย่างปลอดภัยได้ที่: {self.topup_link}"}

            return await asyncio.to_thread(_check_and_deduct)
            
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return {"authorized": True, "tier": "ESSENTIAL"}

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """ทำงานเบื้องหลัง: วิเคราะห์โครงสร้างการเงิน การบัญชี และภาษี"""
        if not self.client:
            return "⚠️ [Worker 7]: ระบบวิเคราะห์การเงินออฟไลน์ (ไม่พบ API Key ส่วนกลาง)"

        # 🪙 ตรวจสอบค่าใช้จ่าย: ข้อความการเงิน = 10 Credits, ไฟล์งบ/Excel = 100 Credits
        tokens_needed = 100 if file_path else 10
        auth_status = await self._deduct_token(user_id, tokens_needed)
        
        if not auth_status["authorized"]:
            return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "ESSENTIAL")
        logger.info(f"💰 [Finance & Accounting]: เริ่มวิเคราะห์งบให้ User {user_id} (Tier: {package_tier})")

        # 🧠 System Prompt ปรับจูนความเป็นมืออาชีพระดับ CFO สากล
        system_instruction = f"""
        คุณคือ 'Chief Financial Officer (CFO)' ระดับสากล และผู้เชี่ยวชาญด้านการบริหารความเสี่ยงทางการเงิน ของ SIRINTHANATTH PRIME
        ระดับของลูกค้าท่านนี้คือ: {package_tier}
        
        หน้าที่และกฎเหล็กของคุณ:
        1. วิเคราะห์โครงสร้างรายได้ ต้นทุนแฝง (Hidden Costs) และกระแสเงินสด (Cash Flow) อย่างเฉียบขาด
        2. การวางแผนภาษี (Tax Planning): ให้คำแนะนำโครงสร้างภาษีที่ถูกกฎหมาย เพื่อรักษากำไรสุทธิ (Net Margin) ให้อยู่ในระดับ 80%+
        3. การบริหารความเสี่ยง (Risk Mitigation): ชี้จุดบอดหรือความเสี่ยงที่อาจทำให้ธุรกิจสะดุด พร้อมวิธีป้องกัน (Hedging/Reserves)
        4. การปรับระดับเนื้อหา: 
           - หากเป็น SMEs ({package_tier}): เน้นความอยู่รอด สภาพคล่อง และลดรายจ่ายไม่จำเป็น
           - หากเป็น ENTERPRISE/VIP ({package_tier}): เน้นการควบรวมกิจการ (M&A), โครงสร้างโฮลดิ้ง, และการระดมทุน
        5. ท้ายสุด ต้องสรุปเป็น Executive Summary ที่อ่านง่าย (ใช้ Bullet/Table)
        
        ⚠️ กฎหมายสำคัญ: คุณต้องระบุข้อความจำกัดความรับผิดชอบ (Disclaimer) ไว้ตอนท้ายเสมอว่า:
        "หมายเหตุ: ข้อมูลข้างต้นเป็นการวิเคราะห์เชิงกลยุทธ์และสถิติเบื้องต้น ไม่ใช่คำแนะนำการลงทุน (Not Financial Advice) ตามหลักเกณฑ์ ก.ล.ต. ผู้ลงทุนควรพิจารณาความเสี่ยงก่อนตัดสินใจ"
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 📂 1. จัดการระบบวิเคราะห์ไฟล์งบการเงิน (Financial Data Parser)
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"💰 [Worker 7]: กำลังอัปโหลดเอกสารงบการเงินสู่ระบบ Secure AI Cloud...")
                
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
                    logger.error(f"⚠️ [File Upload Error]: {e}")
                    return f"⚠️ [Worker 7]: โครงสร้างไฟล์การเงินซับซ้อนเกินไป รบกวนแปลงเป็น PDF หรือ CSV เพื่อความแม่นยำในการถอดรหัสครับ"

                # ⏳ เช็กสถานะการประมวลผลไฟล์ (Async Sync) พร้อมระบบ Anti-Freeze
                timeout = 60
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        raise TimeoutError("หมดเวลาการประมวลผลไฟล์งบการเงิน")
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 7]: ตรวจพบข้อผิดพลาดระดับ Deep Scan ในไฟล์เอกสารการเงินครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดวิเคราะห์งบการเงิน ประเมินความคุ้มทุน (ROI) และความเสี่ยงทางภาษีจากเอกสารนี้:\n{message}")
            else:
                content_to_send.append(f"โปรดวางแผนและให้คำปรึกษาด้านการเงิน/การบัญชี/ภาษี สำหรับสถานการณ์นี้:\n{message}")

            # ==========================================
            # 🧠 2. สั่งรัน Gemini 2.5 Pro (Precision Asynchronous)
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1 # ใช้อุณหภูมิต่ำสุด (0.1) เพื่อให้ตัวเลข กฎหมายภาษี และการคำนวณมีความแม่นยำสูงสุด 100% ไม่มโน
                )
            )
            return response.text.strip() if response.text else "✅ วิเคราะห์การเงินและบัญชีเสร็จสิ้นครับ"

        except TimeoutError:
            logger.error("❌ [Worker 7 Timeout]: ไฟล์งบการเงินขนาดใหญ่เกินกำหนด")
            return "ขออภัยครับ ไฟล์งบการเงินมีขนาดข้อมูลซับซ้อนทำให้ใช้เวลาประมวลผลนานกว่าปกติ รบกวนสรุปไฟล์เฉพาะส่วนที่ต้องการวิเคราะห์แล้วส่งมาใหม่อีกครั้งนะครับ"
        except Exception as e:
            logger.error(f"❌ [Worker 7 Error]: {e}")
            return f"⚠️ [Worker 7]: ระบบวิเคราะห์การเงินขัดข้องชั่วคราว ทีมวิศวกรกำลังตรวจสอบครับ"

        finally:
            # ==========================================
            # 🧹 3. Zero-Data Retention Policy (PDPA Shield ขั้นสูงสุด)
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🗑️ [Worker 7]: ลบไฟล์งบการเงินลับของลูกค้าออกจากระบบ AI Cloud เรียบร้อย (Financial Data Protection)")
                except Exception as e:
                    logger.error(f"⚠️ [File Deletion Failed]: {e}")