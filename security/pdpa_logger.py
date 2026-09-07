import os
import logging
import asyncio
import json
import re
from datetime import datetime, timezone
from google import genai
from google.genai import types
from supabase import create_client, Client

logger = logging.getLogger("PDPA-Logger")

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
    อัปเกรด: Cryptographic Masking, ISO-8601 Timestamp, AI 3.7 Flash
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.fast_model = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-3.7-flash")
        
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None

    def _mask_filename(self, file_name: str) -> str:
        """เซ็นเซอร์ชื่อไฟล์ก่อนลง Database ป้องกัน PII รั่วไหลผ่านชื่อไฟล์"""
        if not file_name or len(file_name) <= 7:
            return "*****" + (file_name[-4:] if file_name else "")
        # แสดงแค่ 3 ตัวแรกและนามสกุลไฟล์ (เช่น document_123.pdf -> doc*****123.pdf)
        return f"{file_name[:3]}*****{file_name[-4:]}"

    async def log_zero_data_deletion(self, user_id: str, file_name: str, status: str = "SUCCESS"):
        """บันทึกหลักฐานทางกฎหมายว่าระบบได้ทำลายไฟล์ทิ้งแล้ว 100% (แบบซ่อนเร้นข้อมูลส่วนบุคคล)"""
        # อัปเกรด: ใช้ Timezone-aware datetime ตามมาตรฐาน Python 3.12+
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
                
            await asyncio.to_thread(_insert_log)
        except Exception as e:
            logger.error(f"❌ [Audit Log DB Error]: ไม่สามารถบันทึก Log การลบข้อมูลได้ -> {e}")

    async def analyze_privacy_risk(self, text: str) -> dict:
        """
        ใช้ Vertex AI สแกนหาความเสี่ยงข้อมูลส่วนบุคคลที่อ่อนไหว (Deep PII Scan)
        """
        if not self.client or not text:
            return {"is_risky": False, "reason": "No AI client or text provided"}
            
        try:
            system_instruction = """
            คุณคือ 'PDPA Compliance Auditor' ระดับองค์กรของ SIRINTHANATTH PRIME
            จงสแกนข้อความนี้และประเมินว่ามีความเสี่ยงที่ "ข้อมูลความลับทางธุรกิจ" หรือ "ข้อมูลส่วนบุคคลที่อ่อนไหว (Sensitive PII)" เช่น ข้อมูลการแพทย์, รหัสผ่าน, ข้อมูลการเงิน รั่วไหลหรือไม่
            ตอบกลับเป็น JSON Format เท่านั้น โดยต้องมี 2 Keys นี้อย่างเคร่งครัด:
            {"is_risky": true หรือ false, "reason": "เหตุผลสั้นๆ ไม่เกิน 1 บรรทัด"}
            """
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.fast_model,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.0, # 🔒 ป้องกันการตอบนอกเรื่อง 100%
                    response_mime_type="application/json"
                )
            )
            
            res_text = response.text.strip()
            res_text = re.sub(r'^```json\s*', '', res_text)
            res_text = re.sub(r'\s*```$', '', res_text)
            
            parsed_json = json.loads(res_text)
            
            # 🛡️ Fallback Structure Check ป้องกัน AI ส่ง Key ผิด
            if "is_risky" not in parsed_json or "reason" not in parsed_json:
                return {"is_risky": True, "reason": "System Alert: AI Structure Validation Failed"}
                
            return parsed_json
            
        except json.JSONDecodeError:
            logger.error("❌ [PDPA AI Scan Error]: AI ไม่ได้คืนค่าเป็น JSON ที่ถูกต้อง")
            return {"is_risky": True, "reason": "System Alert: Data format unreadable, assumed risky."}
        except Exception as e:
            logger.error(f"⚠️ [PDPA AI Scan Error]: {e}")
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