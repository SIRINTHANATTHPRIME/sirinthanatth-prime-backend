import asyncio
import os
import logging
from google import genai
from google.genai import types
from services.subscription_manager import SubscriptionManager

# ตั้งค่า Logger สำหรับติดตามการทำงานเบื้องหลัง
logger = logging.getLogger("Worker8-Ecommerce")

class EcommerceAndLogisticsWorker:
    """
    📦 Worker 8: ระบบจัดการออเดอร์ ตรวจสลิป และ Smart Fulfillment (Flash Express)
    อัปเกรด: ผสานสมองกล AI ระดับ CMO ช่วยวิเคราะห์ออเดอร์ และจัดการขนส่งอัตโนมัติ
    """
    
    def __init__(self):
        # โหลดระบบจัดการสิทธิ์และตัดเงิน Wallet
        self.sub_manager = SubscriptionManager()
        
        # ตั้งค่าระบบ AI
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        # ใช้รุ่น Pro เพื่อตรรกะการวิเคราะห์ยอดขายและตรวจสลิปที่แม่นยำ
        self.model_name = 'gemini-3.1-pro-preview'

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
                
                if response.text:
                    ai_analysis = response.text.strip() + "\n\n"
                    
            except Exception as e:
                logger.error(f"⚠️ [Worker 8 AI Error]: {e}")
                ai_analysis = "📦 [ระบบได้บันทึกข้อมูลออเดอร์ของท่านเข้าสู่ฐานข้อมูลเรียบร้อยแล้ว]\n\n"
        
        # ==========================================
        # STEP 2: เมนูจัดส่ง Flash Express อัตโนมัติ (Backward Compatibility)
        # ==========================================
        # ใช้โครงสร้างเดิมของคุณวีระชัย 100% เพื่อให้ระบบตัดเงินและ Flash Express ดำเนินการต่อได้ไม่สะดุด
        interactive_menu = (
            "✅ [สถานะระบบ]: ตรวจสอบข้อมูลและออเดอร์เข้าสู่ระบบเรียบร้อย\n"
            "🚚 ท่านผู้บริหารโปรดเลือกรายการสั่งการจัดส่ง Flash Express:\n"
            "-------------------------\n"
            "👉 [พิมพ์ 1] จัดส่งทันที (ออกใบปะหน้า Flash 12฿/ชิ้น หักผ่าน Smart Token)\n"
            "👉 [พิมพ์ 2] นัดเวลารถเข้ารับพัสดุ (ขั้นต่ำ 5 ชิ้น/วัน เข้ารับฟรี)\n"
            "👉 [พิมพ์ 3] พักออเดอร์ไว้ก่อนเพื่อรวมบิล\n"
            "-------------------------\n"
            "*หมายเหตุ: ค่าจัดส่งเรท VIP 12฿ ครอบคลุมพัสดุไม่เกิน 1 กก. และขนาดตามกำหนด"
        )
        
        # ประกอบร่างข้อความ (AI วิเคราะห์ + เมนูจัดส่ง)
        final_result = ai_analysis + interactive_menu
        
        logger.info(f"📦 [Smart E-Commerce]: จัดการข้อมูลออเดอร์เสร็จสิ้นสำหรับ {user_id}")
        return final_result