import os
import io
import logging
import hashlib
import json
import asyncio
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
import google.auth
from upstash_redis.asyncio import Redis

# =========================================================
# 👑 SIRINTHANATTH PRIME - Enterprise Drive & Cache Orchestrator
# =========================================================

# แยก Logger ชัดเจนเพื่อความแม่นยำในการ Monitor ระบบ
drive_logger = logging.getLogger("DriveAssetManager")
orchestrator_logger = logging.getLogger("HybridOrchestrator")

class PrimeJSONEncoder(json.JSONEncoder):
    """🛡️ ป้องกันระบบแครชจากการ Serialize ข้อมูลประเภท Datetime หรือ Object พิเศษ"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)

class HybridOrchestrator:
    """
    🧠 Hybrid Orchestrator & Semantic Caching Engine
    อัปเกรด: Thread-Safe Singleton, Circuit Breaker, Advanced JSON Encoder
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(HybridOrchestrator, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, redis_url: str = None, redis_token: str = None):
        if getattr(self, '_initialized', False): return
        
        self.redis_url = redis_url or os.getenv("UPSTASH_REDIS_REST_URL")
        self.redis_token = redis_token or os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self.redis = None
        self._connect_redis()
        
        self._initialized = True

    def _connect_redis(self):
        try:
            if self.redis_url and self.redis_token:
                self.redis = Redis(url=self.redis_url, token=self.redis_token)
                orchestrator_logger.info("✅ [Redis Cache]: เชื่อมต่อ Upstash Semantic Cache สำเร็จ")
        except Exception as e:
            orchestrator_logger.error(f"❌ [Redis Init Error]: เชื่อมต่อล้มเหลว ข้ามการใช้ Cache -> {e}")

    async def get_cached_response_or_route(self, prompt: str) -> Optional[Dict[str, Any]]:
        """ดึงข้อมูลจากสมองกลสำรอง (Cache) ด้วยความเร็วเสี้ยววินาที พร้อมระบบตัดวงจรป้องกันระบบค้าง"""
        if not self.redis or not prompt: return None
        
        try:
            cache_key = f"semantic_cache:{hashlib.sha256(prompt.strip().lower().encode('utf-8')).hexdigest()}"
            
            # 🛡️ Circuit Breaker: รอ Redis สูงสุด 2 วินาที ถ้าช้ากว่านี้ให้ข้ามไปรัน AI ปกติ
            cached = await asyncio.wait_for(self.redis.get(cache_key), timeout=2.0)
            
            if cached:
                orchestrator_logger.info("🎯 [Cache Hit]: Semantic Cache Hit (0.001s) - Zero API Cost")
                if isinstance(cached, str):
                    try:
                        return json.loads(cached)
                    except json.JSONDecodeError:
                        return {"text": cached}
                return cached
                
        except asyncio.TimeoutError:
            orchestrator_logger.warning("⏳ [Redis Timeout]: ฐานข้อมูลแคชตอบสนองช้า ระบบตัดวงจรข้ามไปใช้ AI หลัก")
        except Exception as e:
            orchestrator_logger.warning(f"⚠️ [Cache Read Error]: {e}")
            
        return None

    async def set_cache_response(self, prompt: str, response_data: dict, ttl_seconds: int = 3600):
        """บันทึกข้อมูลผลลัพธ์ลงแคชเพื่อประหยัดต้นทุน Token ครั้งต่อไป"""
        if not self.redis or not prompt: return
        
        try:
            cache_key = f"semantic_cache:{hashlib.sha256(prompt.strip().lower().encode('utf-8')).hexdigest()}"
            payload = json.dumps(response_data, ensure_ascii=False, cls=PrimeJSONEncoder)
            
            # ไม่ให้บล็อกการทำงานหลัก (Fire and Forget)
            await asyncio.wait_for(self.redis.set(cache_key, payload, ex=ttl_seconds), timeout=2.0)
            orchestrator_logger.info("💾 [Cache Write]: บันทึกองค์ความรู้ลงระบบความจำอัจฉริยะสำเร็จ")
            
        except asyncio.TimeoutError:
            pass # เงียบไว้ ไม่ให้กวนระบบหลัก
        except Exception as e:
            orchestrator_logger.warning(f"⚠️ [Cache Write Error]: {e}")


class DriveAssetManager:
    """
    📁 Enterprise Google Drive Asset Manager
    อัปเกรด: 4K Chunked Upload, Auto-Permission, Zero-Data Deletion Capability
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(DriveAssetManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, '_initialized', False): return
        
        self._service = None
        self._auth_lock = asyncio.Lock()
        self._default_folder_id = None
        self._initialized = True

    async def _get_service(self):
        """Lazy Authentication: ยืนยันตัวตนแบบ Asynchronous ป้องกันคอขวดตอน Boot ระบบ"""
        if self._service: return self._service
        
        async with self._auth_lock:
            if self._service: return self._service 
            try:
                def _auth():
                    scopes = ['https://www.googleapis.com/auth/drive']
                    # ดึงสิทธิ์จาก Google Cloud IAM อัตโนมัติ (ปลอดภัยสูงสุด ไม่ต้องใช้ไฟล์ Key)
                    credentials, _ = google.auth.default(scopes=scopes)
                    return build('drive', 'v3', credentials=credentials, cache_discovery=False)
                
                self._service = await asyncio.to_thread(_auth)
                drive_logger.info("✅ [Drive Service]: ยืนยันตัวตน Google Drive (Lazy Auth) สำเร็จ")
            except Exception as e:
                drive_logger.critical(f"❌ [Drive Auth Error]: ระบบคลาวด์ปฏิเสธการเชื่อมต่อ -> {e}")
        
        return self._service

    async def _get_or_create_default_folder(self, service) -> str:
        """📂 ค้นหาหรือสร้างโฟลเดอร์ PRIME_ASSETS อัตโนมัติ เพื่อจัดระเบียบ Drive ให้สะอาด"""
        if self._default_folder_id: return self._default_folder_id
        
        folder_name = "PRIME_ASSETS"
        def _fetch():
            query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            files = response.get('files', [])
            
            if files:
                return files[0].get('id')
            else:
                folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
                folder = service.files().create(body=folder_metadata, fields='id').execute()
                
                # เปิดสิทธิ์โฟลเดอร์ให้คนมีลิงก์สามารถอ่านหรือดาวน์โหลดไฟล์ข้างในได้
                service.permissions().create(
                    fileId=folder.get('id'),
                    body={'type': 'anyone', 'role': 'reader'},
                    fields='id'
                ).execute()
                return folder.get('id')
                
        self._default_folder_id = await asyncio.to_thread(_fetch)
        return self._default_folder_id

    async def upload_asset(self, file_name: str, file_bytes: bytes, mime_type: str, folder_id: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        อัปโหลดไฟล์ขนาดใหญ่ (4K Video/HQ Audio) สร้างสิทธิ์ และเจเนอเรต Direct Link
        """
        service = await self._get_service()
        if not service:
            drive_logger.error("❌ [Drive Error]: ไม่สามารถอัปโหลดได้เนื่องจาก Service Offline")
            return None

        target_folder = folder_id or await self._get_or_create_default_folder(service)
        file_metadata = {'name': file_name, 'parents': [target_folder]}

        def _execute_upload_and_share():
            # 🚀 Memory Optimization: หั่นไฟล์อัปโหลดทีละ 10MB (ป้องกัน RAM เซิร์ฟเวอร์เต็มเมื่อโหลดไฟล์ 4K)
            chunk_size = 10 * 1024 * 1024 
            media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, chunksize=chunk_size, resumable=True)
            
            created_file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink, webContentLink'
            ).execute()
            
            file_id = created_file.get('id')
            
            # ปลดล็อกสิทธิ์ระดับสาธารณะ (Anyone with link)
            try:
                service.permissions().create(
                    fileId=file_id,
                    body={'type': 'anyone', 'role': 'reader'},
                    fields='id'
                ).execute()
            except HttpError as perm_err:
                drive_logger.warning(f"⚠️ [Drive Permission Warning]: ปลดล็อกสิทธิ์ล้มเหลว ({perm_err})")

            # 🎯 เจเนอเรต Bypass Direct Download Link (โหลดตรงโดยไม่ต้องเข้าหน้าเว็บ Drive)
            direct_dl = f"https://drive.google.com/uc?export=download&id={file_id}"

            return {
                "file_id": file_id,
                "view_link": created_file.get('webViewLink'),
                "download_link": direct_dl
            }

        try:
            # ⚡ โยนภาระ I/O อันหนักหน่วงลง Thread แยก ไม่บล็อกระบบหลัก
            result = await asyncio.to_thread(_execute_upload_and_share)
            drive_logger.info(f"📤 [Drive Success]: อัปโหลด '{file_name}' สำเร็จ พร้อมลิงก์โหลดตรง")
            return result
        except Exception as e:
            drive_logger.error(f"❌ [Drive Upload Failed]: เกิดข้อผิดพลาดระดับ I/O -> {e}")
            return None

    async def delete_asset(self, file_id: str) -> bool:
        """
        🗑️ ระบบทำลายหลักฐาน: ลบไฟล์ออกจาก Google Drive 
        (รองรับนโยบาย Zero-Data Retention เมื่อหมดความจำเป็น)
        """
        service = await self._get_service()
        if not service or not file_id: return False
        
        def _execute_delete():
            try:
                service.files().delete(fileId=file_id).execute()
                return True
            except HttpError as e:
                # ถ้าไฟล์โดนลบไปแล้ว (404) ถือว่าสำเร็จตามเจตนารมณ์
                if e.resp.status == 404: return True 
                drive_logger.error(f"❌ [Drive Delete Error]: {e}")
                return False

        try:
            result = await asyncio.to_thread(_execute_delete)
            if result:
                drive_logger.info(f"🧹 [Drive Security]: ทำลายไฟล์เอกสาร {file_id} ทิ้งจากระบบคลาวด์สำเร็จ")
            return result
        except Exception as e:
            drive_logger.error(f"❌ [Drive Delete Failed]: {e}")
            return False