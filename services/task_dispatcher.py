from email.mime import message
import os
import re
import json
import hashlib
import logging
import asyncio
from typing import Dict, Any, Literal
from urllib import response
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from services import semantic_cache
from services.semantic_cache import SemanticCacheManager
semantic_cache = SemanticCacheManager()

# =========================================================
# 🛡️ Pydantic Schema: 2-in-1 (แยกคิวงาน + อ่านใจลูกค้า)
# =========================================================
class TaskClassificationSchema(BaseModel):
    task_type: Literal["media_render", "standard_chat", "complex_strategy"] = Field(
        ..., description="media_render (วิดีโอ/เสียง), standard_chat (แชททั่วไป), complex_strategy (วิเคราะห์ลึก/กลยุทธ์/กฎหมาย)"
    )
    customer_sentiment: Literal["positive", "neutral", "frustrated", "urgent"] = Field(
        ..., description="สภาวะอารมณ์ของลูกค้า ณ วินาทีนี้"
    )
    recommended_tone: str = Field(
        ..., description="น้ำเสียงที่ AI ควรใช้ตอบกลับ เช่น 'ต้องขออภัยและกระชับ', 'นุ่มนวลและเห็นอกเห็นใจ', 'เป็นทางการและหนักแน่น'"
    )

# =========================================================
# 🌐 นำเข้าศูนย์บัญชาการ AI และระบบนิเวศ
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-3.7-flash" # 🚀 ด่านหน้า: รวดเร็ว ประหยัด
        EXECUTIVE_MODEL = "gemini-3.1-pro-preview" # 🧠 สมองกลลึก: ฉลาด ซับซ้อน
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
    🚦 ระบบจ่ายงานอัจฉริยะ (Predictive Empathy & Hybrid Router)
    สลับสับเปลี่ยนรุ่น AI อัตโนมัติ พร้อมวิเคราะห์อารมณ์ลูกค้าก่อนตอบกลับ
    """
    def __init__(self):
        self.STANDARD_WEIGHT = 1.0     
        self.PRO_WEIGHT = 5.0          
        self.MEDIA_HEAVY_WEIGHT = 8.5  
        
        self.sub_manager = SubscriptionManager() if SubscriptionManager else None
        self.client = PrimeAIConfig.get_client()
        
        self.router_model = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-3.7-flash")
        self.executive_model = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.1-pro-preview")

        redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
        redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self.redis = Redis(url=redis_url, token=redis_token) if redis_url and redis_token and Redis else None

    async def process_task(self, user_id: str, message: str) -> str:
        # 2. ⚡ ดักจับด้วย Semantic Cache (ตรวจสอบความเหมือน > 90%)
        cached_response = await semantic_cache.get_cached_response(message)
        if cached_response:
            return cached_response # ส่งคำตอบจาก RAM กลับทันที (ต้นทุน 0 บาท)

        # ---------------------------------------------------------
        # 3. ถ้าไม่เคยมีคนถามคำถามนี้เลย ค่อยปลุก Gemini API ให้ทำงาน
        # ---------------------------------------------------------
        logger.info("🧠 [AI Engine]: ไม่พบในแคช กำลังประมวลผลคำตอบใหม่...")
        response = await self.client.models.generate_content(...)
        final_text = response.text

        # 4. 💾 นำคำตอบใหม่ที่ AI คิดเสร็จแล้ว กลับไปฝากไว้ในแคช
        await semantic_cache.set_cached_response(message, final_text)

        return final_text

    async def _ai_classify_task(self, payload: Dict[Any, Any]) -> dict:
        """🧠 วิเคราะห์ 2-in-1: จัดคิวงาน + อ่านอารมณ์ลูกค้า (Predictive Empathy)"""
        default_result = {
            "task_type": "standard_chat",
            "customer_sentiment": "neutral",
            "recommended_tone": "สุภาพและเป็นมืออาชีพ"
        }
        
        if not payload: return default_result

        payload_str = json.dumps(payload, ensure_ascii=False)[:500] 
        
        cache_key = None
        if self.redis:
            try:
                payload_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()
                cache_key = f"task_route_v2:{payload_hash}"
                
                cached_data = await self.redis.get(cache_key)
                if cached_data:
                    logger.info(f"⚡ [Edge Cache Hit]: ดึงเส้นทางและอารมณ์จาก RAM -> {cached_data}")
                    return json.loads(cached_data) if isinstance(cached_data, (str, bytes)) else cached_data
            except Exception as e:
                logger.warning(f"⚠️ [Redis Cache Error]: {e}")

        if not self.client: return default_result

        system_instruction = """
        คุณคือ 'Smart Load Balancer & Empathy Engine' ของ SIRINTHANATTH PRIME
        หน้าที่ของคุณคือ 2 อย่าง:
        1. ประเมินหมวดหมู่งาน: 
           - 'วิดีโอ', '4K', 'เรนเดอร์', 'คลิป', 'เสียงพากย์', 'ภาพ 3D' = media_render
           - 'วิเคราะห์งบ', 'วางแผนกลยุทธ์', 'ตรวจสอบสัญญา', 'โฉนดที่ดิน', 'กฎหมาย', 'ลงทุน' = complex_strategy
           - 'แชททั่วไป', 'สวัสดี', 'สรุปสั้นๆ', 'คำนวณเบื้องต้น', 'flash express' = standard_chat
        2. อ่านอารมณ์ลูกค้า: ประเมินว่าเขากำลังโกรธ (frustrated), รีบเร่ง (urgent), พอใจ (positive), หรือปกติ (neutral)
           และกำหนด 'recommended_tone' ให้ AI ตัวถัดไปใช้ตอบอย่างเหมาะสมที่สุด (เช่น 'ใจเย็นและเห็นอกเห็นใจ' หรือ 'กระชับรวดเร็ว')
        """
        
        try:
            async def _classify():
                return await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.router_model,
                    contents=f"ประเมิน Payload และอารมณ์ลูกค้า: {payload_str}",
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.1,
                        response_mime_type="application/json",
                        response_schema=TaskClassificationSchema
                    )
                )
            
            response = await asyncio.wait_for(_classify(), timeout=4.0)
            
            if response.text:
                decision = json.loads(response.text)
            else:
                decision = default_result

            if self.redis and cache_key:
                await self.redis.setex(cache_key, 7200, json.dumps(decision, ensure_ascii=False)) 

            logger.info(f"🧠 [Empathy Router]: อารมณ์ '{decision.get('customer_sentiment', 'neutral').upper()}' -> ลงคิว '{decision.get('task_type', 'standard_chat').upper()}'")
            return decision
            
        except asyncio.TimeoutError:
            logger.warning("⚠️ [Router Timeout]: ตอบกลับช้ากว่า 4 วิ -> Fallback")
            return default_result
        except Exception as e:
            logger.warning(f"⚠️ [Router Error]: ประเมินโหลดงานล้มเหลว ({e}) -> Fallback")
            return default_result

    async def route_and_execute(self, user_id: str, task_type: str, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """สลับทิศทางงาน พร้อมแนบ 'น้ำเสียง' (Empathy Tone) ไปให้ AI ปลายทาง"""
        try:
            decision = await self._ai_classify_task(payload)
            final_task_type = decision.get("task_type", "standard_chat")
            empathy_tone = decision.get("recommended_tone", "สุภาพและเป็นมืออาชีพ")
            sentiment = decision.get("customer_sentiment", "neutral")
            
            if task_type != "auto" and task_type in ["media_render", "complex_strategy", "standard_chat"]:
                final_task_type = task_type

            # นำ Empathy Tone แนบเข้า Payload เพื่อส่งให้ Worker นำไปใช้คุม Tone การตอบ
            payload["_empathy_context"] = {
                "sentiment": sentiment,
                "recommended_tone": empathy_tone
            }

            if self.sub_manager:
                has_access = await self.sub_manager.check_feature_access(user_id, final_task_type)
                if not has_access:
                    logger.warning(f"🚫 [Access Denied]: {user_id} พยายามเข้าถึง {final_task_type} โดยไม่มีสิทธิ์")
                    return {
                        "status": "error", 
                        "engine": "none", 
                        "message": "⚠️ ขออภัยครับ แพ็กเกจของคุณยังไม่รองรับฟีเจอร์นี้ กรุณาอัปเกรดสิทธิ์ผ่าน Smart Wallet ครับ"
                    }

            if final_task_type == "media_render":
                if self.sub_manager:
                    payment_check = await self.sub_manager.deduct_media_fee(user_id, 49.0)
                    if payment_check and payment_check.get("status") == "error":
                        return {"status": "error", "message": payment_check.get("msg", "ยอดเงินไม่พอ")}

                logger.info(f"⚡ [Hybrid Switcher]: โหมด MEDIA ENGINE สำหรับ {user_id}")
                result = await self._run_heavy_media_engine(payload)
                return {"status": "success", "engine": "prime-media-engine", "cost": self._calculate_tokens(10, self.MEDIA_HEAVY_WEIGHT), "data": result}
            
            elif final_task_type == "complex_strategy":
                logger.info(f"🧠 [Hybrid Switcher]: โหมด EXECUTIVE PRO สำหรับ {user_id} (อารมณ์: {sentiment})")
                result = await self._run_executive_agent(payload)
                return {"status": "success", "engine": "prime-executive-pro", "cost": self._calculate_tokens(1, self.PRO_WEIGHT), "data": result}
            
            else:
                logger.info(f"⚡ [Hybrid Switcher]: โหมด STANDARD FLASH สำหรับ {user_id} (อารมณ์: {sentiment})")
                result = await self._run_standard_agent(payload)
                return {"status": "success", "engine": "prime-core-flash", "cost": self._calculate_tokens(1, self.STANDARD_WEIGHT), "data": result}

        except Exception as e:
            logger.error(f"❌ Error in HybridTaskDispatcher: {str(e)}", exc_info=True)
            return {"status": "error", "message": "เกิดข้อผิดพลาดในการจ่ายคิวงานระบบ กรุณาลองใหม่อีกครั้งครับ"}

    async def _run_standard_agent(self, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """จำลองการทำงานของ Core Agent (ใช้โมเดล Flash)"""
        await asyncio.sleep(0.1) 
        return {"message": "Standard processing completed via High-Speed Flash.", "payload_received": payload}

    async def _run_executive_agent(self, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """จำลองการทำงานของ Executive Agent (ใช้โมเดล Pro)"""
        await asyncio.sleep(0.3) 
        return {"message": "Complex strategy analyzed successfully via Executive Pro.", "payload_received": payload}

    async def _run_heavy_media_engine(self, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """จำลองการทำงานของ Media Engine 4K"""
        await asyncio.sleep(0.5) 
        return {"message": "Media rendering completed.", "media_url": "https://storage.googleapis.com/sirinthanatthprime/output.mp4"}

    def _calculate_tokens(self, base_cost: int, weight: float) -> float:
        """คำนวณต้นทุนการประมวลผล (Tokenomics Scaling)"""
        return round(base_cost * weight, 2)