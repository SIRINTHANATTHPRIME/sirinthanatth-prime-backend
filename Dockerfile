# ==============================================================================
# 🚀 SIRINTHANATTH PRIME - Enterprise Production Dockerfile
# ==============================================================================

# 1. ใช้ Base Image เวอร์ชันเสถียรและปลอดภัยที่สุด (Debian Bookworm)
FROM python:3.10-slim-bookworm

# 2. ตั้งค่า Environment Variables ระดับ Production (สำคัญมากสำหรับ Cloud Run)
# PYTHONDONTWRITEBYTECODE: ป้องกันการเขียนไฟล์ขยะ (.pyc) ช่วยลดขนาด Container
# PYTHONUNBUFFERED: ส่ง Log เข้า Google Cloud Logging แบบเรียลไทม์ (ไม่เกิดอาการ Log ดีเลย์)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# 3. กำหนดโฟลเดอร์ทำงานหลักในเซิร์ฟเวอร์
WORKDIR /app

# 4. อัปเดตแพตช์ความปลอดภัย OS และติดตั้งเครื่องมือที่จำเป็น (ล้าง Cache ทันทีเพื่อประหยัดพื้นที่)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 5. คัดลอกเฉพาะไฟล์ Requirements ก่อน (เทคนิค Docker Cache: ทำให้การ Deploy ครั้งต่อไปเร็วขึ้น 10 เท่า)
COPY requirements.txt .

# 6. อัปเกรด pip เป็นเวอร์ชันล่าสุด และติดตั้ง Library แบบไม่เก็บ Cache
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir -r requirements.txt

# 7. คัดลอก Source Code ทั้งหมดของโปรเจกต์ลงเซิร์ฟเวอร์
COPY . .

# 8. [Security Best Practice] สร้าง User ทั่วไปที่ไม่ใช่ Root เพื่อความปลอดภัยระดับสูงสุด
RUN useradd -m primeuser && chown -R primeuser:primeuser /app
USER primeuser

# 9. สั่งรันระบบผ่าน Uvicorn แบบรีดประสิทธิภาพ (Async Worker)
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1