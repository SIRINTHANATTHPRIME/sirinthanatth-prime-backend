import logging
from fastapi import APIRouter

logger = logging.getLogger("RoutesStats")

# สร้าง Router สำหรับแผนกสถิติ
router = APIRouter()

@router.get("/vip-quota")
async def get_vip_quota():
    """
    📊 Endpoint สำหรับส่งตัวเลขสถิติแบบ Real-Time ไปแสดงที่หน้าเว็บ
    URL จริงจะเป็น: /api/v1/stats/vip-quota
    """
    try:
        # ในอนาคต: ท่านประธานสามารถเขียนโค้ดดึงยอดตรงจาก Stripe หรือ Supabase ตรงนี้ได้เลย
        # สมมติว่าตอนนี้ดึงยอดมาได้ 82 คน
        current_paid_users = 82
        
        return {
            "status": "success",
            "paid_count": current_paid_users,
            "max_quota": 100
        }
    except Exception as e:
        logger.error(f"❌ [Stats API Error]: {e}")
        # ระบบ Fallback ส่ง 0 กลับไปเพื่อไม่ให้หน้าเว็บลูกค้าพัง
        return {"status": "error", "paid_count": 0, "max_quota": 100}