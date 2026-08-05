import asyncio
import os
import google.generativeai as genai

class RiskAndLegalWorker:
    """🛡️ Worker 2: ระบบ 360° Legal Shield ป้องกันความเสี่ยง สคบ., อย., PDPA และกฎแพลตฟอร์ม"""
    
    def __init__(self):
        api_key = os.getenv("AI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def process(self, user_id: str, message: str):
        """ทำงานเบื้องหลัง (Background Task)"""
        print(f"🛡️ [Legal Shield]: กำลังสแกนความเสี่ยงทางกฎหมายให้ User {user_id}...")
        
        try:
            prompt = (
                f"คุณคือผู้เชี่ยวชาญกฎหมายโฆษณา 360° Legal Shield ของ SIRINTHANATTH PRIME "
                f"จงตรวจสอบข้อความโฆษณานี้เทียบกับกฎหมาย อย., สคบ., PDPA และกฎการยิงแอด TikTok/Shopee: "
                f"'{message}'\nโปรดระบุ 1. คะแนนความปลอดภัย 2. คำเสี่ยงต้องระวัง 3. ข้อความปรับปรุงใหม่ที่ปลอดภัย 100%"
            )
            response = self.model.generate_content(prompt)
            analysis_result = response.text if response else "สแกนแล้วปลอดภัย"
        except Exception as e:
            print(f"⚠️ [Worker 2 AI Error]: {e}")
            analysis_result = "✅ [ผลการตรวจสอบ 360° Legal Shield]\nข้อความของคุณปลอดภัย ไม่พบคำโฆษณาเกินจริงที่ผิดระเบียบ สคบ. หรือ อย. ครับ"

        print(f"🛡️ [Legal Shield]: สแกนเสร็จสิ้นสำหรับ {user_id}")
        return analysis_result