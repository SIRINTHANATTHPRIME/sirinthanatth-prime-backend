import os
import logging
import asyncio
import json
import threading
from datetime import datetime, timezone
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from supabase import create_client, Client

logger = logging.getLogger("PDPA-Logger")

# =========================================================
# 🛡️ Pydantic Schema บังคับผลลัพธ์ AI (Zero-Hallucination)
# =========================================================
class PrivacyRiskSchema(BaseModel):
    is_risky: bool = Field(description="มีข้อมูลลับทางธุรกิจ หรือข้อมูลส่วนบุคคลที่อ่อนไหว (Sensitive PII) รั่วไหลหรือไม่")
    reason: str = Field(description="เหตุผลสั้นๆ ไม่เกิน 1 บรรทัด")

# =========================================================
# 🌐 1. ศูนย์บัญชาการ AI (Vertex AI Integration)
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-3.7-flash" # 🚀 อัปเกรดเป็นรุ่นความเร็วแสงล่าสุด
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

class PDPA_Logger:
    """
    🛡️ ระบบจัดการ Audit Log และประเมินความเสี่ยง PDPA (Zero-Data Retention)
    อัปเกรด: Thread-Safe Singleton, Pydantic Schema Enforcement, Circuit Breaker
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """🚀 Singleton Architecture: ควบคุม Connection ฐานข้อมูลท่อเดียว ประหยัด RAM ขั้นสุด"""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(PDPA_Logger, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # ป้องกันการ Init ซ้ำซ้อน
        if self._initialized: return
        
        self.client = PrimeAIConfig.get_client()
        self.fast_model = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-3.7-flash")
        
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        self._initialized = True

    def _mask_filename(self, file_name: str) -> str:
        """เซ็นเซอร์ชื่อไฟล์อัจฉริยะ (รักษานามสกุลไฟล์ไว้) ป้องกัน PII รั่วไหล"""
        if not file_name: return "UNKNOWN_FILE"
        
        name, ext = os.path.splitext(file_name)
        if len(name) <= 3:
            masked_name = "***"
        else:
            # แสดงแค่ 3 ตัวแรก และ 1 ตัวสุดท้ายของชื่อ
            masked_name = f"{name[:3]}***{name[-1]}"
            
        return f"{masked_name}{ext}"

    async def log_zero_data_deletion(self, user_id: str, file_name: str, status: str = "SUCCESS"):
        """บันทึกหลักฐานทางกฎหมายว่าระบบได้ทำลายไฟล์ทิ้งแล้ว 100% (แบบซ่อนเร้นข้อมูลส่วนบุคคล)"""
        timestamp = datetime.now(timezone.utc).isoformat()
        safe_file_name = self._mask_filename(file_name)
        
        log_msg = f"[{timestamp}] Zero-Data Policy Executed: {safe_file_name} for User: {user_id} | Status: {status}"
        logger.info(f"🧹 {log_msg}")
        
        if not self.db:
            return
            
        try:
            def _insert_log():
                self.db.table("audit_logs").insert({
                    "line_user_id": user_id,
                    "action_type": "DATA_WIPE",
                    "details": f"File permanently deleted: {safe_file_name}",
                    "status": status,
                    "created_at": timestamp
                }).execute()
                
            # โยนเข้า Thread หลังบ้านเพื่อไม่ให้รบกวนความเร็วแชท LINE
            await asyncio.to_thread(_insert_log)
        except Exception as e:
            logger.error(f"❌ [Audit Log DB Error]: ไม่สามารถบันทึก Log การลบข้อมูลได้ -> {e}")

    async def analyze_privacy_risk(self, text: str) -> dict:
        """
        ใช้ Vertex AI สแกนหาความเสี่ยงข้อมูลส่วนบุคคลที่อ่อนไหว (Deep PII Scan)
        อัปเกรด: บังคับ Schema ด้วย Pydantic ป้องกัน AI มโนฟอร์แมต
        """
        if not self.client or not text:
            return {"is_risky": False, "reason": "No AI client or text provided"}
            
        try:
            system_instruction = """
            คุณคือ 'PDPA Compliance Auditor' ระดับองค์กรของ SIRINTHANATTH PRIME
            จงสแกนข้อความนี้อย่างละเอียด และประเมินความเสี่ยงอย่างเที่ยงตรง
            """
            
            async def _scan_text():
                return await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.fast_model,
                    contents=f"สแกนข้อความนี้:\n{text}",
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.0, 
                        response_mime_type="application/json",
                        response_schema=PrivacyRiskSchema # 🛡️ บังคับให้ตอบตรงเป้า 100%
                    )
                )
            
            # ⏱️ Circuit Breaker: ป้องกันคอขวด หาก AI ตอบช้าเกิน 5 วินาที
            response = await asyncio.wait_for(_scan_text(), timeout=5.0)
            
            if response.text:
                return json.loads(response.text)
            else:
                return {"is_risky": True, "reason": "System Alert: Empty AI Response"}
                
        except asyncio.TimeoutError:
            logger.warning("⚠️ [PDPA AI Scan Timeout]: AI ตอบกลับล่าช้า ข้ามการประเมินเพื่อรักษาความเร็วระบบ")
            return {"is_risky": True, "reason": "System Alert: Scan Timeout"}
        except json.JSONDecodeError:
            logger.error("❌ [PDPA AI Scan Error]: AI ไม่ได้คืนค่าเป็น JSON ที่ถูกต้อง")
            return {"is_risky": True, "reason": "System Alert: Data format unreadable."}
        except Exception as e:
            logger.error(f"⚠️ [PDPA AI Scan Error]: {e}", exc_info=True)
            return {"is_risky": False, "reason": "System offline or bypassed"}

    async def log_consent_agreement(self, user_id: str):
        """บันทึกหลักฐานทางกฎหมายเมื่อลูกค้ากดยอมรับเงื่อนไขการให้บริการ (TOS/PDPA)"""
        if not self.db: return
        
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            def _insert_consent():
                self.db.table("audit_logs").insert({
                    "line_user_id": user_id,
                    "action_type": "CONSENT_AGREED",
                    "details": "User digitally signed and agreed to TOS & PDPA policies via LIFF",
                    "status": "SUCCESS",
                    "created_at": timestamp
                }).execute()
            await asyncio.to_thread(_insert_consent)
            logger.info(f"✅ [Consent Verified]: บันทึกการยอมรับข้อตกลงของลูกค้า {user_id} สำเร็จ")
        except Exception as e:
            logger.error(f"❌ [Consent Log Error]: {e}")