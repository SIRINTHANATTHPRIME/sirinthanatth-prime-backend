import os
import uuid
import logging
import httpx
import asyncio
from google import genai
from google.genai import types

logger = logging.getLogger("ElevenLabs-VoiceEngine-Premium")

# =========================================================
# 🌐 1. นำเข้าศูนย์บัญชาการ AI ส่วนกลาง (Vertex AI)
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-2.5-flash"
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

# 2. ดึง API Key จากระบบรักษาความปลอดภัยระดับองค์กร
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
DEFAULT_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") 

async def optimize_tts_script(text: str) -> str:
    """🧠 ใช้ Vertex AI (Gemini) เป็น Voice Director ปรับแต่งสคริปต์ให้พากย์เป็นธรรมชาติที่สุด"""
    client = PrimeAIConfig.get_client()
    model_name = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-2.5-flash")
    
    if not client:
        return text
        
    system_instruction = """
    คุณคือ 'Voice Director' ผู้เชี่ยวชาญด้านการจัดสคริปต์สำหรับ AI Text-to-Speech (TTS) ภาษาไทย
    หน้าที่ของคุณคือการนำข้อความต้นฉบับมาปรับปรุง เพื่อให้ AI อ่านออกเสียงได้เป็นธรรมชาติเหมือนมนุษย์ที่สุด:
    1. แปลงคำย่อเป็นคำเต็ม (เช่น บ. -> บริษัท, ชม. -> ชั่วโมง)
    2. คำภาษาอังกฤษที่อ่านยาก ให้เขียนเป็นคำอ่านภาษาไทย (เช่น startup -> สตาร์ทอัป)
    3. เติมเครื่องหมาย ... หรือ เว้นวรรค เพื่อสร้างจังหวะหายใจ (Pacing) ที่เหมาะสม
    4. ห้ามเปลี่ยนความหมายของประโยคเด็ดขาด ให้ปรับแค่รูปแบบการอ่านเท่านั้น
    ตอบกลับเฉพาะสคริปต์ที่ปรับปรุงแล้วเท่านั้น ห้ามมีคำอธิบายเพิ่มเติม
    """
    
    try:
        async def fetch_optimized_script():
            return await asyncio.to_thread(
                client.models.generate_content,
                model=model_name,
                contents=f"ปรับสคริปต์นี้สำหรับการพากย์เสียง:\n{text}",
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2 # ใช้อุณหภูมิต่ำเพื่อไม่ให้ AI ดัดแปลงเนื้อหาหลัก
                )
            )
        
        # ⏳ Guardrail: หาก AI นานเกิน 5 วินาที ให้ข้ามไปใช้สคริปต์เดิมทันที
        response = await asyncio.wait_for(fetch_optimized_script(), timeout=5.0)
        return response.text.strip() if response.text else text
    except Exception as e:
        logger.warning(f"⚠️ [Voice Director Warning]: ปรับสคริปต์ไม่สำเร็จ ใช้ข้อความต้นฉบับ ({e})")
        return text

async def generate_voice_from_text(text: str) -> tuple[str | None, int]:
    """
    🎙️ ฟังก์ชันแปลงข้อความเป็นเสียงพูดภาษาไทยแบบ Asynchronous ระดับ World-Class
    ผสาน AI Director + ElevenLabs เพื่อสร้างน้ำเสียงที่นุ่มนวล เป็นธรรมชาติ และน่าเชื่อถือ
    """
    if not ELEVENLABS_API_KEY:
        logger.warning("⚠️ [System]: ไม่พบ ELEVENLABS_API_KEY ปิดโหมดสังเคราะห์เสียง")
        return None, 0
        
    try:
        # 1. 🧠 ผสานพลัง Vertex AI ช่วยเกลาสคริปต์ให้พากย์เนียนขึ้น (Voice Director)
        optimized_text = await optimize_tts_script(text)
        
        # 2. 🛡️ Legal & Cost Shield: ตัดข้อความส่วนเกินป้องกัน API Reject และคุมต้นทุน
        clean_text = optimized_text.strip()[:5000]
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{DEFAULT_VOICE_ID}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        # 3. 🚀 Psychological Acoustic Tuning: ตั้งค่าเสียงเชิงจิตวิทยา
        data = {
            "text": clean_text,
            "model_id": "eleven_multilingual_v2_5", # อัปเกรดเป็นโมเดลล่าสุด รวดเร็วและสมจริงที่สุด
            "voice_settings": {
                "stability": 0.45,         # ลดความแข็งทื่อของ AI ให้มีโทนเสียงขึ้นลงแบบธรรมชาติ
                "similarity_boost": 0.80,  # ดึงเอกลักษณ์เสียงต้นฉบับให้ชัดเจน หนักแน่น น่าเชื่อถือ
                "style": 0.15,             # เพิ่มจังหวะการพูด (Intonation) ให้น่าฟัง ไม่น่าเบื่อ
                "use_speaker_boost": True  # บูสต์ความคมชัดของเสียงระดับสตูดิโอ 4K
            }
        }
        
        # 4. ⚡ สถาปัตยกรรมเครือข่าย Enterprise (Non-blocking I/O)
        async with httpx.AsyncClient(timeout=45.0) as client:
            logger.info(f"🎙️ [ElevenLabs Premium]: สังเคราะห์เสียงจิตวิทยาความยาว {len(clean_text)} ตัวอักษร...")
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status() # โยน Error ทันทีถ้าสถานะไม่ใช่ 200
            
            # 🛡️ สร้างชื่อไฟล์แบบสุ่ม (Thread-Safe) ป้องกันไฟล์ทับซ้อนเมื่อใช้งานพร้อมกัน
            filename = f"reply_prime_{uuid.uuid4().hex}.mp3"
            save_dir = os.path.join(os.getcwd(), "static", "audio")
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, filename)
            
            # 💾 บันทึกไฟล์ลง Disk แบบ Async (ไม่ฉุดประสิทธิภาพเซิร์ฟเวอร์หลัก)
            def save_file():
                with open(save_path, "wb") as f:
                    f.write(response.content)
            await asyncio.to_thread(save_file)
            
            # ⏱️ คำนวณความยาวเสียง (ภาษาไทย 1 ตัวอักษรใช้เวลาเฉลี่ย ~ 75-80ms)
            estimated_duration_ms = max(len(clean_text) * 80, 1000)
            
            logger.info(f"✅ [ElevenLabs Premium]: สร้างไฟล์เสียงระดับ World-Class สำเร็จ -> {filename}")
            return filename, estimated_duration_ms
            
    except httpx.HTTPStatusError as http_err:
        logger.error(f"❌ [ElevenLabs API Error]: {http_err.response.text}")
    except Exception as e:
        logger.error(f"❌ [Voice Gen Error]: ขัดข้องระหว่างสังเคราะห์เสียง -> {e}")
        
    return None, 0