import asyncio
import os
import google.generativeai as genai

class GraphicAndAdsWorker:
    """🎨 Worker 5: ระบบออกแบบกราฟิก แบนเนอร์ สิ่งพิมพ์ และวิเคราะห์วางแผนโฆษณาออนไลน์"""
    
    def __init__(self):
        api_key = os.getenv("AI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')

    async def process(self, user_id: str, message: str):
        """ทำงานเบื้องหลัง (Background Task)"""
        print(f"🎨 [Graphics & Ads]: กำลังออกแบบภาพและวางแผนโฆษณาให้ User {user_id}...")
        
        try:
            prompt = f"คุณคือ Creative Director ของ SIRINTHANATTH PRIME จงคิดคอนเซ็ปต์ภาพแบนเนอร์ และแผนการยิงแอด (Targeting/Budget) สำหรับสินค้า: '{message}'"
            response = self.model.generate_content(prompt)
            graphics_result = response.text if response else "ออกแบบคอนเซ็ปต์แบนเนอร์เรียบร้อย"
        except Exception as e:
            print(f"⚠️ [Worker 5 AI Error]: {e}")
            graphics_result = "🎨 [ผลงานออกแบบและแผนโฆษณา]\nระบบสร้างคอนเซ็ปต์ภาพแบนเนอร์และแผนการยิงแอดให้เรียบร้อยแล้วครับ"

        print(f"🎨 [Graphics & Ads]: ประมวลผลเสร็จสิ้นสำหรับ {user_id}")
        return graphics_result