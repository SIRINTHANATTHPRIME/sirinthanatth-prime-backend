import os
import logging
import asyncio
import stripe
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger("Stripe-Service")

try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-2.5-flash"
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

class StripeService:
    """
    💳 ระบบจัดการ Payment Gateway ระดับ Enterprise (Stripe & PromptPay)
    อัปเกรด: Async I/O, Vertex AI Dynamic Copywriting และ Webhook Synchronization
    """
    
    def __init__(self):
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        stripe.api_version = "2023-10-16" 
        
        default_line_url = "https://line.me/R/ti/p/@U5ea62530173fdb932bb85acd9fd8fbd3"
        self.success_url = os.getenv("LINE_OA_URL", default_line_url)
        self.cancel_url = os.getenv("LINE_OA_URL", default_line_url)
        
        self.ai_client = PrimeAIConfig.get_client()
        self.ai_model = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-2.5-flash")

    async def create_checkout_session(self, user_id: str, package_name: str, agent_code: str = "NOAGENT") -> str:
        """สร้างลิงก์ชำระเงิน (Checkout URL) แบบ Asynchronous พร้อม AI Copywriting"""
        if not stripe.api_key:
            logger.error("❌ [Stripe]: ไม่พบ STRIPE_SECRET_KEY ระบบชำระเงินออฟไลน์")
            return ""

        packages = {
            "ESSENTIAL": {"price": 59000, "name": "แพ็กเกจ ESSENTIAL (เพื่อนคู่คิด)"},
            "PRIME": {"price": 149000, "name": "แพ็กเกจ PRIME (ที่ปรึกษาส่วนตัว)"},
            "ENTERPRISE": {"price": 490000, "name": "แพ็กเกจ ENTERPRISE (พันธมิตรองค์กร)"},
            "VIP_FOUNDER": {"price": 449000, "name": "100 VIP Founders (ตลอดชีพ)"}
        }

        selected_pkg = packages.get(package_name.upper(), packages["PRIME"])
        
        dynamic_desc = 'SIRINTHANATTH PRIME - Enterprise AI SaaS'
        if self.ai_client:
            try:
                prompt = f"เขียนคำอธิบายสั้นๆ 1 ประโยค (ไม่เกิน 15 คำ) เพื่อกระตุ้นให้ลูกค้าซื้อแพ็กเกจ '{selected_pkg['name']}' ให้ดูหรูหราและทรงพลัง"
                
                async def fetch_ad_copy():
                    return await asyncio.to_thread(
                        self.ai_client.models.generate_content,
                        model=self.ai_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.7)
                    )
                
                ai_res = await asyncio.wait_for(fetch_ad_copy(), timeout=5.0)
                if ai_res.text:
                    dynamic_desc = ai_res.text.strip()
            except asyncio.TimeoutError:
                logger.warning("⚠️ [Stripe AI]: AI Copywriting Timeout ใช้ข้อความมาตรฐาน")
            except Exception as e:
                logger.warning(f"⚠️ [Stripe AI Warning]: AI Copywriting ขัดข้อง ใช้ข้อความเริ่มต้น ({e})")

        client_ref = f"{package_name.upper()}_AGENT_{agent_code}_LINE_{user_id}"

        try:
            def _create_session():
                return stripe.checkout.Session.create(
                    payment_method_types=['promptpay', 'card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'thb',
                            'product_data': {
                                'name': selected_pkg["name"], 
                                'description': dynamic_desc
                            },
                            'unit_amount': selected_pkg["price"],
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url=self.success_url,
                    cancel_url=self.cancel_url,
                    client_reference_id=client_ref, 
                    metadata={
                        "user_id": user_id,
                        "package_name": package_name.upper(),
                        "agent_code": agent_code,
                        "system_version": "3.0.1",
                        "ai_generated_desc": dynamic_desc
                    }
                )
            
            session = await asyncio.to_thread(_create_session)
            logger.info(f"💳 [Stripe]: สร้างบิลชำระเงิน {package_name} สำเร็จ (Ref: {client_ref})")
            return session.url
            
        except stripe.error.StripeError as e:
            logger.error(f"❌ [Stripe API Error]: สร้างลิงก์ล้มเหลว -> {e.user_message or str(e)}")
            return ""
        except Exception as e:
            logger.error(f"❌ [Stripe System Error]: {str(e)}")
            return ""