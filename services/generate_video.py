import os
import time
import logging
import asyncio
import platform
from PIL import Image
from google.genai import types
from gtts import gTTS
from moviepy.editor import ImageClip, ColorClip, TextClip, CompositeVideoClip, AudioFileClip

logger = logging.getLogger("VideoGenerator")

# ==========================================
# 1. ⚙️ Dynamic ImageMagick Resolution (Cloud-Ready)
# ==========================================
if platform.system() == "Windows":
    magick_path = os.environ.get("IMAGEMAGICK_BINARY", r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe")
else:
    magick_path = os.environ.get("IMAGEMAGICK_BINARY", "/usr/bin/convert") # มาตรฐานบน Linux/Docker

if os.path.exists(magick_path):
    os.environ["IMAGEMAGICK_BINARY"] = magick_path
else:
    logger.warning("⚠️ [System]: ไม่พบ ImageMagick ในระบบ การสร้าง TextClip อาจล้มเหลว")

# แก้ปัญหา Compatibility ระหว่าง Pillow รุ่นใหม่กับ MoviePy
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

def _sync_create_voiceover(text: str, filename: str):
    """ระบบพากย์เสียงสำรอง (รันใน Thread แยก)"""
    tts = gTTS(text=text, lang='th', slow=False)
    tts.save(filename)
    return filename

async def create_marketing_video(user_id: str, text: str, script_text: str, output_filename: str, output_path: str, ai_client=None, video_model=None, image_model=None):
    """
    🎬 ระบบเรนเดอร์วิดีโอ 4K อัตโนมัติ (Asynchronous Enterprise Grade)
    """
    logger.info(f"🎬 [Video Studio]: กำลังเตรียมทรัพยากรภาพและเสียงระดับ 4K สำหรับ {user_id}")
    
    bg_clip = None
    txt_clip = None
    audio_clip = None
    final_video = None
    
    temp_img_path = f"temp_bg_{user_id}_{int(time.time())}.png"
    temp_voice_path = f"temp_voice_{user_id}_{int(time.time())}.mp3"

    try:
        # ==========================================
        # 🌟 1. ใช้ Imagen 3.0 สร้างภาพกราฟิก (Async I/O)
        # ==========================================
        if ai_client and image_model:
            try:
                logger.info(f"🎨 [Vision Engine]: กำลังสร้างภาพโฆษณาด้วย {image_model}...")
                
                def _generate_image():
                    return ai_client.models.generate_images(
                        model=image_model,
                        prompt=f"Cinematic commercial photography, highly detailed, luxury 4K: {text}",
                        config=types.GenerateImagesConfig(
                            number_of_images=1, 
                            aspect_ratio="16:9",
                            output_mime_type="image/png"
                        )
                    )
                
                img_result = await asyncio.to_thread(_generate_image)
                
                if img_result.generated_images:
                    def _save_image():
                        with open(temp_img_path, "wb") as f:
                            f.write(img_result.generated_images[0].image.image_bytes)
                    await asyncio.to_thread(_save_image)
                    
                    bg_clip = ImageClip(temp_img_path)
                    logger.info("✅ [Vision Engine]: สร้างภาพพื้นหลัง 4K สำเร็จ")
            except Exception as e:
                logger.warning(f"⚠️ [Vision Engine Warning]: Imagen ขัดข้อง สลับใช้พื้นหลังสีดำ ({e})")

        # ==========================================
        # 🎞️ 2. กระบวนการตัดต่อ (MoviePy Assembly)
        # ==========================================
        # สร้างเสียงพากย์ฉุกเฉินผ่าน Thread
        await asyncio.to_thread(_sync_create_voiceover, script_text, temp_voice_path)
        audio_clip = AudioFileClip(temp_voice_path)
        duration = audio_clip.duration
        
        if bg_clip is None:
            bg_clip = ColorClip(size=(1920, 1080), color=(10, 14, 23))
            
        bg_clip = bg_clip.set_duration(duration)
        
        try:
            # ใช้ฟอนต์มาตรฐานที่ปลอดภัยหากไม่มี Impact
            font_choice = 'Impact' if platform.system() == "Windows" else 'DejaVu-Sans-Bold'
            txt_clip = TextClip(script_text, fontsize=70, color='gold', font=font_choice, size=(1800, None), method='caption')
            txt_clip = txt_clip.set_position('center').set_duration(duration)
            # 🐛 แก้บั๊กตัวพิมพ์เล็กที่ทำให้ระบบล่ม
            final_video = CompositeVideoClip([bg_clip, txt_clip]).set_audio(audio_clip)
        except Exception as txt_err:
            logger.warning(f"⚠️ [MoviePy Warning]: TextClip สร้างไม่ได้ ({txt_err}) เรนเดอร์เฉพาะภาพและเสียง")
            final_video = bg_clip.set_audio(audio_clip)
        
        final_video.fps = 24
        
        # ==========================================
        # ⚙️ 3. เรนเดอร์ไฟล์ออกสู่ระบบ (Async Export)
        # ==========================================
        logger.info("⚙️ [Video Studio]: เริ่มกระบวนการ Export (H.264/AAC)...")
        
        def _write_video():
            final_video.write_videofile(
                output_path, 
                codec="libx264", 
                audio_codec="aac", 
                threads=4, 
                preset="ultrafast", 
                logger=None
            )
            
        await asyncio.to_thread(_write_video)
        logger.info(f"✅ [Video Engine]: เรนเดอร์วิดีโอเสร็จสมบูรณ์! ส่งมอบไปยัง: {output_path}")
        return output_filename

    finally:
        # ==========================================
        # 🧹 4. ทำความสะอาดทรัพยากร (Strict Memory Cleanup)
        # ==========================================
        if audio_clip: audio_clip.close()
        if bg_clip: bg_clip.close()
        if txt_clip: txt_clip.close()
        if final_video: final_video.close()
        
        # ลบไฟล์ Temp ขยะคืนพื้นที่ให้เซิร์ฟเวอร์
        for temp_file in [temp_voice_path, temp_img_path]:
            if os.path.exists(temp_file):
                try: os.remove(temp_file)
                except Exception as cleanup_err:
                    logger.debug(f"Failed to remove temp file {temp_file}: {cleanup_err}")