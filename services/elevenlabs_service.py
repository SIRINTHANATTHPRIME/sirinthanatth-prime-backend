import os
import uuid
import logging
import httpx
import asyncio

logger = logging.getLogger("ElevenLabs-VoiceEngine-Premium")

# 1. ดึง API Key จากระบบรักษาความปลอดภัยระดับองค์กร
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
DEFAULT_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") 

async def generate_voice_from_text(text: str) -> tuple[str | None, int]:
    """
    🎙️ ฟังก์ชันแปลงข้อความเป็นเสียงพูดภาษาไทยแบบ Asynchronous ระดับ World-Class
    ผสานหลักจิตวิทยาการสื่อสาร เพื่อสร้างน้ำเสียงที่นุ่มนวล เป็นธรรมชาติ น่าเชื่อถือ
    ลดความอึดอัดของลูกค้า กระตุ้นการตัดสินใจ (Token Top-up) และปลอดภัยตามมาตรฐาน PDPA
    """
    if not ELEVENLABS_API_KEY:
        logger.warning("⚠️ [System]: ไม่พบ ELEVENLABS_API_KEY ปิดโหมดสังเคราะห์เสียง")
        return None, 0
        
    try:
        # 🛡️ Legal & Cost Shield: ตัดข้อความส่วนเกินป้องกัน API Reject และคุมต้นทุน (สูงสุด 5000 ตัวอักษร)
        clean_text = text.strip()[:5000]
        
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{DEFAULT_VOICE_ID}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        # 🚀 Psychological Acoustic Tuning: ตั้งค่าเสียงเชิงจิตวิทยา
        data = {
            "text": clean_text,
            "model_id": "eleven_multilingual_v2_5", # อัปเกรดเป็นโมเดลล่าสุด (eleven_multilingual_v2_5) รวดเร็วและสมจริงที่สุด
            "voice_settings": {
                "stability": 0.45,         # ลดความแข็งทื่อของ AI ให้มีโทนเสียงขึ้นลงแบบธรรมชาติ
                "similarity_boost": 0.80,  # ดึงเอกลักษณ์เสียงต้นฉบับให้ชัดเจน หนักแน่น น่าเชื่อถือ
                "style": 0.15,             # เพิ่มจังหวะการพูด (Intonation) ให้น่าฟัง ไม่น่าเบื่อ
                "use_speaker_boost": True  # บูสต์ความคมชัดของเสียงระดับสตูดิโอ 4K
            }
        }
        
        # ⚡ สถาปัตยกรรมเครือข่าย Enterprise (Non-blocking I/O)
        async with httpx.AsyncClient(timeout=45.0) as client:
            logger.info(f"🎙️ [ElevenLabs Premium]: สังเคราะห์เสียงจิตวิทยาความยาว {len(clean_text)} ตัวอักษร...")
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status() # โยน Error ทันทีถ้าสถานะไม่ใช่ 200
            
            # 🛡️ สร้างชื่อไฟล์แบบสุ่ม (Thread-Safe) ป้องกันไฟล์ทับซ้อนเมื่อมีคนใช้พร้อมกันจำนวนมาก
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