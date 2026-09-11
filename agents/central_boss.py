import os
import time
import logging
import asyncio
import httpx 
import json
from pydantic import BaseModel, Field, ConfigDict
from google import genai
from google.genai import types
from supabase import create_client, Client
from fastapi import BackgroundTasks

# นำเข้าศูนย์กลางสื่อสาร (Swarm Hub)
from core_services.swarm_dispatcher import swarm_hub

logger = logging.getLogger("CentralBoss-Swarm")

# =========================================================
# 🌐 1. นำเข้าศูนย์บัญชาการ AI และฐานข้อมูล
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-3.7-flash" # 🚀 แกนสมองเรือธงสายสปีดที่เร็วและฉลาดที่สุด
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key, http_options={'timeout': 300.0})
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3",
                http_options={'timeout': 300.0}
            )

# 🧠 [NEW] สถาปัตยกรรมบังคับโครงสร้างความคิด AI (Structured Outputs)
class SwarmRoutingSchema(BaseModel):
    model_config = ConfigDict(strict=True)
    pipeline: list[str] = Field(description='รายชื่อแผนก (Worker Keys) ที่ต้องส่งงานให้ทำตามลำดับ เช่น ["WORKER_2_RISK_QA", "WORKER_6_STRATEGY"]. หากเป็นคำทักทายทั่วไปให้ปล่อยว่าง []')
    routing_msg: str = Field(description='ข้อความสุภาพที่จะตอบกลับลูกค้าทันที เพื่อแจ้งให้ทราบว่าระบบกำลังส่งงานให้แผนกไหนทำ')

class CentralBossAgent:
    """
    🎩 ผู้บัญชาการส่วนกลาง (Central Boss Agent - The Master Orchestrator)
    จัดการ Pipeline ฝูงสมองกล (Swarm Intelligence) จ่ายงานต่อเนื่องและ Push ผลลัพธ์กลับสู่ LINE
    อัปเกรด: Native Async I/O, Pydantic Structured Outputs, 14-Worker Network Support
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-3.7-flash")
        self.liff_url = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")
        self.line_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
        
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        self.system_instruction = """
        คุณคือ 'Central Boss' ผู้จัดการระดับสูงสุดของระบบ SIRINTHANATTH PRIME
        จิตวิทยาในการสื่อสาร: สุภาพ หรูหรา อบอุ่น และเป็นมืออาชีพ (ใช้คำว่า ครับ/ค่ะ เสมอ) ไม่เยิ่นเย้อ
        """

    async def _get_user_profile(self, user_id: str) -> dict:
        """🔍 ตรวจสอบ Tier และ Token เพื่อให้บริการตรงระดับ"""
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
        """💎 ระบบต้อนรับด้วยจิตวิทยา สร้าง Emotional Connection"""
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
        🚀 Multi-Agent Swarm Pipeline:
        ส่งไม้ต่อให้พนักงานแต่ละแผนกประมวลผล (Chain of Thought) และ Push กลับสู่ LINE
        """
        current_message = initial_message
        current_file = file_path
        final_result = ""

        try:
            for idx, w_key in enumerate(pipeline):
                w_key = w_key.upper()
                
                # 1. ตรวจสอบ Worker จากระบบลงทะเบียนส่วนกลาง
                worker_instance = swarm_hub._workers.get(w_key)
                if not worker_instance: 
                    logger.warning(f"⚠️ [Swarm Pipeline]: ข้ามแผนก {w_key} เนื่องจากยังไม่ได้ออนไลน์ในระบบ")
                    continue

                logger.info(f"🔄 [Swarm Pipeline]: ส่งไม้ต่อให้ {w_key} (Step {idx+1}/{len(pipeline)})")

                # 2. ประกอบร่างบริบท (ส่งต่อความจำแบบ Inter-Agent Communication)
                if idx > 0 and final_result:
                    prompt = f"คำสั่งดั้งเดิมของลูกค้า: {initial_message}\n\n[ข้อมูล/ผลลัพธ์ที่สกัดได้จากแผนกก่อนหน้า]:\n{final_result}\n\nโปรดสานต่องานนี้ในส่วนที่คุณรับผิดชอบและสรุปผล"
                else:
                    prompt = current_message

                # 3. สั่งรันผ่าน Method Discovery (แบบ Dynamic)
                if hasattr(worker_instance, "process_task"):
                    res = worker_instance.process_task(user_id, prompt, current_file)
                    final_result = await res if asyncio.iscoroutine(res) else res
                elif hasattr(worker_instance, "process_command"):
                    res = worker_instance.process_command(user_id, prompt, current_file, file_type)
                    final_result = await res if asyncio.iscoroutine(res) else res
                elif hasattr(worker_instance, "process_ceo_command"):
                    res = worker_instance.process_ceo_command(prompt, current_file, file_type)
                    final_result = await res if asyncio.iscoroutine(res) else res
                else:
                    # Fallback ให้ Swarm Hub จัดการส่งให้
                    final_result = await swarm_hub.delegate_task("CENTRAL_BOSS", w_key, user_id, prompt, current_file, file_type)

                # 🛡️ Zero-Data Guard: แผนกแรกประมวลผลไฟล์ไปแล้ว ห้ามส่ง Path ให้แผนกถัดไปเพื่อป้องกันไฟล์รั่วไหล
                current_file = None 

            # 4. สิ้นสุด Pipeline จัดส่งผลลัพธ์ให้ลูกค้าผ่าน Push API (⚡ อัปเกรดใช้ httpx แบบ Async)
            if final_result and self.line_token:
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.line_token}"}
                
                # 💎 รองรับการตอบกลับด้วย Flex Message จาก Worker
                if isinstance(final_result, dict) and final_result.get("type") in ["flex", "template"]:
                    payload = final_result
                else:
                    payload = {"type": "text", "text": str(final_result)}
                    
                data = {"to": user_id, "messages": [payload]}
                
                async with httpx.AsyncClient() as http_client:
                    res = await http_client.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data, timeout=15.0)
                    res.raise_for_status()
                    logger.info(f"✅ [Swarm Delivery]: จัดส่งผลการประมวลผลเครือข่ายองค์กรให้ {user_id} สำเร็จ!")

        except Exception as e:
            logger.error(f"❌ [Swarm Execution Error]: {e}", exc_info=True)
            if self.line_token:
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.line_token}"}
                data = {"to": user_id, "messages": [{"type": "text", "text": f"⚠️ ขออภัยครับ เกิดข้อขัดข้องระหว่างการประสานงานของทีมผู้เชี่ยวชาญข้ามแผนก ทีมวิศวกรกำลังเร่งตรวจสอบครับ"}]}
                async with httpx.AsyncClient() as http_client:
                    await http_client.post("https://api.line.me/v2/bot/message/push", headers=headers, json=data, timeout=10.0)

    async def route_task(self, user_id: str, message: str, bg_tasks: BackgroundTasks, incoming_message: str = "", file_path: str = None, file_type: str = None) -> str:
        """🧠 แกนสมอง Router ประเมินเจตนาลูกค้าและสร้างแผนผังการประชุม Swarm (Pipeline)"""
        
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
            worker_11 = swarm_hub._workers.get("WORKER_11_MEDIA_ENGINE")
            if worker_11:
                media_type = "video_4k" if "คลิป" in message_lower else "voice"
                bg_tasks.add_task(swarm_hub.delegate_task, "CENTRAL_BOSS", "WORKER_11_MEDIA_ENGINE", user_id, actual_message, file_path, file_type)
                return (
                    "✅ ได้รับการอนุมัติระดับผู้บริหารเรียบร้อยครับ!\n"
                    "ระบบได้จัดการหัก PRIME CREDITS และส่งคำสั่งเข้าสู่คิวโปรดักชันเรียบร้อยแล้วครับ\n\n"
                    "☕ ระหว่างนี้ท่านสามารถพักผ่อนได้เลยครับ เมื่อผลงานเสร็จสมบูรณ์ ระบบจะนำส่งให้ทันทีครับ"
                )

        # ==========================================
        # 🤖 3. SWARM INTELLIGENCE ROUTER (AI จัดโครงสร้างทีม)
        # ==========================================
        if not self.client:
            return "⚠️ ระบบบัญชาการส่วนกลางออฟไลน์ เนื่องจากไม่พบคีย์เชื่อมต่อ AI ครับ"

        swarm_instruction = """
        คุณคือ 'Central Boss' ผู้บัญชาการ AI Swarm ของ SIRINTHANATTH PRIME
        หน้าที่: วิเคราะห์คำสั่งลูกค้าและจัดคิวแผนก (Pipeline) เพื่อทำงานร่วมกันแบบสอดประสาน
        
        รายชื่อแผนกที่พร้อมใช้งาน (Agent Network):
        - "WORKER_0_CEO": เลคาส่วนตัว CEO (งานบริหารสูงสุด ควบคุมระบบ อนุมัติโค้ด)
        - "WORKER_1_REPORT": วิเคราะห์ Data, Excel, สรุปเอกสาร, ประเมินราคา
        - "WORKER_2_RISK_QA": กฎหมาย, ความเสี่ยง, สัญญา, PDPA
        - "WORKER_3_AUDIO": ไฟล์เสียง, สังเคราะห์เสียง, สคริปต์เสียง
        - "WORKER_4_VIDEO": ไฟล์วิดีโอ, Storyboard, งานโปรดักชัน
        - "WORKER_5_GRAPHICS_ADS": ไฟล์ภาพ, กราฟิก, โฆษณา, คอนเทนต์
        - "WORKER_6_STRATEGY": กลยุทธ์การตลาด, แผนธุรกิจ, วิสัยทัศน์
        - "WORKER_7_FINANCE": การเงิน, บัญชี, ภาษี, จุดคุ้มทุน
        - "WORKER_8_ECOMMERCE": E-Commerce, สลิปโอนเงิน, ระบบ Logistics
        - "WORKER_9_PRIME": ที่ปรึกษาส่วนตัว, วางสถาปัตยกรรมธุรกิจเบื้องต้น
        - "WORKER_10_ENTERPRISE": Big Data ระดับองค์กร, Supply Chain
        - "WORKER_11_MEDIA_ENGINE": Engine ประมวลผลสื่อวิดีโอ/เสียงระดับสูง
        - "WORKER_12_SELF_LEARNING": วิเคราะห์พฤติกรรม และเรียนรู้ข้อมูลใหม่
        - "WORKER_13_IT_ARCHITECT": (Internal) วิศวกรระบบ ตรวจสอบและเขียนโค้ด ซ่อมเซิร์ฟเวอร์

        เงื่อนไขการส่งต่อ (Pipeline Logistics):
        1. หากเป็นการสนทนาทั่วไป ทักทาย หรือถามสารทุกข์สุกดิบ ให้ส่ง pipeline เป็นค่าว่าง: []
        2. งานเฉพาะทางให้ใช้ 1 แผนก เช่น ลูกค้าให้เขียนเว็บส่ง ["WORKER_13_IT_ARCHITECT"] หรือทำบัญชีส่ง ["WORKER_7_FINANCE"]
        3. งานซับซ้อนให้เรียงลำดับ (Chain) เช่น สแกนสัญญาและวางแผนธุรกิจ = ["WORKER_2_RISK_QA", "WORKER_6_STRATEGY"]
        4. หากประธาน (CEO) สั่งงาน ให้มี ["WORKER_0_CEO"] อยู่ด้วยเสมอ
        """

        prompt = f"""
        วิเคราะห์การส่งไม้ต่อ (Pipeline) จากคำสั่ง/ข้อมูลของลูกค้า:
        ข้อความ: {actual_message}
        สถานะไฟล์แนบ: {'มีไฟล์ประเภท ' + str(file_type) if file_type else 'ไม่มีไฟล์แนบ'}
        """

        try:
            # 🧠 [Native Async Pydantic Output]
            # ใช้ client.aio.models.generate_content เพื่อดึงความเร็ว Native Async 100%
            res = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=swarm_instruction,
                    temperature=0.1, 
                    response_mime_type="application/json",
                    response_schema=SwarmRoutingSchema
                )
            )
            
            routing_data = json.loads(res.text)
            
            pipeline = routing_data.get("pipeline", [])
            routing_msg = routing_data.get("routing_msg", "รับทราบครับ ระบบกำลังดำเนินการประสานงานให้ครับ")

            if pipeline:
                if file_path:
                    routing_msg += "\n\n📂 (ข้อมูลเข้าสู่กระบวนการรักษาความลับ Zero-Data Retention เรียบร้อยครับ)"
                
                # โยนเข้า Executor เพื่อรันข้ามแผนกแบบ Asynchronous ไม่ให้ LINE ค้าง (Non-Blocking)
                bg_tasks.add_task(self._execute_swarm_pipeline_and_push, user_id, pipeline, actual_message, file_path, user_tier, file_type)
                return routing_msg

        except Exception as e:
            logger.error(f"⚠️ [Swarm Router Error]: {e} -> Fallback to Fast Conversation", exc_info=True)

        # ==========================================
        # 💬 4. โหมดสนทนาด่านหน้า (Fast Conversation Fallback)
        # ==========================================
        try:
            chat_prompt = f"ลูกค้า (ID: {user_id} - Tier: {user_tier}) ส่งข้อความมาว่า: {actual_message}"
            if file_type:
                chat_prompt += f"\n[ลูกค้ารายนี้แนบไฟล์ {file_type} มาด้วย โปรดตอบรับอย่างเป็นมิตรและแจ้งว่าระบบกำลังประมวลผลเชิงลึก]"
            
            # ⚡ ใช้ Native Async สำหรับการสนทนาเร็วสุดขีด
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=chat_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.5 
                )
            )
            
            return response.text if response.text else "รับทราบครับ ระบบได้รับข้อมูลและเตรียมดำเนินการต่อให้ครับ"
            
        except Exception as e:
            logger.error(f"❌ [Central Boss Error]: {e}")
            return "ขออภัยครับ ระบบประสานงานส่วนกลางติดขัดชั่วคราว ทีมวิศวกรกำลังเร่งตรวจสอบให้ครับ"