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
    🧠 Hybrid Orchestrator & Semantic Caching Engine
    อัปเกรด: Fault-Tolerance, JSON Safety, & Connection Resiliency
    """
    def __init__(self, redis_url: str = None, redis_token: str = None):
        self.redis_url = redis_url or os.getenv("UPSTASH_REDIS_REST_URL")
        self.redis_token = redis_token or os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self.redis = None
        self._connect_redis()

    def _connect_redis(self):
        try:
            if self.redis_url and self.redis_token:
                self.redis = Redis(url=self.redis_url, token=self.redis_token)
                orchestrator_logger.info("✅ [Redis Cache]: เชื่อมต่อ Upstash Semantic Cache สำเร็จ")
        except Exception as e:
            orchestrator_logger.error(f"❌ [Redis Init Error]: เชื่อมต่อล้มเหลว ระบบจะข้ามการใช้ Cache อัตโนมัติ -> {e}")

    async def get_cached_response_or_route(self, prompt: str) -> Optional[Dict[str, Any]]:
        if not self.redis: return None
        try:
            cache_key = f"semantic_cache:{hashlib.sha256(prompt.strip().lower().encode()).hexdigest()}"
            cached = await self.redis.get(cache_key)
            
            if cached:
                orchestrator_logger.info("🎯 [Cache Hit]: Semantic Cache Hit (0.001s) - Zero API Cost")
                if isinstance(cached, str):
                    try:
                        return json.loads(cached)
                    except json.JSONDecodeError:
                        return {"text": cached} # Fallback ป้องกันระบบล่มหากข้อมูลไม่ใช่ JSON
                return cached
        except Exception as e:
            orchestrator_logger.warning(f"⚠️ [Cache Read Error]: {e}")
        return None

    async def set_cache_response(self, prompt: str, response_data: dict, ttl_seconds: int = 3600):
        if not self.redis: return
        try:
            cache_key = f"semantic_cache:{hashlib.sha256(prompt.strip().lower().encode()).hexdigest()}"
            payload = json.dumps(response_data, ensure_ascii=False)
            await self.redis.set(cache_key, payload, ex=ttl_seconds)
            orchestrator_logger.info("💾 [Cache Write]: บันทึกองค์ความรู้ลงระบบความจำสำเร็จ")
        except Exception as e:
            orchestrator_logger.warning(f"⚠️ [Cache Write Error]: {e}")

class DriveAssetManager:
    """
    📁 Enterprise Google Drive Asset Manager
    อัปเกรด: Auto-Permission (Anyone with link), Lazy Auth, & Direct Download
    """
    def __init__(self):
        self._service = None
        self._auth_lock = asyncio.Lock()

    async def _get_service(self):
        """Lazy Authentication: ยืนยันตัวตนแบบ Asynchronous ป้องกันการบล็อกเซิร์ฟเวอร์ตอนสตาร์ทระบบ"""
        if self._service: return self._service
        
        async with self._auth_lock:
            if self._service: return self._service # Double-checked locking
            try:
                def _auth():
                    scopes = ['https://www.googleapis.com/auth/drive']
                    credentials, _ = google.auth.default(scopes=scopes)
                    return build('drive', 'v3', credentials=credentials, cache_discovery=False)
                
                self._service = await asyncio.to_thread(_auth)
                drive_logger.info("✅ [Drive Service]: ยืนยันตัวตน Google Drive (Lazy Auth) สำเร็จ")
            except Exception as e:
                drive_logger.critical(f"❌ [Drive Auth Error]: ระบบคลาวด์ปฏิเสธการเชื่อมต่อ -> {e}")
        
        return self._service

    async def upload_asset(self, file_name: str, file_bytes: bytes, mime_type: str, folder_id: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        อัปโหลดไฟล์และตั้งค่าสิทธิ์ให้เข้าถึงได้ผ่านลิงก์ทันที 100%
        Return: Dict ประกอบด้วย view_link (ดูผ่านเว็บ) และ download_link (โหลดตรง)
        """
        service = await self._get_service()
        if not service:
            drive_logger.error("❌ [Drive Error]: ไม่สามารถอัปโหลดได้เนื่องจาก Service Offline")
            return None

        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        def _execute_upload_and_share():
            # 1. อัปโหลดไฟล์
            media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
            created_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            
            file_id = created_file.get('id')
            
            # 2. ปลดล็อกสิทธิ์ (Auto-Permission): สำคัญมาก! หากไม่ทำ ลูกค้าจะติด Access Denied
            service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'},
                fields='id'
            ).execute()
            
            return created_file

        try:
            # ⚡ รันคำสั่ง API ทั้งหมดใน Thread แยกเพื่อไม่ให้ Event Loop หลักสะดุด
            result = await asyncio.to_thread(_execute_upload_and_share)
            
            drive_logger.info(f"📤 [Drive Success]: อัปโหลดและปลดล็อกสิทธิ์ '{file_name}' สำเร็จ")
            return {
                "view_link": result.get('webViewLink'),
                "download_link": result.get('webContentLink')
            }
            
        except Exception as e:
            drive_logger.error(f"❌ [Drive Upload Failed]: เกิดข้อผิดพลาดระดับ I/O -> {e}")
            return None