import os
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

logger = logging.getLogger("Worker2-RiskQA")

class RiskQAWorker:
    """
    🛡️ Worker 2: Risk Assessment & QA (ผู้ตรวจสอบคุณภาพและประเมินความเสี่ยง)
    อัปเกรด: [Gemini 2.5 Pro] เพื่อการสแกนหาช่องโหว่ระดับองค์กร
    """
    def __init__(self):
        self.api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        
        self.model_name = 'gemini-3.1-pro-preview'
        
        self.system_instruction = """
        คุณคือ 'Worker 2' ผู้เชี่ยวชาญด้าน Risk Management และ Quality Assurance
        
        หน้าที่ของคุณ:
        1. ตรวจสอบเนื้อหา แผนงาน สัญญา หรือข้อมูลที่ได้รับ เพื่อค้นหา 'ความเสี่ยง' หรือ 'ช่องโหว่' (Vulnerabilities)
        2. ประเมินผลกระทบที่อาจเกิดขึ้นกับองค์กร และให้คะแนนความเสี่ยง (สูง, กลาง, ต่ำ)
        3. เสนอแนวทางป้องกัน (Mitigation Plan) อย่างเป็นรูปธรรม
        4. ใช้ภาษาที่รัดกุม เป็นทางการ และตรงไปตรงมา
        """

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        if not self.client:
            return "⚠️ [Worker 2]: ระบบประเมินความเสี่ยงออฟไลน์ (ไม่พบ API Key)"

        uploaded_file = None
        content_to_send = []

        try:
            if file_path and os.path.exists(file_path):
                logger.info(f"🛡️ [Worker 2]: กำลังสแกนไฟล์เพื่อตรวจสอบความเสี่ยง...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith('.xlsx'): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif file_path.lower().endswith('.xls'): mime_type = "application/vnd.ms-excel"
                elif file_path.lower().endswith('.csv'): mime_type = "text/csv"
                if not mime_type: mime_type = "application/octet-stream"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    return f"⚠️ [Worker 2]: ไฟล์มีความซับซ้อนเกินไปสำหรับการสแกนความเสี่ยงอัตโนมัติ รบกวนแปลงเป็น PDF เพื่อความปลอดภัยครับ"

                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 2]: ตรวจพบความขัดข้องในการสแกนไฟล์ ไม่สามารถประเมินได้ครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดตรวจสอบความเสี่ยงและหาช่องโหว่จากเอกสารนี้ ตามเงื่อนไข: {message}")
            else:
                content_to_send.append(f"โปรดตรวจสอบความเสี่ยงจากข้อมูลนี้: {message}")

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.3 # อุณหภูมิต่ำเพื่อให้การประเมินรัดกุมที่สุด
                )
            )
            return response.text if response.text else "✅ สแกนเสร็จสิ้น ไม่พบความเสี่ยงที่น่ากังวลครับ"

        except Exception as e:
            logger.error(f"❌ [Worker 2 Error]: {e}")
            return f"⚠️ [Worker 2]: ระบบตรวจสอบความเสี่ยงขัดข้องชั่วคราวครับ (Debug: {str(e)[:100]})"

        finally:
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except:
                    pass
