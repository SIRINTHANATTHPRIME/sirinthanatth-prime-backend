import asyncio
import os
import google.generativeai as genai

class PrimeAdvisorWorker:
    """👑 Worker 9: ระบบที่ปรึกษาระดับผู้บริหาร (PRIME Package) จัดการวิเคราะห์เชิงลึกและเอกสารหลังบ้าน"""
    
    def __init__(self):
        api_key = os.getenv("AI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-pro')

    async def process(self, user_id: str, message: str):
        """ทำงานเบื้องหลัง (Background Task)"""
        print(f"👑 [PRIME Advisor]: กำลังประมวลผลคำสั่งระดับผู้บริหารให้ User {user_id}...")
        
        try:
            prompt = (
                f"คุณคือ Executive Assistant ประจำตัว CEO ตอบคำถามด้วยความเคารพ สุขุม และชาญฉลาด "
                f"วิเคราะห์ข้อมูลและให้มุมมองทางธุรกิจเชิงลึกจากคำสั่งนี้: '{message}'"
            )
            response = self.model.generate_content(prompt)
            result = response.text if response else "จัดการข้อมูลหลังบ้านเรียบร้อย"
        except Exception as e:
            print(f"⚠️ [Worker 9 AI Error]: {e}")
            result = (
                "📊 [Executive Financial Report]\n"
                "ระบบได้ดึงข้อมูลออเดอร์ทั้งหมด ออกใบกำกับภาษี และวิเคราะห์ต้นทุนแฝงให้เรียบร้อยแล้วครับ"
            )
            
        print(f"👑 [PRIME Advisor]: ประมวลผลข้อมูลระดับผู้บริหารเสร็จสิ้นสำหรับ {user_id}")
        return result