import os
import hashlib
import logging
import asyncio
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
    🧠 ระบบ Semantic Caching อัจฉริยะ 
    ผสมผสาน Supabase (Vector Search) และ Upstash Redis (RAM Retrieval)
    """
    def __init__(self):
        # 1. เชื่อมต่อ Redis (RAM)
        redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
        redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self.redis = Redis(url=redis_url, token=redis_token) if redis_url and redis_token else None

        # 2. เชื่อมต่อ Supabase (Vector Index)
        supa_url = os.environ.get("SUPABASE_URL")
        supa_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
        self.supabase: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None

        self.similarity_threshold = 0.90 # ความหมายต้องเหมือนกัน 90% ขึ้นไป
        self.cache_ttl_seconds = 86400   # อายุของ Cache (24 ชั่วโมง)

    async def get_cached_response(self, user_text: str) -> str:
        """🔍 ตรวจสอบว่าคำถามนี้เคยมีคนถามและ AI เคยตอบไปแล้วหรือไม่ (ความเหมือน > 90%)"""
        if not self.redis or not self.supabase or len(user_text) < 5:
            return ""
            
        try:
            # 1. แปลงคำถามใหม่เป็น Vector
            vector_data = await asyncio.to_thread(get_text_embedding, user_text)
            if not vector_data: return ""

            # 2. ค้นหาใน Supabase ว่ามีประโยคความหมายคล้ายกันเกิน 90% หรือไม่
            def fetch_match():
                return self.supabase.rpc('match_semantic_cache', {
                    'query_embedding': vector_data, 
                    'match_threshold': self.similarity_threshold
                }).execute()
                
            match_result = await asyncio.to_thread(fetch_match)
            
            if match_result.data and len(match_result.data) > 0:
                cache_key = match_result.data[0]['cache_key']
                similarity = match_result.data[0]['similarity']
                
                # 3. ดึงคำตอบจาก RAM ของ Redis ทันที (0.01 วินาที)
                cached_answer = await self.redis.get(cache_key)
                
                if cached_answer:
                    logger.info(f"⚡ [Semantic Cache Hit]: ค้นพบคำถามความหมายคล้ายกัน {similarity*100:.2f}% (ไม่ต้องเรียก API)")
                    return cached_answer.decode('utf-8') if isinstance(cached_answer, bytes) else cached_answer

            return ""
            
        except Exception as e:
            logger.warning(f"⚠️ [Semantic Cache Fetch Error]: {e}")
            return ""

    async def set_cached_response(self, user_text: str, ai_response: str):
        """💾 บันทึกคำถามและคำตอบใหม่ลงระบบแคช เพื่อใช้รับมือคำถามซ้ำในอนาคต"""
        if not self.redis or not self.supabase or len(user_text) < 5:
            return
            
        try:
            # 1. สร้าง Cache Key เฉพาะตัว
            payload_hash = hashlib.sha256(user_text.encode('utf-8')).hexdigest()
            cache_key = f"semantic_ans:{payload_hash}"
            
            # 2. เก็บคำตอบลง Redis (ดึงไวระดับ RAM)
            await self.redis.setex(cache_key, self.cache_ttl_seconds, ai_response)
            
            # 3. แปลงคำถามเป็น Vector และเก็บ Index ลง Supabase (ทำแบบ Async ไม่ขวางระบบหลัก)
            async def _save_index():
                vector_data = get_text_embedding(user_text)
                if vector_data:
                    self.supabase.table("semantic_cache_index").insert({
                        "query_text": user_text[:500],
                        "cache_key": cache_key,
                        "embedding": vector_data
                    }).execute()
                    
            asyncio.create_task(_save_index())
            logger.info("💾 [Semantic Cache Set]: บันทึกองค์ความรู้ใหม่ลงระบบแคชเรียบร้อยแล้ว")
            
        except Exception as e:
            logger.warning(f"⚠️ [Semantic Cache Save Error]: {e}")