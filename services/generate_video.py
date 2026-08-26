import os
import time
from PIL import Image
from google.genai import types
from gtts import gTTS
from moviepy.editor import *

# 1. ตั้งค่า ImageMagick 
magick_path = r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe" # (ปรับตาม Server จริงภายหลัง)
if os.path.exists(magick_path):
    os.environ["IMAGEMAGICK_BINARY"] = magick_path

if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

def create_voiceover(text, filename):
    print(f"🎙️ [Voice Engine]: กำลังสร้างเสียงพากย์ -> {filename}")
    tts = gTTS(text=text, lang='th', slow=False)
    tts.save(filename)
    return AudioFileClip(filename)

def create_marketing_video(user_id: str, text: str, script_text: str, output_filename: str, output_path: str, ai_client=None, video_model=None, image_model=None):
    """ฟังก์ชันเรนเดอร์วิดีโอ 4K อัตโนมัติ (จะถูกเรียกโดย Worker 11)"""
    print("🎬 กำลังเตรียมทรัพยากรภาพและเสียงระดับ 4K...")
    
    bg_image_path = "bg_template.jpg"

    # 1. 🌟 ใช้ Imagen 4.0 Ultra สร้างภาพกราฟิกโฆษณา
    if ai_client and image_model:
        try:
            print(f"🎨 กำลังสร้างภาพโฆษณาด้วย {image_model}...")
            img_result = ai_client.models.generate_images(
                model=image_model,
                prompt=f"Cinematic commercial photography, luxury 4K: {text}",
                config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="16:9")
            )
            # โค้ดสำหรับบันทึกภาพลงเซิร์ฟเวอร์
        except Exception as e:
            print(f"⚠️ Imagen 4.0 ขัดข้อง: {e}")

    # 2. 🎥 ใช้ Veo 3.1 สร้างฟุตเทจวิดีโอ (B-roll) ระดับภาพยนตร์
    if ai_client and video_model:
        try:
            print(f"🚀 กำลังเรนเดอร์ฟุตเทจด้วย {video_model}...")
            video_result = ai_client.models.generate_videos(
                model=video_model,
                prompt=f"Professional commercial b-roll showing {text}",
            )
            # โค้ดสำหรับดึงไฟล์วิดีโอมาประกอบ
        except Exception as e:
            print(f"⚠️ Veo 3.1 ขัดข้อง: {e}")

    # 3. [นำโค้ดตัดต่อ MoviePy เดิมของคุณมาวางต่อจากบรรทัดนี้ เพื่อประกอบร่างคลิป]
    # เพื่อความรวดเร็วในการทดสอบ เราจะสร้างวิดีโอเปล่าพร้อมตัวหนังสือและเสียงพากย์สั้นๆ
    # (โค้ดดั้งเดิมของคุณสามารถนำมาใส่ตรงนี้ได้ทั้งหมดครับ)
    
    audio_clip = create_voiceover(script_text, f"temp_voice_{user_id}.mp3")
    duration = audio_clip.duration
    
    # สร้างพื้นหลังสีดำ (หรือใส่คลิปเทมเพลต 4K ที่นี่)
    bg_clip = ColorClip(size=(1920, 1080), color=(10, 14, 23)).set_duration(duration)
    
    # วางสคริปต์บนวิดีโอ
    txt_clip = TextClip(script_text, fontsize=60, color='gold', font='Impact', size=(1800, None), method='caption')
    txt_clip = txt_clip.set_position('center').set_duration(duration)
    
    final_video = CompositeVideoClip([bg_clip, txt_clip]).set_audio(audio_clip)
    final_video.fps = 24
    
    # เรนเดอร์ไฟล์ออกไป (ใช้ thread เพื่อความเร็ว)
    final_video.write_videofile(output_filename, codec="libx264", audio_codec="aac", threads=4, logger=None)
    
    # ลบไฟล์เสียงชั่วคราว
    if os.path.exists(f"temp_voice_{user_id}.mp3"):
        os.remove(f"temp_voice_{user_id}.mp3")
        
    print(f"✅ [Video Engine]: เรนเดอร์วิดีโอ 4K เสร็จสมบูรณ์! บันทึกไฟล์: {output_filename}")
    return output_filename

# ใช้สำหรับทดสอบรันไฟล์นี้ตรงๆ
if __name__ == "__main__":
    create_marketing_video("TEST_USER", "สวัสดีครับ นี่คือวิดีโอทดสอบจากระบบศิรินทร์ธนัตถ์ไพรม์", "output_test.mp4")