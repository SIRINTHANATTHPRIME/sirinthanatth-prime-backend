import os
import logging
import asyncio
import json
import re
from datetime import datetime
from google import genai
from google.genai import types
from supabase import create_client, Client

# ตั้งค่า Logger สำหรับระบบ Audit
logger = logging.getLogger("PDPA-Logger")

# =========================================================
# 🌐 1. ศูนย์บัญชาการ AI (Vertex AI Integration)
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-3.7-flash" # ใช้โมเดลความเร็วแสงสำหรับสแกน Log
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            # รองรับระบบ Vertex AI อัตโนมัติบน Google Cloud
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

class PDPA_Logger:
    """
    🛡️ ระบบจัดการ Audit Log และประเมินความเสี่ยง PDPA (Zero-Data Retention)
    อัปเกรด: ใช้ Vertex AI สแกนพฤติกรรมเสี่ยง และบันทึกหลักฐานการลบข้อมูลลง Supabase แบบ Async
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.fast_model = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-3.7-flash")
        
        # เชื่อมต่อ Supabase สำหรับเก็บประวัติ Audit Log แบบเข้ารหัส
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None

    async def log_zero_data_deletion(self, user_id: str, file_name: str, status: str = "SUCCESS"):
        """บันทึกหลักฐานทางกฎหมายว่าระบบได้ทำลายไฟล์ทิ้งแล้ว 100%"""
        timestamp = datetime.utcnow().isoformat()
        log_msg = f"[{timestamp}] Zero-Data Policy Executed: {file_name} for User: {user_id} | Status: {status}"
        logger.info(f"🧹 {log_msg}")
        
        if not self.db:
            return
            
        try:
            def _insert_log():
                self.db.table("audit_logs").insert({
                    "line_user_id": user_id,
                    "action_type": "DATA_WIPE",
                    "details": f"File deleted: {file_name}",
                    "status": status,
                    "created_at": timestamp
                }).execute()
                
            # โยนเข้า Thread หลังบ้านเพื่อไม่ให้รบกวนความเร็วแชท LINE
            await asyncio.to_thread(_insert_log)
        except Exception as e:
            logger.error(f"❌ [Audit Log DB Error]: {e}")

    async def analyze_privacy_risk(self, text: str) -> dict:
        """
        ใช้ Vertex AI สแกนหาความเสี่ยงข้อมูลส่วนบุคคลที่อ่อนไหว (Deep PII Scan)
        คืนค่าเป็น JSON เพื่อให้นำไปประมวลผลต่อได้ทันที
        """
        if not self.client or not text:
            return {"is_risky": False, "reason": "No AI client or text provided"}
            
        try:
            system_instruction = """
            คุณคือ 'PDPA Compliance Auditor' ระดับโลกของ SIRINTHANATTH PRIME
            จงสแกนข้อความนี้และประเมินว่ามีความเสี่ยงที่ "ข้อมูลความลับทางธุรกิจ" หรือ "ข้อมูลส่วนบุคคลที่อ่อนไหว (Sensitive PII)" เช่น ข้อมูลสุขภาพ, รหัสผ่าน, ประวัติอาชญากรรม รั่วไหลหรือไม่
            ตอบกลับเป็น JSON เท่านั้น: {"is_risky": true/false, "reason": "เหตุผลสั้นๆ ไม่เกิน 1 บรรทัด"}
            """
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.fast_model,
                contents=text,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1, # ต้องการความแม่นยำทางกฎหมายสูงสุด
                    response_mime_type="application/json"
                )
            )
            
            # ทำความสะอาดข้อมูล JSON จาก Markdown
            res_text = response.text.strip()
            res_text = re.sub(r'^```json\s*', '', res_text)
            res_text = re.sub(r'\s*```$', '', res_text)
            
            return json.loads(res_text)
            
        except Exception as e:
            logger.error(f"⚠️ [PDPA AI Scan Error]: {e}")
            return {"is_risky": False, "reason": str(e)}

    async def log_consent_agreement(self, user_id: str):
        """บันทึกเมื่อลูกค้ากดยอมรับเงื่อนไขการให้บริการ (TOS/PDPA)"""
        if not self.db: return
        
        try:
            timestamp = datetime.utcnow().isoformat()
            def _insert_consent():
                self.db.table("audit_logs").insert({
                    "line_user_id": user_id,
                    "action_type": "CONSENT_AGREED",
                    "details": "User agreed to TOS & PDPA policies via LIFF",
                    "status": "SUCCESS",
                    "created_at": timestamp
                }).execute()
            await asyncio.to_thread(_insert_consent)
        except Exception as e:
            logger.error(f"❌ [Consent Log Error]: {e}")