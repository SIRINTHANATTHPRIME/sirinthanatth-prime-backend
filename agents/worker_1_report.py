import os
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

logger = logging.getLogger("Worker1-Report")

class ReportWorker:
    """
    📊 Worker 1: Data & Report Analyst (นักวิเคราะห์ข้อมูลและจัดทำรายงาน)
    อัปเกรด: [Gemini 2.5 Pro] เพื่อการวิเคราะห์เชิงลึก (Deep Analysis) 
    และรองรับไฟล์ Data ทุกรูปแบบ (Crash-Proof)
    """
    def __init__(self):
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model_name = 'gemini-1.5-pro' # ใช้รุ่น Pro สำหรับงานที่ต้องการตรรกะซับซ้อน เช่น การเขียนสูตร Excel

    async def process(self, user_id: str, message: str) -> str:
        """ทำงานเบื้องหลัง (Background Task) สำหรับสร้างโครงร่างเอกสาร"""
        logger.info(f"📊 [Document Engineering]: กำลังวิเคราะห์ข้อมูลและสร้างเอกสารให้ User {user_id}...")
        
        if not self.client:
            return "⚠️ [Worker 1]: ระบบวิเคราะห์ข้อมูลออฟไลน์ (ไม่พบ API Key)"

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # ระบบจัดการไฟล์ข้อมูลแบบชาญฉลาด
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"📊 [Worker 1]: กำลังอัปโหลดไฟล์ข้อมูลเพื่อวิเคราะห์...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith('.xlsx'): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif file_path.lower().endswith('.xls'): mime_type = "application/vnd.ms-excel"
                elif file_path.lower().endswith('.csv'): mime_type = "text/csv"
                if not mime_type: mime_type = "application/octet-stream"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    return f"⚠️ [Worker 1]: โครงสร้างไฟล์นี้ซับซ้อนเกินไปครับ รบกวนคุณลูกค้าหรือท่านประธานแปลงเป็น PDF หรือ CSV เพื่อให้ผมวิเคราะห์ได้อย่างแม่นยำครับ"

                # ⏳ รอจนกว่า AI จะย่อยข้อมูลเสร็จ
                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 1]: เกิดข้อผิดพลาดในการถอดรหัสไฟล์ข้อมูลครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดวิเคราะห์ข้อมูลจากไฟล์นี้ และจัดทำรายงานสรุปตามคำสั่ง: {message}")
            else:
                content_to_send.append(f"จัดทำรายงานและวิเคราะห์ข้อมูลจากข้อความนี้: {message}")

            # ==========================================
            # ประมวลผลขั้นสูงด้วย Gemini 2.5 Pro
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.2 # ใช้อุณหภูมิต่ำ (0.2) เพื่อให้การวิเคราะห์ตัวเลขมีความแม่นยำ ไม่เพ้อเจ้อ
                )
            )
            return response.text if response.text else "✅ วิเคราะห์ข้อมูลเสร็จสิ้น ไม่มีข้อผิดพลาดครับ"

        except Exception as e:
            logger.error(f"❌ [Worker 1 Error]: {e}")
            return f"⚠️ [Worker 1]: ระบบวิเคราะห์ข้อมูลขัดข้องชั่วคราวครับ (Debug: {str(e)[:100]})"

        finally:
            # 🧹 ทำลายไฟล์ทิ้งเพื่อความปลอดภัยของข้อมูล
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except:
                    pass
