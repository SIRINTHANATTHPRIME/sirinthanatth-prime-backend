import os
import re
import json
import hashlib
import logging
import asyncio
from typing import Dict, Any
from google import genai
from google.genai import types

# =========================================================
# 🌐 1. นำเข้าศูนย์บัญชาการ AI ส่วนกลาง (Vertex AI / Zero Downtime)
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-2.5-flash" # 🚀 อัปเกรดเป็นแกนสมองสายสปีดที่เร็วและฉลาดที่สุดของโลกที่มีอยู่จริง
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

# 🛡️ 2. นำเข้าระบบตรวจสอบสิทธิ์และ Wallet
try:
    from services.subscription_manager import SubscriptionManager
except ImportError:
    SubscriptionManager = None

# ⚡ 3. นำเข้า Edge Caching (Redis) เพื่อความเร็วดุจสายฟ้า
try:
    from upstash_redis.asyncio import Redis
except ImportError:
    Redis = None

logger = logging.getLogger("TaskDispatcher-Swarm")

class HybridTaskDispatcher:
    """
    🚦 ระบบจ่ายงานอัจฉริยะ (Hybrid Task Dispatcher & AI Load Balancer)
    อัปเกรดขั้นสุด: ผสาน Edge Caching (Redis) + Gemini 2.5 Flash เพื่อแยกประเภทงานเบา/หนัก อัตโนมัติ (Zero Latency)
    """
    def __init__(self):
        # กำหนดอัตราส่วนน้ำหนัก Token (Weight Multiplier) สำหรับซ่อนเรตหลังบ้าน
        self.STANDARD_WEIGHT = 1.0
        self.MEDIA_HEAVY_WEIGHT = 8.5  # อ้างอิงสเปกเทียบเคียงคลาวด์ 32 GiB / 8 vCPU
        
        self.sub_manager = SubscriptionManager() if SubscriptionManager else None
        
        # 🚀 Vertex AI Client สำหรับวิเคราะห์โหลดงาน (Smart Load Balancing)
        self.client = PrimeAIConfig.get_client()
        self.router_model = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-2.5-flash")

        # ⚡ เชื่อมต่อ Redis สำหรับ Semantic Caching (จดจำการจัดคิวงาน ไม่ต้องถาม AI ซ้ำ)
        redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
        redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self.redis = Redis(url=redis_url, token=redis_token) if redis_url and redis_token and Redis else None

    async def _ai_classify_task(self, payload: Dict[Any, Any]) -> str:
        """🧠 ให้ AI สแกน Payload ภายในเสี้ยววินาที พร้อมระบบ Redis Caching ลดภาระ API"""
        if not payload: return "standard"

        # ตัดเฉพาะข้อมูลสำคัญมาตรวจสอบความรวดเร็ว
        payload_str = json.dumps(payload, ensure_ascii=False)[:500] 
        
        # ==========================================
        # ⚡ 1. ตรวจสอบจาก Redis Cache ก่อน (Edge Caching) เร็วระดับมิลลิวินาที (0ms)
        # ==========================================
        cache_key = None
        if self.redis:
            try:
                # สร้างรหัส Hash จากข้อความ Payload เพื่อเป็นกุญแจค้นหาใน RAM
                payload_hash = hashlib.md5(payload_str.encode('utf-8')).hexdigest()
                cache_key = f"task_route:{payload_hash}"
                
                cached_route = await self.redis.get(cache_key)
                if cached_route:
                    logger.info(f"⚡ [Edge Cache Hit]: ดึงเส้นทางคิวงานจาก RAM อัตโนมัติ -> '{cached_route}'")
                    return cached_route.decode('utf-8') if isinstance(cached_route, bytes) else cached_route
            except Exception as e:
                logger.warning(f"⚠️ [Redis Cache Error]: {e}")

        if not self.client: return "standard"

        # ==========================================
        # 🧠 2. ถ้าไม่มีใน Cache ให้ Gemini 2.5 Flash คิดและตัดสินใจ
        # ==========================================
        system_instruction = """
        คุณคือ 'Smart Load Balancer' ของระบบ SIRINTHANATTH PRIME
        หน้าที่: ประเมิน Payload ว่าต้องใช้พลังประมวลผลระดับไหน
        - หากมีคีย์เวิร์ดเกี่ยวกับ: 'วิดีโอ', '4K', 'เรนเดอร์', 'คลิป', 'เสียงพากย์', 'ภาพ 3D' ให้ตอบ "media_render"
        - หากเป็นเรื่องทั่วไป: 'แชท', 'คำนวณ', 'excel', 'สรุป', 'flash express' ให้ตอบ "standard"
        ตอบกลับเป็น JSON เท่านั้น: {"task_type": "media_render" หรือ "standard"}
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.router_model,
                contents=f"ประเมิน Payload นี้: {payload_str}",
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.0, # ต้องการความแม่นยำทางตรรกะสูงสุดแบบตายตัว
                    response_mime_type="application/json"
                )
            )
            
            res_text = re.sub(r'^```json\s*', '', response.text.strip())
            res_text = re.sub(r'\s*```$', '', res_text)
            decision = json.loads(res_text)
            final_route = decision.get("task_type", "standard")

            # ==========================================
            # ⚡ 3. บันทึกผลลัพธ์ลง Redis Cache (อายุ 24 ชั่วโมง)
            # ==========================================
            if self.redis and cache_key:
                await self.redis.setex(cache_key, 86400, final_route) # 86400 วินาที = 24 ชม.

            logger.info(f"🧠 [AI Router]: วิเคราะห์ Payload ใหม่สำเร็จ -> จัดลงคิว '{final_route.upper()}'")
            return final_route
            
        except Exception as e:
            logger.warning(f"⚠️ [AI Router Warning]: ประเมินโหลดงานล้มเหลว ({e}) -> Fallback to Standard")
            return "standard"

    async def route_and_execute(self, user_id: str, task_type: str, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """ฟังก์ชันสลับทิศทางงาน (Hybrid Switching) รองรับ Async I/O 100% พร้อม Backward Compatibility"""
        try:
            # 1. 🤖 [Autonomous AI Routing]: หากระบบโยนงานมาแบบ 'auto' ให้ AI ตัดสินใจเอง
            if task_type == "auto":
                task_type = await self._ai_classify_task(payload)

            # 2. 🛡️ เช็กสิทธิ์แพ็กเกจของลูกค้าจาก SubscriptionManager
            if self.sub_manager:
                def _check_access():
                    return self.sub_manager.check_feature_access(user_id, task_type)
                
                has_access = await asyncio.to_thread(_check_access)
                if not has_access:
                    logger.warning(f"🚫 [Access Denied]: {user_id} พยายามเข้าถึง {task_type} โดยไม่มีสิทธิ์")
                    return {
                        "status": "error", 
                        "engine": "none", 
                        "message": "⚠️ ขออภัยครับ แพ็กเกจของคุณยังไม่รองรับการใช้งานฟีเจอร์หรือการเรนเดอร์ระดับนี้ กรุณาอัปเกรดสิทธิ์ผ่าน Smart Wallet ครับ"
                    }

            # 3. 🎬 โหมดงานหนัก (HEAVY WORKLOAD): เรนเดอร์วิดีโอ / เสียง 4K
            if task_type == "media_render":
                # เช็กและหักเงินแบบ Non-blocking ก่อนใช้เซิร์ฟเวอร์หนัก
                if self.sub_manager:
                    payment_check = await asyncio.to_thread(self.sub_manager.deduct_media_fee, user_id, 49.0)
                    if payment_check and payment_check.get("status") == "error":
                        return {"status": "error", "message": payment_check.get("msg", "ยอดเงินไม่พอ")}

                logger.info(f"⚡ [Hybrid Switcher]: สลับโหมดเป็น HEAVY WORKLOAD สำหรับ {user_id}")
                result = await self._run_heavy_media_engine(payload)
                token_cost = self._calculate_tokens(base_cost=10, weight=self.MEDIA_HEAVY_WEIGHT)
                
                return {"status": "success", "engine": "prime-media-engine", "cost": token_cost, "data": result}
            
            # 4. 🧠 โหมดงานมาตรฐาน (STANDARD WORKLOAD): ประมวลผลข้อมูลทั่วไป
            else:
                logger.info(f"🧠 [Hybrid Switcher]: ส่งงานเข้า STANDARD WORKLOAD สำหรับ {user_id}")
                result = await self._run_standard_agent(payload)
                token_cost = self._calculate_tokens(base_cost=1, weight=self.STANDARD_WEIGHT)
                return {"status": "success", "engine": "prime-core-agent", "cost": token_cost, "data": result}

        except Exception as e:
            logger.error(f"❌ Error in HybridTaskDispatcher: {str(e)}")
            return {"status": "error", "message": "เกิดข้อผิดพลาดในการจ่ายคิวงานระบบ กรุณาลองใหม่อีกครั้งครับ"}

    async def _run_standard_agent(self, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """จำลองการทำงานของ Core Agent แบบไม่บล็อกระบบ (Async I/O)"""
        await asyncio.sleep(0.1) # Simulate Async Data Processing
        return {"message": "Standard processing completed.", "payload_received": payload}

    async def _run_heavy_media_engine(self, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """จำลองการทำงานของ Media Engine 4K บนสเปกสูง"""
        await asyncio.sleep(0.5) # Simulate Cloud Run Heavy Rendering Delay
        return {"message": "Media rendering completed via heavy worker.", "media_url": "https://storage.googleapis.com/sirinthanatthprime/output.mp4"}

    def _calculate_tokens(self, base_cost: int, weight: float) -> float:
        """คำนวณต้นทุนการประมวลผล (Tokenomics Scaling)"""
        return round(base_cost * weight, 2)