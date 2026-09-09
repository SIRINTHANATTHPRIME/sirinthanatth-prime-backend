import os
import time
import logging
import asyncio
import re
import mimetypes
from datetime import datetime
from google import genai
from google.genai import types
from core_services.swarm_dispatcher import swarm_hub

try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.1-pro-preview"
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(vertexai=True, project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), location="asia-southeast3")

try: from supabase import create_client, Client
except ImportError: Client = None

logger = logging.getLogger("Worker9-PrimeAdvisor")

class PrimeAdvisorWorker:
    """
    👑 Worker 9: CTO ตรวจจับช่องโหว่และส่งโค้ดกลับไปให้ Worker 0 (CEO Sec) สร้างปุ่มอนุมัติ
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.1-pro-preview")
        self.base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
        
        supa_url, supa_key = os.getenv("SUPABASE_URL"), (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY"))
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        self.topup_link = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")
        self.prime_upgrade_link = "https://lin.ee/@636pgjnh/SIRINTHANATTH_PRIME"

    async def _check_tier_and_deduct_token(self, user_id: str, tokens_needed: int) -> dict:
        if not self.db: return {"authorized": True, "tier": "PRIME"}
        try:
            def _check_and_deduct():
                user_data = self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
                if not user_data.data: return {"authorized": False, "msg": "⚠️ ไม่พบข้อมูลบัญชี"}
                
                balance = float(user_data.data[0].get("token_balance", 0.0))
                tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
                
                if tier not in ["PRIME", "ENTERPRISE", "VIP_FOUNDER", "VIP", "ADMIN"]:
                    return {"authorized": False, "msg": f"👑 สิทธิ์นี้เฉพาะแพ็กเกจ PRIME ขึ้นไป อัปเกรดได้ที่: {self.prime_upgrade_link}"}
                if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]: return {"authorized": True, "tier": tier}
                if balance >= tokens_needed:
                    self.db.table("prime_clients").update({"token_balance": balance - tokens_needed}).eq("line_user_id", user_id).execute()
                    return {"authorized": True, "tier": tier}
                return {"authorized": False, "msg": f"👑 PRIME CREDITS ของท่านใกล้หมด เติมด่วนที่: {self.topup_link}"}
            return await asyncio.to_thread(_check_and_deduct)
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return {"authorized": True, "tier": "PRIME"}

    async def process_command(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        return await self.process_task(user_id, message, file_path)

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        if not self.client: return "⚠️ ระบบที่ปรึกษาออฟไลน์ (Missing API Key)"

        auth_status = await self._check_tier_and_deduct_token(user_id, 150 if file_path else 20)
        if not auth_status["authorized"]: return auth_status["msg"]
        
        system_instruction = f"""
        คุณคือ 'Executive Prime Advisor' และ 'CTO' อัจฉริยะระดับโลกของ SIRINTHANATTH PRIME
        
        🚨 กฎเหล็กระดับสูงสุด (SYSTEM OVERRIDE TRIGGERS):
        1. หากตรวจพบข้อบกพร่อง, ช่องโหว่, หรือโค้ด Error คุณต้องเขียนโค้ดแก้ไขทันที
        2. ทุกครั้งที่มีการแก้ไขไฟล์ คุณต้องแนบโค้ดในรูปแบบนี้อย่างเคร่งครัด:
           [UPDATE_SYSTEM_FILE: target/path/to/file.py]
           เนื้อหาโค้ดฉบับสมบูรณ์ที่พร้อมใช้งาน...
           [/UPDATE_SYSTEM_FILE]
        3. หากมีการอัปเดตไฟล์ ห้ามลืมเขียนคำว่า [REQUIRE_APPROVAL] ในบรรทัดสุดท้าย เพื่อให้เลขาฯ สร้างปุ่มอนุมัติ
        4. ใช้ Bullet Points อธิบายความเสี่ยงที่พบก่อนเสนอโค้ดแก้ไข
        """

        uploaded_file = None
        content_to_send = []

        try:
            if file_path and os.path.exists(file_path):
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith(('.py', '.html', '.js', '.json', '.txt', '.log')): mime_type = "text/plain"
                if not mime_type: mime_type = "application/octet-stream"

                upload_config = types.UploadFileConfig(mime_type=mime_type)
                uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)

                timeout, start_time = 60, time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout: raise TimeoutError("หมดเวลาการสแกนระบบ")
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)

                content_to_send.append(uploaded_file)
                content_to_send.append(f"วิเคราะห์ความเสี่ยงและเขียนโค้ดแก้ไข [UPDATE_SYSTEM_FILE] จากไฟล์นี้: {message}")
            else:
                content_to_send.append(f"โปรดให้คำปรึกษาและเขียนโค้ดแก้ไขตามนี้: {message}")

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1, 
                    tools=[{"google_search": {}}]
                )
            )
            
            return response.text.strip() if response.text else "👑 วิเคราะห์เสร็จสิ้น ไม่พบช่องโหว่ครับ"

        except TimeoutError:
            return "⚠️ ข้อมูลมีความซับซ้อนเกินไป รบกวนส่งเฉพาะฟังก์ชันที่เกิดปัญหาครับ"
        except Exception as e:
            logger.error(f"❌ [Worker 9 Error]: {e}")
            return "⚠️ ระบบประมวลผลเชิงลึกขัดข้องชั่วคราวครับ"
        finally:
            if uploaded_file:
                try: await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except Exception: pass