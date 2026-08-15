import os
import requests
import uuid

# 1. ดึง API Key จากไฟล์ .env (ถ้าไม่มีจะข้ามการทำเสียงอัตโนมัติ)
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

# 2. ตั้งค่า Voice ID เริ่มต้น (สามารถเปลี่ยนเป็น ID ของธนัตถ์ หรือ สิรินทร์ ได้ในอนาคต)
# ปัจจุบันใช้เสียงพื้นฐาน (Rachel) เป็นค่าเริ่มต้น
DEFAULT_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM") 

def generate_voice_from_text(text: str):
    """
    ฟังก์ชันแปลงข้อความเป็นเสียงพูดภาษาไทย (Text-to-Speech)
    คืนค่าเป็น: (ชื่อไฟล์เสียง, ความยาวเสียงเป็นมิลลิวินาที)
    """
    if not ELEVENLABS_API_KEY:
        print("⚠️ [System]: ไม่พบ ELEVENLABS_API_KEY สลับกลับไปใช้ข้อความตัวอักษรอย่างเดียว")
        return None, 0
        
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{DEFAULT_VOICE_ID}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_API_KEY
        }
        
        # ใช้โมเดล eleven_multilingual_v2 เพื่อให้ออกเสียงภาษาไทยได้ชัดเจนและเป็นธรรมชาติ
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2", 
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        print(f"🎙️ [ElevenLabs]: กำลังสังเคราะห์เสียงสำหรับข้อความความยาว {len(text)} ตัวอักษร...")
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            # สร้างชื่อไฟล์แบบสุ่มป้องกันการทับซ้อน (UUID)
            filename = f"reply_{uuid.uuid4().hex}.mp3"
            
            # ตรวจสอบและสร้างโฟลเดอร์ static/audio หากยังไม่มี
            save_dir = os.path.join(os.getcwd(), "static", "audio")
            os.makedirs(save_dir, exist_ok=True)
            
            save_path = os.path.join(save_dir, filename)
            
            # บันทึกไฟล์เสียงลงโฟลเดอร์
            with open(save_path, "wb") as f:
                f.write(response.content)
            
            # ประเมินความยาวเสียงคร่าวๆ สำหรับส่งให้ LINE (ภาษาไทย 1 ตัวอักษร ~ 80ms)
            estimated_duration_ms = len(text) * 80 
            if estimated_duration_ms < 1000:
                estimated_duration_ms = 1000 # ขั้นต่ำ 1 วินาที
                
            print(f"✅ [ElevenLabs]: สร้างไฟล์เสียงสำเร็จ -> {filename}")
            return filename, estimated_duration_ms
        else:
            print(f"❌ [ElevenLabs Error]: API ปฏิเสธการเชื่อมต่อ -> {response.text}")
            return None, 0
            
    except Exception as e:
        print(f"❌ [Voice Gen Error]: เกิดข้อผิดพลาดระหว่างสร้างเสียง -> {e}")
        return None, 0