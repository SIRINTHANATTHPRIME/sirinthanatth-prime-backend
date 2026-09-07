import os
import io
import logging
import hashlib
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import google.auth
from upstash_redis.asyncio import Redis

# 1. แยกตัวแปร Logger ให้ชัดเจน เพื่อความง่ายในการตรวจสอบข้อผิดพลาด (Monitoring)
drive_logger = logging.getLogger("DriveAssetManager")
orchestrator_logger = logging.getLogger("HybridOrchestrator")

class HybridOrchestrator:
    def __init__(self, redis_url: str, redis_token: str):
        self.redis = Redis(url=redis_url, token=redis_token) if redis_url and redis_token else None

    async def get_cached_response_or_route(self, prompt: str):
        if not self.redis:
            return None
        cache_key = f"semantic_cache:{hashlib.md5(prompt.encode()).hexdigest()}"
        cached = await self.redis.get(cache_key)
        if cached:
            orchestrator_logger.info("Semantic Cache Hit - Zero Cost Incurred")
            return json.loads(cached)
        return None

class DriveAssetManager:
    def __init__(self):
        try:
            # ใช้ Default Credentials ของ Google Cloud Run ที่ผูกกับ Service Account ไว้แล้ว
            credentials, _ = google.auth.default(scopes=['https://www.googleapis.com/auth/drive'])
            self.service = build('drive', 'v3', credentials=credentials)
        except Exception as e:
            drive_logger.error(f"Failed to initialize Drive service: {e}")
            self.service = None

    async def upload_asset(self, file_name: str, file_bytes: bytes, mime_type: str, folder_id: str = None) -> str:
        if not self.service:
            raise RuntimeError("Drive Service not authenticated")
        
        file_metadata = {'name': file_name}
        if folder_id:
            file_metadata['parents'] = [folder_id]

        # โหลดไฟล์เข้าหน่วยความจำแบบ BytesIO และสตรีมขึ้น Drive
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
        created_file = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        drive_logger.info(f"Uploaded asset {file_name} to Drive: {created_file.get('id')}")
        return created_file.get('webViewLink')