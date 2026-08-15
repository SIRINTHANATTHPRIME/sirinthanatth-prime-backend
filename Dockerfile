# ใช้ Python เวอร์ชันเสถียร
FROM python:3.10-slim

# ตั้งค่าโฟลเดอร์ทำงานในเซิร์ฟเวอร์
WORKDIR /app

# คัดลอกและติดตั้ง Library ทั้งหมด
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกไฟล์ทั้งหมดในโปรเจกต์ลงเซิร์ฟเวอร์
COPY . .

# กำหนดตัวแปรพอร์ตให้ Cloud Run รู้จัก
ENV PORT=8080

# สั่งรันระบบและเชื่อมต่อพอร์ตแบบอัตโนมัติ (จุดนี้สำคัญมาก)
CMD exec uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1