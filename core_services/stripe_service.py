import os
import time
import logging
import asyncio
import hashlib
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
        CORE_MODEL = "gemini-3.7-flash" # 🚀 อัปเกรดโมเดลให้ตรงกับศูนย์บัญชาการ
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
    อัปเกรด: Idempotency Key, Satang Precision, Auto-Expiration, และ AI Copywriting 3.7
    """
    
    def __init__(self):
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        stripe.api_version = "2023-10-16" 
        
        default_line_url = "https://line.me/R/ti/p/@U5ea62530173fdb932bb85acd9fd8fbd3"
        self.success_url = os.getenv("LINE_OA_URL", default_line_url)
        self.cancel_url = os.getenv("LINE_OA_URL", default_line_url)
        
        self.ai_client = PrimeAIConfig.get_client()
        self.ai_model = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-3.7-flash")

    async def create_checkout_session(self, user_id: str, package_name: str, agent_code: str = "NOAGENT") -> str:
        """สร้างลิงก์ชำระเงิน (Checkout URL) ป้องกันบิลซ้ำซ้อน และใช้ AI กระตุ้นยอดขาย"""
        if not stripe.api_key:
            logger.error("❌ [Stripe]: ไม่พบ STRIPE_SECRET_KEY ระบบชำระเงินออฟไลน์")
            return ""

        # ข้อมูลราคาตั้งต้นในหน่วย 'บาท'
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
                prompt = f"เขียนคำอธิบาย 1 ประโยค (15-20 คำ) กระตุ้นให้ลูกค้าโอนเงินซื้อ '{selected_pkg['name']}' ให้ดูพรีเมียมและคุ้มค่าที่สุด ห้ามใช้เครื่องหมายคำพูด"
                
                async def fetch_ad_copy():
                    return await asyncio.to_thread(
                        self.ai_client.models.generate_content,
                        model=self.ai_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(temperature=0.7)
                    )
                
                ai_res = await asyncio.wait_for(fetch_ad_copy(), timeout=5.0)
                if ai_res.text:
                    # ทำความสะอาดตัวอักษรพิเศษก่อนส่งขึ้นหน้าเว็บ Stripe
                    dynamic_desc = ai_res.text.strip().replace('"', '').replace('**', '')
            except Exception as e:
                logger.warning(f"⚠️ [Stripe AI Warning]: ข้ามการใช้ AI Copywriting ({e})")

        client_ref = f"{package_name.upper()}_AGENT_{agent_code}_LINE_{user_id}"
        
        # 🛡️ Idempotency Key ป้องกันการตัดเงินลูกค้าซ้ำซ้อน (Double Billing)
        hash_str = f"{client_ref}_{int(time.time() // 86400)}"
        idempotency_key = hashlib.md5(hash_str.encode()).hexdigest()

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
                            # ⚠️ แก้บั๊กการเงิน: สกุลเงิน THB ใน Stripe ต้องส่งค่าเป็น 'สตางค์' (คูณ 100)
                            'unit_amount': selected_pkg["price"] * 100,
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url=self.success_url,
                    cancel_url=self.cancel_url,
                    client_reference_id=client_ref, 
                    expires_at=int(time.time()) + (24 * 3600), # ⏳ บังคับลิงก์จ่ายเงินหมดอายุใน 24 ชม.
                    metadata={
                        "user_id": user_id,
                        "package_name": package_name.upper(),
                        "agent_code": agent_code,
                        "system_version": "3.1.0",
                        "ai_generated_desc": dynamic_desc
                    }
                , idempotency_key=idempotency_key)
            
            session = await asyncio.to_thread(_create_session)
            logger.info(f"💳 [Stripe]: สร้างบิลชำระเงิน {selected_pkg['price']:,.2f} THB สำเร็จ (Ref: {client_ref})")
            return session.url
            
        except stripe.error.StripeError as e:
            logger.error(f"❌ [Stripe API Error]: สร้างลิงก์ล้มเหลว -> {e.user_message or str(e)}")
            return ""
        except Exception as e:
            logger.error(f"❌ [Stripe System Error]: {str(e)}")
            return ""