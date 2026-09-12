import os
import time
import logging
import threading
from typing import Optional, Dict, Tuple

# 🛡️ Graceful Import: ป้องกันระบบพังหากไลบรารี GCP ขัดข้อง
try:
    from google.cloud import secretmanager
    from google.api_core.exceptions import GoogleAPICallError, RetryError
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False

logger = logging.getLogger("Prime-SecretVault")

class PrimeSecretVault:
    """
    🔐 Enterprise Secret Manager Vault (Zero-Trust & Zero-Latency)
    อัปเกรด: In-Memory TTL Caching, Auto-Environment Detection, Graceful Fallback
    """
    _client: Optional['secretmanager.SecretManagerServiceClient'] = None
    
    # เก็บข้อมูลแบบ Tuple (ค่าความลับ, เวลาที่หมดอายุ) สำหรับระบบ TTL
    _secret_cache: Dict[str, Tuple[str, float]] = {}
    _lock = threading.Lock()
    
    # ⏱️ ตั้งค่า TTL (Time-To-Live) เป็น 3600 วินาที (1 ชั่วโมง)
    # ระบบจะดึงกุญแจใหม่จากคลาวด์อัตโนมัติหากกุญแจเดิมหมดอายุ (รองรับ Secret Rotation)
    CACHE_TTL_SECONDS = 3600

    @classmethod
    def _get_client(cls):
        """🚀 Singleton Architecture: สร้าง Connection ท่อเดียวเพื่อลด Overhead"""
        if not GCP_AVAILABLE:
            return None
        if cls._client is None:
            with cls._lock:
                if cls._client is None:
                    cls._client = secretmanager.SecretManagerServiceClient()
        return cls._client

    @classmethod
    def get_secret(cls, secret_id: str, version_id: str = "latest", fallback_env: str = "") -> str:
        """ดึงกุญแจลับเข้าสู่ RAM พร้อมระบบ Auto-Refresh (TTL) และอ่านจาก Cloud Run Environment ตรงๆ"""
        current_time = time.time()
        
        # 1. ⚡ ตรวจสอบจาก Cache และ TTL (ความเร็วระดับ 0.001ms)
        if secret_id in cls._secret_cache:
            secret_value, expire_time = cls._secret_cache[secret_id]
            if current_time < expire_time:
                return secret_value

        # 2. ⚡ อ่านจาก Environment Variables ทันที! (Cloud Run เมานต์กุญแจมาให้แล้วอย่างปลอดภัย)
        env_val = os.environ.get(secret_id)
        if env_val:
            cls._secret_cache[secret_id] = (env_val, current_time + cls.CACHE_TTL_SECONDS)
            return env_val
            
        # 3. 🔄 หากหาไม่เจอจริงๆ ค่อยใช้ Google Cloud Secret Manager API
        try:
            with cls._lock:
                client = cls._get_client()
                if client:
                    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1")
                    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
                    response = client.access_secret_version(request={"name": name})
                    secret_value = response.payload.data.decode("UTF-8")
                    cls._secret_cache[secret_id] = (secret_value, current_time + cls.CACHE_TTL_SECONDS)
                    return secret_value
        except Exception as e:
            logger.warning(f"⚠️ [Vault API]: ไม่สามารถดึง '{secret_id}' จากคลาวด์ได้ -> {e}")
            
        return fallback_env

    @classmethod
    def _is_cloud_environment(cls) -> bool:
        """☁️ ตรวจสอบอัตโนมัติว่ารันบน Google Cloud Run หรือเครื่อง Local"""
        # K_SERVICE คือ Environment Variable ที่ Cloud Run จะฉีดเข้ามาให้อัตโนมัติ
        return "K_SERVICE" in os.environ or os.environ.get("ENVIRONMENT", "").lower() in ["production", "prod"]

    @classmethod
    def get_secret(cls, secret_id: str, version_id: str = "latest", fallback_env: str = "") -> str:
        """
        ดึงกุญแจลับเข้าสู่ RAM พร้อมระบบ Auto-Refresh (TTL) และ Fallback ขั้นสูงสุด
        """
        current_time = time.time()
        
        # 1. ⚡ ตรวจสอบจาก Cache และ TTL (ความเร็วระดับ 0.001ms)
        if secret_id in cls._secret_cache:
            secret_value, expire_time = cls._secret_cache[secret_id]
            if current_time < expire_time:
                return secret_value
            else:
                logger.info(f"🔄 [Secret Vault]: กุญแจ '{secret_id}' หมดอายุในหน่วยความจำ ระบบกำลังดึงค่าใหม่...")

        # 2. 💻 หากรันบน Local เครื่องนักพัฒนา ให้ใช้ .env ทันที (ไม่ต้องต่อคลาวด์ให้เสียเวลา)
        if not cls._is_cloud_environment():
            val = os.environ.get(secret_id, fallback_env)
            cls._secret_cache[secret_id] = (val, current_time + cls.CACHE_TTL_SECONDS)
            return val
            
        try:
            # 🛡️ ล็อก Thread ป้องกัน Thundering Herd Problem ตอน Boot ระบบ
            with cls._lock:
                # Double-check locking เผื่อมี Thread อื่นดึงข้อมูลมาให้แล้วระหว่างที่รอคิว
                if secret_id in cls._secret_cache and current_time < cls._secret_cache[secret_id][1]:
                    return cls._secret_cache[secret_id][0]

                client = cls._get_client()
                if client:
                    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1")
                    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
                    response = client.access_secret_version(request={"name": name})
                    
                    # ถอดรหัส Payload เข้าสู่ RAM และประทับเวลาหมดอายุ
                    secret_value = response.payload.data.decode("UTF-8")
                    cls._secret_cache[secret_id] = (secret_value, current_time + cls.CACHE_TTL_SECONDS)
                    
                    logger.info(f"🔓 [Secret Vault]: ปลดล็อกกุญแจ '{secret_id}' เข้าสู่หน่วยความจำสำเร็จ")
                    return secret_value
                
        except Exception as e:
            logger.error(f"❌ [Vault Security Error]: ไม่สามารถเชื่อมต่อตู้เซฟคลาวด์สำหรับ '{secret_id}' -> {e}")
            
        # 3. 🔄 Fallback ขั้นสูงสุด: หาก Cloud Secret Manager ล่ม ให้ดึงจาก OS Environment (Cloud Run Env Vars) แทน
        fallback_value = os.environ.get(secret_id, fallback_env)
        if fallback_value:
            logger.warning(f"⚠️ [Vault Fallback]: สลับไปใช้กุญแจสำรองของ '{secret_id}' จาก Environment Variables")
            cls._secret_cache[secret_id] = (fallback_value, current_time + cls.CACHE_TTL_SECONDS)
        
        return fallback_value

    @classmethod
    def clear_cache(cls):
        """🧹 เคลียร์หน่วยความจำทิ้งเมื่อจำเป็น (รองรับนโยบาย Zero-Data Retention)"""
        with cls._lock:
            cls._secret_cache.clear()
            logger.info("🧹 [Secret Vault]: ทำลายข้อมูลกุญแจลับทั้งหมดออกจาก RAM เรียบร้อย")