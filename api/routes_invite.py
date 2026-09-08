import os
import secrets
import logging
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from supabase import create_client, Client
from services.payment_gateway import PaymentGatewayService

logger = logging.getLogger("Enterprise-Invite-System")

# ==========================================
# 🚀 1. ตั้งค่า Router และ Services
# ==========================================
router = APIRouter()

supa_url = os.getenv("SUPABASE_URL", "")
supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY", "")
supabase: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None

payment_service = PaymentGatewayService()

# ==========================================
# 🛡️ 2. โครงสร้างข้อมูลความปลอดภัย (Pydantic V2)
# ==========================================
class InvitePayload(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    target_ref: str = Field(..., min_length=3, max_length=100, description="LINE ID หรือข้อมูลระบุตัวตนของผู้รับ")

class VerifyPayload(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    invite_token: str = Field(..., description="Token ที่ได้จากลิงก์เชิญ")
    user_id: str = Field(..., description="LINE ID ของผู้ที่กดลิงก์เข้ามา")

# ==========================================
# 🎫 3. API Endpoints
# ==========================================
@router.post("/api/v1/generate-enterprise-invite")
async def generate_enterprise_invite(payload: InvitePayload):
    """สร้างลิงก์เชิญระดับ Enterprise โดยยกเว้นระบบเลขา"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection offline.")
        
    # สร้าง Token เข้ารหัสป้องกันการปลอมแปลง
    token = secrets.token_urlsafe(32)
    
    data = {
        "invite_token": token,
        "assigned_user_ref": payload.target_ref,
        "package_tier": "ENTERPRISE",
        "excluded_features": ["secretary_system"],
        "is_used": False
    }
    
    try:
        # ⚡ ป้องกันเซิร์ฟเวอร์ค้างด้วย Asynchronous DB Threading
        def _insert_invite():
            return supabase.table("custom_invitations").insert(data).execute()
        await asyncio.to_thread(_insert_invite)
    except Exception as e:
        logger.error(f"❌ [Generate Invite Error]: {e}")
        raise HTTPException(status_code=500, detail="ไม่สามารถสร้างลิงก์เชิญได้ในขณะนี้")
    
    invite_url = f"https://prime-core-agent-601183279633.asia-southeast3.run.app/liff/register?token={token}"
    
    logger.info(f"🎫 [Invite Generated]: สร้างลิงก์เชิญพิเศษสำหรับ {payload.target_ref} สำเร็จ")
    return {
        "status": "success",
        "invite_link": invite_url,
        "restrictions": "Enterprise Tier (No Secretary System)"
    }

@router.post("/api/v1/verify-and-pay-invite")
async def verify_and_pay_invite(payload: VerifyPayload):
    """ตรวจสอบลิงก์เชิญและบังคับเปิดหน้าชำระเงิน Stripe (ขั้นต่ำ 100 บาท)"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection offline.")
        
    try:
        # 1. ตรวจสอบความถูกต้องและสถานะ Token ในฐานข้อมูล
        def _verify_invite():
            return supabase.table("custom_invitations").select("*").eq("invite_token", payload.invite_token).eq("is_used", False).execute()
        
        res = await asyncio.to_thread(_verify_invite)
        
        if not res.data:
            logger.warning(f"⚠️ [Invite Denied]: ผู้ใช้ {payload.user_id} พยายามใช้ Token ที่ไม่ถูกต้องหรือถูกใช้ไปแล้ว")
            raise HTTPException(status_code=403, detail="ลิงก์นี้ไม่ถูกต้อง หมดอายุ หรือถูกใช้งานไปแล้ว")
        
        # 2. สร้าง Stripe Checkout สำหรับเติมเงิน Wallet ขั้นต่ำ 100 บาท
        checkout_url = await payment_service.create_wallet_topup_checkout(user_id=payload.user_id, amount_thb=100)
        
        if not checkout_url:
            raise HTTPException(status_code=500, detail="ไม่สามารถเชื่อมต่อระบบชำระเงินระดับองค์กร (Stripe) ได้ในขณะนี้")
            
        logger.info(f"💳 [Invite Payment Init]: ผู้ใช้ {payload.user_id} เข้าสู่ระบบชำระเงินเพื่อยืนยันสิทธิ์ Enterprise")
        return {
            "status": "pending_payment",
            "stripe_checkout_url": checkout_url,
            "notice": "กรุณาชำระเงินขั้นต่ำ 100 บาทเพื่อยืนยันสิทธิ์และเปิดใช้งาน Enterprise Package"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [Verify Invite Error]: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="ระบบตรวจสอบสิทธิ์ขัดข้องชั่วคราว ทีมวิศวกรกำลังเร่งแก้ไข")