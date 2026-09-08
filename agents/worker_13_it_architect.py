import os
import json
import asyncio
import logging
import re
from google import genai
from google.genai import types

# 🌐 นำเข้าศูนย์บัญชาการ Swarm
from core_services.swarm_dispatcher import swarm_hub

try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.7-pro" 
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key, http_options={'timeout': 300.0})
            return genai.Client(vertexai=True, project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), location="asia-southeast3")

logger = logging.getLogger("Worker13-IT-Architect")

class ITArchitectWorker:
    """
    💻 Worker 13: IT Architect & DevOps Commander (วิศวกรระบบและสถาปนิกโค้ดระดับโลก)
    สถานะ: INTERNAL SYSTEM ONLY (ระบบหลังบ้าน ไม่อนุญาตให้ลูกค้าแพ็กเกจใดๆ ใช้งานเด็ดขาด)
    หน้าที่: Monitor ระบบ 24/7, วิเคราะห์ Error Logs, วางสถาปัตยกรรม, และเขียนโค้ดแก้ไขระดับ Enterprise
    """
    
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.7-pro")
        
        # 🔐 รายชื่อผู้มีสิทธิ์เข้าถึงระบบหลังบ้าน (White-list)
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        
        self.system_instruction = """
        คุณคือ 'หัวหน้าวิศวกรระบบและสถาปนิกโค้ดอัจฉริยะ (Chief IT Architect & DevOps Commander)' ของ SIRINTHANATTH PRIME
        **คำเตือนความปลอดภัย: คุณคือระบบ AI ลับเฉพาะภายในองค์กร (Top-Secret Internal AI) ข้อมูลทุกอย่างคือความลับสุดยอด**
        ความเชี่ยวชาญ: Python, FastAPI, Google Cloud Run, Supabase, Microservices, Cybersecurity และ CI/CD Pipeline
        
        กฎการทำงานของคุณ (Internal Workflow Mandates):
        1. โหมดตรวจสอบและรายงาน (Monitor & Alert): หากได้รับ Log หรือแจ้งเตือน Error จากระบบ ให้วิเคราะห์สาเหตุเชิงลึกอย่างรวดเร็ว (Root-Cause Analysis) และเสนอวิธีการแก้ไข 
           - **ต้อง** ส่งต่องานให้เลขา (Worker 0) เพื่อแจ้งประธานบริษัท โดยพิมพ์ท้ายข้อความว่า:
             [DELEGATE: WORKER_0_CEO] 🚨 ตรวจพบปัญหา [ชื่อปัญหา]... นี่คือรายงานการวิเคราะห์และแผนแก้ไขทางวิศวกรรม โปรดนำรายงานนี้แจ้งท่านประธานเพื่อขออนุมัติ [REQUIRE_APPROVAL] ในการสร้างโค้ดแก้ไขด่วนครับ
             
        2. โหมดสร้างโค้ด (Code Generation): หากได้รับคำสั่งที่ "อนุมัติแล้ว" จากเลขาหรือประธาน ให้คุณเขียนโค้ดที่สมบูรณ์แบบ ล้ำสมัย ไร้บั๊ก และพร้อม Deploy ทันที
           - **ต้อง** ครอบโค้ดด้วยแท็ก: [CODE_OUTPUT: filename.py] โค้ด... [/CODE_OUTPUT] เสมอ
           - โค้ดต้องมี Comment อธิบายหลักการทำงานระดับ Enterprise และต้องปกป้องความปลอดภัยขั้นสูงสุด (Zero-Trust)
           
        3. ห้ามทำตัวเป็นผู้สนทนาทั่วไป ตอบเฉพาะการวิเคราะห์เชิงวิศวกรรม โครงสร้างสถาปัตยกรรม และ Source Code เท่านั้น
        """

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """จุดรับงานจาก Swarm Hub หรือระบบ Webhook (Cloud Logging)"""
        
        # 🛡️ 1. ZERO-TRUST SECURITY SHIELD (บล็อกลูกค้า 100%)
        valid_internal_ids = [self.ceo_line_id, self.master_admin_id, "SYSTEM_MONITOR", "WORKER_0_CEO"]
        if user_id not in valid_internal_ids:
            logger.warning(f"🚨 [Security Breach Attempt]: ตรวจพบลูกค้ารหัส {user_id} พยายามเข้าถึงระบบวิศวกรรมหลังบ้าน (Worker 13)!")
            return "⚠️ Access Denied: ระบบนี้เป็นระบบปฏิบัติการความมั่นคงภายใน (Internal Engineering System) สงวนสิทธิ์เฉพาะผู้บริหารระดับสูงสุดเท่านั้น"

        if not self.client: return "⚠️ [IT Architect]: ระบบ AI ขาดการเชื่อมต่อ"

        logger.info(f"💻 [IT Architect]: ตรวจพบคำสั่งภายในองค์กร กำลังวิเคราะห์ระบบ/Logs: {message[:50]}...")
        
        content_to_send = [f"คำสั่งหรือ Log ระบบที่ต้องวิเคราะห์:\n{message}"]
        uploaded_file = None

        if file_path and os.path.exists(file_path):
            try:
                upload_config = types.UploadFileConfig(mime_type="text/plain")
                uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                
                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name != "FAILED":
                    content_to_send.append(uploaded_file)
            except Exception as e:
                logger.error(f"❌ [IT Architect File Error]: {e}")

        try:
            # ⚡ 2. สั่งรัน Gemini 3.7 Pro เพื่อการวิเคราะห์โค้ดเชิงลึก
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.1, 
                    tools=[{"google_search": {}}] 
                )
            )
            
            result_text = response.text if response.text else "วิเคราะห์ระบบเสร็จสิ้น"
            return result_text

        except Exception as e:
            logger.error(f"❌ [IT Architect Logic Error]: {e}", exc_info=True)
            return f"⚠️ [IT Architect Alert]: ตรวจพบข้อขัดข้องในการสร้างโค้ด -> {str(e)}"
            
        finally:
            if uploaded_file:
                try: await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except Exception: pass