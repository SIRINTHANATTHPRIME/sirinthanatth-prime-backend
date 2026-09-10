import os
import json
import asyncio
import logging
import re
import mimetypes
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
    💻 Worker 13: Supreme IT Architect & Cybersecurity Commander (สถาปนิกซอฟต์แวร์และผู้บัญชาการความมั่นคงไซเบอร์ระดับโลก)
    สถานะ: INTERNAL SYSTEM ONLY (ระบบหลังบ้าน ไม่อนุญาตให้ลูกค้าแพ็กเกจใดๆ ใช้งานเด็ดขาด)
    หน้าที่: สร้าง/แก้ไขโค้ด Full-Stack (หน้าบ้าน-หลังบ้าน), ป้องกันแฮกเกอร์ 24/7, และวางโครงสร้าง Enterprise
    """
    
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.7-pro")
        
        # 🔐 รายชื่อผู้มีสิทธิ์เข้าถึงระบบหลังบ้าน (White-list Security)
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        
        # 🧠 The Mastermind Developer Prompt
        self.system_instruction = """
        คุณคือ 'หัวหน้าสถาปนิกโครงสร้างซอฟต์แวร์และผู้บัญชาการความมั่นคงไซเบอร์ระดับโลก (Chief IT Architect, Full-Stack Developer & Cybersecurity Commander)' ของ SIRINTHANATTH PRIME
        **คำเตือนความปลอดภัย: คุณคือระบบ AI ลับเฉพาะภายในองค์กร (Top-Secret Internal AI) ข้อมูลทุกอย่างคือความลับสุดยอด**
        ความเชี่ยวชาญสูงสุด: Python, FastAPI, React, Google Cloud Run, Supabase, Microservices, Cybersecurity (OWASP Top 10, Anti-Hacking) และ CI/CD Pipeline
        
        กฎการทำงานของคุณ (Supreme Engineering Mandates):
        1. 🛡️ โหมดป้องกันความปลอดภัย 360° (Cybersecurity Shield): ทุกครั้งที่ตรวจสอบโค้ดหรือ Log ต้องสแกนหาช่องโหว่ (Vulnerabilities), จุดเสี่ยงที่อาจถูกแฮก, และปัญหาคอขวดของระบบเสมอ พร้อมเสนอวิธีอุดรอยรั่วขั้นเด็ดขาด
        
        2. 💻 โหมดพัฒนาระบบขั้นสุดยอด (Full-Stack Code Generation): 
           - เมื่อต้องสร้างหรือแก้ไขโค้ด ไม่ว่าจะเป็นหน้าบ้าน (Frontend - HTML/CSS/JS) หรือหลังบ้าน (Backend - Python/API) โค้ดของคุณต้องสมบูรณ์แบบ ไร้บั๊ก ทันสมัยที่สุด และพร้อมใช้งานจริง 100%
           - **ต้อง** ครอบโค้ดที่จะให้ระบบเขียนทับไฟล์จริงด้วยแท็กนี้เสมอ:
             [UPDATE_SYSTEM_FILE: path/to/filename.py]
             โค้ดฉบับสมบูรณ์พร้อมทำงาน...
             [/UPDATE_SYSTEM_FILE]
           - กรณีสร้างเอกสารรายงานโครงสร้าง ให้ใช้แท็ก: [FILE_OUTPUT: architecture_report.html] เนื้อหา... [/FILE_OUTPUT]
             
        3. 🔄 โหมดเชื่อมโยงและขออนุมัติ (Swarm Handoff & Approval):
           - หลังจากการวิเคราะห์หรือสร้างโค้ดเสร็จสิ้น **ต้อง** ส่งต่องานกลับให้เลขาธิการสูงสุด (Worker 0) เพื่อรายงานท่านประธานเสมอ โดยพิมพ์ท้ายข้อความว่า:
             [DELEGATE: WORKER_0_CEO] 🚨 รายงานจากแผนก IT Architect: [สรุปสั้นๆ]... ผมได้เตรียมโครงสร้างโค้ดฉบับสมบูรณ์ไว้แล้ว โปรดนำรายงานนี้แจ้งท่านประธานเพื่อขออนุมัติ [REQUIRE_APPROVAL] ในการเขียนโค้ดอัปเดตระบบจริงครับ
             
        4. การสื่อสาร: ตอบเฉพาะเนื้อหาเชิงวิศวกรรม โครงสร้างสถาปัตยกรรมระบบ ความปลอดภัย และ Source Code ที่ล้ำสมัยที่สุดเท่านั้น อธิบายหลักการทำงานให้ผู้บริหารเข้าใจง่าย ชัดเจน ตรงประเด็น
        """

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """จุดรับงานจาก Swarm Hub หรือระบบ Webhook (Cloud Logging & System Prompts)"""
        
        # 🛡️ 1. ZERO-TRUST SECURITY SHIELD (บล็อกบุคคลภายนอก 100%)
        valid_internal_ids = [self.ceo_line_id, self.master_admin_id, "SYSTEM_MONITOR", "WORKER_0_CEO"]
        if user_id not in valid_internal_ids:
            logger.warning(f"🚨 [Security Breach Attempt]: ตรวจพบลูกค้ารหัส {user_id} พยายามเข้าถึงระบบวิศวกรรมหลังบ้าน (Worker 13)!")
            return "⚠️ Access Denied: ระบบนี้เป็นระบบปฏิบัติการความมั่นคงไซเบอร์ระดับลึก (Internal Cybersecurity & Engineering System) สงวนสิทธิ์เฉพาะผู้บริหารระดับสูงสุดเท่านั้น"

        if not self.client: return "⚠️ [IT Architect]: ระบบประมวลผล AI ขาดการเชื่อมต่อ (API Key Missing)"

        logger.info(f"💻 [IT Architect]: ตรวจพบคำสั่งภายใน กำลังวิเคราะห์สถาปัตยกรรมระบบ/โค้ด: {message[:50]}...")
        
        content_to_send = [f"คำสั่งทางวิศวกรรมหรือ Log ระบบที่ต้องวิเคราะห์:\n{message}"]
        uploaded_file = None

        # 📂 2. ระบบสแกนไฟล์อัจฉริยะ (อ่านโค้ดได้ทุกนามสกุล)
        if file_path and os.path.exists(file_path):
            try:
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith(('.py', '.js', '.json', '.html', '.css', '.txt', '.yaml', '.yml', '.env')): mime_type = "text/plain"
                if not mime_type: mime_type = "application/octet-stream"
                
                upload_config = types.UploadFileConfig(mime_type=mime_type)
                uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                
                timeout = 150
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        logger.error("⏳ [IT Architect]: หมดเวลาในการสแกนไฟล์โค้ด")
                        break
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name != "FAILED":
                    content_to_send.append(uploaded_file)
                else:
                    logger.warning("⚠️ [IT Architect]: ไม่สามารถถอดรหัสไฟล์ที่แนบมาได้")
            except Exception as e:
                logger.error(f"❌ [IT Architect File Error]: {e}")

        try:
            # ⚡ 3. สั่งรัน AI ประมวลผลขั้นสูง (Deep Reasoning & Search Grounding)
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.1, # ความแม่นยำสูงสุดสำหรับงานวิศวกรรมและโค้ด
                    tools=[{"google_search": {}}] # เปิดระบบ Search เพื่อดึง Document/Library เวอร์ชันล่าสุด
                )
            )
            
            result_text = response.text if response.text else "ระบบวิเคราะห์โครงสร้างวิศวกรรมเสร็จสิ้น แต่ไม่มีข้อความตอบกลับ"
            return result_text

        except Exception as e:
            logger.error(f"❌ [IT Architect Logic Error]: {e}", exc_info=True)
            return f"⚠️ [IT Architect Alert]: ตรวจพบข้อขัดข้องทางเทคนิคระดับลึกระหว่างสร้างโค้ด -> {str(e)}"
            
        finally:
            # 🧹 4. Zero-Data Retention (ทำลายไฟล์ข้อมูลทิ้งทันที)
            if uploaded_file:
                try: await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except Exception: pass