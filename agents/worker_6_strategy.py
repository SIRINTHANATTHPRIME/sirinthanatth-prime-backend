import os
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

# 🌐 นำเข้าศูนย์บัญชาการ AI และฐานข้อมูล (รองรับ Zero Downtime Fallback)
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-2.5-pro"
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            return genai.Client(api_key=api_key) if api_key else None

try:
    from supabase import create_client, Client
except ImportError:
    Client = None

logger = logging.getLogger("Worker6-Strategy")

class MarketingStrategyWorker:
    """
    📈 Worker 6: Chief Marketing Officer (CMO) & Global Strategy Analyst
    อัปเกรด: [Gemini 2.5 Pro] ระบบวางแผน Full-Funnel, วิเคราะห์ธุรกิจเชิงลึก, และ Dynamic Upsell
    """
    def __init__(self):
        # 🚀 โหลด Client และโมเดลรุ่นท็อปสำหรับงานตรรกะซับซ้อน
        self.client = PrimeAIConfig.get_client()
        self.model_name = PrimeAIConfig.EXECUTIVE_MODEL
        
        # 💾 เชื่อมต่อฐานข้อมูล Supabase สำหรับระบบ Smart Wallet
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        # 🔗 ลิงก์ระบบชำระเงินสำหรับการ Upsell
        self.vip_link = "https://buy.stripe.com/00weVf1JdeBn07t7gI6Zy00"
        self.topup_link = "https://buy.stripe.com/YOUR_TOPUP_LINK" # เปลี่ยนเป็นลิงก์เติม Token ของคุณ

    async def _deduct_token(self, user_id: str, tokens_needed: int) -> dict:
        """💳 ตรวจสอบแพ็กเกจและหัก PRIME CREDITS อัจฉริยะ"""
        if not self.db:
            return {"authorized": True, "tier": "ESSENTIAL"} # Fallback หาก DB ออฟไลน์
        
        try:
            user_data = await asyncio.to_thread(
                lambda: self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
            )
            
            if not user_data.data:
                return {"authorized": False, "msg": "⚠️ ไม่พบข้อมูลบัญชี กรุณาลงทะเบียนผ่านเมนูเพื่อรับสิทธิ์ครับ"}
                
            balance = float(user_data.data[0].get("token_balance", 0.0))
            tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
            
            # 👑 VIP_FOUNDER และ ENTERPRISE ใช้งานระบบวิเคราะห์แผนธุรกิจได้ไม่จำกัด (หรือตามโควตา)
            if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]:
                return {"authorized": True, "tier": tier}
                
            if balance >= tokens_needed:
                new_balance = balance - tokens_needed
                await asyncio.to_thread(
                    lambda: self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                )
                logger.info(f"🪙 [Token Engine]: หัก {tokens_needed} Credits จาก {user_id}")
                return {"authorized": True, "tier": tier}
            else:
                return {"authorized": False, "msg": f"⚠️ ขออภัยครับ PRIME CREDITS ของท่านไม่เพียงพอสำหรับการวิเคราะห์กลยุทธ์เชิงลึก (ต้องการ {tokens_needed} Credits)\n👉 เติมเครดิตได้ที่: {self.topup_link}"}
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return {"authorized": True, "tier": "ESSENTIAL"}

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """ทำงานเบื้องหลัง: วิเคราะห์ยุทธศาสตร์ตลาดระดับโลก และ Dynamic Upsell"""
        if not self.client:
            return "⚠️ [Worker 6]: ระบบวิเคราะห์กลยุทธ์ออฟไลน์ (ไม่พบ API Key)"

        # 🪙 ตรวจสอบค่าใช้จ่าย: ข้อความ = 10 Credits, ไฟล์ Excel/PDF = 100 Credits
        tokens_needed = 100 if file_path else 10
        auth_status = await self._deduct_token(user_id, tokens_needed)
        
        if not auth_status["authorized"]:
            return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "ESSENTIAL")
        logger.info(f"📈 [Marketing Strategy]: วิเคราะห์แผนให้ User {user_id} (Tier: {package_tier})")

        # 🧠 System Prompt ปรับจูนตามระดับแพ็กเกจของลูกค้า
        system_instruction = f"""
        คุณคือ 'Chief Marketing Officer (CMO)' และสุดยอดที่ปรึกษากลยุทธ์ระดับโลก ของ SIRINTHANATTH PRIME
        ระดับของลูกค้าท่านนี้คือ: {package_tier}
        
        หน้าที่ของคุณ:
        1. วิเคราะห์แผนธุรกิจ โครงการลงทุน อสังหาริมทรัพย์ หรือกลยุทธ์การตลาด (Full-Funnel) อย่างเฉียบขาด
        2. หากลูกค้าเป็น {package_tier} (SMEs): เน้นกลยุทธ์สร้างยอดขายเร็ว ROI สูง งบประมาณต่ำ
        3. หากลูกค้าเป็น ENTERPRISE / VIP: เน้นกลยุทธ์ระดับ Global Scaling, การควบรวมกิจการ, และ Big Data
        4. ใช้ Business Frameworks ระดับโลก (เช่น SWOT, 4Ps, Blue Ocean) นำเสนอแบบ Executive Summary (สั้น กระชับ ทรงพลัง)
        
        💎 กฎเหล็กการทำ Dynamic Upsell (ปิดการขายอัตโนมัติ):
        - ท้ายบทวิเคราะห์ ให้เสนอขายบริการของ SIRINTHANATTH PRIME ที่ตรงกับบริบทอย่างเนียนที่สุด 1 อย่าง
        - หากลูกค้าต้องทำคอนเทนต์: เสนอ "บริการผลิตวิดีโอ 4K สไตล์ Cinematic และพากย์เสียง AI"
        - หากลูกค้าต้องการลดต้นทุน/ขยายสเกล: เสนอ "สมัคร 100 VIP Founders (4,490 บาท/ปี ล็อกราคาตลอดชีพ) รับ 49,000 Tokens" พร้อมแนบลิงก์: {self.vip_link}
        - ให้เขียนในเชิง "แนะนำเพื่อนนักธุรกิจ" ไม่ใช่ยัดเยียดขาย
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 📂 1. จัดการระบบวิเคราะห์ไฟล์ (Business Plan Parser)
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"♟️ [Worker 6]: กำลังอัปโหลดเอกสารแผนงานสู่ระบบ Secure Cloud...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith('.xlsx'): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif file_path.lower().endswith('.xls'): mime_type = "application/vnd.ms-excel"
                elif file_path.lower().endswith('.csv'): mime_type = "text/csv"
                if not mime_type: mime_type = "application/octet-stream"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    return f"⚠️ [Worker 6]: โครงสร้างไฟล์แผนงานมีความซับซ้อนเกินไป รบกวนแปลงเป็น PDF เพื่อความแม่นยำในการวิเคราะห์ครับ"

                # ⏳ เช็กสถานะการประมวลผลไฟล์ (Async Sync)
                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 6]: ตรวจพบข้อผิดพลาดระดับ Deep Scan ในไฟล์เอกสารครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดวิเคราะห์ยุทธศาสตร์ แผนการเงิน/การตลาด จากเอกสารนี้: {message}")
            else:
                content_to_send.append(f"โปรดวิเคราะห์และวางกลยุทธ์การตลาดระดับโลกสำหรับสถานการณ์นี้: {message}")

            # ==========================================
            # 🧠 2. สั่งรัน Gemini 2.5 Pro (Asynchronous)
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3 # อุณหภูมิต่ำเพื่อเน้นตรรกะธุรกิจที่เฉียบคมและใช้งานได้จริง
                )
            )
            return response.text if response.text else "✅ วิเคราะห์แผนกลยุทธ์และการตลาดเสร็จสิ้นครับ"

        except Exception as e:
            logger.error(f"❌ [Worker 6 Error]: {e}")
            return f"⚠️ [Worker 6]: ระบบวิเคราะห์กลยุทธ์ขัดข้องชั่วคราว ทีมวิศวกรกำลังตรวจสอบครับ (Error: {str(e)[:50]})"

        finally:
            # ==========================================
            # 🧹 3. Zero-Data Retention Policy (PDPA Shield)
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🗑️ [Worker 6]: ลบไฟล์ลับทางธุรกิจออกจากระบบเรียบร้อย (Data Protection)")
                except:
                    pass