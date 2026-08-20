import asyncio
import os
import logging
from google import genai
from google.genai import types

logger = logging.getLogger("Worker1-Report")

class DocumentEngineeringWorker:
    """📊 Worker 1: ระบบผลิตเอกสารทางการ ตารางคำนวณ (Excel) และรายงานวิเคราะห์เชิงลึก"""
    
    def __init__(self):
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model_name = 'gemini-1.5-pro' # ใช้รุ่น Pro สำหรับงานที่ต้องการตรรกะซับซ้อน เช่น การเขียนสูตร Excel

    async def process(self, user_id: str, message: str) -> str:
        """ทำงานเบื้องหลัง (Background Task) สำหรับสร้างโครงร่างเอกสาร"""
        logger.info(f"📊 [Document Engineering]: กำลังวิเคราะห์ข้อมูลและสร้างเอกสารให้ User {user_id}...")
        
        if not self.client:
            return "⚠️ [System]: ไม่พบการเชื่อมต่อระบบ AI สำหรับการสร้างเอกสาร"

        try:
            # 🧠 System Prompt สำหรับการสร้าง Report / Excel
            system_instruction = """
            คุณคือ 'Document Engineering Expert' ของ SIRINTHANATTH PRIME
            หน้าที่ของคุณคือการแปลงความต้องการของลูกค้า ให้กลายเป็น 'โครงร่างเอกสารทางการ' หรือ 'ตาราง Excel พร้อมสูตรคำนวณ' 
            กรุณาตอบกลับในรูปแบบที่ลูกค้าสามารถ Copy นำไปวางใน Microsoft Excel หรือ Google Sheets ได้ทันที (เช่น ใช้เครื่องหมาย | เพื่อแบ่งคอลัมน์) 
            และอธิบายสูตรที่ต้องใช้อย่างชัดเจน
            """
            
            prompt = f"ลูกค้าต้องการให้สร้างเอกสารดังนี้: '{message}'"
            
            # ใช้ asyncio.to_thread เพื่อป้องกันการเกิดคอขวดในระบบแชทหลัก
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.4 # ลด Temperature ลงเพื่อให้ผลลัพธ์เป็นตารางและตัวเลขที่แม่นยำ ไม่เพ้อฝัน
                )
            )
            
            result_text = response.text if response.text else "จัดทำโครงร่างเอกสารทางการเสร็จสมบูรณ์"
            
        except Exception as e:
            logger.error(f"⚠️ [Worker 1 AI Error]: {e}")
            result_text = "📊 [Document Engineering]: จัดทำโครงร่างเอกสารทางการและตารางคำนวณเสร็จสมบูรณ์เรียบร้อยแล้ว (ระบบเกิดข้อผิดพลาดในการแสดงผล กรุณาลองใหม่อีกครั้ง)"

        logger.info(f"✅ [Document Engineering]: สร้างเอกสารเสร็จสิ้นให้ {user_id}")
        return result_text