# ==============================================================================
# 🚀 SIRINTHANATTH PRIME - Enterprise Production Dockerfile
# สถาปัตยกรรม: Multi-Stage Build, Python 3.12, Zero-Layer Bloat
# ==============================================================================

# ------------------------------------------------------------------------------
# 🏗️ STAGE 1: The Builder (ห้องประกอบเครื่องยนต์ - จะถูกทิ้งไปเมื่อประกอบเสร็จ)
# ------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

# ติดตั้ง Compiler และเครื่องมือที่จำเป็นสำหรับการ Build Library บางตัว (เช่น ตัวเชื่อม DB)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# สร้าง Virtual Environment (venv) เพื่อแยก Library ให้เป็นระเบียบและย้ายข้าม Stage ได้ง่าย
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# ติดตั้ง Library ทิ้งไว้ใน venv
COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------------------------
# 🌟 STAGE 2: The Production Runner (ห้องรันระบบจริง - เบาหวิว ปลอดภัยสูงสุด)
# ------------------------------------------------------------------------------
FROM python:3.12-slim-bookworm

# 1. ตั้งค่า Environment Variables ระดับ Production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    TZ=Asia/Bangkok \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# 2. ติดตั้งเฉพาะสิ่งที่จำเป็นตอนรัน (tzdata) และตั้งค่าเวลาไทย (GMT+7)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 3. สร้าง User ทั่วไป (Non-Root) เพื่อความปลอดภัยสูงสุด ปิดประตูแฮกเกอร์ 100%
RUN useradd -m -s /bin/bash primeuser

# 4. คัดลอกเฉพาะ Library ที่ Build เสร็จแล้วจาก STAGE 1 (ทิ้งขยะ Compiler ไว้ข้างหลัง)
COPY --from=builder /opt/venv /opt/venv

# 5. คัดลอก Source Code และมอบสิทธิ์ให้ primeuser ในคำสั่งเดียว (Zero-Layer Bloat)
COPY --chown=primeuser:primeuser . .

# 6. สลับไปใช้ User ที่ปลอดภัย
USER primeuser

# 7. Document Port
EXPOSE 8080

# 8. 🚀 คำสั่งจุดระเบิดเซิร์ฟเวอร์ (Uvicorn) สำหรับ Google Cloud Run
# - เพิ่ม --timeout-keep-alive 75 เพื่อซิงค์กับ Load Balancer ของ Google ป้องกันปัญหา 502 Bad Gateway
# - เพิ่ม --workers 1 (Cloud Run จัดการ Scale ให้แล้ว ให้ 1 Container โฟกัสงานตัวเองเต็มที่)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]