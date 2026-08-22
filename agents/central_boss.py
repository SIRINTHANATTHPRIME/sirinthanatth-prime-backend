import os
import logging
import asyncio
from google import genai
from google.genai import types

logger = logging.getLogger("CentralBoss")

class CentralBossAgent:
    """
    🎩 ผู้บัญชาการส่วนกลาง (Central Boss Agent)
    ทำหน้าที่สกรีนเจตนาของลูกค้า (Intent Routing) แบบรวดเร็วพิเศษ
    อัปเกรด: [Gemini 3.7 Flash] ระบบ SDK ใหม่ล่าสุด ตัดปัญหา Error 404
    """
    def __init__(self):
        self.api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        
        # 🚀 ใช้สมองกลสายสปีดความเร็วแสง
        self.model_name = 'gemini-3.7-flash' 
        
    async def route_task(self, user_id: str, message: str, bg_tasks, incoming_message: str = "", file_path: str = None, file_type: str = None) -> str:
        """ประเมินและโต้ตอบลูกค้าเบื้องต้น ในกรณีที่ระบบหลักขัดข้อง"""
        if not self.client:
            return "⚠️ ระบบผู้จัดการส่วนกลางออฟไลน์ เนื่องจากไม่พบคีย์เชื่อมต่อ AI ครับ"
            
        try:
            system_instruction = """
            คุณคือ 'Central Boss' ผู้จัดการคัดกรองคำสั่งขั้นสูงสุดของ SIRINTHANATTH PRIME
            หน้าที่ของคุณคือประเมินความต้องการของลูกค้า และตอบกลับด้วยความเป็นมืออาชีพ สุภาพ และช่วยเหลือ
            หากคำถามเป็นการทักทายทั่วไป ให้ตอบกลับเพื่อต้อนรับทันที
            """
            
            prompt = f"ลูกค้า (ID: {user_id}) ส่งข้อความมาว่า: {message}"
            if file_type:
                prompt += f"\n[หมายเหตุ: ลูกค้าแนบไฟล์ประเภท {file_type} มาด้วย แต่ยังไม่ต้องเจาะลึกไฟล์]"
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.4 # ควบคุมอารมณ์ให้เป็นทางการและแม่นยำ
                )
            )
            return response.text if response.text else "ระบบได้รับข้อมูลของคุณแล้วครับ เจ้าหน้าที่จะรีบตรวจสอบและดำเนินการให้ครับ"
            
        except Exception as e:
            logger.error(f"❌ [Central Boss Error]: {e}")
            return "ขออภัยครับ ระบบประสานงานส่วนกลางติดขัดชั่วคราว ทีมงานกำลังเร่งแก้ไขครับ"
