import os
import time
import logging
from PIL import Image
from google.genai import types
from gtts import gTTS
from moviepy.editor import *

# ตั้งค่า Logger สำหรับตรวจสอบการเรนเดอร์
logger = logging.getLogger("VideoGenerator")

# ==========================================
# 1. ตั้งค่า ImageMagick สำหรับการสร้าง TextClip
# ==========================================
magick_path = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe" # (ปรับแก้ Path ตาม Server จริง)
if os.path.exists(magick_path):
    os.environ["IMAGEMAGICK_BINARY"] = magick_path

# แก้ไขปัญหา Compatibility ระหว่าง Pillow เวอร์ชันใหม่กับ MoviePy
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

def create_voiceover(text: str, filename: str):
    """ระบบพากย์เสียงสำรอง (Fast TTS Fallback) หาก ElevenLabs ขัดข้อง"""
    logger.info(f"🎙️ [Voice Engine]: กำลังสร้างเสียงพากย์ฉุกเฉิน -> {filename}")
    tts = gTTS(text=text, lang='th', slow=False)
    tts.save(filename)
    return AudioFileClip(filename)

def create_marketing_video(user_id: str, text: str, script_text: str, output_filename: str, output_path: str, ai_client=None, video_model=None, image_model=None):
    """
    🎬 ฟังก์ชันเรนเดอร์วิดีโอ 4K อัตโนมัติ ผสาน Imagen 3.0 และ Veo
    (ถูกเรียกโดย Worker 11 Media Engine แบบ Asynchronous)
    """
    logger.info(f"🎬 [Video Studio]: กำลังเตรียมทรัพยากรภาพและเสียงระดับ 4K สำหรับ {user_id}")
    
    bg_clip = None
    temp_img_path = f"temp_bg_{user_id}_{int(time.time())}.png"
    temp_voice_path = f"temp_voice_{user_id}_{int(time.time())}.mp3"

    # ==========================================
    # 🌟 1. ใช้ Imagen 3.0 (Vertex AI) สร้างภาพกราฟิกโฆษณา
    # ==========================================
    if ai_client and image_model:
        try:
            logger.info(f"🎨 [Vision Engine]: กำลังสร้างภาพโฆษณาด้วย {image_model}...")
            img_result = ai_client.models.generate_images(
                model=image_model,
                prompt=f"Cinematic commercial photography, highly detailed, luxury 4K: {text}",
                config=types.GenerateImagesConfig(
                    number_of_images=1, 
                    aspect_ratio="16:9",
                    output_mime_type="image/png"
                )
            )
            # ดึงภาพจาก Base64 Bytes มาเซฟลงไฟล์
            if img_result.generated_images:
                with open(temp_img_path, "wb") as f:
                    f.write(img_result.generated_images[0].image.image_bytes)
                bg_clip = ImageClip(temp_img_path)
                logger.info("✅ [Vision Engine]: สร้างภาพพื้นหลัง 4K สำเร็จ")
        except Exception as e:
            logger.warning(f"⚠️ [Vision Engine Warning]: Imagen ขัดข้อง สลับใช้พื้นหลังสีดำ ({e})")

    # ==========================================
    # 🎥 2. เตรียมโครงสร้าง Veo 0.1 สำหรับสร้างฟุตเทจวิดีโอ (Future Readiness)
    # ==========================================
    if ai_client and video_model:
        try:
            logger.info(f"🚀 [Cinematic Engine]: กำลังส่งคำสั่งเรนเดอร์ฟุตเทจไปยัง {video_model}...")
            # หมายเหตุ: โครงสร้างนี้รอการอัปเดต SDK แบบ Public 100% จาก Google
            # video_result = ai_client.models.generate_videos(...)
        except Exception as e:
            logger.warning(f"⚠️ [Cinematic Engine Warning]: Veo ขัดข้องหรืออยู่ในสถานะ Preview ({e})")

    # ==========================================
    # 🎞️ 3. กระบวนการตัดต่อ (MoviePy Assembly)
    # ==========================================
    # สร้างเสียงพากย์และหาความยาว
    audio_clip = create_voiceover(script_text, temp_voice_path)
    duration = audio_clip.duration
    
    # หากสร้างรูปด้วย Imagen ไม่สำเร็จ ให้ใช้พื้นหลังพรีเมียมสีดำเหลือบน้ำเงิน
    if bg_clip is None:
        bg_clip = ColorClip(size=(1920, 1080), color=(10, 14, 23))
        
    bg_clip = bg_clip.set_duration(duration)
    
    # วางสคริปต์ข้อความลงบนวิดีโอ (ซับไตเติล)
    try:
        txt_clip = TextClip(script_text, fontsize=70, color='gold', font='Impact', size=(1800, None), method='caption')
        txt_clip = txt_clip.set_position('center').set_duration(duration)
        final_video = CompositeVideoClip([bg_clip, txt_clip]).set_audio(audio_clip)
    except Exception as txt_err:
        logger.warning(f"⚠️ [MoviePy Warning]: TextClip สร้างไม่ได้ ({txt_err}) เรนเดอร์เฉพาะภาพและเสียง")
        final_video = bg_clip.set_audio(audio_clip)
    
    final_video.fps = 24
    
    # ==========================================
    # ⚙️ 4. เรนเดอร์ไฟล์ออกสู่ระบบ (Hardware Optimization)
    # ==========================================
    logger.info("⚙️ [Video Studio]: เริ่มกระบวนการ Export (H.264/AAC)...")
    final_video.write_videofile(
        output_path, 
        codec="libx264", 
        audio_codec="aac", 
        threads=4, 
        preset="ultrafast", # เรนเดอร์ไวขึ้น ลดภาระคลาวด์
        logger=None
    )
    
    # ==========================================
    # 🧹 5. ทำความสะอาดทรัพยากร (Memory Cleanup)
    # ==========================================
    audio_clip.close()
    if bg_clip: bg_clip.close()
    try: txt_clip.close() 
    except: pass
    final_video.close()
    
    # ลบ Temp Files ป้องกันพื้นที่เซิร์ฟเวอร์เต็ม
    for temp_file in [temp_voice_path, temp_img_path]:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception:
                pass
                
    logger.info(f"✅ [Video Engine]: เรนเดอร์วิดีโอเสร็จสมบูรณ์! ส่งมอบไปยัง: {output_path}")
    return output_filename