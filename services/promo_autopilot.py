import os
import time
import logging
import asyncio
from google import genai
from google.genai import types

# =========================================================
# 🌐 1. นำเข้าศูนย์บัญชาการ AI ส่วนกลาง (Vertex AI / Zero Downtime)
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-2.5-pro" # 🚀 อัปเกรดเป็นรุ่นเรือธงสำหรับงาน Creative & Marketing
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

logger = logging.getLogger("PromoAutopilot")

class PromoAutopilotService:
    """
    🎉 Festival & Promo Auto-Pilot Service
    ระบบสร้างสรรค์แคมเปญโปรโมชันเชิงรุกตามเทศกาลอัตโนมัติ (Proactive AI)
    พร้อมระบบ Human-in-the-Loop (Approval Workflow)
    """
    def __init__(self):
        # 🚀 โหลด Client และโมเดลรุ่นท็อปจากศูนย์กลาง
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-2.5-pro")

    async def generate_seasonal_campaign(self, store_name: str, festival_name: str, product_details: str) -> dict:
        """สร้างสรรค์แคมเปญและแคปชันโฆษณา พร้อมสร้าง Flex Message สำหรับพรีวิวแบบเรียลไทม์"""
        if not self.client:
            logger.warning("⚠️ [Promo]: API Key missing, skipping generation.")
            return {"type": "text", "text": "⚠️ ระบบ AI ศูนย์กลางออฟไลน์ ไม่สามารถสร้างแคมเปญอัตโนมัติได้ในขณะนี้ครับ"}

        system_instruction = """
        คุณคือ 'Chief Marketing Officer (CMO)' ระดับโลก ประจำระบบ SIRINTHANATTH PRIME
        หน้าที่ของคุณคือการคิดค้นแคมเปญการตลาดเชิงรุก (Proactive Marketing) ที่หรูหรา ดึงดูด และสร้างยอดขายได้จริง
        """

        prompt = f"""
        จงสร้างสรรค์แคมเปญโปรโมชันต้อนรับเทศกาล '{festival_name}' สำหรับแบรนด์ '{store_name}' 
        รายละเอียดสินค้า/บริการ: {product_details}
        
        กรุณาจัดทำผลลัพธ์ในรูปแบบโครงสร้างที่คมชัด ดึงดูดลูกค้า ประกอบด้วย:
        1. 🎯 ชื่อแคมเปญสุดปัง (Catchy Campaign Title)
        2. 🎁 ข้อเสนอพิเศษ/ส่วนลดกระตุ้นยอดขาย (Special Offer)
        3. 📝 แคปชันโฆษณาพร้อมใช้งาน (Ad Copy & Hashtags) สำหรับโพสต์ลงโซเชียลมีเดีย
        4. 💡 คำแนะนำเทคนิคการยิงแอด (Targeting & Media Buying) สั้นๆ ให้ได้ผลลัพธ์สูงสุด
        """

        try:
            logger.info(f"🚀 [Promo]: กำลังประมวลผลแคมเปญ '{festival_name}' สำหรับแบรนด์ '{store_name}'")
            
            async def fetch_campaign():
                return await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.8 # ปรับให้เปิดรับความคิดสร้างสรรค์แตะระดับ Marketing สากล
                    )
                )
            
            # ⏳ ระบบ Guardrail ป้องกันการประมวลผลค้าง (Anti-Freeze Timeout 45s)
            response = await asyncio.wait_for(fetch_campaign(), timeout=45.0)
            
            campaign_text = response.text.strip() if response.text else "ระบบไม่สามารถประมวลผลข้อความแคมเปญได้"
            
            # สร้างรหัสเฉพาะ (ID) สำหรับแคมเปญนี้เพื่อรอรับคำสั่งปุ่มกด
            campaign_id = f"PROMO_{int(time.time())}"
            
            logger.info(f"✅ [Promo]: สร้างร่างแคมเปญ {campaign_id} สำเร็จ! รอการอนุมัติ...")
            
            # ส่งกลับเป็น Flex Message ให้ผู้บริหารหรือแอดมินกดอนุมัติ
            return self._build_promo_flex_message(campaign_text, campaign_id, festival_name)

        except asyncio.TimeoutError:
            logger.error("❌ [Promo Autopilot Timeout]: AI ใช้เวลาคิดแคมเปญนานเกินไป")
            return {"type": "text", "text": "⚠️ ขออภัยครับ ระบบประมวลผลแคมเปญการตลาดใช้เวลานานกว่าปกติ รบกวนกดสั่งงานใหม่อีกครั้งนะครับ"}
        except Exception as e:
            logger.error(f"❌ [Promo Autopilot Error]: {e}")
            return {"type": "text", "text": f"⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อทีมนักการตลาด AI ครับ ทีมวิศวกรกำลังตรวจสอบ"}

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
                    "backgroundColor": "#0A1128" # สีกรมท่าเข้มพรีเมียม (Premium Navy Blue)
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text", 
                            "text": campaign_text[:400] + "...\n\n(โปรดตรวจสอบรายละเอียดแคมเปญฉบับเต็มในข้อความด้านบนครับ)", 
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
                            "action": {"type": "message", "label": "✅ อนุมัติแคมเปญนี้ (Approve)", "text": f"ACTION:PROMO_ACCEPT:{campaign_id}"}
                        },
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#D4AF37",
                            "action": {"type": "message", "label": "📝 ขอปรับแก้แคปชันใหม่ (Modify)", "text": f"ACTION:PROMO_MODIFY:{campaign_id}"}
                        }
                    ]
                }
            }
        }