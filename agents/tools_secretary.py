import os
import uuid
import stripe
from core_services.db_supabase import supabase # ตรวจสอบให้แน่ใจว่า import ถูกต้อง

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

def create_exclusive_invite(min_topup_thb: int = 100) -> str:
    """
    เรียกใช้ฟังก์ชันนี้เมื่อประธานบริษัท (CEO) สั่งให้สร้างลิงก์เชิญคนนอกเข้าใช้งานระบบ
    ระบบจะสร้าง Single-use Token ระดับ Enterprise (แต่ล็อกไม่ให้เข้าถึงเลขา)
    และสร้างระบบตัดเงิน Stripe อัตโนมัติ
    
    Args:
        min_topup_thb: จำนวนเงินขั้นต่ำที่ผู้ถูกเชิญต้องเติมเข้า Wallet (ค่าเริ่มต้นคือ 100)
    """
    try:
        # 1. สร้างรหัสผ่านแบบใช้ครั้งเดียว
        token = f"PRIME-{uuid.uuid4().hex[:12].upper()}"
        
        # 2. บันทึกลง Supabase ล็อกสิทธิ์ Enterprise Guest
        supabase.table("invite_tokens").insert({
            "token": token,
            "tier": "ENTERPRISE_GUEST",
            "is_used": False,
            "min_topup_thb": min_topup_thb
        }).execute()
        
        # 3. สร้าง Stripe Checkout สำหรับให้ผู้ถูกเชิญสแกนจ่าย/รูดบัตร 100 บาท
        session = stripe.checkout.Session.create(
            payment_method_types=['card', 'promptpay'],
            line_items=[{
                'price_data': {
                    'currency': 'thb',
                    'product_data': {'name': 'SIRINTHANATTH PRIME - Initial Wallet Token'},
                    'unit_amount': min_topup_thb * 100, # Stripe รับค่าเป็นสตางค์
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"https://www.sirinthanatthprime.com/onboarding?token={token}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url="https://www.sirinthanatthprime.com/cancel",
        )
        
        # 4. ส่งผลลัพธ์กลับให้ AI เพื่อนำไปสรุปตอบท่านประธาน
        return (f"สร้างระบบคำเชิญสำเร็จแล้วครับท่านประธาน:\n\n"
                f"🔗 ลิงก์ลงทะเบียนสิทธิ์ (ใช้ได้แค่คนเดียว): https://www.sirinthanatthprime.com/invite/{token}\n"
                f"💳 ลิงก์ชำระเงินเปิดระบบ (ขั้นต่ำ {min_topup_thb} บาท): {session.url}")
                
    except Exception as e:
        return f"พบข้อผิดพลาดในการสร้างลิงก์ครับท่านประธาน: {str(e)}"