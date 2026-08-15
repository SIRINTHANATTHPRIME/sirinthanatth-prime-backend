# ใช้ Python 3.10 เป็นฐาน (เบาและทำงานไว)
FROM python:3.10-slim

# ตั้งค่าพื้นที่ทำงานในเซิร์ฟเวอร์
WORKDIR /app

# คัดลอกไฟล์ requirements.txt และติดตั้งไลบรารี
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ติดตั้งไลบรารีระดับระบบปฏิบัติการสำหรับประมวลผลสื่อ (FFmpeg และ ImageMagick)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    && rm -rf /var/lib/apt/lists/*

# ปลดล็อกสิทธิ์ ImageMagick ให้สามารถอ่าน/เขียนไฟล์ภาพและข้อความได้
RUN sed -i 's/none/read,write/g' /etc/ImageMagick-6/policy.xml || true

# คัดลอกโค้ดทั้งหมดขึ้นไปบน Container
COPY . .

# เปิดพอร์ต 8080 (Google Cloud Run บังคับใช้พอร์ตนี้)
ENV PORT=8080
EXPOSE 8080

# คำสั่งสตาร์ทเครื่องยนต์ FastAPI แบบรองรับพอร์ต Dynamic ของ Cloud Run
# ให้ Uvicorn ดึงค่าพอร์ตจาก Environment Variable ของ Cloud Run ($PORT) อัตโนมัติ
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1