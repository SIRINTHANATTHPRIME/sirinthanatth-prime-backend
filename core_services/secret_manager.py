import os
import logging
import threading
from typing import Optional, Dict
from google.cloud import secretmanager
from google.api_core.exceptions import GoogleAPICallError, RetryError

logger = logging.getLogger("Prime-SecretVault")

class PrimeSecretVault:
    """
    🔐 Enterprise Secret Manager Vault (Zero-Trust & Zero-Latency)
    อัปเกรด: In-Memory Caching, Connection Pooling, Double-Check Locking
    """
    _client: Optional[secretmanager.SecretManagerServiceClient] = None
    _secret_cache: Dict[str, str] = {}
    _lock = threading.Lock()

    @classmethod
    def _get_client(cls) -> secretmanager.SecretManagerServiceClient:
        """🚀 Singleton Architecture: สร้าง Connection ท่อเดียวเพื่อลด Overhead"""
        if cls._client is None:
            with cls._lock:
                if cls._client is None:
                    cls._client = secretmanager.SecretManagerServiceClient()
        return cls._client

    @classmethod
    def get_secret(cls, secret_id: str, version_id: str = "latest", fallback_env: str = "") -> str:
        """
        ดึงกุญแจลับเข้าสู่ RAM หากเคยดึงแล้วจะใช้จาก Cache ทันที (Zero-Latency)
        """
        # 1. ⚡ ตรวจสอบจาก Cache ก่อน (ความเร็วระดับ 0.001ms)
        if secret_id in cls._secret_cache:
            return cls._secret_cache[secret_id]

        # 2. 💻 กรณีรันบน Local เครื่องนักพัฒนา ให้ใช้ .env ทันที
        if os.environ.get("ENVIRONMENT", "").lower() == "local":
            val = os.environ.get(secret_id, fallback_env)
            cls._secret_cache[secret_id] = val
            return val
            
        try:
            # 🛡️ ล็อก Thread ป้องกัน Thundering Herd Problem ตอน Boot ระบบ
            with cls._lock:
                # Double-check locking (เผื่อมี Thread อื่นดึงไปแล้วระหว่างรอคิว)
                if secret_id in cls._secret_cache:
                    return cls._secret_cache[secret_id]

                project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1")
                client = cls._get_client()
                
                # เส้นทางเข้าถึง Vault ดิจิทัลนิรภัยของ Google Cloud
                name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
                response = client.access_secret_version(request={"name": name})
                
                # ถอดรหัส Payload เข้าสู่ RAM และเก็บลง Cache อย่างปลอดภัย
                secret_value = response.payload.data.decode("UTF-8")
                cls._secret_cache[secret_id] = secret_value
                
                logger.info(f"🔓 [Secret Vault]: ปลดล็อกกุญแจ '{secret_id}' เข้าสู่หน่วยความจำสำเร็จ")
                return secret_value
            
        except (GoogleAPICallError, RetryError) as net_err:
            logger.error(f"❌ [Vault Network Error]: การเชื่อมต่อ Google Secret Manager ขัดข้อง ({secret_id}) -> {net_err}")
        except Exception as e:
            logger.error(f"❌ [Vault Security Error]: ปฏิเสธการเข้าถึงกุญแจ '{secret_id}' (ตรวจสอบสิทธิ์ IAM) -> {e}")
            
        # 3. 🔄 Fallback ขั้นสูงสุด: หาก Cloud Secret Manager ล่ม ให้ดึงจาก OS Environment แทน
        fallback_value = os.environ.get(secret_id, fallback_env)
        if fallback_value:
            logger.warning(f"⚠️ [Vault Fallback]: สลับไปใช้กุญแจสำรองของ '{secret_id}' จาก Environment")
            cls._secret_cache[secret_id] = fallback_value
        
        return fallback_value

    @classmethod
    def clear_cache(cls):
        """🧹 เคลียร์หน่วยความจำทิ้งเมื่อจำเป็น (รองรับนโยบาย Zero-Data Retention)"""
        with cls._lock:
            cls._secret_cache.clear()
            logger.info("🧹 [Secret Vault]: ทำลายข้อมูลกุญแจลับทั้งหมดออกจาก RAM เรียบร้อย")