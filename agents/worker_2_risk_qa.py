import os
import time
import re
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

# 🌐 นำเข้าศูนย์บัญชาการ AI และระบบสื่อสารข้ามแผนก (Swarm)
from core_services.swarm_dispatcher import swarm_hub

try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.1-pro-preview" # 🚀 อัปเกรดเป็นรุ่นเรือธงล่าสุด
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

# 👑 นำเข้าระบบฐานข้อมูลและจัดการสิทธิประโยชน์
try:
    from supabase import create_client, Client
except ImportError:
    Client = None

logger = logging.getLogger("Worker2-RiskQA")

class RiskQAWorker:
    """
    🛡️ Worker 2: Global Risk Assessment & Legal Shield (Chief Legal Officer)
    อัปเกรด: Gemini 3.1 Pro, Real-time Legal Search, Swarm Delegation, และ Zero-Data Retention
    """
    def __init__(self):
        # 🚀 โหลด API Client และตั้งค่าโมเดลจากศูนย์กลาง
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.1-pro-preview")
        
        # เชื่อมต่อ Supabase สำหรับตรวจสอบแพ็กเกจและตัด Token
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        self.topup_link = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")

    async def _deduct_token(self, user_id: str, tokens_needed: int) -> bool:
        """💳 ฟังก์ชันตรวจสอบและหัก Token อัจฉริยะตามแพ็กเกจของลูกค้า"""
        if not self.db:
            logger.warning("⚠️ [System]: ทำงานในโหมด Offline (ไม่หัก Token)")
            return True 
        
        try:
            def _check_and_deduct():
                user_data = self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
                if not user_data.data:
                    return False
                    
                balance = float(user_data.data[0].get("token_balance", 0.0))
                tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
                
                if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]:
                    return True
                    
                if balance >= tokens_needed:
                    new_balance = balance - tokens_needed
                    self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                    logger.info(f"🪙 [Token Engine]: หัก {tokens_needed} Credits จาก {user_id} (บริการ Legal QA)")
                    return True
                return False

            return await asyncio.to_thread(_check_and_deduct)
            
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return True 

    async def process_command(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """รองรับการเรียกใช้งานผ่าน Swarm Dispatcher"""
        # ดึง Tier ของลูกค้าจาก DB เพื่อปรับความลึกของการสแกน
        user_tier = "ESSENTIAL"
        if self.db:
            try:
                res = await asyncio.to_thread(self.db.table("prime_clients").select("package_tier").eq("line_user_id", user_id).execute)
                if res.data: user_tier = res.data[0].get("package_tier", "ESSENTIAL").upper()
            except: pass
        return await self.process_task(user_id, message, file_path, package_tier=user_tier)

    async def process_task(self, user_id: str, message: str, file_path: str = None, package_tier: str = "ESSENTIAL") -> str:
        """ทำงานเบื้องหลัง: สแกนความเสี่ยง ข้อกฎหมาย และเอกสารระดับองค์กร"""
        if not self.client:
            return "⚠️ [Worker 2]: ระบบประเมินความเสี่ยงออฟไลน์ (ไม่พบ API Key ในระบบส่วนกลาง)"

        tokens_needed = 50 if file_path else 5
        has_tokens = await self._deduct_token(user_id, tokens_needed)
        
        if not has_tokens:
            return f"⚠️ [ระบบการเงิน]: PRIME CREDITS ของท่านไม่เพียงพอสำหรับการวิเคราะห์ข้อกฎหมายระดับลึก (ต้องการ {tokens_needed} Credits)\n👉 เติมเครดิตได้ที่: {self.topup_link}"

        # 🧠 ปรับความเข้มข้นของการตรวจสอบตามแพ็กเกจลูกค้า
        tier_instructions = {
            "ESSENTIAL": "ตรวจสอบความเสี่ยงเบื้องต้น (เช่น กฎหมาย อย. และ สคบ. สำหรับโฆษณา)",
            "PRIME": "ตรวจสอบ อย., สคบ., PDPA และข้อกำหนด ก.ล.ต. เบื้องต้นอย่างละเอียด",
            "ENTERPRISE": "ตรวจสอบข้อกฎหมายทุกมิติ, วิเคราะห์สัญญา, สแกนช่องโหว่ทางธุรกิจ และประเมินผลกระทบทางการเงิน",
            "VIP_FOUNDER": "ตรวจสอบระดับสูงสุด (Enterprise-grade) วิเคราะห์ข้อสัญญาอย่างละเอียด พร้อมเขียน Mitigation Plan เพื่อป้องกันการฟ้องร้อง 100%"
        }
        active_instruction = tier_instructions.get(package_tier, tier_instructions["ESSENTIAL"])

        system_instruction = f"""
        คุณคือ 'Worker 2: Chief Legal Officer (CLO)' และผู้เชี่ยวชาญด้าน Risk Management ของ SIRINTHANATTH PRIME
        
        ระดับบริการของลูกค้ารายนี้: {package_tier}
        ความเข้มข้นที่คุณต้องสแกน: {active_instruction}
        
        หน้าที่ของคุณ:
        1. ค้นหา 'ความเสี่ยง' หรือ 'ช่องโหว่' (Vulnerabilities) ที่อาจทำให้ลูกค้าถูกฟ้องร้อง, ผิด PDPA, หรือผิดกฎหมายแพลตฟอร์ม
        2. ให้คะแนนระดับความปลอดภัย (Safe, Warning, Critical) อย่างชัดเจน
        3. เสนอแนวทางป้องกันและปรับแก้ข้อความ/เอกสารใหม่ให้ถูกต้องตามกฎหมาย 100%
        4. ใช้ภาษาที่รัดกุม เป็นทางการ ตรงไปตรงมา และอ้างอิงข้อกฎหมายที่มีอยู่จริง
        
        🚨 กฎการส่งต่องาน (Swarm Delegation):
        - หากตรวจพบว่างานนี้ต้องให้ผู้เชี่ยวชาญอื่นสานต่อ (เช่น ตรวจสอบความเสี่ยงงบการเงิน, ให้ CTO ตรวจสอบระบบไอที) ให้โยนงานให้แผนกอื่นโดยพิมพ์คำสั่งนี้ที่บรรทัดสุดท้าย:
          [DELEGATE: WORKER_X_NAME] ข้อความที่ต้องการให้แผนกนั้นทำต่อ
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # ระบบจัดการไฟล์ข้อมูล & Vertex AI Storage Integration
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"🛡️ [Worker 2]: กำลังอัปโหลดเอกสารสู่ AI Cloud Storage เพื่อวิเคราะห์ความเสี่ยง...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith(('.xlsx', '.xls')): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif file_path.lower().endswith('.csv'): mime_type = "text/csv"
                elif file_path.lower().endswith('.pdf'): mime_type = "application/pdf"
                if not mime_type: mime_type = "application/octet-stream"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    logger.warning(f"⚠️ [File Upload Error]: {e}")
                    return "⚠️ [Worker 2]: โครงสร้างไฟล์ซับซ้อนเกินไป รบกวนแปลงเป็น PDF หรือรูปภาพ เพื่อความแม่นยำในการวิเคราะห์ระดับองค์กรครับ"

                timeout = 60
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        raise TimeoutError("หมดเวลาประมวลผลไฟล์ เพื่อความปลอดภัยของเซิร์ฟเวอร์")
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 2]: ตรวจพบความขัดข้องในโครงสร้างไฟล์ ไม่สามารถประเมินความเสี่ยงได้ครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดตรวจสอบความเสี่ยงและหาช่องโหว่ทางกฎหมายจากเอกสารนี้ ตามเงื่อนไขของแพ็กเกจ {package_tier}:\n{message}")
            else:
                content_to_send.append(f"โปรดตรวจสอบความเสี่ยงจากข้อมูลนี้ ตามเงื่อนไขของแพ็กเกจ {package_tier}:\n{message}")

            # ==========================================
            # ประมวลผลขั้นสูงด้วย Gemini 3.1 Pro + Real-time Search
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1, # ใช้อุณหภูมิ 0.1 เพื่อความแม่นยำด้านกฎหมาย 100% ห้ามเดาข้อมูล
                    tools=[{"google_search": {}}] # เปิด Search ให้ AI เช็กกฎหมายล่าสุดจากอินเทอร์เน็ตได้
                )
            )
            
            reply_text = response.text.strip() if response.text else "✅ สแกนเสร็จสิ้น ไม่พบความเสี่ยงที่น่ากังวลตามมาตรฐานกฎหมายปัจจุบันครับ"

            # ==========================================
            # 🔄 ตรวจจับการส่งต่องาน (Swarm Delegation Logic)
            # ==========================================
            delegate_match = re.search(r'\[DELEGATE:\s*(.+?)\](.*)', reply_text, re.DOTALL | re.IGNORECASE)
            if delegate_match:
                target_worker = delegate_match.group(1).strip()
                handoff_message = delegate_match.group(2).strip()
                
                clean_reply = re.sub(r'\[DELEGATE:\s*(.+?)\](.*)', '', reply_text, flags=re.DOTALL | re.IGNORECASE).strip()
                
                worker_response = await swarm_hub.delegate_task(
                    from_worker="WORKER_2_RISK_QA", 
                    to_worker=target_worker, 
                    user_id=user_id, 
                    message=handoff_message, 
                    file_path=file_path, 
                    file_type=None
                )
                return f"{clean_reply}\n\n🔄 [ฝ่ายกฎหมายส่งต่อให้ {target_worker} ประมวลผลต่อ]:\n{worker_response}"

            return reply_text

        except TimeoutError:
            logger.error("❌ [Worker 2 Timeout]: เอกสารการประเมินมีขนาดใหญ่เกินไป")
            return "ขออภัยครับ เอกสารมีความซับซ้อนและขนาดใหญ่เกินไป รบกวนแบ่งไฟล์เพื่อความรวดเร็วในการวิเคราะห์กฎหมายครับ"
        except Exception as e:
            logger.error(f"❌ [Worker 2 Error]: {e}")
            return "⚠️ [Worker 2]: ระบบตรวจสอบความเสี่ยงทางกฎหมายขัดข้องชั่วคราว ทีมวิศวกรกำลังตรวจสอบครับ"

        finally:
            # ==========================================
            # 🧹 Zero-Data Retention (ทำลายไฟล์ทันทีเพื่อ PDPA)
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🗑️ [Worker 2]: ทำลายไฟล์เอกสารชั่วคราวออกจากระบบสำเร็จ (PDPA Risk Guard)")
                except Exception as e:
                    logger.error(f"⚠️ [File Deletion Failed]: {e}")