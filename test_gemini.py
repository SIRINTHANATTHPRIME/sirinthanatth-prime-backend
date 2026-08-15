import os
from dotenv import load_dotenv
from google import genai

# โหลดตัวแปรจากไฟล์ .env
load_dotenv()

api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

try:
    print("🔍 [System] กำลังเจาะระบบสแกนรายชื่อโมเดลทั้งหมดที่คุณวีระชัยสามารถใช้งานได้...")
    print("-" * 50)
    
    # สั่งให้ดึงรายชื่อโมเดลโดยตรง (ไม่ผ่านการแชท เพื่อเลี่ยง Error 404)
    for m in client.models.list():
        # แสดงเฉพาะชื่อโมเดลออกมา
        print(f"✅ พบโมเดลที่ใช้งานได้: {m.name}")
        
    print("-" * 50)
    print("ภารกิจสแกนเสร็จสิ้น! กรุณาคัดลอกชื่อโมเดลด้านบนมาใช้งานได้เลยครับ")

except Exception as e:
    print(f"❌ เกิดข้อผิดพลาดในการดึงรายชื่อโมเดล: {e}")