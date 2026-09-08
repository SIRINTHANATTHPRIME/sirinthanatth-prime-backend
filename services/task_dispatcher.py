import os
import re
import json
import hashlib
import logging
import asyncio
from typing import Dict, Any, Literal
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# =========================================================
# 🛡️ Pydantic Schema: บังคับ AI Router ให้ทำงานเป๊ะ 100%
# =========================================================
class TaskClassificationSchema(BaseModel):
    task_type: Literal["media_render", "standard"] = Field(
        ..., description="ประเภทของงานประเมินจากข้อความ (media_render สำหรับวิดีโอ/เสียง, standard สำหรับแชททั่วไป)"
    )

# =========================================================
# 🌐 นำเข้าศูนย์บัญชาการ AI และระบบนิเวศ
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-3.7-flash" # 🚀 โมเดลเรือธงความเร็วแสงล่าสุด
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

try:
    from services.subscription_manager import SubscriptionManager
except ImportError:
    SubscriptionManager = None

try:
    from upstash_redis.asyncio import Redis
except ImportError:
    Redis = None

logger = logging.getLogger("TaskDispatcher-Swarm")

class HybridTaskDispatcher:
    """
    🚦 ระบบจ่ายงานอัจฉริยะ (Hybrid Task Dispatcher & AI Load Balancer)
    อัปเกรด: Pydantic Routing, Fixed Async Awaits, 3.7 Flash Engine
    """
    def __init__(self):
        self.STANDARD_WEIGHT = 1.0
        self.MEDIA_HEAVY_WEIGHT = 8.5 
        
        self.sub_manager = SubscriptionManager() if SubscriptionManager else None
        
        self.client = PrimeAIConfig.get_client()
        self.router_model = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-3.7-flash")

        redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
        redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self.redis = Redis(url=redis_url, token=redis_token) if redis_url and redis_token and Redis else None

    async def _ai_classify_task(self, payload: Dict[Any, Any]) -> str:
        """🧠 ให้ AI สแกน Payload ภายในเสี้ยววินาที พร้อมระบบ Redis Caching"""
        if not payload: return "standard"

        payload_str = json.dumps(payload, ensure_ascii=False)[:500] 
        
        cache_key = None
        if self.redis:
            try:
                payload_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
                cache_key = f"task_route:{payload_hash}"
                
                cached_route = await self.redis.get(cache_key)
                if cached_route:
                    logger.info(f"⚡ [Edge Cache Hit]: ดึงเส้นทางคิวงานจาก RAM อัตโนมัติ -> '{cached_route}'")
                    return cached_route.decode('utf-8') if isinstance(cached_route, bytes) else cached_route
            except Exception as e:
                logger.warning(f"⚠️ [Redis Cache Error]: {e}")

        if not self.client: return "standard"

        system_instruction = """
        คุณคือ 'Smart Load Balancer' ของระบบ SIRINTHANATTH PRIME
        หน้าที่: ประเมิน Payload ว่าต้องใช้พลังประมวลผลระดับไหน
        - 'วิดีโอ', '4K', 'เรนเดอร์', 'คลิป', 'เสียงพากย์', 'ภาพ 3D' = media_render
        - 'แชท', 'คำนวณ', 'excel', 'สรุป', 'flash express' = standard
        """
        
        try:
            async def _classify():
                return await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.router_model,
                    contents=f"ประเมิน Payload นี้: {payload_str}",
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.0,
                        response_mime_type="application/json",
                        response_schema=TaskClassificationSchema # 🛡️ บังคับโครงสร้างป้องกัน AI พัง
                    )
                )
            
            response = await asyncio.wait_for(_classify(), timeout=3.0)
            
            if response.text:
                decision = json.loads(response.text)
                final_route = decision.get("task_type", "standard")
            else:
                final_route = "standard"

            if self.redis and cache_key:
                # ลดเวลาแคชเหลือ 2 ชม. ป้องกันข้อมูลหลงลืมข้ามวัน
                await self.redis.setex(cache_key, 7200, final_route) 

            logger.info(f"🧠 [AI Router]: วิเคราะห์ Payload ใหม่สำเร็จ -> จัดลงคิว '{final_route.upper()}'")
            return final_route
            
        except asyncio.TimeoutError:
            logger.warning("⚠️ [AI Router Timeout]: AI ตอบกลับช้ากว่า 3 วิ -> Fallback to Standard")
            return "standard"
        except Exception as e:
            logger.warning(f"⚠️ [AI Router Warning]: ประเมินโหลดงานล้มเหลว ({e}) -> Fallback to Standard")
            return "standard"

    async def route_and_execute(self, user_id: str, task_type: str, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """ฟังก์ชันสลับทิศทางงาน (Hybrid Switching) รองรับ Async I/O 100%"""
        try:
            if task_type == "auto":
                task_type = await self._ai_classify_task(payload)

            # 🛡️ ใช้วิธี await ตรงๆ เพราะ check_feature_access เป็นฟังก์ชันแบบ async แล้ว
            if self.sub_manager:
                has_access = await self.sub_manager.check_feature_access(user_id, task_type)
                if not has_access:
                    logger.warning(f"🚫 [Access Denied]: {user_id} พยายามเข้าถึง {task_type} โดยไม่มีสิทธิ์")
                    return {
                        "status": "error", 
                        "engine": "none", 
                        "message": "⚠️ ขออภัยครับ แพ็กเกจของคุณยังไม่รองรับฟีเจอร์นี้ กรุณาอัปเกรดสิทธิ์ผ่าน Smart Wallet ครับ"
                    }

            if task_type == "media_render":
                if self.sub_manager:
                    # 🛡️ ใช้วิธี await ตรงๆ เพราะ deduct_media_fee เป็นฟังก์ชันแบบ async แล้ว
                    payment_check = await self.sub_manager.deduct_media_fee(user_id, 49.0)
                    if payment_check and payment_check.get("status") == "error":
                        return {"status": "error", "message": payment_check.get("msg", "ยอดเงินไม่พอ")}

                logger.info(f"⚡ [Hybrid Switcher]: สลับโหมดเป็น HEAVY WORKLOAD สำหรับ {user_id}")
                result = await self._run_heavy_media_engine(payload)
                token_cost = self._calculate_tokens(base_cost=10, weight=self.MEDIA_HEAVY_WEIGHT)
                return {"status": "success", "engine": "prime-media-engine", "cost": token_cost, "data": result}
            
            else:
                logger.info(f"🧠 [Hybrid Switcher]: ส่งงานเข้า STANDARD WORKLOAD สำหรับ {user_id}")
                result = await self._run_standard_agent(payload)
                token_cost = self._calculate_tokens(base_cost=1, weight=self.STANDARD_WEIGHT)
                return {"status": "success", "engine": "prime-core-agent", "cost": token_cost, "data": result}

        except Exception as e:
            logger.error(f"❌ Error in HybridTaskDispatcher: {str(e)}", exc_info=True)
            return {"status": "error", "message": "เกิดข้อผิดพลาดในการจ่ายคิวงานระบบ กรุณาลองใหม่อีกครั้งครับ"}

    async def _run_standard_agent(self, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """จำลองการทำงานของ Core Agent"""
        await asyncio.sleep(0.1) 
        return {"message": "Standard processing completed.", "payload_received": payload}

    async def _run_heavy_media_engine(self, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """จำลองการทำงานของ Media Engine 4K"""
        await asyncio.sleep(0.5) 
        return {"message": "Media rendering completed via heavy worker.", "media_url": "https://storage.googleapis.com/sirinthanatthprime/output.mp4"}

    def _calculate_tokens(self, base_cost: int, weight: float) -> float:
        """คำนวณต้นทุนการประมวลผล (Tokenomics Scaling)"""
        return round(base_cost * weight, 2)