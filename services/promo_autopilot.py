import os
import time
import logging
import asyncio
from google import genai
from google.genai import types

# นำเข้า Pydantic Model จากส่วนกลางเพื่อบังคับ Structured Output
try:
    from core_services.models import PromoCampaignData
except ImportError:
    PromoCampaignData = None

# =========================================================
# 🌐 1. นำเข้าศูนย์บัญชาการ AI ส่วนกลาง (Vertex AI / Zero Downtime)
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.7-flash" # 🚀 อัปเกรดเป็นรุ่นเรือธงล่าสุดสำหรับงาน Creative & Marketing
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
    🎉 Festival & Promo Auto-Pilot Service (Enterprise CMO Engine)
    อัปเกรด: Structured JSON Output, Smart Truncation, และ Fault-Tolerance 100%
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.7-flash")

    async def generate_seasonal_campaign(self, store_name: str, festival_name: str, product_details: str) -> dict:
        """สร้างสรรค์แคมเปญเชิงรุกด้วย Structured AI และแปลงร่างเป็น Flex Message ระดับ Giga"""
        if not self.client:
            logger.warning("⚠️ [Promo]: API Key missing, skipping generation.")
            return {"type": "text", "text": "⚠️ ระบบ AI ศูนย์กลางออฟไลน์ ไม่สามารถสร้างแคมเปญอัตโนมัติได้ในขณะนี้ครับ"}

        system_instruction = """
        คุณคือ 'Global Chief Marketing Officer (CMO)' ระดับโลก ประจำระบบ SIRINTHANATTH PRIME
        หน้าที่ของคุณคือคิดค้นแคมเปญการตลาดเชิงรุก (Proactive Marketing) ที่หรูหรา ทรงพลัง ดึงดูด และสร้างยอดขายได้จริง
        """

        prompt = f"""
        จงสร้างสรรค์แคมเปญโปรโมชันต้อนรับเทศกาล '{festival_name}' สำหรับแบรนด์ '{store_name}' 
        รายละเอียดสินค้า/บริการ: {product_details}
        """

        try:
            logger.info(f"🚀 [Promo]: กำลังประมวลผลแคมเปญ '{festival_name}' สำหรับแบรนด์ '{store_name}'")
            
            async def fetch_campaign():
                # หากมี PromoCampaignData ให้บังคับ Structured Output เพื่อความแม่นยำสูงสุด
                config_params = {
                    "system_instruction": system_instruction,
                    "temperature": 0.8
                }
                if PromoCampaignData:
                    config_params["response_mime_type"] = "application/json"
                    config_params["response_schema"] = PromoCampaignData

                return await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(**config_params)
                )
            
            # ⏳ Guardrail: ป้องกันการประมวลผลค้าง (Anti-Freeze Timeout 45s)
            response = await asyncio.wait_for(fetch_campaign(), timeout=45.0)
            raw_text = response.text.strip() if response.text else "{}"

            # แปลงข้อมูลโครงสร้าง AI หรือใช้ Fallback ข้อความดิบ
            campaign_data = {}
            if PromoCampaignData:
                try:
                    import json
                    campaign_data = json.loads(raw_text)
                except Exception:
                    campaign_data = {
                        "campaign_title": f"แคมเปญพิเศษ {festival_name}",
                        "special_offer": "สิทธิพิเศษเฉพาะผู้บริหารระดับสูง",
                        "ad_copy": raw_text,
                        "target_audience_advice": "เจาะกลุ่มเป้าหมายกำลังซื้อสูง"
                    }
            else:
                campaign_data = {
                    "campaign_title": f"แคมเปญพิเศษ {festival_name}",
                    "special_offer": "ส่วนลดและสิทธิพิเศษพรีเมียม",
                    "ad_copy": raw_text,
                    "target_audience_advice": "กลุ่มลูกค้าระดับ VVIP"
                }

            # สร้างรหัสเฉพาะ (ID) สำหรับรอรับคำสั่งปุ่มกด
            campaign_id = f"PROMO_{int(time.time())}"
            logger.info(f"✅ [Promo]: สร้างร่างแคมเปญ {campaign_id} สำเร็จ! รอการอนุมัติ...")
            
            return self._build_promo_flex_message(campaign_data, campaign_id, festival_name)

        except asyncio.TimeoutError:
            logger.error("❌ [Promo Autopilot Timeout]: AI ใช้เวลาคิดแคมเปญนานเกินไป")
            return {"type": "text", "text": "⚠️ ขออภัยครับ ระบบประมวลผลแคมเปญใช้เวลานานกว่าปกติ รบกวนกดสั่งงานใหม่อีกครั้งครับ"}
        except Exception as e:
            logger.error(f"❌ [Promo Autopilot Error]: {e}", exc_info=True)
            return {"type": "text", "text": f"⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อทีมนักการตลาด AI ครับ ทีมวิศวกรกำลังตรวจสอบ"}

    def _build_promo_flex_message(self, data: dict, campaign_id: str, festival_name: str) -> dict:
        """สร้างการ์ดพรีวิวโปรโมชันบน LINE (Flex Message ไซส์ Giga ดีไซน์ระดับหรูหรา)"""
        title = data.get("campaign_title", festival_name)
        offer = data.get("special_offer", "ข้อเสนอสุดพิเศษ")
        copy = data.get("ad_copy", "")
        advice = data.get("target_audience_advice", "")

        # 🛡️ Smart Truncation: ป้องกันข้อความยาวเกินลิมิตของ LINE Flex
        formatted_body = (
            f"🎯 ชื่อแคมเปญ:\n{title}\n\n"
            f"🎁 ข้อเสนอพิเศษ:\n{offer}\n\n"
            f"📝 แคปชันโฆษณา:\n{copy[:300]}...\n\n"
            f"💡 คำแนะนำการยิงแอด:\n{advice}"
        )

        return {
            "type": "flex",
            "altText": f"🎉 แผนโปรโมชันพิเศษเทศกาล {festival_name} พร้อมพิจารณา",
            "contents": {
                "type": "bubble",
                "size": "giga", 
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "🎉 SIRINTHANATTH PRIME - CMO", "weight": "bold", "color": "#D4AF37", "size": "xs"},
                        {"type": "text", "text": f"เทศกาล: {festival_name}", "weight": "bold", "color": "#FFFFFF", "size": "lg", "margin": "sm", "wrap": True}
                    ],
                    "backgroundColor": "#0A1128" # สีกรมท่าเข้มพรีเมียม (Premium Navy Blue)
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text", 
                            "text": formatted_body, 
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
                            "action": {"type": "message", "label": "📝 ขอปรับแก้แคปชัน (Modify)", "text": f"ACTION:PROMO_MODIFY:{campaign_id}"}
                        }
                    ]
                }
            }
        }