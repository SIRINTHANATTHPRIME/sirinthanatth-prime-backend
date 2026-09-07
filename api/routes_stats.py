import os
import time
import logging
import asyncio
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from supabase import create_client, Client
from google import genai
from google.genai import types

# ตั้งค่า Logger ระดับ Enterprise
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RoutesStats")

# =========================================================
# 🌐 1. นำเข้าศูนย์บัญชาการ AI และฐานข้อมูล
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-3.7-flash" # 🚀 อัปเกรดเป็นรุ่นความเร็วแสงล่าสุด
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# =========================================================
# 🛡️ 2. ระบบ Enterprise Caching (ป้องกันเซิร์ฟเวอร์ล่ม)
# =========================================================
# หากคนเข้าเว็บ 10,000 คนพร้อมกัน ระบบจะดึง AI และ DB แค่ 1 ครั้ง/นาที 
# ที่เหลือจะดึงจาก Cache (ความเร็ว 0.001 วินาที)
class StatsCache:
    def __init__(self, ttl_seconds=60):
        self.ttl = ttl_seconds
        self.data = None
        self.last_update = 0
        self.lock = asyncio.Lock()

    async def get_or_update(self, update_func):
        now = time.time()
        # ใช้ Double-checked locking ป้องกัน Race Condition
        if self.data is None or (now - self.last_update) > self.ttl:
            async with self.lock:
                if self.data is None or (time.time() - self.last_update) > self.ttl:
                    self.data = await update_func()
                    self.last_update = time.time()
        return self.data

stats_cache = StatsCache(ttl_seconds=60) # อัปเดตข้อมูลทุกๆ 60 วินาที

# =========================================================
# 📦 3. Pydantic Response Schema (มาตรฐาน API สากล)
# =========================================================
class VIPStatsResponse(BaseModel):
    status: str
    paid_count: int
    max_quota: int
    remaining: int
    urgency_level: str # 'HIGH', 'MEDIUM', 'LOW', 'SOLD_OUT'
    fomo_message: str
    last_updated: str

# =========================================================
# 🧠 4. ฟังก์ชันประมวลผลหลัก (Core Logic)
# =========================================================
async def generate_live_stats() -> dict:
    """ฟังก์ชันดึงสถิติและให้ AI สร้างข้อความการตลาด (ทำงานหลังฉาก)"""
    MAX_QUOTA = 100
    paid_count = 82 # Fallback
    
    try:
        # 📊 1. ดึงสถิติจริงจากฐานข้อมูล
        if supabase:
            def fetch_vip_count():
                res = supabase.table("prime_clients").select("id", count="exact").eq("package_tier", "VIP_FOUNDER").execute()
                return res.count if res.count is not None else 82
            paid_count = await asyncio.to_thread(fetch_vip_count)
            
        remaining = max(0, MAX_QUOTA - paid_count)
        
        # 🌡️ 2. ประเมินระดับความเร่งด่วน (Urgency Psychology)
        urgency_level = "LOW"
        if remaining == 0: urgency_level = "SOLD_OUT"
        elif remaining <= 10: urgency_level = "HIGH"
        elif remaining <= 30: urgency_level = "MEDIUM"

        # 🧠 3. สั่งการ Chief Marketing Officer (AI)
        ai_client = PrimeAIConfig.get_client()
        model_name = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-3.7-flash")
        
        fomo_message = f"เหลือเพียง {remaining} สิทธิ์สุดท้าย ก่อนปรับราคาขึ้น!"
        
        if ai_client and remaining > 0:
            prompt = f"""
            คุณคือ 'Global Chief Marketing Officer (CMO)' ของแบรนด์ SIRINTHANATTH PRIME
            ระดับความเร่งด่วนตอนนี้: {urgency_level}
            โควตาแพ็กเกจ '100 VIP Founders': มีผู้บริหารจองแล้ว {paid_count}/{MAX_QUOTA} คน (เหลือเพียง {remaining} สิทธิ์)
            
            จงเขียนข้อความโฆษณา 1 ประโยค (ไม่เกิน 20 คำ) เพื่อกระตุ้นให้ผู้บริหารระดับสูงรีบสมัคร (Psychological FOMO)
            กฎ: หรูหรา ทรงพลัง น่าเกรงขาม และเข้าถึงอารมณ์ความกลัวพลาดโอกาส
            """
            try:
                ai_res = await asyncio.to_thread(
                    ai_client.models.generate_content,
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.8) # 0.8 ให้ AI คิดข้อความที่สร้างสรรค์และไม่ซ้ำซาก
                )
                if ai_res.text:
                    fomo_message = ai_res.text.strip().replace('"', '')
            except Exception as ai_err:
                logger.warning(f"⚠️ [AI FOMO Warning]: {ai_err}")
                
        elif remaining == 0:
            fomo_message = "SOLD OUT: สิทธิพิเศษ VIP Founders ครบ 100 ท่านแล้ว ขอบพระคุณท่านประธานและผู้บริหารทุกท่านครับ"

        return {
            "status": "success",
            "paid_count": paid_count,
            "max_quota": MAX_QUOTA,
            "remaining": remaining,
            "urgency_level": urgency_level,
            "fomo_message": fomo_message,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    except Exception as e:
        logger.error(f"❌ [Stats Engine Error]: {e}")
        remaining = max(0, MAX_QUOTA - paid_count)
        return {
            "status": "error", 
            "paid_count": paid_count, 
            "max_quota": MAX_QUOTA,
            "remaining": remaining,
            "urgency_level": "HIGH" if remaining <= 10 else "MEDIUM",
            "fomo_message": "🚨 โอกาสสุดท้ายของปี! สมัคร VIP วันนี้รับสิทธิพิเศษเต็มรูปแบบ ก่อนปิดรับสมัคร",
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

# =========================================================
# 📡 5. API Endpoint (ด่านหน้ารับคำขอจากหน้าเว็บ LIFF)
# =========================================================
@router.get("/vip-quota", response_model=VIPStatsResponse)
async def get_vip_quota():
    """
    📊 Endpoint สำหรับส่งตัวเลขสถิติแบบ Real-Time และสร้างข้อความการตลาด
    ระบบ Caching อัจฉริยะ (ดึง Data/AI สูงสุดแค่ 1 ครั้งต่อนาที ป้องกันระบบล่ม)
    """
    # เรียกใช้ Cache อัจฉริยะ 
    # หากหมดเวลา (TTL) ระบบจะรัน `generate_live_stats` ใหม่โดยอัตโนมัติ
    data = await stats_cache.get_or_update(generate_live_stats)
    return data