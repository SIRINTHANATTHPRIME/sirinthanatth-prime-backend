# ใช้ Python 3.10 เป็นฐาน (เบาและทำงานไว)
FROM python:3.10-slim

# ตั้งค่าพื้นที่ทำงานในเซิร์ฟเวอร์
WORKDIR /app

# 🎬 ติดตั้งไลบรารีระดับระบบปฏิบัติการ สำหรับ Worker 11 (FFmpeg และ ImageMagick)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# ปลดล็อกสิทธิ์ ImageMagick ให้สามารถอ่าน/เขียนไฟล์ภาพและข้อความได้ (แก้บัค MoviePy)
RUN sed -i 's/none/read,write/g' /etc/ImageMagick-6/policy.xml || true

# คัดลอกไฟล์ requirements.txt และติดตั้ง
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกโค้ดทั้งหมดของเราขึ้นไป
COPY . .

# เปิดพอร์ต 8080 (Google Cloud Run บังคับใช้พอร์ตนี้)
EXPOSE 8080

# คำสั่งสตาร์ทเครื่องยนต์ FastAPI ทันทีที่เซิร์ฟเวอร์เปิด
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]