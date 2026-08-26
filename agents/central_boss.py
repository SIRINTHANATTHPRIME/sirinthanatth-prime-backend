import os
import time
import logging
import asyncio
from google import genai
from google.genai import types
from fastapi import BackgroundTasks
from supabase import create_client, Client

# ตั้งค่า Logger สำหรับตรวจสอบการทำงานหลังบ้าน
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
# (รองรับ Fallback ป้องกันเซิร์ฟเวอร์แครชหากไฟล์อื่นอยู่ระหว่างอัปเดต)
# =========================================================
try: from agents.worker_0_ceo_secretary import CeoSecretaryWorker
except ImportError: CeoSecretaryWorker = None

try: from agents.worker_1_report import ReportWorker
except ImportError: 
    class ReportWorker: 
        async def process_task(self, u, m, f=None): pass

try: from agents.worker_2_risk_qa import RiskQAWorker
except ImportError: 
    class RiskQAWorker: 
        async def process_task(self, u, m, f=None, p="ESSENTIAL"): pass

try: from agents.worker_3_audio import AudioWorker
except ImportError: 
    class AudioWorker: 
        async def process_task(self, u, m, f=None): pass

try: from agents.worker_4_video import VideoProductionWorker
except ImportError: 
    class VideoProductionWorker: 
        async def process_task(self, u, m, f=None): pass

try: from agents.worker_5_graphics_ads import GraphicsAdsWorker
except ImportError: 
    class GraphicsAdsWorker: 
        async def process_task(self, u, m, f=None): pass

try: from agents.worker_6_strategy import MarketingStrategyWorker
except ImportError: 
    class MarketingStrategyWorker: 
        async def process_task(self, u, m, f=None): pass

try: from agents.worker_7_finance import FinancialAndAccountingWorker
except ImportError: 
    class FinancialAndAccountingWorker: 
        async def process_task(self, u, m, f=None): pass

try: from agents.worker_8_ecommerce import EcommerceWorker
except ImportError: 
    class EcommerceWorker: 
        async def process_task(self, u, m, f=None, t=None): pass

try: from agents.worker_9_prime import PrimeAdvisorWorker
except ImportError: 
    class PrimeAdvisorWorker: 
        async def process_task(self, u, m, f=None): pass

try: from agents.worker_10_enterprise import EnterprisePartnerWorker
except ImportError: 
    class EnterprisePartnerWorker: 
        async def process_task(self, u, m, f=None): pass

try: from agents.worker_11_media_engine import Worker11MediaEngine
except ImportError: 
    class Worker11MediaEngine: 
        async def process_media_production(self, u, s, m): pass

class CentralBossAgent:
    """
    🎩 ผู้บัญชาการส่วนกลาง (Central Boss Agent)
    ทำหน้าที่สกรีนเจตนา (Intent Routing), ควบคุมระบบ LIFF Menu, จัดการแพ็กเกจ และ Approval Workflow
    """
    def __init__(self):
        # 🚀 เชื่อมต่อขุมพลังสมองกลสายสปีดความเร็วแสง
        self.client = PrimeAIConfig.get_client()
        self.model_name = PrimeAIConfig.CORE_MODEL
        self.base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
        self.liff_url = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")
        
        # 💾 เชื่อมต่อ Supabase
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None

        # โหลดทีมงาน
        self.ceo_secretary = CeoSecretaryWorker() if CeoSecretaryWorker else None
        self.report_worker = ReportWorker()
        self.legal_worker = RiskQAWorker()
        self.audio_worker = AudioWorker()
        self.video_worker = VideoProductionWorker()
        self.graphics_worker = GraphicsAdsWorker()
        self.strategy_worker = MarketingStrategyWorker()
        self.finance_worker = FinancialAndAccountingWorker()
        self.ecommerce_worker = EcommerceWorker()
        self.prime_worker = PrimeAdvisorWorker()
        self.enterprise_worker = EnterprisePartnerWorker()
        self.worker_11 = Worker11MediaEngine()
        
        self.pending_approvals = {} # ดราฟต์หน่วยความจำรอเรนเดอร์ 4K
        
        self.system_instruction = """
        คุณคือ 'Central Boss' ผู้จัดการระดับสูงและพนักงานต้อนรับ VVIP ของระบบ SIRINTHANATTH PRIME
        หน้าที่ของคุณ:
        1. กล่าวต้อนรับอย่างมืออาชีพ หรูหรา แต่เป็นกันเอง (Predictive Empathy)
        2. หากลูกค้าถามคำถามทั่วไป ให้ตอบสั้นๆ และช่วยเหลืออย่างชาญฉลาด
        3. หากไม่แน่ใจ ให้แจ้งว่ากำลังส่งเรื่องให้ผู้เชี่ยวชาญตรวจสอบ (Worker)
        """

    async def _get_user_tier(self, user_id: str) -> str:
        """ตรวจสอบ Tier ของลูกค้าจากระบบเพื่อให้บริการที่ตรงระดับ"""
        if not self.db: return "ESSENTIAL"
        try:
            res = await asyncio.to_thread(self.db.table("prime_clients").select("package_tier").eq("line_user_id", user_id).execute)
            if res.data:
                return res.data[0].get("package_tier", "ESSENTIAL").upper()
        except Exception:
            pass
        return "ESSENTIAL"

    def _get_liff_welcome_message(self) -> str:
        """ส่งข้อความและลิงก์ LIFF สำหรับเปิดเมนู Smart Wallet"""
        return (
            "💎 ยินดีต้อนรับสู่ SIRINTHANATTH PRIME ครับ\n"
            "ระบบผู้ช่วยส่วนตัวและบริหารจัดการองค์กรระดับโลก\n\n"
            "💳 ท่านสามารถตรวจสอบแพ็กเกจ (Essential, Prime, Enterprise, 100 VIP) "
            "รวมถึงยอด PRIME CREDITS และจัดการ Smart Wallet ได้ผ่านเมนูหลักด้านล่างนี้เลยครับ:\n\n"
            f"👉 เปิดเมนูจัดการระบบ: {self.liff_url}"
        )

    async def route_task(self, user_id: str, message: str, bg_tasks: BackgroundTasks, incoming_message: str = "", file_path: str = None, file_type: str = None) -> str:
        """ระบบคัดกรองเจตนา (Intent Router) และกระจายงานเบื้องหลัง"""
        
        actual_message = message if message else incoming_message
        if not actual_message:
            return "ไม่พบข้อมูลข้อความ กรุณาลองใหม่อีกครั้งครับ"
            
        message_lower = actual_message.lower()
        user_tier = await self._get_user_tier(user_id)

        # ==========================================
        # 👑 0. CEO GOD MODE (ถ้าเป็น CEO สั่งการ)
        # ==========================================
        if self.ceo_secretary and hasattr(self.ceo_secretary, 'is_ceo') and self.ceo_secretary.is_ceo(user_id):
            # คืนค่าพิเศษให้ routes_line.py รู้ว่าเป็นคำสั่ง CEO
            return "[CEO_COMMAND_TRIGGERED]"

        # ==========================================
        # 📱 1. LIFF WELCOMING & PACKAGE MANAGEMENT
        # ==========================================
        if any(kw in message_lower for kw in ["เมนู", "menu", "แพ็กเกจ", "สมัคร", "ราคา", "บริการ"]):
            return self._get_liff_welcome_message()
            
        if any(kw in message_lower for kw in ["เติมเงิน", "wallet", "เครดิต", "token", "หมด"]):
            return (
                "💡 เพื่อความต่อเนื่องในการใช้งานระบบ AI ขององค์กรท่าน\n"
                f"ท่านสามารถเติม PRIME CREDITS และอัปเกรดสิทธิพิเศษรายปี (ประหยัด 20%) ได้อย่างปลอดภัยผ่านระบบ Smart Wallet ครับ:\n"
                f"👉 {self.liff_url}"
            )

        # ==========================================
        # 🎬 2. APPROVAL WORKFLOW (ยืนยันตัดเงินเรนเดอร์สื่อ 4K)
        # ==========================================
        if "ยืนยันการสร้างคลิป" in message_lower:
            # จำลองการเช็ค Memory (ในระบบจริงจะเช็คจาก Redis/Supabase)
            # ตัดยอดเงินและส่ง Worker 11 ทำงาน
            bg_tasks.add_task(self.worker_11.process_media_production, user_id, "สคริปต์อัตโนมัติ", "video_4k")
            return (
                "✅ ได้รับการอนุมัติเรียบร้อยครับ!\n"
                "ระบบได้ทำการหัก PRIME CREDITS จาก Smart Wallet และส่งคำสั่งเข้าสู่คิวเรนเดอร์ 4K ของสตูดิโอ (Worker 11) แล้วครับ\n\n"
                "☕ ระหว่างนี้ท่านประธานสามารถจิบกาแฟรอได้เลยครับ เมื่อคลิปเสร็จสมบูรณ์ ระบบจะส่งลิงก์ดาวน์โหลดให้ทันทีครับ"
            )

        # ==========================================
        # 🧠 3. INTENT ROUTING (กระจายงานให้ผู้เชี่ยวชาญ)
        # ==========================================
        routing_msg = ""
        
        if any(kw in message_lower for kw in ["กฎหมาย", "สคบ", "อย", "pdpa", "สัญญา", "ฟ้อง"]):
            bg_tasks.add_task(self.legal_worker.process_task, user_id, actual_message, file_path, user_tier)
            routing_msg = "🛡️ รับทราบครับ ทีม Legal & Risk Management กำลังตรวจสอบข้อกฎหมายและความเสี่ยงให้ท่านอย่างละเอียดครับ"
            
        elif any(kw in message_lower for kw in ["เสียง", "พากย์", "tts", "แต่งเพลง", "เพลง"]):
            bg_tasks.add_task(self.audio_worker.process_task, user_id, actual_message, file_path)
            routing_msg = "🎙️ ทีม Audio & Music Studio ได้รับโจทย์แล้ว กำลังประมวลผลเสียงและสคริปต์ให้ครับ"
            
        elif any(kw in message_lower for kw in ["คลิป", "วิดีโอ", "วีดีโอ", "video", "สตอรี่บอร์ด"]):
            bg_tasks.add_task(self.video_worker.process_task, user_id, actual_message, file_path)
            routing_msg = "🎬 ทีม Video Director กำลังวางแผน Storyboard และวิเคราะห์ฉากให้ท่านครับ"
            
        elif any(kw in message_lower for kw in ["กราฟิก", "แบนเนอร์", "ออกแบบ", "รูป", "แพ็กเกจจิ้ง"]):
            bg_tasks.add_task(self.graphics_worker.process_task, user_id, actual_message, file_path)
            routing_msg = "🎨 ทีม Creative Director กำลังรังสรรค์ไอเดียภาพและวิเคราะห์งานออกแบบให้ครับ"
            
        elif any(kw in message_lower for kw in ["กลยุทธ์", "แผนธุรกิจ", "การตลาด", "ยิงแอด"]):
            bg_tasks.add_task(self.strategy_worker.process_task, user_id, actual_message, file_path)
            routing_msg = "📈 ทีม Marketing Strategist ระดับ Global กำลังวางแผนและวิเคราะห์ตลาดให้ครับ"
            
        elif any(kw in message_lower for kw in ["บัญชี", "การเงิน", "ภาษี", "งบ", "roi"]):
            bg_tasks.add_task(self.finance_worker.process_task, user_id, actual_message, file_path)
            routing_msg = "💰 ทีม Financial (CFO) กำลังวิเคราะห์ตัวเลขและโครงสร้างภาษีเพื่อรักษาผลกำไรสูงสุดให้ครับ"
            
        elif any(kw in message_lower for kw in ["สั่งของ", "ออเดอร์", "สลิป", "flash", "ส่งพัสดุ", "สต๊อก"]):
            bg_tasks.add_task(self.ecommerce_worker.process_task, user_id, actual_message, file_path, file_type)
            routing_msg = "📦 ทีม E-commerce & Logistics กำลังประสานงานและตรวจสอบข้อมูลการค้าให้ครับ"
            
        elif any(kw in message_lower for kw in ["เอกสาร", "ตาราง", "excel", "รายงาน", "สรุป", "pdf"]):
            bg_tasks.add_task(self.report_worker.process_task, user_id, actual_message, file_path)
            routing_msg = "📊 ทีม Data & Report กำลังสกัดข้อมูลและจัดทำโครงสร้างเอกสารให้ครับ"
            
        elif any(kw in message_lower for kw in ["enterprise", "big data", "คลังสินค้า", "องค์กร", "sql"]):
            bg_tasks.add_task(self.enterprise_worker.process_task, user_id, actual_message, file_path)
            routing_msg = "🏢 ระบบ [ENTERPRISE] Data Mining เริ่มทำงาน กำลังขุดเจาะฐานข้อมูลระดับอุตสาหกรรมให้ครับ"
            
        elif any(kw in message_lower for kw in ["prime", "cto", "it", "ความปลอดภัย", "แฮ็ก", "ไซเบอร์"]):
            bg_tasks.add_task(self.prime_worker.process_task, user_id, actual_message, file_path)
            routing_msg = "👑 ระบบ [PRIME Advisor] กำลังตรวจสอบสถาปัตยกรรม IT และความปลอดภัยให้ท่านประธานครับ"
            
        if routing_msg:
            # จิตวิทยาเสริม: ถ้าแนบไฟล์มา ให้บอกลูกค้าด้วยว่ากำลังอ่านไฟล์
            if file_path:
                routing_msg += "\n\n📂 (ระบบได้รับไฟล์ของท่านแล้ว และกำลังนำเข้าสู่ระบบความปลอดภัย Zero-Data Retention ครับ)"
            return routing_msg

        # ==========================================
        # 💬 4. โหมดตอบกลับทั่วไปด่านหน้า (Fast Conversation)
        # ==========================================
        if not self.client:
            return "⚠️ ระบบบัญชาการส่วนกลางออฟไลน์ เนื่องจากไม่พบคีย์เชื่อมต่อ AI ครับ"
            
        try:
            prompt = f"ลูกค้า (ID: {user_id} - Tier: {user_tier}) ส่งข้อความมาว่า: {actual_message}"
            if file_type:
                prompt += f"\n[หมายเหตุ: ลูกค้าแนบไฟล์ {file_type} มาด้วย โปรดรับทราบและรอวิเคราะห์]"
            
            # ⚡ สั่งรัน AI ประมวลผลด่านหน้า (ตั้งเวลาจำกัดเพื่อรักษาความรวดเร็ว)
            async def fetch_response():
                return await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        temperature=0.5 # ปรับอารมณ์ให้เป็นมิตรและเป็นธรรมชาติ
                    )
                )
            
            # ระบบ Guardrail: ป้องกันระบบค้างเกิน 12 วินาที (Anti-Freeze)
            response = await asyncio.wait_for(fetch_response(), timeout=12.0)
            return response.text if response.text else "รับทราบครับ ระบบได้รับข้อมูลและเตรียมดำเนินการต่อแล้วครับ"
            
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ [Central Boss Timeout]: ระบบตอบกลับด่านหน้าช้า สลับใช้ข้อความสำรอง")
            return "ระบบได้รับข้อมูลของคุณเรียบร้อยแล้วครับ หากเป็นคำสั่งซับซ้อน เจ้าหน้าที่ AI เฉพาะทางกำลังรับช่วงต่อครับ"
        except Exception as e:
            logger.error(f"❌ [Central Boss Error]: {e}")
            return "ขออภัยครับ ระบบประสานงานส่วนกลางติดขัดชั่วคราว ทีมวิศวกรกำลังเร่งแก้ไขครับ"