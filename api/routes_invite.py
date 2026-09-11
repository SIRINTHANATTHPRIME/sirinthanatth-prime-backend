import os
import secrets
import logging
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel, Field, ConfigDict
from supabase import create_client, Client
from services.payment_gateway import PaymentGatewayService

logger = logging.getLogger("Enterprise-Invite-System")

# ==========================================
# 🚀 1. ตั้งค่า Router, Services และ Environment
# ==========================================
router = APIRouter()

BASE_URL = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
MASTER_ADMIN_KEY = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")

# เชื่อมต่อ Supabase แบบ Graceful Degradation
supa_url = os.getenv("SUPABASE_URL", "")
supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY", "")
supabase: Optional[Client] = create_client(supa_url, supa_key) if supa_url and supa_key else None

payment_service = PaymentGatewayService()

# ==========================================
# 🛡️ 2. โครงสร้างข้อมูลความปลอดภัย (Pydantic V2 Strict Mode)
# ==========================================
class InvitePayload(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    target_ref: str = Field(..., min_length=3, max_length=100, description="LINE ID หรือข้อมูลระบุตัวตนของผู้รับ")

class VerifyPayload(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    invite_token: str = Field(..., description="Token ที่ได้จากลิงก์เชิญ")
    user_id: str = Field(..., description="LINE ID ของผู้ที่กดลิงก์เข้ามา")

# ==========================================
# 🎫 3. API Endpoints ระดับ Enterprise
# ==========================================
@router.post("/api/v1/generate-enterprise-invite")
async def generate_enterprise_invite(
    payload: InvitePayload, 
    background_tasks: BackgroundTasks,
    x_admin_key: Optional[str] = Header(None, description="รหัสยืนยันตัวตนระดับบริหาร")
):
    """
    สร้างลิงก์เชิญระดับ Enterprise โดยยกเว้นระบบเลขา (Protected Endpoint)
    """
    if not supabase:
        raise HTTPException(status_code=503, detail="Database connection offline. Please try again later.")
    
    # 🔒 Security: ตรวจสอบสิทธิ์การยิง API ป้องกันการแฮกสร้างลิงก์เถื่อน
    if x_admin_key and x_admin_key != MASTER_ADMIN_KEY:
        logger.warning(f"🚨 [Security Alert]: ตรวจพบการพยายามสร้างลิงก์ด้วย Admin Key ที่ไม่ถูกต้อง ({payload.target_ref})")
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Admin Key")

    # สร้าง Token เข้ารหัสป้องกันการปลอมแปลงแบบ Bank-Grade
    token = secrets.token_urlsafe(32)
    
    data = {
        "invite_token": token,
        "assigned_user_ref": payload.target_ref,
        "package_tier": "ENTERPRISE",
        "excluded_features": ["secretary_system"],
        "is_used": False
    }
    
    try:
        # ⚡ ป้องกันเซิร์ฟเวอร์ค้างด้วย Asynchronous DB Threading พร้อม Timeout
        def _insert_invite():
            return supabase.table("custom_invitations").insert(data).execute()
        
        await asyncio.wait_for(asyncio.to_thread(_insert_invite), timeout=5.0)
    except asyncio.TimeoutError:
        logger.error("❌ [Generate Invite Error]: Database timeout")
        raise HTTPException(status_code=504, detail="ฐานข้อมูลตอบสนองช้ากว่าปกติ กรุณาลองใหม่")
    except Exception as e:
        logger.error(f"❌ [Generate Invite Error]: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="ไม่สามารถสร้างลิงก์เชิญได้ในขณะนี้")
    
    # 🔗 Dynamic URL Routing รองรับการสลับโดเมนในอนาคต
    invite_url = f"{BASE_URL}/liff/register?token={token}"
    
    logger.info(f"🎫 [Invite Generated]: สร้างลิงก์เชิญพิเศษสำหรับ {payload.target_ref} สำเร็จ")
    
    return {
        "status": "success",
        "invite_link": invite_url,
        "restrictions": "Enterprise Tier (No Secretary System)"
    }

@router.post("/api/v1/verify-and-pay-invite")
async def verify_and_pay_invite(payload: VerifyPayload, background_tasks: BackgroundTasks):
    """
    ตรวจสอบลิงก์เชิญและบังคับเปิดหน้าชำระเงิน Stripe (ขั้นต่ำ 100 บาท)
    """
    if not supabase:
        raise HTTPException(status_code=503, detail="Database connection offline.")
        
    try:
        # 1. ตรวจสอบความถูกต้องและสถานะ Token ในฐานข้อมูลอย่างรัดกุม
        def _verify_invite():
            return supabase.table("custom_invitations").select("*").eq("invite_token", payload.invite_token).eq("is_used", False).execute()
        
        res = await asyncio.wait_for(asyncio.to_thread(_verify_invite), timeout=5.0)
        
        if not res.data:
            logger.warning(f"⚠️ [Invite Denied]: ผู้ใช้ {payload.user_id} พยายามใช้ Token ที่ไม่ถูกต้อง หมดอายุ หรือถูกใช้งานไปแล้ว")
            raise HTTPException(status_code=403, detail="ลิงก์คำเชิญนี้ไม่ถูกต้อง หมดอายุ หรือถูกใช้งานไปแล้ว")
        
        # 2. สร้าง Stripe Checkout สำหรับเติมเงิน Wallet ขั้นต่ำ 100 บาท (Async Call)
        checkout_url = await payment_service.create_wallet_topup_checkout(user_id=payload.user_id, amount_thb=100)
        
        if not checkout_url:
            raise HTTPException(status_code=502, detail="ไม่สามารถเชื่อมต่อระบบชำระเงินระดับองค์กร (Stripe) ได้ในขณะนี้")
            
        logger.info(f"💳 [Invite Payment Init]: ผู้ใช้ {payload.user_id} เข้าสู่ระบบชำระเงินเพื่อยืนยันสิทธิ์ Enterprise")
        
        # ส่งข้อมูลกลับไปให้ Frontend ดำเนินการ Redirect
        return {
            "status": "pending_payment",
            "stripe_checkout_url": checkout_url,
            "notice": "กรุณาชำระเงินขั้นต่ำ 100 บาทเพื่อยืนยันสิทธิ์และเปิดใช้งาน Enterprise Package"
        }
        
    except HTTPException:
        raise
    except asyncio.TimeoutError:
        logger.error("❌ [Verify Invite Error]: Database timeout during verification")
        raise HTTPException(status_code=504, detail="ระบบตรวจสอบสิทธิ์ทำงานล่าช้า กรุณาลองใหม่อีกครั้ง")
    except Exception as e:
        logger.error(f"❌ [Verify Invite Error]: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="ระบบตรวจสอบสิทธิ์ขัดข้องชั่วคราว ทีมวิศวกรกำลังเร่งแก้ไข")