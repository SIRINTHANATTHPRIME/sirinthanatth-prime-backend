import os
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

logger = logging.getLogger("Worker6-Strategy")

class StrategyWorker:
    """
    ♟️ Worker 6: Global Strategy Analyst (นักวิเคราะห์กลยุทธ์ระดับโลก)
    อัปเกรด: [Gemini 2.5 Pro] เพื่อวิเคราะห์โมเดลธุรกิจ อสังหาริมทรัพย์ และยุทธศาสตร์องค์กร
    """
    def __init__(self):
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        # 🚀 ใช้รุ่น Pro สำหรับการวิเคราะห์ตรรกะการตลาดเชิงลึกและการเขียนสคริปต์ขั้นสูง
        self.model_name = 'gemini-1.5-pro'

    async def process(self, user_id: str, message: str) -> str:
        """ทำงานเบื้องหลัง (Background Task) สำหรับวางแผนกลยุทธ์การตลาดและหาโอกาส Upsell"""
        logger.info(f"📈 [Marketing Strategy]: กำลังวิเคราะห์กลยุทธ์ระดับโลกและหาจังหวะ Upsell ให้ User {user_id}...")
        
        if not self.client:
            return "⚠️ [Worker 6]: ระบบวิเคราะห์กลยุทธ์ออฟไลน์ (ไม่พบ API Key)"

        uploaded_file = None
        content_to_send = []

        try:
            if file_path and os.path.exists(file_path):
                logger.info(f"♟️ [Worker 6]: กำลังอัปโหลดเอกสารแผนงานเพื่อวิเคราะห์เชิงกลยุทธ์...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith('.xlsx'): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif file_path.lower().endswith('.xls'): mime_type = "application/vnd.ms-excel"
                elif file_path.lower().endswith('.csv'): mime_type = "text/csv"
                if not mime_type: mime_type = "application/octet-stream"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    return f"⚠️ [Worker 6]: เอกสารแผนงานมีความซับซ้อนเกินไป รบกวนแปลงเป็นรูปแบบ PDF ก่อนส่งเข้าสู่ระบบประเมินกลยุทธ์ครับ"

                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 6]: ตรวจพบข้อผิดพลาดในการวิเคราะห์เอกสารยุทธศาสตร์ครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดวิเคราะห์ยุทธศาสตร์และให้คำปรึกษาเชิงลึกจากข้อมูลในเอกสารนี้: {message}")
            else:
                content_to_send.append(f"โปรดวิเคราะห์และวางกลยุทธ์ระดับโลกสำหรับสถานการณ์นี้: {message}")

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.3 # ใช้อุณหภูมิต่ำเพื่อเน้นตรรกะ เหตุผล และความน่าเชื่อถือ
                )
            )
            return response.text if response.text else "✅ วิเคราะห์แผนกลยุทธ์เสร็จสิ้นครับ"

        except Exception as e:
            logger.error(f"❌ [Worker 6 Error]: {e}")
            return f"⚠️ [Worker 6]: ระบบวิเคราะห์กลยุทธ์ขัดข้องชั่วคราวครับ (Debug: {str(e)[:100]})"

        finally:
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except:
                    pass
