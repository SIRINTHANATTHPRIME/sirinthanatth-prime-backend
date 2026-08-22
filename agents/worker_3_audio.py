import os
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

# 🎙️ นำเข้าระบบเสียงระดับโลก ElevenLabs 
try:
    from services.elevenlabs_service import generate_voice_from_text
except ImportError:
    generate_voice_from_text = None

logger = logging.getLogger("Worker3-Audio")

class AudioWorker:
    """
    🎙️ Worker 3: Audio Analyst & Voice Synthesizer (ผู้เชี่ยวชาญด้านเสียง)
    อัปเกรด: [Gemini 2.5 Pro] + [ElevenLabs API]
    ถอดรหัสเสียง, วิเคราะห์อารมณ์, และสร้างเสียงพากย์ตอบกลับได้
    """
    def __init__(self):
        self.api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        
        self.model_name = 'gemini-3.1-pro-preview'
        self.base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
        
        self.system_instruction = """
        คุณคือ 'Worker 3' ผู้เชี่ยวชาญด้าน Audio Intelligence ประจำ SIRINTHANATTH PRIME
        
        หน้าที่ของคุณ:
        1. ถอดรหัสไฟล์เสียง (Transcription) ที่ได้รับอย่างแม่นยำ
        2. วิเคราะห์น้ำเสียงและอารมณ์ (Sentiment Analysis) ของผู้พูด
        3. สรุปใจความสำคัญและเรียบเรียงเนื้อหาให้กระชับ
        4. ใช้ภาษาที่เป็นธรรมชาติ น่าฟัง และเป็นมืออาชีพ เพื่อเตรียมพร้อมให้ระบบแปลงเป็นเสียงพากย์
        """

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        if not self.client:
            return "⚠️ [Worker 3]: ระบบประมวลผลเสียงออฟไลน์ (ไม่พบ API Key)"

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 1. จัดการไฟล์เสียงและการอัปโหลด
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"🎙️ [Worker 3]: กำลังอัปโหลดไฟล์เสียงเพื่อวิเคราะห์ขั้นสูง...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = "audio/mp4" # ค่าเริ่มต้นสำหรับไฟล์เสียง LINE (.m4a)

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    return f"⚠️ [Worker 3]: ระบบไม่รองรับไฟล์เสียงประเภทนี้ครับ กรุณาส่งเป็นไฟล์ .mp3 หรือ .m4a แทนครับ"

                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 3]: เกิดข้อผิดพลาดในการถอดรหัสคลื่นเสียงครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดถอดรหัสและวิเคราะห์ไฟล์เสียงนี้ ตามคำสั่ง: {message}")
            else:
                content_to_send.append(f"โปรดวิเคราะห์ข้อความนี้สำหรับเตรียมพากย์เสียง: {message}")

            # ==========================================
            # 2. ประมวลผลขั้นสูงด้วย Gemini 2.5 Pro
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.6 # ให้อารมณ์ภาษาเป็นธรรมชาติ
                )
            )
            
            reply_text = response.text if response.text else "วิเคราะห์เสียงเสร็จสิ้นครับ"
            
            # ==========================================
            # 3. 🎙️ ผสมผสานขุมพลัง ElevenLabs API (สร้างเสียงทันที)
            # ==========================================
            if generate_voice_from_text and ("พากย์" in message or "สร้างเสียง" in message):
                logger.info("🎙️ [ElevenLabs]: ได้รับคำสั่งให้สร้างเสียงพากย์ กำลังเชื่อมต่อ API...")
                filename, duration_ms = await asyncio.to_thread(generate_voice_from_text, reply_text)
                if filename:
                    audio_link = f"{self.base_url}/static/audio/{filename}"
                    reply_text += f"\n\n🎧 ระบบได้สร้างเสียงพากย์ด้วย ElevenLabs เรียบร้อยแล้ว:\n{audio_link}"
            
            return reply_text

        except Exception as e:
            logger.error(f"❌ [Worker 3 Error]: {e}")
            return f"⚠️ [Worker 3]: ระบบเสียงขัดข้องชั่วคราวครับ (Debug: {str(e)[:100]})"

        finally:
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except:
                    pass
