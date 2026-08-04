import os
import stripe

class PaymentGatewayService:
    """💳 ระบบ Payment Gateway ควบคุมการเติมเงินและการสมัครแพ็กเกจ"""

    def __init__(self):
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        self.success_url = "https://line.me/R/ti/p/@U5ea62530173fdb932bb85acd9fd8fbd3"
        self.cancel_url = "https://line.me/R/ti/p/@U5ea62530173fdb932bb85acd9fd8fbd3"

    def create_wallet_topup_checkout(self, user_id: str, amount_thb: int = 500) -> str:
        """สร้างลิงก์สำหรับเติมเงิน Smart Wallet ขั้นต่ำ 500 บาท"""
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['promptpay', 'card'],
                line_items=[{
                    'price_data': {
                        'currency': 'thb',
                        'unit_amount': amount_thb * 100, 
                        'product_data': {
                            'name': 'เติมเงิน Smart Wallet (THB)',
                            'description': 'เครดิตใช้งาน AI, สื่อ 4K และ Flash Express',
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                client_reference_id=f"topup_{user_id}", # เติม topup_ นำหน้าให้แยกว่าเป็นการเติมเงิน
                success_url=self.success_url,
                cancel_url=self.cancel_url,
            )
            return session.url
        except Exception as e:
            print(f"⚠️ [Stripe Topup Error]: {str(e)}")
            return ""

    def create_subscription_checkout(self, user_id: str, plan_type: str) -> str:
        """สร้างลิงก์ชำระเงินค่าสมาชิก VIP / PRIME"""
        if plan_type == "VIP_FOUNDER":
            price_amount, product_name = 4490 * 100, 'VIP Founder Member (ตลอดชีพ)'
        else:
            price_amount, product_name = 1490 * 100, 'PRIME Creator (รายเดือน)'

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['promptpay', 'card'],
                line_items=[{
                    'price_data': {
                        'currency': 'thb',
                        'unit_amount': price_amount,
                        'product_data': {'name': product_name},
                    },
                    'quantity': 1,
                }],
                mode='payment', 
                client_reference_id=f"sub_{user_id}",
                success_url=self.success_url,
                cancel_url=self.cancel_url,
            )
            return session.url
        except Exception as e:
            print(f"⚠️ [Stripe Sub Error]: {str(e)}")
            return ""