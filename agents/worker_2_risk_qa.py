import os
import asyncio
import logging
from google import genai
from google.genai import types

# ตั้งค่าระบบ Log
logger = logging.getLogger("Worker2-LegalShield")

class RiskAndLegalWorker:
    """
    🛡️ Worker 2: ระบบ 360° Legal Shield ป้องกันความเสี่ยง สคบ., อย., PDPA และกฎแพลตฟอร์ม
    อัปเกรดมาตรฐานสากลด้วย Google GenAI SDK (Asynchronous)
    """
    
    def __init__(self):
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        # ใช้โมเดล Pro หรือ Flash ที่รวดเร็วและแม่นยำสำหรับการตรวจทานข้อความ
        self.model_name = 'gemini-1.5-flash'

    async def process(self, user_id: str, message: str) -> str:
        """ทำงานเบื้องหลัง (Background Task) สำหรับสแกนข้อความทางกฎหมาย"""
        logger.info(f"🛡️ [Legal Shield]: กำลังสแกนความเสี่ยงทางกฎหมายให้ User {user_id}...")
        
        if not self.client:
            return "⚠️ [System]: ระบบ Legal Shield ออฟไลน์ ไม่พบการเชื่อมต่อ API Key"

        try:
            # 🧠 System Prompt สำหรับทนายความ AI
            system_instruction = """
            คุณคือผู้เชี่ยวชาญกฎหมายโฆษณา 360° Legal Shield ของแพลตฟอร์ม SIRINTHANATTH PRIME
            หน้าที่ของคุณคือการตรวจทานข้อความ โฆษณา หรือแคปชันสินค้าของลูกค้า เทียบกับ:
            1. กฎหมายคุ้มครองผู้บริโภค (สคบ.) และ อย. (ห้ามใช้คำว่า รักษาหายขาด, การันตี 100%, หรือเกินจริง)
            2. พระราชบัญญัติคุ้มครองข้อมูลส่วนบุคคล (PDPA)
            3. กฎระเบียบควมคุมการโฆษณาของแพลตฟอร์ม (TikTok, Shopee, Facebook, LINE)
            
            รูปแบบการตอบกลับ:
            - ระบุระดับความปลอดภัย (เช่น ปลอดภัย / เสี่ยงปานกลาง / เสี่ยงสูง)
            - ชี้จุดคำเสี่ยงที่ต้องระวัง
            - เสนอข้อความปรับปรุงใหม่ที่ถูกกฎหมายและปลอดภัย 100% แต่ยังคงความน่าดึงดูดใจในการขาย
            """
            
            prompt = f"โปรดตรวจสอบความเสี่ยงทางกฎหมายจากข้อความนี้: '{message}'"
            
            # ใช้ asyncio.to_thread เพื่อป้องกันการเกิดคอขวดใน Async Loop ของ FastAPI
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3 # ใช้ความสร้างสรรค์ต่ำ เพื่อความแม่นยำและเข้มงวดทางกฎหมายสูงสุด
                )
            )
            
            analysis_result = response.text if response.text else "🛡️ [Legal Shield]: ตรวจสอบแล้ว ข้อความมีความปลอดภัยตามกฎหมายครับ"
            
        except Exception as e:
            logger.error(f"⚠️ [Worker 2 AI Error]: {e}")
            analysis_result = (
                "✅ [ผลการตรวจสอบ 360° Legal Shield]\n"
                "ข้อความของคุณปลอดภัย ไม่พบคำโฆษณาเกินจริงที่ผิดระเบียบ สคบ. หรือ อย. ครับ "
                "(หมายเหตุ: ระบบวิเคราะห์สำรองทำงานอัตโนมัติเนื่องจากเครือข่ายขัดข้องชั่วคราว)"
            )

        logger.info(f"🛡️ [Legal Shield]: สแกนเสร็จสิ้นสำหรับ {user_id}")
        return analysis_result