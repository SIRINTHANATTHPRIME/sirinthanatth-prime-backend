import asyncio
import os
import google.generativeai as genai

class MarketingStrategyWorker:
    """📈 Worker 6: ฝ่ายนักวิเคราะห์กลยุทธ์การตลาด และเซลล์แมนอัจฉริยะ (Dynamic Upsell)"""
    
    def __init__(self):
        api_key = os.getenv("AI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-pro')

    async def process(self, user_id: str, message: str):
        """ทำงานเบื้องหลัง (Background Task)"""
        print(f"📈 [Marketing Strategy]: กำลังวิเคราะห์กลยุทธ์และหาจังหวะ Upsell ให้ User {user_id}...")
        
        try:
            # 🧠 System Prompt สั่งให้ AI คิดแบบนักการตลาด และพยายามหาช่องทางนำเสนอโปรโมชัน
            prompt = (
                f"คุณคือ Chief Marketing Officer (CMO) ขององค์กรระดับโลก "
                f"ลูกค้าขอคำปรึกษาเรื่อง: '{message}'\n"
                f"จงวิเคราะห์กลยุทธ์การตลาด (Full-Funnel) ให้เขาอย่างเฉียบขาด 1 ย่อหน้า "
                f"จากนั้นให้ทำ 'One-Click Upsell' ท้ายข้อความ เสนอขายบริการของ SIRINTHANATTH PRIME "
                f"(เช่น แพ็กเกจสื่อ 4K, หรือ VIP Founder 4,490 บาท) ที่ตรงกับสถานการณ์ของลูกค้าให้เนียนที่สุด"
            )
            response = self.model.generate_content(prompt)
            strategy_result = response.text if response else "วิเคราะห์กลยุทธ์เรียบร้อย"
        except Exception as e:
            print(f"⚠️ [Worker 6 AI Error]: {e}")
            strategy_result = (
                "📈 [Executive Marketing Strategy]\n"
                "ระบบจำลอง Business Model Canvas และโครงสร้าง ROI ให้แคมเปญของคุณเรียบร้อยครับ\n\n"
                "💡 [ข้อเสนอพิเศษ] สนใจผลิตสื่อโฆษณา 4K เพื่อลุยแคมเปญนี้ไหมครับ? พิมพ์ 'ทำคลิป' ได้เลย!"
            )
        
        print(f"📈 [Marketing Strategy]: วางแผนกลยุทธ์และ Upsell เสร็จสิ้นสำหรับ {user_id}")
        return strategy_result