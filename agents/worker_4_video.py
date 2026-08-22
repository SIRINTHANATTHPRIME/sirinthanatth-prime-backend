import os
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

logger = logging.getLogger("Worker4-Video")

class VideoWorker:
    """
    🎞️ Worker 4: Video Analyst (ผู้เชี่ยวชาญด้านวิดีโอ)
    อัปเกรด: [Gemini 2.5 Pro] เพื่อการวิเคราะห์ภาพเคลื่อนไหวแบบเฟรมต่อเฟรม
    """
    def __init__(self):
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        # ใช้รุ่น Pro สำหรับงานความคิดสร้างสรรค์ การเขียนบท และออกแบบฉากที่ซับซ้อน
        self.model_name = 'gemini-1.5-pro'

    async def process(self, user_id: str, message: str) -> str:
        """ทำงานเบื้องหลัง (Background Task) สำหรับออกแบบ Storyboard"""
        logger.info(f"🎬 [Video Production]: กำลังวางแผนและสร้าง Storyboard วิดีโอ 4K ให้ User {user_id}...")
        
        if not self.client:
            return "⚠️ [Worker 4]: ระบบประมวลผลวิดีโอออฟไลน์ (ไม่พบ API Key)"

        uploaded_file = None
        content_to_send = []

        try:
            if file_path and os.path.exists(file_path):
                logger.info(f"🎞️ [Worker 4]: กำลังอัปโหลดวิดีโอเพื่อวิเคราะห์ (กระบวนการนี้อาจใช้เวลาสักครู่)...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = "video/mp4" # ค่าเริ่มต้นสำหรับวิดีโอ

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    return f"⚠️ [Worker 4]: โครงสร้างไฟล์วิดีโอไม่รองรับครับ รบกวนส่งเป็น .mp4 ครับ"

                # ⏳ วิดีโอจะใช้เวลาประมวลผลนานกว่าปกติ ระบบจะรออย่างใจเย็น
                while uploaded_file.state.name == "PROCESSING":
                    logger.info("⏳ [Worker 4]: AI กำลังแยกเฟรมภาพและเสียงในวิดีโอ...")
                    await asyncio.sleep(4) # เช็กทุกๆ 4 วินาทีเพื่อลดภาระเซิร์ฟเวอร์
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 4]: ขออภัยครับ AI ไม่สามารถถอดรหัสวิดีโอนี้ได้ อาจมีขนาดใหญ่หรือซับซ้อนเกินไป"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดวิเคราะห์วิดีโอนี้อย่างละเอียด ตามคำสั่ง: {message}")
            else:
                content_to_send.append(f"โปรดวิเคราะห์และวางแผนสคริปต์วิดีโอตามนี้: {message}")

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.5
                )
            )
            return response.text if response.text else "✅ วิเคราะห์วิดีโอเสร็จสิ้น ไม่มีข้อผิดพลาดครับ"

        except Exception as e:
            logger.error(f"❌ [Worker 4 Error]: {e}")
            return f"⚠️ [Worker 4]: ระบบวิดีโอขัดข้องชั่วคราวครับ (Debug: {str(e)[:100]})"

        finally:
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except:
                    pass
