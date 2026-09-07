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

# นำเข้าศูนย์กลางสื่อสาร (ป้องกัน Circular Import และดึง Worker จากส่วนกลาง)
from core_services.swarm_dispatcher import swarm_hub

logger = logging.getLogger("CentralBoss-Swarm")

# =========================================================
# 🌐 นำเข้าศูนย์บัญชาการ AI และฐานข้อมูล
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-3.7-flash" # 🚀 อัปเกรดแกนสมองสายสปีดรุ่นล่าสุด
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

class CentralBossAgent:
    """
    🎩 ผู้บัญชาการส่วนกลาง (Central Boss Agent - The Master Orchestrator)
    จัดการ Pipeline ฝูงสมองกล (Swarm Intelligence) จ่ายงานต่อเนื่องและ Push ผลลัพธ์กลับสู่ LINE
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
        จิตวิทยาในการสื่อสาร: สุภาพ หรูหรา อบอุ่น และเป็นมืออาชีพ (ใช้คำว่า ครับ/ค่ะ เสมอ)
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
                
                # ดึง Worker จากระบบลงทะเบียนส่วนกลางใน main.py
                worker_instance = swarm_hub._workers.get(w_key)
                if not worker_instance: 
                    logger.warning(f"⚠️ [Swarm Pipeline]: ข้ามแผนก {w_key} เนื่องจากยังไม่ได้ออนไลน์ในระบบ")
                    continue

                logger.info(f"🔄 [Swarm Pipeline]: ส่งไม้ต่อให้ {w_key} (Step {idx+1}/{len(pipeline)})")

                # ประกอบร่างบริบท หากเป็นคิวที่ 2 เป็นต้นไป ให้นำผลลัพธ์ของคิวแรกมาเป็นบริบท
                if idx > 0 and final_result:
                    prompt = f"คำสั่งดั้งเดิมของลูกค้า: {initial_message}\n\n[ข้อมูล/ผลลัพธ์ที่สกัดได้จากแผนกก่อนหน้า]:\n{final_result}\n\nโปรดสานต่องานนี้ในส่วนที่คุณรับผิดชอบและสรุปผล"
                else:
                    prompt = current_message

                # เรียกใช้งาน Worker ด้วยสถาปัตยกรรม Method แบบยืดหยุ่น
                if hasattr(worker_instance, "process_task"):
                    final_result = await worker_instance.process_task(user_id, prompt, current_file)
                elif hasattr(worker_instance, "process_command"):
                    final_result = await worker_instance.process_command(user_id, prompt, current_file, file_type)
                elif hasattr(worker_instance, "process_ceo_command"):
                    final_result = await worker_instance.process_ceo_command(prompt, current_file, file_type)
                else:
                    continue

                # 🛡️ Zero-Data Guard: แผนกแรกประมวลผลและลบไฟล์ไปแล้ว ห้ามส่ง Path ให้แผนกถัดไป
                current_file = None 

            # สิ้นสุด Pipeline จัดส่งผลลัพธ์ให้ลูกค้าผ่าน Push API
            if final_result and self.line_token:
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.line_token}"}
                data = {"to": user_id, "messages": [{"type": "text", "text": str(final_result)}]}
                res = await asyncio.to_thread(requests.post, "https://api.line.me/v2/bot/message/push", headers=headers, json=data)
                res.raise_for_status()
                logger.info(f"✅ [Swarm Delivery]: จัดส่งผลการประมวลผลเครือข่ายองค์กรให้ {user_id} สำเร็จ!")

        except Exception as e:
            logger.error(f"❌ [Swarm Execution Error]: {e}")
            if self.line_token:
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.line_token}"}
                data = {"to": user_id, "messages": [{"type": "text", "text": f"⚠️ ขออภัยครับ เกิดข้อขัดข้องระหว่างการประสานงานของทีมผู้เชี่ยวชาญ ทีมวิศวกรกำลังตรวจสอบครับ"}]}
                await asyncio.to_thread(requests.post, "https://api.line.me/v2/bot/message/push", headers=headers, json=data)

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
            worker_11 = swarm_hub._workers.get("WORKER_11_MEDIA")
            if worker_11:
                media_type = "video_4k" if "คลิป" in message_lower else "voice"
                bg_tasks.add_task(worker_11.process_media_production, user_id, "สคริปต์อัตโนมัติ", media_type)
                return (
                    "✅ ได้รับการอนุมัติระดับผู้บริหารเรียบร้อยครับ!\n"
                    "ระบบได้จัดการหัก PRIME CREDITS และส่งคำสั่งเข้าสู่คิวสตูดิโอ 4K เรียบร้อยแล้วครับ\n\n"
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
        
        รายชื่อแผนกที่พร้อมใช้งาน:
        - "WORKER_0_CEO": เลคาส่วนตัว CEO (ใช้วิเคราะห์คำสั่งบริหารสูงสุด หรือทำงานแทนประธาน)
        - "WORKER_1_REPORT": วิเคราะห์ Data, Excel, สรุปเอกสาร, ประเมินราคา
        - "WORKER_2_RISK_QA": กฎหมาย, ความเสี่ยง, สัญญา
        - "WORKER_3_AUDIO": ไฟล์เสียง, สังเคราะห์เสียง
        - "WORKER_4_VIDEO": ไฟล์วิดีโอ, Storyboard
        - "WORKER_5_GRAPHICS": ไฟล์ภาพ, กราฟิก, โฆษณา
        - "WORKER_6_STRATEGY": กลยุทธ์การตลาด, แผนธุรกิจ
        - "WORKER_7_FINANCE": การเงิน, บัญชี, ภาษี, จุดคุ้มทุน
        - "WORKER_8_ECOMMERCE": E-Commerce, สลิปโอนเงิน, ระบบ Logistics
        - "WORKER_9_PRIME": สถาปัตยกรรม IT, Cyber Security, โค้ดโปรแกรม
        - "WORKER_10_ENTERPRISE": Big Data ระดับองค์กร, Supply Chain

        เงื่อนไข:
        1. หากเป็นบทสนทนาทักทายทั่วไป ให้ส่ง pipeline ว่าง: []
        2. งานเฉพาะทางให้ใช้ 1 แผนก เช่น ["WORKER_9_PRIME"]
        3. งานซับซ้อนให้เรียงลำดับ เช่น สแกนสัญญาและวางแผนธุรกิจ = ["WORKER_2_RISK_QA", "WORKER_6_STRATEGY"]
        4. ตอบกลับเป็นรูปแบบ JSON เท่านั้น โครงสร้าง: {"pipeline": [...], "routing_msg": "..."}
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
                    temperature=0.1, # ลดการคาดเดา เพื่อให้ได้โครงสร้าง JSON 100%
                    response_mime_type="application/json"
                )
            )
            
            res_text = re.sub(r'^```json\s*', '', res.text.strip())
            res_text = re.sub(r'\s*```$', '', res_text)
            routing_data = json.loads(res_text)
            
            pipeline = routing_data.get("pipeline", [])
            routing_msg = routing_data.get("routing_msg", "รับทราบครับ ระบบกำลังดำเนินการประสานงานให้ครับ")

            if pipeline:
                if file_path:
                    routing_msg += "\n\n📂 (ข้อมูลเข้าสู่กระบวนการรักษาความลับ Zero-Data Retention เรียบร้อยครับ)"
                
                # โยนเข้า Executor เพื่อรันข้ามแผนกแบบ Asynchronous ไม่ให้ LINE ค้าง
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
                chat_prompt += f"\n[ลูกค้ารายนี้แนบไฟล์ {file_type} มาด้วย โปรดตอบรับอย่างเป็นมิตรและรอการวิเคราะห์เชิงลึก]"
            
            async def fetch_response():
                return await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=chat_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        temperature=0.6 
                    )
                )
            
            response = await asyncio.wait_for(fetch_response(), timeout=12.0)
            return response.text if response.text else "รับทราบครับ ระบบได้รับข้อมูลและเตรียมดำเนินการต่อให้ครับ"
            
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ [Central Boss Timeout]: ระบบด่านหน้าช้า สลับใช้ข้อความสำรองอัตโนมัติ")
            return "ระบบได้รับข้อมูลเรียบร้อยแล้วครับ หากเป็นคำสั่งเฉพาะทาง ทีม AI ผู้เชี่ยวชาญกำลังรับช่วงต่อดำเนินการครับ"
        except Exception as e:
            logger.error(f"❌ [Central Boss Error]: {e}")
            return "ขออภัยครับ ระบบประสานงานส่วนกลางติดขัดชั่วคราว ทีมวิศวกรกำลังเร่งตรวจสอบให้ครับ"