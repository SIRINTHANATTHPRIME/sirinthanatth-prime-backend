import os
import stripe
import logging

logger = logging.getLogger("PaymentGateway")

class PaymentGatewayService:
    """💳 ระบบ Payment Gateway ระดับ Enterprise (Stripe Integration)"""

    def __init__(self):
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        # ดึง LINE OA URL จากระบบ หากไม่มีให้ใช้ค่าเริ่มต้น ป้องกันลิงก์พัง
        self.success_url = os.getenv("LINE_OA_URL", "https://lin.ee/@636pgjnh/SIRINTHANATTH_PRIME")
        self.cancel_url = os.getenv("LINE_OA_URL", "https://lin.ee/@636pgjnh/SIRINTHANATTH_PRIME")

    def create_wallet_topup_checkout(self, user_id: str, amount_thb: int = 500) -> str:
        """สร้างลิงก์สำหรับเติมเงิน Smart Wallet ขั้นต่ำ 500 บาท"""
        if not stripe.api_key:
            logger.error("❌ [Stripe]: ไม่พบ STRIPE_SECRET_KEY ในระบบ")
            return ""
            
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['promptpay', 'card'],
                line_items=[{
                    'price_data': {
                        'currency': 'thb',
                        'unit_amount': amount_thb * 100, 
                        'product_data': {
                            'name': 'เติมเงิน PRIME Smart Wallet (THB)',
                            'description': 'เครดิตใช้งาน AI, สื่อ 4K และ โลจิสติกส์',
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                client_reference_id=f"topup_{user_id}",
                success_url=self.success_url,
                cancel_url=self.cancel_url,
            )
            logger.info(f"💳 [Stripe]: สร้างลิงก์เติมเงินสำเร็จสำหรับ ID: {user_id}")
            return session.url
        except Exception as e:
            logger.error(f"⚠️ [Stripe Topup Error]: {str(e)}")
            return ""

    def create_subscription_checkout(self, user_id: str, plan_type: str) -> str:
        """สร้างลิงก์ชำระเงินค่าสมาชิก VIP / PRIME / ENTERPRISE"""
        if not stripe.api_key: return ""
        
        # วางโครงสร้างราคาระดับ Enterprise
        if plan_type == "VIP_FOUNDER":
            price_amount, product_name = 4490 * 100, 'VIP Founder Member (ตลอดชีพ)'
        elif plan_type == "ENTERPRISE":
            price_amount, product_name = 39900 * 100, 'Enterprise Package (รายปี)'
        elif plan_type == "ESSENTIAL":
            price_amount, product_name = 990 * 100, 'Essential Plan (รายเดือน)'
        else:
            price_amount, product_name = 2500 * 100, 'PRIME Executive (รายเดือน)'

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
            logger.info(f"💳 [Stripe]: สร้างลิงก์ Subscription ({plan_type}) สำเร็จสำหรับ ID: {user_id}")
            return session.url
        except Exception as e:
            logger.error(f"⚠️ [Stripe Sub Error]: {str(e)}")
            return ""