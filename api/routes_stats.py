import os
import logging
import asyncio
from fastapi import APIRouter
from supabase import create_client, Client
from google import genai
from google.genai import types

# ตั้งค่า Logger
logger = logging.getLogger("RoutesStats")

# =========================================================
# 🌐 1. นำเข้าศูนย์บัญชาการ AI และฐานข้อมูล
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-2.5-flash" # 🚀 ใช้โมเดลความเร็วแสงสำหรับการสร้างข้อความการตลาด
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

# สร้าง Router สำหรับแผนกสถิติ
router = APIRouter()

# เชื่อมต่อ Supabase สำหรับดึงสถิติ
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None


@router.get("/vip-quota")
async def get_vip_quota():
    """
    📊 Endpoint สำหรับส่งตัวเลขสถิติแบบ Real-Time และสร้างข้อความการตลาด (FOMO)
    URL: /api/v1/stats/vip-quota
    """
    MAX_QUOTA = 100
    paid_count = 82 # Fallback กรณี Database ขัดข้อง
    
    try:
        # ==========================================
        # 1. ดึงสถิติจริงจากฐานข้อมูล Supabase (นับจำนวน VIP_FOUNDER)
        # ==========================================
        if supabase:
            def fetch_vip_count():
                # ดึงจำนวนแถวที่มี package_tier เป็น VIP_FOUNDER
                res = supabase.table("prime_clients").select("id", count="exact").eq("package_tier", "VIP_FOUNDER").execute()
                return res.count if res.count is not None else 82
                
            paid_count = await asyncio.to_thread(fetch_vip_count)
            
        remaining = MAX_QUOTA - paid_count
        if remaining < 0: remaining = 0
        
        # ==========================================
        # 2. ใช้ Vertex AI สร้างข้อความกระตุ้นยอดขาย (Psychological FOMO)
        # ==========================================
        ai_client = PrimeAIConfig.get_client()
        model_name = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-2.5-flash")
        
        fomo_message = f"เหลือเพียง {remaining} สิทธิ์สุดท้าย ก่อนปรับราคาขึ้น!"
        
        if ai_client and remaining > 0:
            prompt = f"""
            คุณคือ CMO (Chief Marketing Officer) ของแบรนด์ SIRINTHANATTH PRIME
            ขณะนี้แพ็กเกจ '100 VIP Founders' (ราคาพิเศษตลอดชีพ) มีนักธุรกิจสมัครแล้ว {paid_count}/{MAX_QUOTA} คน (เหลือเพียง {remaining} สิทธิ์)
            
            จงเขียนข้อความสั้นๆ 1 ประโยค (ไม่เกิน 20 คำ) เพื่อกระตุ้นให้คนรีบสมัคร (FOMO) 
            ให้ดูพรีเมียม หรูหรา สงวนสิทธิ์เฉพาะผู้บริหารระดับสูง ห้ามใช้คำหยาบหรือดูถูก
            """
            
            try:
                ai_res = await asyncio.to_thread(
                    ai_client.models.generate_content,
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7 # ใช้อุณหภูมิ 0.7 เพื่อสร้างสรรค์ข้อความการตลาดที่ไม่ซ้ำซาก
                    )
                )
                if ai_res.text:
                    fomo_message = ai_res.text.strip()
            except Exception as ai_err:
                logger.warning(f"⚠️ [AI FOMO Warning]: {ai_err}")
                
        elif remaining == 0:
            fomo_message = "Sold Out! สิทธิ์ 100 VIP Founders เต็มแล้ว ขอบพระคุณนักลงทุนทุกท่านครับ"

        # ==========================================
        # 3. จัดส่งข้อมูล JSON สำหรับหน้าเว็บ LIFF (Frontend)
        # ==========================================
        return {
            "status": "success",
            "paid_count": paid_count,
            "max_quota": MAX_QUOTA,
            "remaining": remaining,
            "fomo_message": fomo_message
        }
        
    except Exception as e:
        logger.error(f"❌ [Stats API Error]: {e}")
        # ระบบ Fallback ทำงานเมื่อระบบล่ม เพื่อไม่ให้หน้าเว็บลูกค้าพัง
        remaining = MAX_QUOTA - paid_count
        return {
            "status": "error", 
            "paid_count": paid_count, 
            "max_quota": MAX_QUOTA,
            "remaining": remaining if remaining > 0 else 0,
            "fomo_message": "โอกาสสุดท้าย! สมัคร VIP วันนี้รับสิทธิพิเศษเต็มรูปแบบ"
        }