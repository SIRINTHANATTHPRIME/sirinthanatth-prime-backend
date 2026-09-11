# ==============================================================================
# 🚀 SIRINTHANATTH PRIME - Enterprise Production Dockerfile
# ==============================================================================
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    TZ=Asia/Bangkok \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r primegroup && useradd -r -g primegroup -m -s /bin/bash primeuser \
    && mkdir -p /app \
    && chown -R primeuser:primegroup /app

WORKDIR /app

COPY --from=builder --chown=primeuser:primegroup /opt/venv /opt/venv
COPY --chown=primeuser:primegroup . .

USER primeuser

EXPOSE 8080

# ใช้ Shell Form เพื่อให้ Uvicorn อ่านค่าพอร์ตจากระบบ Cloud Run ได้อย่างถูกต้อง
CMD ["sh", "-c", "uvicorn main_api:app --host 0.0.0.0 --port ${PORT:-8080}"]