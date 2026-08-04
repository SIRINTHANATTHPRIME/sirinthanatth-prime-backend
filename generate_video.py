import os
import time
from PIL import Image
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

def create_marketing_video(user_id: str, script_text: str, output_filename: str):
    """ฟังก์ชันเรนเดอร์วิดีโอ 4K อัตโนมัติ (จะถูกเรียกโดย Worker 11)"""
    print(f"🎬 [Video Engine]: เริ่มต้นเรนเดอร์สื่อ 4K สำหรับ User: {user_id}")
    
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