import os
import logging
import asyncio
from google import genai
from google.genai import types

logger = logging.getLogger("Worker9-Prime")

class PrimeWorker:
    """
    🌟 Worker 9: Flagship Core Orchestrator (สมองกลเรือธงหลัก)
    อัปเกรด: [Gemini 2.5 Pro] ประสานงานระบบภาพรวมและกลยุทธ์ขั้นสูง
    """
    def __init__(self):
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        # 🚀 ใช้รุ่น Pro สำหรับการวิเคราะห์เชิงลึกระดับผู้บริหารและการตรวจสอบสถาปัตยกรรม IT ที่ซับซ้อน
        self.model_name = 'gemini-1.5-pro'

    async def process(self, user_id: str, message: str) -> str:
        """ทำงานเบื้องหลัง (Background Task) สำหรับสิทธิพิเศษ PRIME Package"""
        logger.info(f"👑 [PRIME Advisor]: กำลังประมวลผลคำสั่งระดับผู้บริหาร (VVIP) ให้ User {user_id}...")
        
        if not self.client:
            return "⚠️ [Worker 9]: ระบบเรือธงออฟไลน์ (ไม่พบ API Key)"
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=message,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.5
                )
            )
            return response.text if response.text else "✅ ประมวลผลระดับเรือธงเสร็จสิ้นครับ"
        except Exception as e:
            logger.error(f"❌ [Worker 9 Error]: {e}")
            return f"⚠️ [Worker 9]: ระบบขัดข้องชั่วคราว ({str(e)[:80]})"
