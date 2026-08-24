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
        self.model_name = 'gemini-2.5-pro' # ใช้สมองกลสายวิเคราะห์เชิงลึกระดับโลก

    async def generate_seasonal_campaign(self, store_name: str, festival_name: str, product_details: str) -> dict:
        """สร้างสรรค์แคมเปญและแคปชันโฆษณา พร้อมสร้าง Flex Message สำหรับพรีวิวแบบเรียลไทม์"""
        if not self.client:
            logger.warning("⚠️ [Promo]: API Key missing, skipping generation.")
            return {"type": "text", "text": "⚠️ ระบบ AI ออฟไลน์ ไม่สามารถสร้างแคมเปญอัตโนมัติได้ในขณะนี้ครับ"}

        prompt = f"""
        คุณคือนักการตลาดระดับโลก ประจำระบบ SIRINTHANATTH PRIME
        จงสร้างสรรค์แคมเปญโปรโมชันต้อนรับเทศกาล '{festival_name}' สำหรับร้านค้า '{store_name}' 
        โดยมีรายละเอียดสินค้า/บริการดังนี้: {product_details}
        
        กรุณาจัดทำผลลัพธ์ในรูปแบบโครงสร้างที่คมชัด ดึงดูดลูกค้า ประกอบด้วย:
        1. ชื่อแคมเปญสุดปัง (Catchy Campaign Title)
        2. ข้อเสนอพิเศษ/ส่วนลดกระตุ้นยอดขาย (Special Offer)
        3. แคปชันโฆษณาพร้อมใช้งาน (Ad Copy & Hashtags) สำหรับโพสต์ลงโซเชียลมีเดีย
        4. คำแนะนำเทคนิคการยิงแอดสั้นๆ ให้ได้ผลลัพธ์สูงสุด
        """

        try:
            logger.info(f"🚀 [Promo]: กำลังวิเคราะห์แคมเปญ '{festival_name}' สำหรับ '{store_name}'")
            
            # โยนภาระไปให้ Thread ย่อย ไม่ให้เซิร์ฟเวอร์หลักพังตอน AI คิดงานนาน
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.75 # ปรับให้สร้างสรรค์แตะระดับ Marketing สากล
                )
            )
            campaign_text = response.text if response.text else "ระบบไม่สามารถประมวลผลข้อความได้"
            
            # สร้างรหัสเฉพาะ (ID) สำหรับแคมเปญนี้เพื่อรอรับคำสั่งปุ่มกด
            campaign_id = f"PROMO_{int(time.time())}"
            
            logger.info(f"✅ [Promo]: สร้างแคมเปญ {campaign_id} สำเร็จ!")
            return self._build_promo_flex_message(campaign_text, campaign_id, festival_name)

        except Exception as e:
            logger.error(f"❌ [Promo Autopilot Error]: {e}")
            return {"type": "text", "text": f"⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อ AI นักการตลาด: {str(e)[:100]}"}

    def _build_promo_flex_message(self, campaign_text: str, campaign_id: str, festival_name: str) -> dict:
        """สร้างการ์ดพรีวิวโปรโมชันบน LINE (Flex Message ไซส์ Giga พรีเมียม)"""
        return {
            "type": "flex",
            "altText": f"🎉 แผนโปรโมชันพิเศษเทศกาล {festival_name} พร้อมพิจารณา",
            "contents": {
                "type": "bubble",
                "size": "giga",  # อัปเกรดไซส์การ์ดให้ใหญ่อ่านง่ายขึ้น
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "🎉 FESTIVAL AUTO-PILOT", "weight": "bold", "color": "#D4AF37", "size": "sm"},
                        {"type": "text", "text": f"แคมเปญ: {festival_name}", "weight": "bold", "color": "#FFFFFF", "size": "xl", "margin": "sm", "wrap": True}
                    ],
                    "backgroundColor": "#0A1128" # สีกรมท่าเข้มพรีเมียม
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text", 
                            "text": campaign_text[:400] + "...\n\n(ตรวจสอบรายละเอียดฉบับเต็มด้านบน)", 
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
                            "action": {"type": "message", "label": "✅ อนุมัติแคมเปญนี้", "text": f"ACTION:PROMO_ACCEPT:{campaign_id}"}
                        },
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#D4AF37",
                            "action": {"type": "message", "label": "📝 ขอปรับแก้แคปชันใหม่", "text": f"ACTION:PROMO_MODIFY:{campaign_id}"}
                        }
                    ]
                }
            }
        }