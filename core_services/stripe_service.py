import os
import logging
import stripe
from dotenv import load_dotenv

load_dotenv()

# ตั้งค่าระบบบันทึกการทำงาน (Enterprise Logging)
logger = logging.getLogger("Stripe-Service")

class StripeService:
    """
    💳 ระบบจัดการ Payment Gateway ระดับ Enterprise (Stripe Integration)
    เชื่อมต่อระบบชำระเงินผ่าน PromptPay และบัตรเครดิต พร้อมระบบ Tracking สากล
    """
    
    def __init__(self):
        # 1. ตั้งค่า API Key
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        
        # 2. [Best Practice] ล็อกเวอร์ชัน API ให้เสถียรที่สุด ป้องกันระบบพังจากการอัปเดตของ Stripe
        stripe.api_version = "2023-10-16" 
        
        # 3. ดึงลิงก์กลับ LINE OA จากตัวแปรระบบ ป้องกันลิงก์ตาย (Fallback ไปยังลิงก์เดิมของท่านประธาน)
        default_line_url = "https://line.me/R/ti/p/@U5ea62530173fdb932bb85acd9fd8fbd3"
        self.success_url = os.getenv("LINE_OA_URL", default_line_url)
        self.cancel_url = os.getenv("LINE_OA_URL", default_line_url)

    def create_checkout_session(self, user_id: str, package_name: str, agent_code: str = "") -> str:
        """สร้างลิงก์ชำระเงิน (Checkout URL) พร้อมฝังข้อมูลสำหรับการตลาดและ Webhook"""
        if not stripe.api_key:
            logger.error("❌ [Stripe]: ไม่พบ STRIPE_SECRET_KEY ระบบชำระเงินออฟไลน์")
            return ""

        # โครงสร้างราคาและแพ็กเกจ (หน่วยเป็นสตางค์)
        packages = {
            "ESSENTIAL": {"price": 59000, "name": "แพ็กเกจ ESSENTIAL (เพื่อนคู่คิด)"},
            "PRIME": {"price": 149000, "name": "แพ็กเกจ PRIME (ที่ปรึกษาส่วนตัว)"},
            "ENTERPRISE": {"price": 490000, "name": "แพ็กเกจ ENTERPRISE (พันธมิตรองค์กร)"},
            "VIP_FOUNDER": {"price": 449000, "name": "100 VIP Founders (ตลอดชีพ)"}
        }

        # หากระบุแพ็กเกจผิด ให้ใช้ PRIME เป็นค่ามาตรฐาน (Fallback)
        selected_pkg = packages.get(package_name.upper(), packages["PRIME"])

        # 🔄 ปรับ Reference ID ให้สอดคล้องกับตัวรับ Webhook ใน main.py เพื่อปลดล็อกสิทธิ์อัตโนมัติ
        client_ref = f"VIP-{user_id}" if package_name.upper() == "VIP_FOUNDER" else f"sub_{user_id}"
        if agent_code:
            client_ref += f"_AGENT_{agent_code}" # ผูกรหัส Agent เข้าไปในบิลเพื่อแบ่งคอมมิชชัน

        try:
            session = stripe.checkout.Session.create(
                # 💡 ดัน PromptPay ขึ้นก่อนเพื่อช่วยองค์กรเซฟค่าธรรมเนียม
                payment_method_types=['promptpay', 'card'],
                line_items=[{
                    'price_data': {
                        'currency': 'thb',
                        'product_data': {
                            'name': selected_pkg["name"], 
                            'description': 'SIRINTHANATTH PRIME - Enterprise AI SaaS'
                        },
                        'unit_amount': selected_pkg["price"],
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=self.success_url,
                cancel_url=self.cancel_url,
                client_reference_id=client_ref, 
                
                # 📊 [Enterprise Feature] ฝังข้อมูล Metadata เข้าบิลใบเสร็จ เพื่อใช้วิเคราะห์การตลาด
                metadata={
                    "user_id": user_id,
                    "package_name": package_name.upper(),
                    "agent_code": agent_code,
                    "system_version": "3.0.1"
                }
            )
            logger.info(f"💳 [Stripe]: สร้างบิลชำระเงิน {package_name} สำเร็จ (Ref: {client_ref})")
            return session.url
            
        except stripe.error.StripeError as e:
            # ดักจับ Error จากฝั่งระบบของ Stripe โดยเฉพาะ
            logger.error(f"❌ [Stripe API Error]: สร้างลิงก์ล้มเหลว -> {e.user_message or str(e)}")
            return ""
        except Exception as e:
            logger.error(f"❌ [Stripe System Error]: {str(e)}")
            return ""