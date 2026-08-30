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
        EXECUTIVE_MODEL = "gemini-2.5-pro" # 🚀 อัปเกรดเป็นรุ่นเรือธงอัจฉริยะที่สุดสำหรับ Big Data
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

logger = logging.getLogger("Worker10-Enterprise")

class EnterprisePartnerWorker:
    """
    🏢 Worker 10: Executive Enterprise Partner & Big Data Architect
    อัปเกรด: Vertex AI (Gemini 2.5 Pro), ระบบจัดการข้อมูลองค์กรระดับมหาภาค, คลังสินค้า และ Zero-Trust Security
    """
    def __init__(self):
        # 🚀 โหลด Client และโมเดลรุ่นท็อป
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-2.5-pro")
        
        # เชื่อมต่อ Supabase สำหรับตรวจสอบแพ็กเกจและ Token
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        # 🔗 ลิงก์สำหรับระบบชำระเงิน
        self.topup_link = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")
        self.enterprise_upgrade_m = "https://buy.stripe.com/eVqeVf2Nh1OBaM7eJa6Zy04" # 4,900 / เดือน
        self.enterprise_upgrade_y = "https://buy.stripe.com/bJe9AVfA3ctf2fB0Sk6Zy05" # 39,900 / ปี (ประหยัด 20%)

    async def _check_tier_and_deduct_token(self, user_id: str, tokens_needed: int) -> dict:
        """💳 ตรวจสอบสิทธิ์ระดับองค์กร (ENTERPRISE) และหักเครดิตอย่างชาญฉลาด"""
        if not self.db:
            return {"authorized": True, "tier": "ENTERPRISE"} # Fallback โหมด Offline
        
        try:
            def _check_and_deduct():
                user_data = self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
                
                if not user_data.data:
                    return {"authorized": False, "msg": "⚠️ ขออภัยครับ ไม่พบข้อมูลบัญชีองค์กรของท่านในระบบ กรุณาติดต่อทีมงานครับ"}
                    
                balance = float(user_data.data[0].get("token_balance", 0.0))
                tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
                
                # 🛡️ ตรวจสอบสิทธิ์: สงวนสิทธิ์เฉพาะ ENTERPRISE, VIP_FOUNDER และ ADMIN
                if tier not in ["ENTERPRISE", "VIP_FOUNDER", "VIP", "ADMIN"]:
                    # 🧠 จิตวิทยาการ Upsell: ทำให้รู้สึกถึงความเหนือระดับ และเสนอแพ็กเกจที่คุ้มค่า
                    upsell_msg = (
                        f"🏢 [Enterprise Exclusive]: ท่านผู้บริหารครับ ระบบวิเคราะห์ข้อมูลตลาด Real-time และการจัดการ Big Data/คลังสินค้า "
                        f"เป็นฟีเจอร์ระดับเอ็กซ์คลูซีฟที่สงวนสิทธิ์เฉพาะแพ็กเกจ **'พันธมิตรองค์กร (ENTERPRISE)'** ขึ้นไปเท่านั้นครับ\n\n"
                        f"💡 เพื่อปกป้องแบรนด์ของคุณและยกระดับระบบหลังบ้านด้วยทีมวิศวกร AI ของเรา ขออนุญาตเรียนเชิญอัปเกรดแพ็กเกจครับ:\n"
                        f"🔹 รายเดือน (4,900 ฿): {self.enterprise_upgrade_m}\n"
                        f"⭐ รายปีสุดคุ้ม (39,900 ฿ - ประหยัด 20%): {self.enterprise_upgrade_y}"
                    )
                    return {"authorized": False, "msg": upsell_msg}
                
                # 👑 VIP_FOUNDER และ ADMIN ใช้งานได้ไร้ขีดจำกัด
                if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]:
                    return {"authorized": True, "tier": tier}
                    
                if balance >= tokens_needed:
                    new_balance = balance - tokens_needed
                    self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                    logger.info(f"🪙 [Enterprise Token Engine]: หัก {tokens_needed} Credits จาก {user_id}. คงเหลือ {new_balance}")
                    return {"authorized": True, "tier": tier}
                else:
                    # 🧠 จิตวิทยาการแจ้งเตือนเติมเงิน (Psychological Top-up) สำหรับระดับองค์กร
                    psychological_topup = (
                        f"🏢 เรียนท่านผู้บริหาร ระบบตรวจพบว่า 'PRIME CREDITS' ใน Smart Wallet ขององค์กรท่านใกล้หมดแล้วครับ "
                        f"(ปริมาณ Data ชุดนี้ต้องการ {tokens_needed} เครดิตในการประมวลผล)\n\n"
                        f"⚡ เพื่อไม่ให้การวิเคราะห์ข้อมูล Real-time และการจัดการคลังสินค้าของท่านหยุดชะงัก "
                        f"ท่านสามารถให้ฝ่ายบัญชีเติมเครดิตเข้าสู่ระบบองค์กรได้ทันทีผ่านลิงก์นี้ครับ:\n"
                        f"👉 {self.topup_link}"
                    )
                    return {"authorized": False, "msg": psychological_topup}

            return await asyncio.to_thread(_check_and_deduct)
                
        except Exception as e:
            logger.error(f"❌ [Enterprise Token Error]: {e}")
            return {"authorized": True, "tier": "ENTERPRISE"}

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """ทำงานเบื้องหลัง: วิเคราะห์ Big Data, วางแผน Supply Chain และ Whitelisting"""
        if not self.client:
            return "⚠️ [Worker 10]: ระบบพันธมิตรองค์กรออฟไลน์ (ไม่พบ API Key)"

        # 🪙 ตรวจสอบค่าใช้จ่าย: ถามกลยุทธ์องค์กร = 50 Credits, ย่อยไฟล์ Big Data/คลังสินค้า = 300 Credits
        tokens_needed = 300 if file_path else 50
        auth_status = await self._check_tier_and_deduct_token(user_id, tokens_needed)
        
        if not auth_status["authorized"]:
            return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "ENTERPRISE")
        logger.info(f"🏢 [Enterprise Analytics]: เริ่มกระบวนการระดับภาคอุตสาหกรรมให้ User {user_id}...")

        # 🧠 System Prompt สวมวิญญาณ Enterprise Architect ระดับโลก
        system_instruction = f"""
        คุณคือ 'Chief Data Officer' และ 'Enterprise Security Architect' ระดับโลก ของ SIRINTHANATTH PRIME
        ลูกค้าท่านนี้คือพันธมิตรองค์กรระดับ: {package_tier}
        
        หน้าที่ของคุณ (Enterprise Solutions):
        1. 📊 Big Data & Supply Chain: วิเคราะห์ข้อมูลคลังสินค้า (Inventory), การพยากรณ์อุปสงค์ (Demand Forecasting) และข้อมูลตลาดแบบ Real-time
        2. 🛡️ Brand Protection & Whitelisting: วางแผนกลยุทธ์การปกป้องแบรนด์ การจัดการลิขสิทธิ์ และความปลอดภัยระดับองค์กร (Zero-Trust Security)
        3. ⚙️ Automation Integration: เสนอโครงสร้างการเชื่อมต่อ API, ERP, หรือ CRM เพื่อให้ระบบของลูกค้าทำงานร่วมกับ AI ได้อัตโนมัติ
        
        รูปแบบการตอบกลับ:
        - ภาษาระดับ Corporate Executive (ใช้ศัพท์เทคนิคทางธุรกิจและ IT ได้อย่างแม่นยำ)
        - โครงสร้างต้องชัดเจน มีการสรุปเป็น Action Plan (สิ่งที่ต้องทำทันที, ระยะกลาง, ระยะยาว)
        - คำนึงถึง "กฎหมาย", "ความเสี่ยงทางธุรกิจ", และ "ความคุ้มค่า (ROI)" เสมอ
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 📂 1. จัดการอัปโหลดไฟล์ (Big Data, CSV, SQL, JSON)
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"🏢 [Worker 10]: กำลังอัปโหลด Big Data เข้าสู่ Secure Cloud เพื่อทำการ Data Mining...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith(('.csv', '.json', '.xml', '.sql')): 
                    mime_type = "text/plain" # ไฟล์ Data ดิบ
                elif file_path.lower().endswith('.xlsx'): 
                    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                if not mime_type: 
                    mime_type = "application/octet-stream"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    logger.error(f"⚠️ [File Upload Error]: {e}")
                    return f"⚠️ [Enterprise Analytics]: โครงสร้าง Database File ซับซ้อนเกินไป รบกวนส่งเป็นไฟล์ .csv, .json หรือ .xlsx ครับ"

                # ⏳ Async Sync รอ Google วิเคราะห์ Big Data (ระบบ Anti-Freeze Timeout 60s)
                timeout = 60
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        raise TimeoutError("หมดเวลาการประมวลผลฐานข้อมูล (Timeout)")
                    await asyncio.sleep(3)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Enterprise Analytics]: เกิดข้อผิดพลาดในการทำ Data Mining ระดับลึกในไฟล์ครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดทำการวิเคราะห์ Big Data / คลังสินค้า จากฐานข้อมูลนี้:\n{message}")
            else:
                content_to_send.append(f"โปรดให้คำปรึกษาระดับองค์กร/Supply Chain สำหรับประเด็นนี้:\n{message}")

            # ==========================================
            # 🧠 2. สั่งรัน Gemini 2.5 Pro (Precision Search Grounding)
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1, # ใช้อุณหภูมิต่ำสุด (0.1) เพื่อความถูกต้องของตัวเลข สถิติ และความปลอดภัย 100%
                    tools=[{"google_search": {}}] # เปิดใช้งาน Search เพื่อให้ AI ดึงข้อมูลเศรษฐกิจและ Supply Chain ล่าสุด
                )
            )
            
            return response.text.strip() if response.text else "🏢 การวิเคราะห์ข้อมูลระดับองค์กรและคลังสินค้า เสร็จสมบูรณ์ครับ"

        except TimeoutError:
            logger.error("❌ [Worker 10 Timeout]: ฐานข้อมูล Big Data มีขนาดใหญ่เกินไป")
            return "ขออภัยครับท่านผู้บริหาร ฐานข้อมูลมีขนาดใหญ่ทำให้ใช้เวลา Data Mining นานกว่าปกติ รบกวนส่งไฟล์ชุดข้อมูลที่เล็กลงมาใหม่อีกครั้งครับ"
        except Exception as e:
            logger.error(f"❌ [Worker 10 Error]: {e}")
            return f"⚠️ [Enterprise Analytics]: ระบบฐานข้อมูลองค์กรขัดข้องชั่วคราว ทีมวิศวกรกำลังตรวจสอบครับ"

        finally:
            # ==========================================
            # 🧹 3. Zero-Data Retention Policy (Military-Grade Cyber Shield)
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🛡️ [Zero-Trust Security]: ทำลายฐานข้อมูลลับขององค์กรลูกค้าออกจากระบบทันที (Data Wiped)")
                except Exception as e:
                    logger.error(f"⚠️ [File Deletion Failed]: {e}")