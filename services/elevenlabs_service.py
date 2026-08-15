import os
import requests
import uuid
import time

# ใช้ไลบรารี moviepy ที่เรามีอยู่แล้วในการคำนวณความยาวไฟล์เสียง (LINE บังคับว่าต้องมี)
try:
    from moviepy.editor import AudioFileClip
except ImportError:
    AudioFileClip = None

def generate_voice_from_text(text: str) -> tuple:
    """
    ฟังก์ชันแปลงข้อความจาก AI เป็นไฟล์เสียง MP3 ด้วย ElevenLabs
    คืนค่า (Return): (ชื่อไฟล์เสียง, ความยาวเสียงเป็นมิลลิวินาที)
    """
    
    # 1. ดึงคีย์และรหัสเสียงจากที่ตั้งค่าไว้ใน Google Cloud (Environment Variables)
    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("voice_id", "bKOllpuXvCoK2MpTT9Yf") # ใช้ Voice ID ของคุณ
    
    if not api_key:
        print("⚠️ [ElevenLabs Warning]: ไม่พบ ELEVENLABS_API_KEY ในระบบ")
        return None, 0

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    
    # 2. ตั้งค่าการสร้างเสียง (ใช้โมเดล v2 ที่รองรับภาษาไทยได้เนียนและมีอารมณ์ที่สุด)
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2", 
        "voice_settings": {
            "stability": 0.5,           # ความนิ่งของเสียง (0.5 คือกำลังดี ไม่แข็งเป็นหุ่นยนต์)
            "similarity_boost": 0.75,   # ความคล้ายกับเสียงต้นฉบับ
            "style": 0.0,
            "use_speaker_boost": True
        }
    }
    
    try:
        print("🎙️ [ElevenLabs]: กำลังสร้างไฟล์เสียงจากข้อความ...")
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        
        # 3. เตรียมโฟลเดอร์ static เพื่อให้ LINE วิ่งมาโหลดไฟล์เสียงไปเปิดให้ลูกค้าฟังได้
        os.makedirs("static/audio", exist_ok=True)
        
        # 4. สร้างชื่อไฟล์แบบสุ่ม (UUID) เพื่อไม่ให้ไฟล์ทับกันเวลาคนทักมาพร้อมกันเยอะๆ
        filename = f"reply_{uuid.uuid4().hex}.mp3"
        file_path = os.path.join("static/audio", filename)
        
        # 5. บันทึกไฟล์เสียงลงเซิร์ฟเวอร์
        with open(file_path, "wb") as f:
            f.write(response.content)
            
        print(f"✅ [ElevenLabs]: บันทึกไฟล์เสียงสำเร็จ -> {filename}")
        
        # 6. คำนวณความยาวของเสียงเป็นมิลลิวินาที (บังคับใช้สำหรับ AudioSendMessage ของ LINE)
        duration_ms = 10000 # ค่าเริ่มต้น 10 วินาทีเผื่อกันพลาด
        if AudioFileClip:
            try:
                clip = AudioFileClip(file_path)
                duration_ms = int(clip.duration * 1000)
                clip.close()
            except Exception as e:
                print(f"⚠️ [ElevenLabs]: คำนวณความยาวเสียงไม่สำเร็จ ใช้ค่าเริ่มต้นแทน ({e})")
        
        # คืนค่า ชื่อไฟล์ และ ความยาวเสียง กลับไปให้ routes_line.py
        return filename, duration_ms
        
    except Exception as e:
        print(f"❌ [ElevenLabs Error]: เชื่อมต่อและสร้างเสียงไม่สำเร็จ ({str(e)})")
        return None, 0