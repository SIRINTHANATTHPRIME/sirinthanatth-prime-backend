# ==============================================================================
# 🚀 SIRINTHANATTH PRIME - Enterprise Production Dockerfile
# ==============================================================================

# 1. ใช้ Base Image เวอร์ชันเสถียรและปลอดภัยที่สุด (Debian Bookworm)
FROM python:3.10-slim-bookworm

# 2. ตั้งค่า Environment Variables ระดับ Production (สำคัญมากสำหรับ Cloud Run)
# PYTHONDONTWRITEBYTECODE: ป้องกันการเขียนไฟล์ขยะ (.pyc) ช่วยลดขนาด Container
# PYTHONUNBUFFERED: ส่ง Log เข้า Google Cloud Logging แบบเรียลไทม์ (ไม่เกิดอาการ Log ดีเลย์)
# TZ: ตั้งค่า Timezone ของระบบปฏิบัติการให้เป็นเวลาประเทศไทย (GMT+7)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    TZ=Asia/Bangkok

# 3. กำหนดโฟลเดอร์ทำงานหลักในเซิร์ฟเวอร์
WORKDIR /app

# 4. อัปเดตแพตช์ความปลอดภัย OS และติดตั้งเครื่องมือที่จำเป็น (ตั้งค่าโซนเวลา และล้าง Cache ทันที)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 5. คัดลอกเฉพาะไฟล์ Requirements ก่อน (เทคนิค Docker Cache: ทำให้การ Deploy ครั้งต่อไปเร็วขึ้น 10 เท่า)
COPY requirements.txt .

# 6. อัปเกรด pip เป็นเวอร์ชันล่าสุด และติดตั้ง Library แบบไม่เก็บ Cache เพื่อให้ Container เบาที่สุด
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir -r requirements.txt

# 7. คัดลอก Source Code ทั้งหมดของโปรเจกต์ลงเซิร์ฟเวอร์
COPY . .

# 8. [Security Best Practice] สร้าง User ทั่วไปที่ไม่ใช่ Root เพื่อความปลอดภัยระดับสูงสุด
RUN useradd -m primeuser && \
    chown -R primeuser:primeuser /app && \
    chmod 755 /app

# สลับไปใช้ User ที่ปลอดภัย (Non-Root)
USER primeuser

# 9. Document Port ที่ใช้งาน (เพื่อความเป็นระเบียบและให้ Google Cloud Run ทราบ)
EXPOSE 8080

# 10. คำสั่งรันเซิร์ฟเวอร์ระดับ Production สำหรับ Google Cloud Run (Exec Form)
# เพิ่ม --proxy-headers และ --forwarded-allow-ips เพื่อให้รองรับ Load Balancer ของ Google ได้สมบูรณ์
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]