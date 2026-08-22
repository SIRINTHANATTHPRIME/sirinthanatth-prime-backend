import os
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

logger = logging.getLogger("Worker7-Finance")

class FinanceWorker:
    """
    💰 Worker 7: Financial & Investment Analyst (ผู้เชี่ยวชาญการเงินและการลงทุน)
    อัปเกรด: [Gemini 2.5 Pro] เพื่อวิเคราะห์งบการเงิน ประเมินความคุ้มทุน และโมเดลการลงทุน
    """
    def __init__(self):
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        # 🚀 ใช้รุ่น Pro เนื่องจากงานการเงินและบัญชีต้องการตรรกะ (Reasoning) ที่แม่นยำและซับซ้อนที่สุด
        self.model_name = 'gemini-1.5-pro'

    async def process(self, user_id: str, message: str) -> str:
        """ทำงานเบื้องหลัง (Background Task) สำหรับวิเคราะห์และวางแผนการเงิน"""
        logger.info(f"💰 [Finance & Accounting]: กำลังวิเคราะห์โครงสร้างการเงินและภาษีให้ User {user_id}...")
        
        if not self.client:
            return "⚠️ [Worker 7]: ระบบการเงินออฟไลน์ (ไม่พบ API Key)"

        uploaded_file = None
        content_to_send = []

        try:
            if file_path and os.path.exists(file_path):
                logger.info(f"💰 [Worker 7]: กำลังอัปโหลดเอกสารการเงินเพื่อคำนวณและวิเคราะห์...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith('.xlsx'): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif file_path.lower().endswith('.xls'): mime_type = "application/vnd.ms-excel"
                elif file_path.lower().endswith('.csv'): mime_type = "text/csv"
                if not mime_type: mime_type = "application/octet-stream"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    return f"⚠️ [Worker 7]: ไม่สามารถประมวลผลไฟล์ตารางคำนวณนี้ได้โดยตรง รบกวนแปลงเป็น PDF หรือส่งออกเป็นไฟล์ CSV ครับ"

                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 7]: ตรวจพบความผิดพลาดในการถอดรหัสเอกสารการเงินครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดวิเคราะห์การเงินและประเมินความคุ้มทุนจากข้อมูลนี้: {message}")
            else:
                content_to_send.append(f"โปรดให้คำปรึกษาและคำนวณด้านการเงินตามโจทย์นี้: {message}")

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.1 # ใช้อุณหภูมิต่ำสุดเพื่อให้ตัวเลขและการคำนวณมีความแม่นยำสูงสุด
                )
            )
            return response.text if response.text else "✅ วิเคราะห์การเงินเสร็จสิ้นครับ"

        except Exception as e:
            logger.error(f"❌ [Worker 7 Error]: {e}")
            return f"⚠️ [Worker 7]: ระบบการเงินขัดข้องชั่วคราวครับ (Debug: {str(e)[:100]})"

        finally:
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except:
                    pass
