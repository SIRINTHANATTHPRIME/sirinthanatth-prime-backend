import os
import uuid
import logging
import httpx
import asyncio

logger = logging.getLogger("ElevenLabs-VoiceEngine")

# 1. ดึง API Key
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
DEFAULT_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") 

async def generate_voice_from_text(text: str) -> tuple[str | None, int]:
    """
    ฟังก์ชันแปลงข้อความเป็นเสียงพูดภาษาไทยแบบ Asynchronous ระดับ Enterprise
    คืนค่าเป็น: (ชื่อไฟล์เสียง, ความยาวเสียงเป็นมิลลิวินาที)
    """
    if not ELEVENLABS_API_KEY:
        logger.warning("⚠️ [System]: ไม่พบ ELEVENLABS_API_KEY ปิดโหมดสังเคราะห์เสียง")
        return None, 0
        
    try:
        # 🛡️ ตัดข้อความส่วนเกินป้องกัน API Reject (สูงสุด 5000 ตัวอักษร)
        clean_text = text.strip()[:5000]
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{DEFAULT_VOICE_ID}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        data = {
            "text": clean_text,
            "model_id": "eleven_multilingual_v2", 
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        # 🚀 ใช้ httpx สำหรับ Asynchronous Non-blocking I/O
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.info(f"🎙️ [ElevenLabs]: สังเคราะห์เสียงความยาว {len(clean_text)} ตัวอักษร...")
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status() # โยน Error ทันทีถ้าสถานะไม่ใช่ 200
            
            # สร้างชื่อไฟล์แบบสุ่มป้องกันการทับซ้อน
            filename = f"reply_{uuid.uuid4().hex}.mp3"
            save_dir = os.path.join(os.getcwd(), "static", "audio")
            os.makedirs(save_dir, exist_ok=True)
            save_path = os.path.join(save_dir, filename)
            
            # 💾 บันทึกไฟล์ลง Disk แบบ Async
            def save_file():
                with open(save_path, "wb") as f:
                    f.write(response.content)
            await asyncio.to_thread(save_file)
            
            # คำนวณความยาวเสียง (ภาษาไทย 1 ตัวอักษร ~ 80ms)
            estimated_duration_ms = max(len(clean_text) * 80, 1000)
            
            logger.info(f"✅ [ElevenLabs]: สร้างไฟล์เสียงสำเร็จ -> {filename}")
            return filename, estimated_duration_ms
            
    except httpx.HTTPStatusError as http_err:
        logger.error(f"❌ [ElevenLabs API Error]: {http_err.response.text}")
    except Exception as e:
        logger.error(f"❌ [Voice Gen Error]: {e}")
        
    return None, 0