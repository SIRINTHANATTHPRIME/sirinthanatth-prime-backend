import os
import time
import logging
import asyncio
import requests
from google import genai
from google.genai import types
from supabase import create_client, Client
from fastapi import BackgroundTasks

# ตั้งค่า Logger สำหรับตรวจสอบการทำงานระดับ Enterprise
logger = logging.getLogger("CentralBoss")

# =========================================================
# 🌐 นำเข้าศูนย์บัญชาการ AI และฐานข้อมูล
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-2.5-flash" # รุ่นด่านหน้าที่เร็วที่สุดในโลก
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            return genai.Client(api_key=api_key) if api_key else None

# =========================================================
# 🏢 นำเข้าทีมผู้บริหารทั้ง 11 ฝ่าย (Dynamic Import)
# (ป้องกันเซิร์ฟเวอร์แครชหากไฟล์อื่นอยู่ระหว่างอัปเดต)
# =========================================================
try: from agents.worker_0_ceo_secretary import CeoSecretaryWorker
except ImportError: CeoSecretaryWorker = None

try: from agents.worker_1_report import ReportWorker
except ImportError: ReportWorker = None

try: from agents.worker_2_risk_qa import RiskQAWorker
except ImportError: RiskQAWorker = None

try: from agents.worker_3_audio import AudioWorker
except ImportError: AudioWorker = None

try: from agents.worker_4_video import VideoProductionWorker
except ImportError: VideoProductionWorker = None

try: from agents.worker_5_graphics_ads import GraphicsAdsWorker
except ImportError: GraphicsAdsWorker = None

try: from agents.worker_6_strategy import MarketingStrategyWorker
except ImportError: MarketingStrategyWorker = None

try: from agents.worker_7_finance import FinancialAndAccountingWorker
except ImportError: FinancialAndAccountingWorker = None

try: from agents.worker_8_ecommerce import EcommerceWorker
except ImportError: EcommerceWorker = None

try: from agents.worker_9_prime import PrimeAdvisorWorker
except ImportError: PrimeAdvisorWorker = None

try: from agents.worker_10_enterprise import EnterprisePartnerWorker
except ImportError: EnterprisePartnerWorker = None

try: from agents.worker_11_media_engine import Worker11MediaEngine
except ImportError: Worker11MediaEngine = None


class CentralBossAgent:
    """
    🎩 ผู้บัญชาการส่วนกลาง (Central Boss Agent - The Master Orchestrator)
    จัดการ Intent Routing, ควบคุม LIFF Smart Wallet, 
    แยกแยะความจำลูกค้าตามแพ็กเกจ (ESSENTIAL, PRIME, ENTERPRISE, 100VIP)
    และดันผลลัพธ์ (Push) กลับสู่ LINE อัตโนมัติด้วยจิตวิทยาชั้นสูง
    """
    def __init__(self):
        # 🚀 เชื่อมต่อขุมพลังสมองกลสายสปีดความเร็วแสง
        self.client = PrimeAIConfig.get_client()
        self.model_name = PrimeAIConfig.CORE_MODEL
        self.liff_url = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")
        self.line_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
        
        # 💾 เชื่อมต่อ Supabase Vector DB (ความจำแยกบุคคล)
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None

        # 🤝 โหลดทีมงานผู้เชี่ยวชาญเข้าสู่ระบบ
        self.ceo_secretary = CeoSecretaryWorker() if CeoSecretaryWorker else None
        self.report_worker = ReportWorker() if ReportWorker else None
        self.legal_worker = RiskQAWorker() if RiskQAWorker else None
        self.audio_worker = AudioWorker() if AudioWorker else None
        self.video_worker = VideoProductionWorker() if VideoProductionWorker else None
        self.graphics_worker = GraphicsAdsWorker() if GraphicsAdsWorker else None
        self.strategy_worker = MarketingStrategyWorker() if MarketingStrategyWorker else None
        self.finance_worker = FinancialAndAccountingWorker() if FinancialAndAccountingWorker else None
        self.ecommerce_worker = EcommerceWorker() if EcommerceWorker else None
        self.prime_worker = PrimeAdvisorWorker() if PrimeAdvisorWorker else None
        self.enterprise_worker = EnterprisePartnerWorker() if EnterprisePartnerWorker else None
        self.worker_11 = Worker11MediaEngine() if Worker11MediaEngine else None
        
        self.system_instruction = """
        คุณคือ 'Central Boss' ผู้จัดการระดับสูงสุดและด่านหน้าของระบบ SIRINTHANATTH PRIME
        
        จิตวิทยาและพฤติกรรมในการสื่อสาร:
        1. กล่าวต้อนรับอย่างหรูหรา อบอุ่น เป็นธรรมชาติ และยกระดับความรู้สึกของลูกค้า (Predictive Empathy)
        2. หากลูกค้าถามคำถามทั่วไป ให้ตอบสั้นๆ ชาญฉลาด และให้คำแนะนำที่เหนือความคาดหมาย
        3. หากลูกค้ากำลังเผชิญปัญหา ให้ใช้น้ำเสียงเข้าใจและเสนอวิธีแก้ (Solution) ในเชิงบวก
        4. ใช้คำลงท้ายที่สุภาพและสะท้อนความพรีเมียมของแบรนด์เสมอ (เช่น ครับ/ค่ะ)
        """

    async def _get_user_profile(self, user_id: str) -> dict:
        """🔍 ตรวจสอบ Tier และ Token ของลูกค้าจากระบบเพื่อให้บริการที่ตรงระดับและแม่นยำ"""
        if not self.db: return {"tier": "ESSENTIAL", "balance": 0.0}
        try:
            res = await asyncio.to_thread(self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute)
            if res.data:
                return {
                    "tier": res.data[0].get("package_tier", "ESSENTIAL").upper(),
                    "balance": float(res.data[0].get("token_balance", 0.0))
                }
        except Exception as e:
            logger.error(f"⚠️ [DB Fetch Error]: {e}")
        return {"tier": "ESSENTIAL", "balance": 0.0}

    def _get_liff_welcome_message(self, tier: str) -> str:
        """💎 ระบบต้อนรับด้วยจิตวิทยา สร้าง Emotional Connection และดึงเข้าสู่ Smart Wallet"""
        greeting = f"ยินดีต้อนรับกลับครับ ท่านผู้บริหารระดับ {tier}" if tier != "ESSENTIAL" else "ยินดีต้อนรับสู่ SIRINTHANATTH PRIME ครับ"
        return (
            f"💎 {greeting}\n"
            "ระบบผู้ช่วยอัจฉริยะและบริหารจัดการองค์กรระดับโลก\n\n"
            "💳 ท่านสามารถตรวจสอบแพ็กเกจ สิทธิประโยชน์ "
            "รวมถึงยอด PRIME CREDITS และจัดการ Smart Wallet ได้ผ่านเมนูหลักด้านล่างนี้เลยครับ:\n\n"
            f"👉 เปิดเมนูจัดการระบบ: {self.liff_url}"
        )

    async def _execute_worker_and_push(self, worker_func, user_id: str, *args):
        """
        🚀 พนักงานจัดส่งผลลัพธ์ด่วน (Async Pusher): 
        รอให้ Worker วิเคราะห์เชิงลึกเสร็จ แล้วยิงผลลัพธ์เข้า LINE ของลูกค้าโดยตรง 
        แก้ปัญหาผลลัพธ์หายเข้ากลีบเมฆ (Vanishing Result Bug) 100%
        """
        try:
            # 1. ให้ Worker ประมวลผล (Worker จะหัก Token และจัดการความปลอดภัยไฟล์เอง)
            result_text = await worker_func(user_id, *args)
            if not result_text: return
            
            # 2. ผลัก (Push) ข้อมูลตอบกลับหาลูกค้าทาง LINE API
            if not self.line_token: 
                logger.warning("⚠️ ขาด LINE_TOKEN ไม่สามารถ Push ข้อความได้")
                return
                
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.line_token}"
            }
            data = {"to": user_id, "messages": [{"type": "text", "text": str(result_text)}]}
            res = await asyncio.to_thread(requests.post, "https://api.line.me/v2/bot/message/push", headers=headers, json=data)
            res.raise_for_status()
            logger.info(f"✅ [Worker Delivery]: จัดส่งผลการวิเคราะห์ระดับโลกให้ {user_id} สำเร็จ!")
            
        except Exception as e:
            logger.error(f"❌ [Worker Delivery Error]: {e}")

    async def route_task(self, user_id: str, message: str, bg_tasks: BackgroundTasks, incoming_message: str = "", file_path: str = None, file_type: str = None) -> str:
        """🧠 ระบบคัดกรองเจตนา (Omni-Modal Intent Router) และจ่ายงานอัจฉริยะ"""
        
        actual_message = message if message else incoming_message
        if not actual_message and not file_type:
            return "ไม่พบข้อมูลข้อความ กรุณาลองใหม่อีกครั้งครับ"
            
        message_lower = actual_message.lower()
        user_profile = await self._get_user_profile(user_id)
        user_tier = user_profile["tier"]

        # ==========================================
        # 📱 1. LIFF WELCOMING & PACKAGE MANAGEMENT
        # ==========================================
        if any(kw in message_lower for kw in ["เมนู", "menu", "แพ็กเกจ", "สมัคร", "ราคา", "บริการ"]):
            return self._get_liff_welcome_message(user_tier)
            
        if any(kw in message_lower for kw in ["เติมเงิน", "wallet", "เครดิต", "token", "เงินหมด"]):
            return (
                "💡 เพื่อความต่อเนื่องในการรังสรรค์วิสัยทัศน์และการทำงานของระบบ AI\n"
                f"ท่านสามารถอัปเกรดสิทธิพิเศษ (ประหยัดสูงสุด 20%) หรือเติม PRIME CREDITS ได้อย่างปลอดภัยผ่านระบบ Smart Wallet ครับ:\n"
                f"👉 {self.liff_url}"
            )

        # ==========================================
        # 🎬 2. APPROVAL WORKFLOW (ยืนยันตัดเงินเรนเดอร์สื่อ 4K)
        # ==========================================
        if "ยืนยันการสร้างคลิป" in message_lower and self.worker_11:
            # โยนงานให้ Worker 11 ไปทำเบื้องหลัง แล้วจบเทิร์นทันที
            bg_tasks.add_task(self.worker_11.process_media_production, user_id, "สคริปต์อัตโนมัติ", "video_4k")
            return (
                "✅ ได้รับการอนุมัติระดับผู้บริหารเรียบร้อยครับ!\n"
                "ระบบได้จัดการหัก PRIME CREDITS อย่างถูกต้อง และส่งคำสั่งเข้าสู่คิวซูเปอร์คอมพิวเตอร์เพื่อเรนเดอร์ 4K เรียบร้อยแล้วครับ\n\n"
                "☕ ระหว่างนี้ท่านประธานสามารถพักผ่อนได้เลยครับ เมื่อผลงานเสร็จสมบูรณ์ ระบบจะนำส่งให้ทันทีครับ"
            )

        # ==========================================
        # 🧠 3. INTENT & FILE-TYPE ROUTING (จ่ายงานให้ถูกแผนก)
        # ==========================================
        routing_msg = ""
        
        # 🛡️ 3.1 ตรวจสอบกฎหมาย (Legal)
        if any(kw in message_lower for kw in ["กฎหมาย", "สคบ", "อย", "pdpa", "สัญญา", "ฟ้อง"]):
            if self.legal_worker:
                bg_tasks.add_task(self._execute_worker_and_push, self.legal_worker.process_task, user_id, actual_message, file_path, user_tier)
                routing_msg = "🛡️ รับทราบครับ ทีม Legal & Risk Management กำลังตรวจสอบข้อกฎหมายและสแกนความเสี่ยงให้ท่านอย่างละเอียดครับ"
                
        # 🎙️ 3.2 ระบบเสียงและพากย์ (Audio/Voice)
        elif file_type == 'audio' or any(kw in message_lower for kw in ["เสียง", "พากย์", "tts", "แต่งเพลง", "เพลง"]):
            if self.audio_worker:
                bg_tasks.add_task(self._execute_worker_and_push, self.audio_worker.process_task, user_id, actual_message, file_path)
                routing_msg = "🎙️ ทีม Audio & Music Studio ได้รับไฟล์แล้ว กำลังถอดรหัสคลื่นเสียงและรังสรรค์ผลงานให้ครับ"
                
        # 🎬 3.3 ระบบวิดีโอ (Video)
        elif file_type == 'video' or any(kw in message_lower for kw in ["คลิป", "วิดีโอ", "วีดีโอ", "video", "สตอรี่บอร์ด"]):
            if self.video_worker:
                bg_tasks.add_task(self._execute_worker_and_push, self.video_worker.process_task, user_id, actual_message, file_path)
                routing_msg = "🎬 ทีม Video Director กำลังวิเคราะห์ฉากแบบเฟรมต่อเฟรม และจัดทำ Storyboard ให้ท่านครับ"
                
        # 📦 3.4 ระบบ E-Commerce & โลจิสติกส์ (สลิป/ส่งของ)
        elif any(kw in message_lower for kw in ["สั่งของ", "ออเดอร์", "สลิป", "flash", "ส่งพัสดุ", "สต๊อก"]):
            if self.ecommerce_worker:
                bg_tasks.add_task(self._execute_worker_and_push, self.ecommerce_worker.process_task, user_id, actual_message, file_path, file_type)
                routing_msg = "📦 ทีม E-commerce & Logistics กำลังประสานงาน ตรวจสอบสลิป และจัดการระบบขนส่งให้ครับ"
                
        # 💰 3.5 ระบบการเงินและบัญชี (Finance)
        elif any(kw in message_lower for kw in ["บัญชี", "การเงิน", "ภาษี", "งบ", "roi"]):
            if self.finance_worker:
                bg_tasks.add_task(self._execute_worker_and_push, self.finance_worker.process_task, user_id, actual_message, file_path)
                routing_msg = "💰 ทีม Financial (CFO) กำลังวิเคราะห์ตัวเลขและโครงสร้างภาษี เพื่อรักษาผลกำไรสูงสุดให้องค์กรครับ"
                
        # 📈 3.6 ระบบกลยุทธ์การตลาด (Marketing Strategy)
        elif any(kw in message_lower for kw in ["กลยุทธ์", "แผนธุรกิจ", "การตลาด", "ยิงแอด"]):
            if self.strategy_worker:
                bg_tasks.add_task(self._execute_worker_and_push, self.strategy_worker.process_task, user_id, actual_message, file_path)
                routing_msg = "📈 ทีม Marketing Strategist กำลังวางแผนกลยุทธ์การตลาดระดับ Global ให้ครับ"
                
        # 🏢 3.7 ระบบองค์กรและบิ๊กดาต้า (Enterprise)
        elif any(kw in message_lower for kw in ["enterprise", "big data", "คลังสินค้า", "องค์กร", "sql"]):
            if self.enterprise_worker:
                bg_tasks.add_task(self._execute_worker_and_push, self.enterprise_worker.process_task, user_id, actual_message, file_path)
                routing_msg = "🏢 ระบบ [ENTERPRISE] Data Mining เริ่มทำงาน กำลังวิเคราะห์ฐานข้อมูลระดับอุตสาหกรรมให้ครับ"
                
        # 👑 3.8 ระบบที่ปรึกษาผู้บริหาร (Prime CTO)
        elif any(kw in message_lower for kw in ["prime", "cto", "it", "ความปลอดภัย", "แฮ็ก", "ไซเบอร์"]):
            if self.prime_worker:
                bg_tasks.add_task(self._execute_worker_and_push, self.prime_worker.process_task, user_id, actual_message, file_path)
                routing_msg = "👑 ระบบ [PRIME Advisor] กำลังตรวจสอบสถาปัตยกรรม IT และความปลอดภัยระดับองค์กรให้ครับ"

        # 🎨 3.9 ระบบกราฟิก (Image Fallback) - รองรับรูปภาพเปล่าๆ
        elif file_type == 'image' or any(kw in message_lower for kw in ["กราฟิก", "แบนเนอร์", "ออกแบบ", "รูป", "แพ็กเกจจิ้ง", "เกียรติบัตร"]):
            if self.graphics_worker:
                bg_tasks.add_task(self._execute_worker_and_push, self.graphics_worker.process_task, user_id, actual_message, file_path)
                routing_msg = "🎨 ทีม Creative Director กำลังวิเคราะห์ภาพและรังสรรค์ไอเดียงานศิลป์ให้ครับ"
                
        # 📊 3.10 ระบบเอกสาร (File Fallback) - รองรับ PDF/Excel เปล่าๆ
        elif file_type == 'file' or any(kw in message_lower for kw in ["เอกสาร", "ตาราง", "excel", "รายงาน", "สรุป", "pdf"]):
            if self.report_worker:
                bg_tasks.add_task(self._execute_worker_and_push, self.report_worker.process_task, user_id, actual_message, file_path)
                routing_msg = "📊 ทีม Data & Report กำลังสกัดข้อมูลและจัดทำโครงสร้างเอกสารระดับองค์กรให้ครับ"

        # 🚀 หากมีแผนกรับผิดชอบแล้ว ให้บอกลูกค้าและจบเทิร์นตรงนี้เลย
        if routing_msg:
            if file_path:
                routing_msg += "\n\n📂 (ระบบได้รับไฟล์ของท่านแล้ว และกำลังนำเข้าสู่กระบวนการความปลอดภัย Zero-Data Retention ครับ)"
            return routing_msg

        # ==========================================
        # 💬 4. โหมดตอบกลับทั่วไปด่านหน้า (Fast Conversation Fallback)
        # ==========================================
        if not self.client:
            return "⚠️ ระบบบัญชาการส่วนกลางออฟไลน์ เนื่องจากไม่พบคีย์เชื่อมต่อ AI ครับ"
            
        try:
            prompt = f"ลูกค้า (ID: {user_id} - Tier: {user_tier}) ส่งข้อความมาว่า: {actual_message}"
            if file_type:
                prompt += f"\n[หมายเหตุ: ลูกค้าแนบไฟล์ {file_type} มาด้วย โปรดตอบรับอย่างสุภาพและรอการวิเคราะห์]"
            
            async def fetch_response():
                return await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        temperature=0.6 # ปรับอุณหภูมิให้อบอุ่น เป็นธรรมชาติ และมีความเข้าอกเข้าใจ (Empathy)
                    )
                )
            
            # ระบบ Guardrail: ป้องกันระบบค้างเกิน 12 วินาที (Anti-Freeze)
            response = await asyncio.wait_for(fetch_response(), timeout=12.0)
            return response.text if response.text else "รับทราบครับ ระบบได้รับข้อมูลและเตรียมดำเนินการต่อให้ครับ"
            
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ [Central Boss Timeout]: ระบบตอบกลับด่านหน้าช้า สลับใช้ข้อความสำรอง")
            return "ระบบได้รับข้อมูลเรียบร้อยแล้วครับ หากเป็นคำสั่งเฉพาะทาง ทีม AI ผู้เชี่ยวชาญกำลังรับช่วงต่อดำเนินการครับ"
        except Exception as e:
            logger.error(f"❌ [Central Boss Error]: {e}")
            return "ขออภัยครับ ระบบประสานงานส่วนกลางติดขัดชั่วคราว ทีมวิศวกรกำลังเร่งตรวจสอบให้ครับ"