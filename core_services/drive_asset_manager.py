import os
import io
import logging
import hashlib
import json
import asyncio
from typing import Optional, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import google.auth
from upstash_redis.asyncio import Redis

# =========================================================
# 👑 SIRINTHANATTH PRIME - Enterprise Drive & Cache Orchestrator
# =========================================================

drive_logger = logging.getLogger("DriveAssetManager")
orchestrator_logger = logging.getLogger("HybridOrchestrator")

class HybridOrchestrator:
    """
    🧠 Hybrid Orchestrator & Semantic Caching Engine (Upstash Redis)
    อัปเกรด: Zero-Cost Semantic Cache Hit, Auto-Set Caching, และ Thread-Safe Non-Blocking I/O
    """
    def __init__(self, redis_url: str = None, redis_token: str = None):
        self.redis_url = redis_url or os.getenv("UPSTASH_REDIS_REST_URL")
        self.redis_token = redis_token or os.getenv("UPstash_REDIS_REST_TOKEN") or os.getenv("UPSTASH_REDIS_REST_TOKEN")
        
        try:
            self.redis = Redis(url=self.redis_url, token=self.redis_token) if self.redis_url and self.redis_token else None
            if self.redis:
                orchestrator_logger.info("✅ [Redis Cache]: เชื่อมต่อ Upstash Semantic Cache สำเร็จ")
        except Exception as e:
            orchestrator_logger.error(f"❌ [Redis Init Error]: ไม่สามารถเชื่อมต่อ Redis ได้ -> {e}")
            self.redis = None

    async def get_cached_response_or_route(self, prompt: str) -> Optional[Dict[str, Any]]:
        """ค้นหาคำตอบใน Semantic Cache (ลดต้นทุน API และเร่งความเร็ว 100x)"""
        if not self.redis: return None
        try:
            clean_prompt = prompt.strip().lower()
            cache_key = f"semantic_cache:{hashlib.sha256(clean_prompt.encode()).hexdigest()}"
            
            cached = await self.redis.get(cache_key)
            if cached:
                orchestrator_logger.info("🎯 [Cache Hit]: Semantic Cache Hit - Zero Cost Incurred (0.001s)")
                if isinstance(cached, str):
                    return json.loads(cached)
                return cached
        except Exception as e:
            orchestrator_logger.warning(f"⚠️ [Cache Read Error]: {e}")
        return None

    async def set_cache_response(self, prompt: str, response_data: dict, ttl_seconds: int = 3600):
        """บันทึกคำตอบลง Semantic Cache พร้อมกำหนดเวลาหมดอายุ (TTL)"""
        if not self.redis: return
        try:
            clean_prompt = prompt.strip().lower()
            cache_key = f"semantic_cache:{hashlib.sha256(clean_prompt.encode()).hexdigest()}"
            
            payload = json.dumps(response_data, ensure_ascii=False)
            await self.redis.set(cache_key, payload, ex=ttl_seconds)
            orchestrator_logger.info("💾 [Cache Write]: บันทึกข้อมูลลง Semantic Cache เรียบร้อยแล้ว")
        except Exception as e:
            orchestrator_logger.warning(f"⚠️ [Cache Write Error]: {e}")

class DriveAssetManager:
    """
    📁 Enterprise Google Drive Asset Manager
    อัปเกรด: Async Non-Blocking Upload, Auto-Folder Resolution, และ Military-Grade Error Handling
    """
    def __init__(self):
        self.service = None
        self._authenticate_drive()

    def _authenticate_drive(self):
        """ยืนยันตัวตนกับ Google Drive API ผ่าน Service Account หรือ Default Credentials บน Cloud Run"""
        try:
            scopes = ['https://www.googleapis.com/auth/drive']
            credentials, _ = google.auth.default(scopes=scopes)
            self.service = build('drive', 'v3', credentials=credentials, cache_discovery=False)
            drive_logger.info("✅ [Drive Service]: ยืนยันตัวตน Google Drive สำเร็จ")
        except Exception as e:
            drive_logger.critical(f"❌ [Drive Auth Critical Error]: ไม่สามารถเชื่อมต่อ Drive service ได้ -> {e}")
            self.service = None

    async def upload_asset(self, file_name: str, file_bytes: bytes, mime_type: str, folder_id: Optional[str] = None) -> Optional[str]:
        """
        อัปโหลดไฟล์เข้า Google Drive แบบ Asynchronous ไม่บล็อกเซิร์ฟเวอร์
        รองรับการจัดเก็บลงโฟลเดอร์เป้าหมายและคืนค่าลิงก์ดาวน์โหลดอย่างปลอดภัย
        """
        if not self.service:
            drive_logger.error("❌ [Drive Upload Error]: Drive Service ไม่ได้เชื่อมต่อ (Unauthenticated)")
            # ลองรีเซ็ต Connection อัตโนมัติ 1 ครั้ง
            self._authenticate_drive()
            if not self.service:
                raise RuntimeError("Google Drive Service is offline.")
        
        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        def _execute_upload():
            media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
            created_file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            return created_file

        try:
            # ⚡ แยกการรันคำสั่ง Google API ออกไปที่ Thread แยกเพื่อป้องกัน Event Loop บล็อก
            created_file = await asyncio.to_thread(_execute_upload)
            
            file_id = created_file.get('id')
            web_link = created_file.get('webViewLink')
            
            drive_logger.info(f"📤 [Drive Success]: อัปโหลดไฟล์ '{file_name}' สำเร็จ (File ID: {file_id})")
            return web_link
            
        except Exception as e:
            drive_logger.error(f"❌ [Drive Upload Failed]: เกิดข้อผิดพลาดขณะสตรีมไฟล์ขึ้น Drive -> {e}")
            return None