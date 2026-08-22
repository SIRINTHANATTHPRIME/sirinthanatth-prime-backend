import os
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

logger = logging.getLogger("Worker8-Ecommerce")

class EcommerceWorker:
    """
    🛒 Worker 8: E-Commerce & Legal Compliance Specialist (ผู้เชี่ยวชาญ E-Commerce และกฎหมายธุรกิจ)
    อัปเกรด: [Gemini 2.5 Pro] เพื่อบริหารจัดการระบบการค้าออนไลน์และกฎระเบียบข้อบังคับ
    """
    def __init__(self):
        # โหลดระบบจัดการสิทธิ์และตัดเงิน Wallet
        self.sub_manager = SubscriptionManager()
        
        # ตั้งค่าระบบ AI
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        # ใช้รุ่น Pro เพื่อตรรกะการวิเคราะห์ยอดขายและตรวจสลิปที่แม่นยำ
        self.model_name = 'gemini-1.5-pro'

    async def process(self, user_id: str, message: str) -> str:
        """ทำงานเบื้องหลัง (Background Task) สำหรับจัดการร้านค้าและโลจิสติกส์"""
        logger.info(f"📦 [Smart E-Commerce]: กำลังวิเคราะห์ออเดอร์และสลิปให้ User {user_id}...")
        
        ai_analysis = ""
        
        # ==========================================
        # STEP 1: ให้ AI วิเคราะห์ข้อมูลออเดอร์/สลิป (Data Extraction & Strategy)
        # ==========================================
        if self.client:
            try:
                system_instruction = """
                คุณคือ 'Chief E-commerce & Logistics Officer (CELO)' ของ SIRINTHANATTH PRIME
                หน้าที่ของคุณคือ:
                1. ตรวจสอบข้อมูลออเดอร์ สลิปโอนเงิน หรือคำสั่งซื้อที่ลูกค้าส่งมา และสรุปยอดให้ชัดเจน
                2. ให้คำแนะนำสั้นๆ เกี่ยวกับการบริหารสต๊อกสินค้า หรือเทคนิคเพิ่มยอดขาย (Upsell/Cross-sell) จากออเดอร์นี้
                3. ตอบกลับอย่างมืออาชีพ กระชับ เพื่อให้เจ้าของร้านทำงานต่อได้รวดเร็วที่สุด
                """
                
                prompt = f"ลูกค้า/ร้านค้า แจ้งข้อมูลออเดอร์เข้ามาดังนี้: '{message}'"
                
                # ⚡ รันแบบ Asynchronous ไม่ให้บล็อกเซิร์ฟเวอร์
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.3 # ควบคุมอุณหภูมิต่ำเพื่อเน้นความถูกต้องของข้อมูลตัวเลขและออเดอร์
                    )
                )
            )
            return response.text if response.text else "✅ ตรวจสอบข้อกฎหมายและระบบเสร็จสิ้นครับ"

        except Exception as e:
            logger.error(f"❌ [Worker 8 Error]: {e}")
            return f"⚠️ [Worker 8]: ระบบ E-Commerce ขัดข้องชั่วคราวครับ (Debug: {str(e)[:100]})"

        finally:
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except:
                    pass
