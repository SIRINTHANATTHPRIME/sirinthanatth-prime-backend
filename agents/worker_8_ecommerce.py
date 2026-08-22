import os
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

logger = logging.getLogger("Worker8-Ecommerce")

class EcommerceWorker:
    """
    🛒 Worker 8: E-Commerce & Legal Compliance Specialist (ผู้เชี่ยวชาญ E-Commerce และกฎหมายธุรกิจ)
    อัปเกรด: [Gemini 2.5 Pro] เพื่อบริหารจัดการระบบการค้าออนไลน์และกฎระเบียบข้อบังคับ
    """
    def __init__(self):
        self.api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        
        self.model_name = 'gemini-2.5-pro'
        
        self.system_instruction = """
        คุณคือ 'Worker 8' ผู้เชี่ยวชาญด้าน E-Commerce, ระบบแพลตฟอร์มดิจิทัล และกฎระเบียบข้อบังคับทางธุรกิจ (Legal Compliance)
        
        หน้าที่ของคุณ:
        1. ให้คำปรึกษา ออกแบบระบบ และวางโครงสร้างการทำธุรกิจออนไลน์ (E-Commerce & Affiliate Systems)
        2. ตรวจสอบข้อกฎหมาย สัญญาซื้อขาย ข้อกำหนดการให้บริการ (Terms of Service) และนโยบายคุ้มครองข้อมูลส่วนบุคคล (PDPA)
        3. ให้คำแนะนำเกี่ยวกับระเบียบข้อบังคับทางราชการ หรือกฎหมายที่เกี่ยวข้องกับประกันภัยและอสังหาริมทรัพย์
        4. ใช้ภาษาที่ชัดเจน เป็นทางการ และมีความแม่นยำทางกฎหมาย
        """

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        if not self.client:
            return "⚠️ [Worker 8]: ระบบ E-Commerce และกฎหมายออฟไลน์ (ไม่พบ API Key)"

        uploaded_file = None
        content_to_send = []

        try:
            if file_path and os.path.exists(file_path):
                logger.info(f"🛒 [Worker 8]: กำลังอัปโหลดเอกสารสัญญาหรือข้อตกลงเพื่อตรวจสอบ...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type: mime_type = "application/pdf"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    return f"⚠️ [Worker 8]: ระบบไม่สามารถอ่านไฟล์เอกสารนี้ได้ รบกวนส่งเป็นไฟล์ PDF ครับ"

                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 8]: ตรวจพบความผิดพลาดในการประมวลผลเอกสารทางกฎหมายครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดตรวจสอบสัญญาหรือข้อตกลงในเอกสารนี้ พร้อมให้ความเห็นทางกฎหมาย: {message}")
            else:
                content_to_send.append(f"โปรดให้คำปรึกษาด้าน E-Commerce หรือข้อกฎหมายตามโจทย์นี้: {message}")

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.3
                )
            )
            return response.text if response.text else "✅ ตรวจสอบข้อกฎหมายและระบบเสร็จสิ้นครับ"

        except Exception as e:
            logger.error(f"❌ [Worker 8 Error]: {e}")
            return f"⚠️ [Worker 8]: ระบบ E-Commerce ขัดข้องชั่วคราวครับ (Debug: {str(e)[:100]})"

        finally:
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except:
                    pass
