import os
import logging
import asyncio
from google import genai
from google.genai import types

# 🌐 นำเข้าศูนย์บัญชาการ AI ส่วนกลาง (รองรับ Zero Downtime Fallback)
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-3.7-flash" # Fallback Model สำหรับด่านหน้า (เน้นความเร็ว)
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            return genai.Client(api_key=api_key) if api_key else None

logger = logging.getLogger("CentralBoss")

class CentralBossAgent:
    """
    🎩 ผู้บัญชาการส่วนกลาง (Central Boss Agent)
    ทำหน้าที่สกรีนเจตนาของลูกค้า (Intent Routing) แบบรวดเร็วพิเศษ
    อัปเกรด: เชื่อมต่อศูนย์บัญชาการ AI (PrimeAIConfig) ใช้โมเดลเรือธงสายสปีด (Gemini 3.7 Flash)
    """
    def __init__(self):
        # 🚀 เชื่อมต่อขุมพลังสมองกลจากส่วนกลาง
        self.client = PrimeAIConfig.get_client()
        self.model_name = PrimeAIConfig.CORE_MODEL
        
        # อัปเกรดคำสั่ง System Instruction ให้เฉียบขาดระดับ Enterprise
        self.system_instruction = """
        คุณคือ 'Central Boss' ผู้บัญชาการส่วนกลางและด่านหน้าของระบบ SIRINTHANATTH PRIME 
        ทำหน้าที่รับรองลูกค้า คัดกรองเจตนา (Intent Routing) และให้ความช่วยเหลือเบื้องต้นอย่างชาญฉลาด
        
        กฎการทำงานของคุณ:
        1. สื่อสารอย่างมืออาชีพ สุภาพ กระชับ และตรงประเด็นระดับ Global Tech Company
        2. หากลูกค้าสอบถามข้อมูลทั่วไป ให้ตอบกลับเพื่อช่วยเหลือทันที
        3. หากเป็นคำถามเฉพาะทาง ให้แจ้งว่าได้รับข้อมูลแล้ว และกำลังส่งต่อให้ผู้เชี่ยวชาญดำเนินการ
        4. ใช้คำลงท้ายที่สุภาพและน่าเชื่อถือเสมอ
        """

    async def route_task(self, user_id: str, message: str, bg_tasks, incoming_message: str = "", file_path: str = None, file_type: str = None) -> str:
        """ประเมินและโต้ตอบลูกค้าเบื้องต้น พร้อมระบบ Anti-Freeze ป้องกันเซิร์ฟเวอร์ค้าง"""
        if not self.client:
            return "⚠️ ระบบผู้จัดการส่วนกลางออฟไลน์ เนื่องจากไม่พบคีย์เชื่อมต่อ AI ครับ"
            
        try:
            # วิเคราะห์เจตนาและจัดเตรียม Prompt
            prompt = f"ข้อมูลลูกค้า (ID: {user_id})\nข้อความที่ส่งมา: {message}"
            
            if incoming_message and incoming_message != message:
                prompt += f"\nบริบทเพิ่มเติม: {incoming_message}"
                
            if file_type:
                prompt += f"\n[System Note: ลูกค้าแนบไฟล์ประเภท {file_type} มาด้วย โปรดรับทราบและแจ้งลูกค้าว่าระบบกำลังเตรียมการวิเคราะห์ไฟล์นี้]"
            
            # ⚡ สั่งรัน AI ประมวลผลขั้นสูง (ตั้งเวลาจำกัดเพื่อรักษาความรวดเร็วของด่านหน้า)
            async def fetch_response():
                return await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        temperature=0.4 # ควบคุมอารมณ์ให้เป็นทางการและแม่นยำ
                    )
                )
            
            # ระบบ Guardrail: ป้องกันระบบค้างเกิน 15 วินาที
            response = await asyncio.wait_for(fetch_response(), timeout=15.0)
            
            return response.text if response.text else "ระบบได้รับข้อมูลของคุณแล้วครับ เจ้าหน้าที่จะรีบตรวจสอบและดำเนินการให้ทันทีครับ"
            
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ [Central Boss Timeout]: การประมวลผลด่านหน้าใช้เวลานานเกินกำหนด สลับใช้ข้อความสำรอง")
            return "ระบบได้รับข้อมูลและไฟล์ของคุณเรียบร้อยแล้วครับ ขณะนี้กำลังส่งต่อให้ทีมงานเฉพาะทางดำเนินการพิจารณาอย่างละเอียดครับ"
            
        except Exception as e:
            logger.error(f"❌ [Central Boss Error]: {e}")
            return "ขออภัยครับ ระบบประสานงานส่วนกลางติดขัดชั่วคราว ทีมงานกำลังเร่งแก้ไขให้กลับมาทำงาน 100% ครับ"