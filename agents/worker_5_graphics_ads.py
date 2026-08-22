import os
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

logger = logging.getLogger("Worker5-GraphicsAds")

class GraphicsAdsWorker:
    """
    🎨 Worker 5: Graphics, Packaging & Ads Specialist (ผู้เชี่ยวชาญด้านกราฟิกและโฆษณา)
    อัปเกรด: [Gemini 2.5 Pro] เพื่อวิเคราะห์ภาพลักษณ์แบรนด์ โครงสร้างการออกแบบ และจิตวิทยาโฆษณา
    """
    def __init__(self):
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        # 🚀 ใช้รุ่น Pro สำหรับงาน Creative & Strategy ที่ต้องคิดวิเคราะห์และใช้ความคิดสร้างสรรค์ขั้นสุด
        self.model_name = 'gemini-1.5-pro'

    async def process(self, user_id: str, message: str) -> str:
        """ทำงานเบื้องหลัง (Background Task) สำหรับออกแบบแคมเปญและสื่อ 4K"""
        logger.info(f"🎨 [Graphics & Ads]: กำลังออกแบบแคมเปญโฆษณาระดับโลกให้ User {user_id}...")
        
        if not self.client:
            return "⚠️ [Worker 5]: ระบบกราฟิกและโฆษณาออฟไลน์ (ไม่พบ API Key)"

        uploaded_file = None
        content_to_send = []

        try:
            if file_path and os.path.exists(file_path):
                logger.info(f"🎨 [Worker 5]: กำลังอัปโหลดภาพเพื่อวิเคราะห์องค์ประกอบงานออกแบบ...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type: mime_type = "image/jpeg"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    return f"⚠️ [Worker 5]: ระบบไม่สามารถประมวลผลไฟล์รูปภาพนี้ได้ครับ รบกวนส่งเป็นไฟล์ .jpg หรือ .png แทนครับ"

                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 5]: เกิดข้อผิดพลาดในการวิเคราะห์พิกเซลของภาพครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดวิเคราะห์องค์ประกอบภาพ/งานออกแบบนี้ และให้ข้อเสนอแนะตามคำสั่ง: {message}")
            else:
                content_to_send.append(f"โปรดร่างไอเดียงานกราฟิก แพ็กเกจจิ้ง หรือสคริปต์โฆษณาตามความต้องการนี้: {message}")

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.7 # ใช้อุณหภูมิปานกลางเพื่อให้เกิดความคิดสร้างสรรค์
                )
            )
            return response.text if response.text else "✅ วิเคราะห์งานออกแบบเสร็จสิ้นครับ"

        except Exception as e:
            logger.error(f"❌ [Worker 5 Error]: {e}")
            return f"⚠️ [Worker 5]: ระบบงานกราฟิกขัดข้องชั่วคราวครับ (Debug: {str(e)[:100]})"

        finally:
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except:
                    pass
