import asyncio
import os
import requests
import uuid
import logging
from gtts import gTTS
from google import genai
from google.genai import types

# ตั้งค่า Logger
logger = logging.getLogger("Worker3-AudioStudio")

class AudioProductionWorker:
    """
    🎙️ Worker 3: ระบบผลิตเสียงพากย์คุณภาพสูง (High-Fidelity Audio Engine)
    อัปเกรด: ElevenLabs Human-like Voice + Gemini Script Polishing + Zero-Downtime Fallback
    """
    
    def __init__(self):
        # 1. โหลดคีย์ AI สำหรับช่วยเกลาบทพูด (ถ้าจำเป็น)
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model_name = 'gemini-1.5-flash'
        
        # 2. โหลดคีย์ ElevenLabs สำหรับเสียงพากย์ระดับมนุษย์
        self.elevenlabs_key = os.getenv("ELEVENLABS_API_KEY", "")
        self.voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") # ค่าเริ่มต้นเสียงพรีเมียม
        
        # 3. เตรียมโฟลเดอร์จัดเก็บ
        self.output_dir = os.path.join(os.getcwd(), "static", "audio")
        os.makedirs(self.output_dir, exist_ok=True)

    async def process(self, user_id: str, message: str) -> str:
        """ทำงานเบื้องหลัง (Background Task) สำหรับสร้างเสียงพากย์"""
        logger.info(f"🎙️ [Audio Production]: กำลังสังเคราะห์เสียงพากย์พรีเมียมให้ User {user_id}...")
        
        # ==========================================
        # STEP 1: ให้ Gemini เกลาบทพูดให้ดูเป็นธรรมชาติ (AI Script Polisher)
        # ==========================================
        script_text = message
        if self.client:
            try:
                prompt = f"โปรดปรับแก้ข้อความนี้ให้เหมาะกับการเป็นบทพากย์เสียงโฆษณาหรือเสียงประกาศภาษาไทยที่ฟังดูเป็นธรรมชาติ ไหลลื่น และเป็นมืออาชีพ (ไม่ต้องใส่เครื่องหมายกำกับอารมณ์หรืออิโมจิ เอาแค่ข้อความที่จะพูดเท่านั้น): '{message}'"
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.4)
                )
                if response.text:
                    script_text = response.text.strip()
                    logger.info("✨ [Audio Production]: เกลาบทพากย์เสียงสำเร็จ")
            except Exception as e:
                logger.warning(f"⚠️ [Script Polish Error]: ข้ามการเกลาบทพูด ({e})")

        # สร้างชื่อไฟล์สุ่ม (UUID) ป้องกันลูกค้าสั่งทำคลิปพร้อมกันแล้วไฟล์ทับกัน
        filename = f"audio_premium_{user_id}_{uuid.uuid4().hex[:8]}.mp3"
        filepath = os.path.join(self.output_dir, filename)

        # ==========================================
        # STEP 2: ระบบสังเคราะห์เสียงมนุษย์ระดับโลก (ElevenLabs)
        # ==========================================
        if self.elevenlabs_key:
            try:
                logger.info("🎙️ [ElevenLabs Engine]: กำลังเจเนอเรตเสียง...")
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": self.elevenlabs_key
                }
                data = {
                    "text": script_text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
                }
                
                # โยนงานเน็ตเวิร์กไปรันหลังบ้าน ไม่ให้เซิร์ฟเวอร์หลักกระตุก
                response = await asyncio.to_thread(requests.post, url, json=data, headers=headers, timeout=30)
                response.raise_for_status()
                
                def save_elevenlabs_audio(path, content):
                    with open(path, "wb") as f:
                        f.write(content)
                
                await asyncio.to_thread(save_elevenlabs_audio, filepath, response.content)
                logger.info(f"✅ [Audio Production]: สังเคราะห์เสียง ElevenLabs สำเร็จ ({filename})")
                
                return f"🎙️ [Audio Production]: สังเคราะห์เสียงพากย์ระดับพรีเมียมเสร็จสมบูรณ์แล้วครับ (บันทึกในชื่อ {filename})"
            
            except Exception as e:
                logger.error(f"❌ [ElevenLabs Error]: {e} -> ระบบกำลังสลับไปใช้เสียงสำรองอัตโนมัติ")

        # ==========================================
        # STEP 3: ระบบสำรองฉุกเฉิน (Graceful Fallback - gTTS)
        # ==========================================
        # กรณีคีย์ ElevenLabs หมด หรือเน็ตเวิร์กฝั่งนั้นพัง ระบบของคุณก็ยังทำเสียงได้ ไม่ล่ม 100%
        try:
            logger.info("🎙️ [gTTS Fallback]: กำลังใช้งานเครื่องยนต์เสียงสำรอง...")
            
            def generate_gtts(text, path):
                tts = gTTS(text=text, lang='th', slow=False)
                tts.save(path)
                
            await asyncio.to_thread(generate_gtts, script_text, filepath)
            logger.info(f"✅ [Audio Production]: สังเคราะห์เสียงสำรองสำเร็จ ({filename})")
            
            return f"🎙️ [Audio Production]: สังเคราะห์เสียงพากย์มาตรฐานเสร็จสมบูรณ์แล้วครับ (บันทึกในชื่อ {filename})"
            
        except Exception as e:
            logger.error(f"❌ [Worker 3 TTS Critical Error]: {e}")
            return "⚠️ [Audio Production Error]: ขออภัยครับ ระบบสังเคราะห์เสียงขัดข้องชั่วคราว ไม่สามารถผลิตเสียงพากย์ได้ในขณะนี้"