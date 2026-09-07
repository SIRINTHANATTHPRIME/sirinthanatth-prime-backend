import os
import time
import hashlib
import stripe
import logging
import asyncio

logger = logging.getLogger("PaymentGateway")

class PaymentGatewayService:
    """💳 ระบบ Payment Gateway ระดับ Enterprise (Stripe Integration & PromptPay)"""

    def __init__(self):
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        stripe.api_version = "2023-10-16" # 🔒 ล็อกเวอร์ชัน API ป้องกันระบบล่มจากการอัปเดตของ Stripe
        
        # เปลี่ยนกลับไปหน้า LIFF Wallet หลังจากชำระเงินเสร็จสิ้น
        self.success_url = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")
        self.cancel_url = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")

    async def create_wallet_topup_checkout(self, user_id: str, amount_thb: int = 500) -> str:
        """สร้างลิงก์สำหรับเติมเงิน Smart Wallet ป้องกันการสร้างบิลซ้ำซ้อน"""
        if not stripe.api_key:
            logger.error("❌ [Stripe]: ไม่พบ STRIPE_SECRET_KEY ในระบบ")
            return ""
            
        # 🛡️ สร้าง Idempotency Key ป้องกันลูกค้ากดปุ่มรัวๆ แล้วโดนหักเงินซ้ำซ้อน
        ref_id = f"topup_{user_id}_{int(time.time())}"
        idempotency_key = hashlib.md5(ref_id.encode()).hexdigest()
            
        try:
            def _create_session():
                return stripe.checkout.Session.create(
                    payment_method_types=['promptpay', 'card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'thb',
                            # ⚠️ ใช้ round() ป้องกันบั๊ก Float Precision หักเงินลูกค้าไม่ตรงเศษสตางค์
                            'unit_amount': int(round(amount_thb * 100)), 
                            'product_data': {
                                'name': '💎 เติมเงิน PRIME Smart Wallet',
                                'description': 'เครดิตสำหรับใช้งาน AI, สื่อ 4K และระบบ Logistics',
                            },
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    client_reference_id=ref_id,
                    metadata={"user_id": user_id, "type": "topup"},
                    success_url=self.success_url,
                    cancel_url=self.cancel_url,
                    expires_at=int(time.time()) + (30 * 60), # ⏳ บังคับบิลเติมเงินหมดอายุใน 30 นาที
                    idempotency_key=idempotency_key
                )
            
            session = await asyncio.to_thread(_create_session)
            logger.info(f"💳 [Stripe]: สร้างลิงก์เติมเงินสำเร็จสำหรับ ID: {user_id}")
            return session.url
            
        except stripe.error.StripeError as e:
            logger.error(f"❌ [Stripe API Error]: สร้างบิลเติมเงินล้มเหลว -> {e.user_message or str(e)}")
            return ""
        except Exception as e:
            logger.error(f"⚠️ [Stripe Topup Error]: {str(e)}")
            return ""

    async def create_subscription_checkout(self, user_id: str, plan_type: str, agent_code: str = "NOAGENT") -> str:
        """สร้างลิงก์ชำระเงินค่าสมาชิก พร้อมส่งโครงสร้าง Data ให้ Webhook หักคอมมิชชันอัตโนมัติ"""
        if not stripe.api_key: 
            return ""
        
        # วางโครงสร้างราคาระดับ Enterprise
        plans = {
            "VIP_FOUNDER": {"price": 4490, "name": "👑 VIP Founder Member (ตลอดชีพ)"},
            "ENTERPRISE": {"price": 39900, "name": "🏢 Enterprise Package (รายปี)"},
            "PRIME": {"price": 2500, "name": "💼 PRIME Executive (รายเดือน)"},
            "ESSENTIAL": {"price": 990, "name": "⭐ Essential Plan (รายเดือน)"}
        }
        
        plan = plans.get(plan_type, plans["ESSENTIAL"])
        price_amount = int(round(plan["price"] * 100))
        product_name = plan["name"]

        # โครงสร้างอ้างอิงที่ Webhook ของ main.py ดักรอรับ
        ref_id = f"{plan_type}_AGENT_{agent_code}_LINE_{user_id}"
        
        # 🛡️ ล็อก Key ไว้ 1 ชั่วโมง ป้องกันคนกดเข้าลิงก์แผนเดิมซ้ำๆ จนสร้างบิลขยะเต็มระบบ
        hash_str = f"{ref_id}_{int(time.time() // 3600)}"
        idempotency_key = hashlib.md5(hash_str.encode()).hexdigest()

        try:
            def _create_sub_session():
                return stripe.checkout.Session.create(
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
                    client_reference_id=ref_id,
                    metadata={
                        "user_id": user_id, 
                        "plan": plan_type, 
                        "agent_code": agent_code
                    },
                    success_url=self.success_url,
                    cancel_url=self.cancel_url,
                    expires_at=int(time.time()) + (24 * 3600), # ⏳ บังคับบิลแพ็กเกจหมดอายุใน 24 ชั่วโมง
                    idempotency_key=idempotency_key
                )
            
            session = await asyncio.to_thread(_create_sub_session)
            logger.info(f"💳 [Stripe]: สร้างลิงก์แพ็กเกจ ({plan_type}) สำเร็จ -> Ref: {ref_id}")
            return session.url
            
        except stripe.error.StripeError as e:
            logger.error(f"❌ [Stripe API Error]: สร้างบิลแพ็กเกจล้มเหลว -> {e.user_message or str(e)}")
            return ""
        except Exception as e:
            logger.error(f"⚠️ [Stripe Sub Error]: {str(e)}")
            return ""