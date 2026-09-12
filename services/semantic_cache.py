import os
import hashlib
import logging
import asyncio
import threading
from typing import Optional
from upstash_redis.asyncio import Redis
from supabase import create_client, Client

# นำเข้าฟังก์ชันแปลงข้อความเป็น Vector
try:
    from agents.memory_engine import get_text_embedding
except ImportError:
    def get_text_embedding(text): return []

logger = logging.getLogger("SemanticCache")

class SemanticCacheManager:
    """
    🧠 ระบบ Semantic Caching อัจฉริยะ ระดับ Enterprise (Zero-Latency)
    อัปเกรด: Singleton Architecture, Dual-Circuit Breaker, Non-Blocking Vector Indexing
    """
    _instance = None
    _init_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """🚀 Singleton: บังคับใช้ท่อการเชื่อมต่อเดียวทั่วทั้งเซิร์ฟเวอร์เพื่อความเสถียร"""
        if not cls._instance:
            with cls._init_lock:
                if not cls._instance:
                    cls._instance = super(SemanticCacheManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False): return
        
        # 1. เชื่อมต่อ Redis (RAM Retrieval - ความเร็วแสง)
        redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
        redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self.redis = Redis(url=redis_url, token=redis_token) if redis_url and redis_token else None

        # 2. เชื่อมต่อ Supabase (Vector Search - ค้นหาความหมาย)
        supa_url = os.environ.get("SUPABASE_URL")
        supa_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
        self.supabase: Optional[Client] = create_client(supa_url, supa_key) if supa_url and supa_key else None

        self.similarity_threshold = 0.90 # ล็อกมาตรฐานความแม่นยำ 90% ขึ้นไป
        self.cache_ttl_seconds = 86400   # อายุของ Cache (24 ชั่วโมง)
        
        self._initialized = True

    async def get_cached_response(self, user_text: str) -> str:
        """🔍 ตรวจสอบว่าคำถามนี้เคยถูกตอบไปแล้วหรือไม่ พร้อมระบบตัดวงจรป้องกันเซิร์ฟเวอร์ค้าง"""
        if not self.redis or not self.supabase or len(user_text) < 5:
            return ""
            
        try:
            # 1. แปลงคำถามใหม่เป็น Vector (ประมวลผลใน Thread แยก ไม่บล็อก Event Loop หลัก)
            vector_data = await asyncio.to_thread(get_text_embedding, user_text)
            if not vector_data: return ""

            # 2. ค้นหาใน Supabase ด้วย RPC พร้อม Circuit Breaker (ตัดการเชื่อมต่อใน 3 วินาที)
            def fetch_match():
                return self.supabase.rpc('match_semantic_cache', {
                    'query_embedding': vector_data, 
                    'match_threshold': self.similarity_threshold
                }).execute()
                
            match_result = await asyncio.wait_for(asyncio.to_thread(fetch_match), timeout=3.0)
            
            if match_result.data and len(match_result.data) > 0:
                cache_key = match_result.data[0]['cache_key']
                similarity = match_result.data[0]['similarity']
                
                # 3. ดึงคำตอบจาก RAM ของ Redis (ตัดการเชื่อมต่อใน 2 วินาที)
                cached_answer = await asyncio.wait_for(self.redis.get(cache_key), timeout=2.0)
                
                if cached_answer:
                    logger.info(f"⚡ [Semantic Cache Hit]: ค้นพบคำถามความหมายคล้ายกัน {similarity*100:.2f}% (ลดต้นทุน API 100%)")
                    return cached_answer.decode('utf-8') if isinstance(cached_answer, bytes) else cached_answer

            return ""
            
        except asyncio.TimeoutError:
            logger.warning("⏳ [Semantic Cache Timeout]: ระบบความจำตอบสนองช้า สลับให้ AI ประมวลผลคำตอบใหม่ทันที")
            return ""
        except Exception as e:
            logger.warning(f"⚠️ [Semantic Cache Fetch Error]: {e}")
            return ""

    async def set_cached_response(self, user_text: str, ai_response: str):
        """💾 บันทึกคำถามและคำตอบใหม่ลงระบบแคช เพื่อใช้รับมือคำถามซ้ำในอนาคต (Non-blocking)"""
        if not self.redis or not self.supabase or len(user_text) < 5:
            return
            
        try:
            # 1. สร้าง Cache Key เฉพาะตัวด้วย SHA-256
            payload_hash = hashlib.sha256(user_text.encode('utf-8')).hexdigest()
            cache_key = f"semantic_ans:{payload_hash}"
            
            # 2. เก็บคำตอบลง Redis (มาตรฐาน Upstash V2 Compatible)
            await asyncio.wait_for(
                self.redis.set(cache_key, ai_response, ex=self.cache_ttl_seconds),
                timeout=2.0
            )
            
            # 3. แปลงคำถามเป็น Vector และเก็บ Index ลง Supabase (Background Fire-and-Forget)
            async def _save_index():
                try:
                    vector_data = await asyncio.to_thread(get_text_embedding, user_text)
                    if vector_data:
                        def insert_vector():
                            self.supabase.table("semantic_cache_index").insert({
                                "query_text": user_text[:500], # จำกัดความยาวป้องกัน Database บวม
                                "cache_key": cache_key,
                                "embedding": vector_data
                            }).execute()
                        await asyncio.to_thread(insert_vector)
                except Exception as inner_e:
                    logger.warning(f"⚠️ [Vector Index Save Error]: {inner_e}")
                    
            asyncio.create_task(_save_index())
            logger.info("💾 [Semantic Cache Set]: บันทึกองค์ความรู้ใหม่ลงระบบความจำอัจฉริยะเรียบร้อยแล้ว")
            
        except asyncio.TimeoutError:
            pass # บันทึกแคชช้าเกินไป ให้ข้ามไปเงียบๆ เพื่อไม่ให้กวนการตอบกลับลูกค้า
        except Exception as e:
            logger.warning(f"⚠️ [Semantic Cache Save Error]: {e}")