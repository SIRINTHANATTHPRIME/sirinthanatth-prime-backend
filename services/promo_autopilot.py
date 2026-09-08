import os
import time
import json
import re
import logging
import asyncio
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# =========================================================
# 🛡️ Pydantic Model: นำเข้าจากส่วนกลาง หรือสร้างจำลองเพื่อความเสถียร 100%
# =========================================================
try:
    from core_services.models import PromoCampaignData
except ImportError:
    class PromoCampaignData(BaseModel):
        campaign_title: str = Field(description="ชื่อแคมเปญที่สั้น กระชับ และดึงดูดสายตา")
        special_offer: str = Field(description="ข้อเสนอพิเศษ ส่วนลด หรือโปรโมชันหลัก")
        ad_copy: str = Field(description="แคปชันโฆษณาพร้อมใช้งานและ Hashtags (ไม่เกิน 300 ตัวอักษร)")
        target_audience_advice: str = Field(description="คำแนะนำในการยิง Ads และกำหนดกลุ่มเป้าหมาย (Targeting)")

# =========================================================
# 🌐 นำเข้าศูนย์บัญชาการ AI ส่วนกลาง (Vertex AI / Zero Downtime)
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.7-flash" 
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
    อัปเกรด: Component-Based UI, Markdown Stripper, Psychological Prompting
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.7-flash")

    async def generate_seasonal_campaign(self, store_name: str, festival_name: str, product_details: str) -> dict:
        """สร้างสรรค์แคมเปญเชิงรุกและประกอบร่างเป็น Flex Message ระดับ Premium Dashboard"""
        if not self.client:
            logger.warning("⚠️ [Promo]: API Key missing, skipping generation.")
            return {"type": "text", "text": "⚠️ ระบบ AI ศูนย์กลางออฟไลน์ ไม่สามารถสร้างแคมเปญอัตโนมัติได้ในขณะนี้ครับ"}

        system_instruction = """
        คุณคือ 'Global Chief Marketing Officer (CMO)' ระดับโลก ประจำระบบ SIRINTHANATTH PRIME
        หน้าที่ของคุณคือคิดค้นแคมเปญการตลาดเชิงรุก ที่หรูหรา ทรงพลัง ดึงดูด และสร้างยอดขายได้จริง
        - ใช้หลักจิตวิทยาการตลาด (เช่น FOMO, Scarcity, Exclusivity)
        - แคปชันโฆษณา (ad_copy) ต้องจำกัดความยาวไม่เกิน 300 ตัวอักษร เพื่อให้แสดงผลบนสมาร์ทโฟนได้สวยงาม
        - ให้ตอบกลับมาเป็น JSON ตาม Schema ที่กำหนดเท่านั้น ห้ามพิมพ์ข้อความอื่นแทรก
        """

        prompt = f"""
        จงสร้างสรรค์แคมเปญโปรโมชันต้อนรับเทศกาล '{festival_name}' สำหรับแบรนด์ '{store_name}' 
        รายละเอียดสินค้า/บริการ: {product_details}
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
                        temperature=0.8,
                        response_mime_type="application/json",
                        response_schema=PromoCampaignData # 🛡️ บังคับโครงสร้างเด็ดขาด
                    )
                )
            
            # ⏳ Guardrail: 20 วินาทีเพียงพอสำหรับ Gemini 3.7 Flash ป้องกัน LINE หมดเวลา
            response = await asyncio.wait_for(fetch_campaign(), timeout=20.0)
            
            # 🧹 ทำความสะอาด Markdown ที่อาจหลุดรอดมาจาก AI
            raw_text = response.text.strip() if response.text else "{}"
            raw_text = re.sub(r'^```json\s*', '', raw_text)
            raw_text = re.sub(r'\s*```$', '', raw_text)

            try:
                campaign_data = json.loads(raw_text)
            except json.JSONDecodeError:
                logger.error("❌ [Promo]: ถอดรหัส JSON ล้มเหลว ใช้ข้อมูลจำลองชั่วคราว")
                campaign_data = {
                    "campaign_title": f"แคมเปญพิเศษ {festival_name}",
                    "special_offer": "ข้อเสนอพิเศษ (ไม่สามารถประมวลผลได้)",
                    "ad_copy": "พบกับข้อเสนอสุดพิเศษเร็วๆ นี้",
                    "target_audience_advice": "ตรวจสอบข้อมูลอีกครั้ง"
                }

            campaign_id = f"PROMO_{int(time.time())}"
            logger.info(f"✅ [Promo]: สร้างร่างแคมเปญ {campaign_id} สำเร็จ! รอการอนุมัติ...")
            
            return self._build_promo_flex_message(campaign_data, campaign_id, festival_name, store_name)

        except asyncio.TimeoutError:
            logger.error("❌ [Promo Autopilot Timeout]: AI ใช้เวลาคิดแคมเปญนานเกินไป")
            return {"type": "text", "text": "⚠️ ขออภัยครับ ระบบประมวลผลแคมเปญใช้เวลานานกว่าปกติ รบกวนกดสั่งงานใหม่อีกครั้งครับ"}
        except Exception as e:
            logger.error(f"❌ [Promo Autopilot Error]: {e}", exc_info=True)
            return {"type": "text", "text": f"⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อทีมนักการตลาด AI ครับ ทีมวิศวกรกำลังตรวจสอบ"}

    def _build_promo_flex_message(self, data: dict, campaign_id: str, festival_name: str, store_name: str) -> dict:
        """สร้างการ์ดพรีวิวบน LINE ด้วยโครงสร้าง Component-Based UI ที่สวยงามระดับโลก"""
        title = data.get("campaign_title", festival_name)
        offer = data.get("special_offer", "ข้อเสนอสุดพิเศษ")
        copy = data.get("ad_copy", "พบกับสินค้าพรีเมียมได้เร็วๆ นี้")
        advice = data.get("target_audience_advice", "-")

        return {
            "type": "flex",
            "altText": f"🎉 แผนโปรโมชันพิเศษเทศกาล {festival_name} พร้อมพิจารณา",
            "contents": {
                "type": "bubble",
                "size": "giga", 
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "paddingAll": "20px",
                    "contents": [
                        {"type": "text", "text": f"CMO ENGINE • {store_name.upper()}", "weight": "bold", "color": "#D4AF37", "size": "xs"},
                        {"type": "text", "text": f"{festival_name}", "weight": "bold", "color": "#FFFFFF", "size": "xl", "margin": "md", "wrap": True}
                    ],
                    "backgroundColor": "#0A1128"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "paddingAll": "20px",
                    "contents": [
                        # 🎯 Title Section
                        {"type": "text", "text": "แคมเปญ", "size": "xs", "color": "#888888", "weight": "bold"},
                        {"type": "text", "text": title, "weight": "bold", "size": "md", "color": "#111111", "wrap": True, "margin": "sm"},
                        {"type": "separator", "margin": "lg", "color": "#EEEEEE"},
                        
                        # 🎁 Offer Section
                        {"type": "text", "text": "ข้อเสนอพิเศษ", "size": "xs", "color": "#888888", "weight": "bold", "margin": "lg"},
                        {"type": "text", "text": offer, "weight": "bold", "size": "sm", "color": "#E63946", "wrap": True, "margin": "sm"},
                        {"type": "separator", "margin": "lg", "color": "#EEEEEE"},
                        
                        # 📝 Copy Section
                        {"type": "text", "text": "แคปชันโฆษณา", "size": "xs", "color": "#888888", "weight": "bold", "margin": "lg"},
                        {"type": "text", "text": f'"{copy}"', "size": "sm", "color": "#333333", "wrap": True, "margin": "sm", "style": "italic"},
                        {"type": "separator", "margin": "lg", "color": "#EEEEEE"},
                        
                        # 💡 Advice Section
                        {"type": "text", "text": "คำแนะนำกลุ่มเป้าหมาย", "size": "xs", "color": "#888888", "weight": "bold", "margin": "lg"},
                        {"type": "text", "text": advice, "size": "xs", "color": "#555555", "wrap": True, "margin": "sm"}
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "paddingAll": "20px",
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
                            "style": "secondary",
                            "action": {"type": "message", "label": "📝 ขอปรับแก้แคปชัน", "text": f"ACTION:PROMO_MODIFY:{campaign_id}"}
                        }
                    ]
                }
            }
        }