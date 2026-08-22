import os
import time
import logging
import asyncio
from google import genai
from google.genai import types

logger = logging.getLogger("PromoAutopilot")

class PromoAutopilotService:
    """
    🎉 Festival & Promo Auto-Pilot Service
    ระบบสร้างสรรค์แคมเปญโปรโมชันตามเทศกาลอัตโนมัติ พร้อมระบบ Human-in-the-Loop (Accept / Modify)
    """
    def __init__(self):
        self.api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.model_name = 'gemini-2.5-pro' # ใช้สมองกลสายวิเคราะห์เชิงลึกเพื่อการตลาด

    async def generate_seasonal_campaign(self, store_name: str, festival_name: str, product_details: str) -> dict:
        """สร้างสรรค์แคมเปญและแคปชันโฆษณาตามเทศกาล พร้อมสร้าง Flex Message สำหรับพรีวิว"""
        if not self.client:
            return {"type": "text", "text": "⚠️ ระบบ AI ออฟไลน์ ไม่สามารถสร้างแคมเปญอัตโนมัติได้ในขณะนี้ครับ"}

        prompt = f"""
        คุณคือนักการตลาดระดับโลก ประจำระบบ SIRINTHANATTH PRIME
        จงสร้างสรรค์แคมเปญโปรโมชันต้อนรับเทศกาล '{festival_name}' สำหรับร้านค้า '{store_name}' 
        โดยมีรายละเอียดสินค้า/บริการดังนี้: {product_details}
        
        กรุณาจัดทำผลลัพธ์ในรูปแบบโครงสร้างที่คมชัด ประกอบด้วย:
        1. ชื่อแคมเปญสุดปัง (Catchy Campaign Title)
        2. ข้อเสนอพิเศษ/ส่วนลดกระตุ้นยอดขาย (Special Offer)
        3. แคปชันโฆษณาพร้อมใช้งาน (Ad Copy & Hashtags) สำหรับโพสต์ลงโซเชียลมีเดีย
        4. คำแนะนำเทคนิคการยิงแอดหรือโปรโมทให้ได้ผลลัพธ์สูงสุด
        """

        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.7 # เพิ่มความคิดสร้างสรรค์ระดับการตลาด
                )
            )
            campaign_text = response.text if response.text else "ไม่สามารถประมวลผลแคมเปญได้ในขณะนี้"
            
            # สร้างรหัสเฉพาะสำหรับแคมเปญนี้เพื่อรอรับคำสั่งปุ่มกด
            campaign_id = f"PROMO_{int(time.time())}"
            
            # ส่งคืนในรูปแบบ LINE Flex Message สไตล์พรีเมียม (Navy & Gold) พร้อม 2 ปุ่ม (อนุมัติโพสต์ / ขอแก้ไข)
            return self._build_promo_flex_message(campaign_text, campaign_id, festival_name)

        except Exception as e:
            logger.error(f"❌ [Promo Autopilot Error]: {e}")
            return {"type": "text", "text": f"⚠️ เกิดข้อผิดพลาดในการสร้างแคมเปญ: {str(e)[:100]}"}

    def _build_promo_flex_message(self, campaign_text: str, campaign_id: str, festival_name: str) -> dict:
        """สร้างการ์ดพรีวิวโปรโมชันบน LINE (Flex Message)"""
        return {
            "type": "flex",
            "altText": f"🎉 แผนโปรโมชันพิเศษเทศกาล {festival_name} พร้อมพิจารณา",
            "contents": {
                "type": "bubble",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "🎉 FESTIVAL AUTO-PILOT", "weight": "bold", "color": "#D4AF37", "size": "xs"},
                        {"type": "text", "text": f"แคมเปญ: {festival_name}", "weight": "bold", "color": "#FFFFFF", "size": "md", "margin": "sm"}
                    ],
                    "backgroundColor": "#0F172A"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text", 
                            "text": campaign_text[:350] + "...\n\n(ตรวจสอบรายละเอียดฉบับเต็มด้านบน)", 
                            "wrap": True, 
                            "size": "sm",
                            "color": "#333333"
                        }
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#00B900",
                            "action": {"type": "message", "label": "✅ อนุมัติและโพสต์ทันที", "text": f"ACTION:PROMO_ACCEPT:{campaign_id}"}
                        },
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#D4AF37",
                            "action": {"type": "message", "label": "📝 ขอปรับแก้แคปชัน/ส่วนลด", "text": f"ACTION:PROMO_MODIFY:{campaign_id}"}
                        }
                    ]
                }
            }
        }