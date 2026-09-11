import os
import uuid
import stripe
import logging
from typing import Dict, Any

logger = logging.getLogger("Prime-Tools-Secretary")

# =========================================================
# 💳 1. ตั้งค่าระบบ Stripe Gateway
# =========================================================
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

# =========================================================
# 🗄️ 2. เชื่อมต่อฐานข้อมูลด้วยระบบ Graceful Degradation
# =========================================================
try:
    from core_services.db_supabase import supabase
except ImportError:
    from supabase import create_client, Client
    supa_url = os.getenv("SUPABASE_URL", "")
    supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY", "")
    supabase = create_client(supa_url, supa_key) if supa_url and supa_key else None

# =========================================================
# 🛠️ 3. เครื่องมืออัจฉริยะ (Autonomous AI Tools)
# =========================================================
def create_exclusive_invite(min_topup_thb: int = 100) -> Dict[str, Any]:
    """
    สร้างลิงก์เชิญใช้งานระบบ (VVIP Invite Link) แบบใช้ครั้งเดียว พร้อมระบบเก็บเงินขั้นต่ำผ่าน Stripe
    ให้ AI เรียกใช้ฟังก์ชันนี้ทันทีเมื่อท่านประธานสั่งให้ "สร้างลิงก์", "ออกคำเชิญ", หรือ "เชิญคนเข้าใช้งาน"

    Args:
        min_topup_thb: จำนวนเงินขั้นต่ำที่ผู้ถูกเชิญต้องเติมเข้า Wallet เพื่อเปิดระบบ (ค่าเริ่มต้น 100 บาท)
    """
    try:
        if not stripe.api_key:
            logger.error("❌ [Tool Error]: ไม่พบ STRIPE_SECRET_KEY ระบบชำระเงินออฟไลน์")
            return {"status": "error", "message": "ระบบชำระเงินยังไม่พร้อมใช้งาน (Missing Stripe Key)"}

        # สร้าง Token ความปลอดภัยสูง 12 หลัก
        token = f"PRIME-{uuid.uuid4().hex[:12].upper()}"
        
        # ดึง Base URL อัตโนมัติ ป้องกันลิงก์พังเมื่อเปลี่ยนเซิร์ฟเวอร์
        base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")

        # 1. บันทึกลงฐานข้อมูล (แยกสิทธิ์การใช้งาน ไม่ให้เข้าถึงระดับบริหารได้)
        if supabase:
            try:
                supabase.table("invite_tokens").insert({
                    "token": token,
                    "tier": "ENTERPRISE_GUEST",
                    "is_used": False,
                    "min_topup_thb": min_topup_thb
                }).execute()
            except Exception as db_err:
                logger.warning(f"⚠️ [DB Warning]: บันทึก Token ลง Supabase ล้มเหลว ({db_err})")
        else:
            logger.warning("⚠️ [DB Offline]: ดำเนินการสร้าง Token ข้ามการบันทึกฐานข้อมูล")

        # 2. สร้างหน้าชำระเงินของ Stripe (Checkout Session)
        session = stripe.checkout.Session.create(
            payment_method_types=['card', 'promptpay'],
            line_items=[{
                'price_data': {
                    'currency': 'thb',
                    'product_data': {'name': 'SIRINTHANATTH PRIME - Executive Wallet Token'},
                    'unit_amount': int(min_topup_thb) * 100, # ระบบ Stripe บังคับใช้ค่าเป็นสตางค์
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{base_url}/onboarding?token={token}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url}/cancel",
        )
        
        logger.info(f"🎫 [Tool Success]: AI สร้างลิงก์คำเชิญ VVIP สำเร็จ (Token: {token})")
        
        # 3. 🚀 ส่งคืนผลลัพธ์เป็น Dictionary (JSON) เพื่อให้สมองกล AI นำไปวิเคราะห์ต่อได้ 100%
        return {
            "status": "success",
            "invite_link": f"{base_url}/invite/{token}",
            "payment_link": session.url,
            "token": token,
            "message": f"ผมได้สร้างรหัสคำเชิญเรียบร้อยแล้วครับ พร้อมผูกระบบตัดเงินขั้นต่ำ {min_topup_thb} บาท"
        }

    except stripe.error.StripeError as stripe_err:
        logger.error(f"❌ [Stripe API Error]: {stripe_err}")
        return {"status": "error", "message": f"ระบบชำระเงินขัดข้องจากทาง Stripe: {str(stripe_err)}"}
    except Exception as e:
        logger.error(f"❌ [System Error]: {e}", exc_info=True)
        return {"status": "error", "message": f"เกิดข้อผิดพลาดเชิงระบบทางวิศวกรรม: {str(e)}"}