import os
import time
import logging
import asyncio
import requests
import json
import re
from google import genai
from google.genai import types
from supabase import create_client, Client
from fastapi import BackgroundTasks

# ตั้งค่า Logger สำหรับตรวจสอบการทำงานระดับ Enterprise
logger = logging.getLogger("CentralBoss-Swarm")

# =========================================================
# 🌐 นำเข้าศูนย์บัญชาการ AI และฐานข้อมูล (Vertex AI / Zero Downtime)
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-2.5-flash" # 🚀 อัปเกรดเป็นแกนสมองสายสปีดรุ่นล่าสุดที่ฉลาดและเร็วที่สุด
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

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
    อัปเกรดสถาปัตยกรรม: Multi-Agent Swarm Pipeline 
    จ่ายงานให้พนักงานทำงานแบบส่งไม้ต่อกัน (Inter-Agent Communication) และ Push ผลลัพธ์กลับสู่ LINE อัตโนมัติ
    """
    def __init__(self):
        # 🚀 เชื่อมต่อขุมพลังสมองกลสายสปีดความเร็วแสง
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-2.5-flash")
        self.liff_url = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")
        self.line_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
        
        # 💾 เชื่อมต่อ Supabase
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None

        # 🤝 แผนที่ทีมงาน (Worker Map) สำหรับระบบ Swarm
        self.workers = {
            "worker_1": ReportWorker() if ReportWorker else None,
            "worker_2": RiskQAWorker() if RiskQAWorker else None,
            "worker_3": AudioWorker() if AudioWorker else None,
            "worker_4": VideoProductionWorker() if VideoProductionWorker else None,
            "worker_5": GraphicsAdsWorker() if GraphicsAdsWorker else None,
            "worker_6": MarketingStrategyWorker() if MarketingStrategyWorker else None,
            "worker_7": FinancialAndAccountingWorker() if FinancialAndAccountingWorker else None,
            "worker_8": EcommerceWorker() if EcommerceWorker else None,
            "worker_9": PrimeAdvisorWorker() if PrimeAdvisorWorker else None,
            "worker_10": EnterprisePartnerWorker() if EnterprisePartnerWorker else None,
        }
        self.worker_11 = Worker11MediaEngine() if Worker11MediaEngine else None
        
        self.system_instruction = """
        คุณคือ 'Central Boss' ผู้จัดการระดับสูงสุดของระบบ SIRINTHANATTH PRIME
        จิตวิทยาในการสื่อสาร: สุภาพ หรูหรา อบอุ่น และเป็นมืออาชีพ (ใช้คำว่า ครับ/ค่ะ เสมอ)
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

    async def _execute_swarm_pipeline_and_push(self, user_id: str, pipeline: list, initial_message: str, file_path: str, user_tier: str, file_type: str):
        """
        🚀 สถาปัตยกรรม Multi-Agent Swarm (Pipeline Executor):
        ให้พนักงานหลายแผนกประมวลผลข้อมูลส่งไม้ต่อกัน (Inter-Agent Communication) และ Push ผลลัพธ์สุดท้ายให้ลูกค้า
        """
        current_message = initial_message
        current_file = file_path
        final_result = ""

        try:
            for idx, w_key in enumerate(pipeline):
                worker_instance = self.workers.get(w_key)
                if not worker_instance: continue

                logger.info(f"🔄 [Swarm Pipeline]: ส่งไม้ต่อให้ {w_key.upper()} (Step {idx+1}/{len(pipeline)})")

                # การจัดเตรียม kwargs อัตโนมัติให้ตรงกับ Signature ของแต่ละ Worker
                kwargs = {"file_path": current_file}
                if w_key == "worker_2": kwargs["package_tier"] = user_tier
                if w_key == "worker_8": kwargs["file_type"] = file_type

                # หากไม่ใช่คิวแรก ให้นำผลลัพธ์ของแผนกที่แล้วมาเป็นบริบทในการทำงานต่อ (Inter-Agent Communication)
                if idx > 0 and final_result:
                    prompt = f"อ้างอิงจากคำสั่งดั้งเดิมของลูกค้า: {initial_message}\n\n[ข้อมูลที่ถูกส่งต่อมาจากแผนกก่อนหน้า]:\n{final_result}\n\nโปรดสานต่องานนี้ในส่วนที่แผนกของคุณรับผิดชอบและสรุปผล"
                else:
                    prompt = current_message

                # เรียกทำงาน Worker (รองรับ Backward Compatibility สำหรับระบบเก่าที่ใช้ process และระบบใหม่ที่ใช้ process_task)
                if hasattr(worker_instance, "process_task"):
                    final_result = await worker_instance.process_task(user_id, prompt, **kwargs)
                elif hasattr(worker_instance, "process"):
                    final_result = await worker_instance.process(user_id, prompt, **kwargs)
                else:
                    logger.warning(f"⚠️ [Swarm Pipeline]: Worker {w_key} ไม่มีฟังก์ชัน process_task หรือ process")
                    continue

                # 🛡️ Zero-Data Sync: เมื่อแผนกแรกประมวลผลและลบไฟล์ไปแล้ว ห้ามส่ง Path ไฟล์เดิมให้แผนกต่อไป
                current_file = None 

            # Push ข้อมูลกลับหาลูกค้าเมื่อสิ้นสุด Pipeline
            if final_result and self.line_token:
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.line_token}"}
                data = {"to": user_id, "messages": [{"type": "text", "text": str(final_result)}]}
                res = await asyncio.to_thread(requests.post, "https://api.line.me/v2/bot/message/push", headers=headers, json=data)
                res.raise_for_status()
                logger.info(f"✅ [Swarm Delivery]: จัดส่งผลการทำงานร่วมกันระดับองค์กรให้ {user_id} สำเร็จ!")

        except Exception as e:
            logger.error(f"❌ [Swarm Execution Error]: {e}")
            if self.line_token:
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.line_token}"}
                data = {"to": user_id, "messages": [{"type": "text", "text": f"⚠️ ขออภัยครับ เกิดข้อขัดข้องระหว่างการประสานงานของทีมงาน ทีมวิศวกรกำลังตรวจสอบครับ"}]}
                await asyncio.to_thread(requests.post, "https://api.line.me/v2/bot/message/push", headers=headers, json=data)

    async def route_task(self, user_id: str, message: str, bg_tasks: BackgroundTasks, incoming_message: str = "", file_path: str = None, file_type: str = None) -> str:
        """🧠 แกนสมอง Router ประเมินเจตนาลูกค้าและสร้างแผนการประชุม Swarm (Pipeline)"""
        
        actual_message = message if message else incoming_message
        if not actual_message and not file_type:
            return "ไม่พบข้อมูลข้อความ กรุณาลองใหม่อีกครั้งครับ"
            
        message_lower = actual_message.lower()
        user_profile = await self._get_user_profile(user_id)
        user_tier = user_profile["tier"]

        # ==========================================
        # 📱 1. Fast-Track: LIFF & PACKAGE MANAGEMENT
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
        # 🎬 2. Fast-Track: APPROVAL WORKFLOW (ยืนยันสร้างสื่อ 4K)
        # ==========================================
        if "ยืนยันการสร้างคลิป" in message_lower or "ยืนยันสร้างเสียง" in message_lower:
            if self.worker_11:
                media_type = "video_4k" if "คลิป" in message_lower else "voice"
                bg_tasks.add_task(self.worker_11.process_media_production, user_id, "สคริปต์อัตโนมัติ", media_type)
                return (
                    "✅ ได้รับการอนุมัติระดับผู้บริหารเรียบร้อยครับ!\n"
                    "ระบบได้จัดการหัก PRIME CREDITS อย่างถูกต้อง และส่งคำสั่งเข้าสู่คิวสตูดิโอ 4K เรียบร้อยแล้วครับ\n\n"
                    "☕ ระหว่างนี้ท่านประธานสามารถพักผ่อนได้เลยครับ เมื่อผลงานเสร็จสมบูรณ์ ระบบจะนำส่งให้ทันทีครับ"
                )

        # ==========================================
        # 🤖 3. SWARM INTELLIGENCE ROUTER (AI ประเมินว่าต้องใช้กี่แผนก)
        # ==========================================
        if not self.client:
            return "⚠️ ระบบบัญชาการส่วนกลางออฟไลน์ เนื่องจากไม่พบคีย์เชื่อมต่อ AI ครับ"

        swarm_instruction = """
        คุณคือ 'Central Boss' ผู้บัญชาการ AI Swarm ของ SIRINTHANATTH PRIME
        หน้าที่: วิเคราะห์คำสั่งลูกค้าและจัดคิวแผนก (Pipeline) เพื่อทำงานร่วมกัน
        
        รายชื่อแผนก:
        - "worker_1": วิเคราะห์ Data, Excel, สรุปเอกสาร, ประเมินราคา
        - "worker_2": กฎหมาย, ความเสี่ยง, สัญญา
        - "worker_3": ไฟล์เสียง, เพลง
        - "worker_4": ไฟล์วิดีโอ, Storyboard
        - "worker_5": ไฟล์ภาพ, กราฟิก, โฆษณา, ร่างภาพตัวอย่าง
        - "worker_6": กลยุทธ์การตลาด, แผนธุรกิจ
        - "worker_7": การเงิน, บัญชี, ภาษี, คุ้มทุน
        - "worker_8": E-Commerce, สลิปโอนเงิน, ส่งของ Flash
        - "worker_9": สถาปัตยกรรม IT, Cyber Security
        - "worker_10": Big Data ระดับองค์กร, Supply Chain

        เงื่อนไข:
        1. หากเป็นบทสนทนาทั่วไป ถามสารทุกข์สุกดิบ ให้ส่ง pipeline ว่าง: []
        2. งาน 1 มิติ ให้ใช้ 1 แผนก เช่น ["worker_1"]
        3. หากงานซับซ้อนข้ามสาย ให้เรียงลำดับแผนก เช่น ลูกค้าส่งแปลนที่ดินมาให้ประเมินและร่างแบบ = ["worker_1", "worker_7", "worker_5"]
        4. หากมีไฟล์ภาพสลิปโอนเงิน ให้ไปที่ "worker_8" 
        5. ตอบกลับเป็น JSON เท่านั้น รูปแบบ: {"pipeline": [...], "routing_msg": "..."}
        """

        prompt = f"""
        วิเคราะห์การส่งไม้ต่อ (Pipeline) จากคำสั่งลูกค้า:
        ข้อความ: {actual_message}
        มีไฟล์แนบหรือไม่: {'มีไฟล์ประเภท ' + str(file_type) if file_type else 'ไม่มีไฟล์แนบ'}
        """

        try:
            res = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=swarm_instruction,
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )
            
            res_text = re.sub(r'^```json\s*', '', res.text.strip())
            res_text = re.sub(r'\s*```$', '', res_text)
            routing_data = json.loads(res_text)
            
            pipeline = routing_data.get("pipeline", [])
            routing_msg = routing_data.get("routing_msg", "รับทราบครับ ระบบกำลังดำเนินการให้ครับ")

            # หากมี Pipeline ส่งเข้า Swarm Executor ทำงานเบื้องหลัง
            if pipeline:
                if file_path:
                    routing_msg += "\n\n📂 (ระบบได้รับข้อมูลของท่านแล้ว และเข้าสู่กระบวนการรักษาความลับ Zero-Data Retention ครับ)"
                
                bg_tasks.add_task(self._execute_swarm_pipeline_and_push, user_id, pipeline, actual_message, file_path, user_tier, file_type)
                return routing_msg

        except Exception as e:
            logger.error(f"⚠️ [Swarm Router Error]: {e} -> Fallback to Fast Conversation")

        # ==========================================
        # 💬 4. โหมดสนทนาด่านหน้า (Fast Conversation Fallback)
        # ==========================================
        try:
            chat_prompt = f"ลูกค้า (ID: {user_id} - Tier: {user_tier}) ส่งข้อความมาว่า: {actual_message}"
            if file_type:
                chat_prompt += f"\n[หมายเหตุ: ลูกค้าแนบไฟล์ {file_type} มาด้วย โปรดตอบรับอย่างสุภาพและรอการวิเคราะห์]"
            
            async def fetch_response():
                return await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=chat_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        temperature=0.6 # ปรับอุณหภูมิให้อบอุ่น เป็นธรรมชาติ และมีความเข้าอกเข้าใจ
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