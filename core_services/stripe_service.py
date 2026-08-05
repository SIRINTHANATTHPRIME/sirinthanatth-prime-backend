import os
import stripe
from dotenv import load_dotenv

load_dotenv()

class StripeService:
    """เชื่อมต่อระบบ Stripe ชำระเงินผ่าน PromptPay และบัตรเครดิต"""
    
    def __init__(self):
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        # กลับเข้า LINE OA ทันทีที่จ่ายเสร็จ
        self.success_url = "https://line.me/R/ti/p/@U5ea62530173fdb932bb85acd9fd8fbd3" 
        self.cancel_url = "https://line.me/R/ti/p/@U5ea62530173fdb932bb85acd9fd8fbd3"

    def create_checkout_session(self, user_id: str, package_name: str) -> str:
        # กลยุทธ์ VIP Founder เคาะราคาที่ 4,490 บาท (449,000 สตางค์)
        packages = {
            "ESSENTIAL": {"price": 59000, "name": "แพ็กเกจ ESSENTIAL (เพื่อนคู่คิด)"},
            "PRIME": {"price": 149000, "name": "แพ็กเกจ PRIME (ที่ปรึกษาส่วนตัว)"},
            "ENTERPRISE": {"price": 490000, "name": "แพ็กเกจ ENTERPRISE (พันธมิตรองค์กร)"},
            "VIP_FOUNDER": {"price": 449000, "name": "100 VIP Founders (ตลอดชีพ)"}
        }

        selected_pkg = packages.get(package_name.upper(), packages["PRIME"])

        try:
            session = stripe.checkout.Session.create(
                # 💡 ดัน PromptPay ขึ้นก่อนเพื่อเซฟค่าธรรมเนียม
                payment_method_types=['promptpay', 'card'],
                line_items=[{
                    'price_data': {
                        'currency': 'thb',
                        'product_data': {'name': selected_pkg["name"], 'description': 'SIRINTHANATTH PRIME'},
                        'unit_amount': selected_pkg["price"],
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=self.success_url,
                cancel_url=self.cancel_url,
                client_reference_id=user_id 
            )
            return session.url
        except Exception as e:
            print(f"❌ [Stripe Error]: สร้างลิงก์ชำระเงินล้มเหลว -> {e}")
            return ""