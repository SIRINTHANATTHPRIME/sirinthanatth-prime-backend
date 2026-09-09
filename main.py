import os
import re
import json
import base64
import hashlib
import hmac
import logging
import stripe
import uvicorn
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from supabase import create_client, Client
from core_services.secret_manager import PrimeSecretVault

# ☁️ นำเข้า Google Cloud Tasks (Enterprise Queue)
try:
    from google.cloud import tasks_v2
    CLOUD_TASKS_AVAILABLE = True
except ImportError:
    CLOUD_TASKS_AVAILABLE = False

# ==========================================
# ⚙️ 1. Initialization & Environment
# ==========================================
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("PRIME_CORE")

# 🛡️ Safe Secret Loading (ป้องกันเซิร์ฟเวอร์พังตอน Startup หากดึงคีย์ไม่สำเร็จ)
def safe_get_secret(secret_name: str, fallback_env: str = "") -> str:
    try:
        val = PrimeSecretVault.get_secret(secret_name)
        return val if val else os.getenv(secret_name, fallback_env)
    except Exception as e:
        logger.warning(f"⚠️ [Secret Vault Warning]: ไม่สามารถดึง {secret_name} ได้ ใช้ค่าสำรองแทน -> {e}")
        return os.getenv(secret_name, fallback_env)

LINE_CHANNEL_ACCESS_TOKEN = safe_get_secret("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = safe_get_secret("LINE_CHANNEL_SECRET")
MASTER_ADMIN_LINE_ID = safe_get_secret("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
CEO_LINE_ID = safe_get_secret("CEO_LINE_ID", MASTER_ADMIN_LINE_ID)
STRIPE_WEBHOOK_SECRET = safe_get_secret("STRIPE_WEBHOOK_SECRET")

# Google Cloud Project Config
GCP_PROJECT = safe_get_secret("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1")
GCP_LOCATION = safe_get_secret("GOOGLE_CLOUD_LOCATION", "asia-southeast3")
GCP_QUEUE_NAME = safe_get_secret("CLOUD_TASKS_QUEUE_NAME", "prime-heavy-workers")

stripe_key = safe_get_secret("STRIPE_SECRET_KEY")
if stripe_key:
    stripe.api_key = stripe_key

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = safe_get_secret("SUPABASE_SERVICE_ROLE_KEY")

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("✅ [System Database]: Supabase Vault initialized successfully.")
    except Exception as e:
        logger.critical(f"❌ [System Critical Error]: Failed to unlock Supabase Vault: {e}")

# ==========================================
# 🚀 2. Lifespan & Swarm Network Bootup
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 [System Ignition]: Booting SIRINTHANATTH PRIME Core Engine...")
    
    required_directories = ["static", "static/audio", "static/images", "static/reports", "css", "assets", "templates"]
    for directory in required_directories:
        os.makedirs(directory, exist_ok=True)
    
    # 🧠 Lazy Initialization: โหลด Worker เฉพาะตอน Boot ประหยัด RAM
    try:
        from core_services.swarm_dispatcher import swarm_hub
        from agents.worker_0_ceo_secretary import CeoSecretaryWorker
        from agents.worker_9_prime import PrimeAdvisorWorker
        from agents.worker_13_it_architect import ITArchitectWorker 
        
        swarm_hub.register("WORKER_0_CEO", CeoSecretaryWorker())
        swarm_hub.register("WORKER_9_PRIME", PrimeAdvisorWorker())
        swarm_hub.register("WORKER_13_IT", ITArchitectWorker())
        logger.info("✅ [Swarm Network]: All AI Agents are online and synchronized.")
    except ImportError as e:
        logger.warning(f"⚠️ [Swarm Network Warning]: AI Workers not fully loaded -> {e}")
    except Exception as e:
        logger.error(f"❌ [Swarm Network Error]: AI Engine failed to ignite -> {e}", exc_info=True)

    yield 
    logger.info("🛑 [System Shutdown]: Gracefully shutting down services. Saving states...")

# ==========================================
# 🛡️ 3. FastAPI Core & Security Middlewares
# ==========================================
app = FastAPI(
    title="SIRINTHANATTH PRIME Core Engine",
    description="Enterprise-grade AI SaaS supporting financial, logistics, voice AI, and heavy media workloads.",
    version="4.0.0",
    lifespan=lifespan
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"]
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    # 🛡️ Military-Grade Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Content-Security-Policy"] = "default-src 'self' https:; script-src 'self' 'unsafe-inline' https:; style-src 'self' 'unsafe-inline' https:; img-src 'self' data: https:;"
    return response

# ==========================================
# 📂 4. Static Files & Routers Mount
# ==========================================
app.mount("/static", StaticFiles(directory="static"), name="static")
if os.path.exists("css"): app.mount("/css", StaticFiles(directory="css"), name="css")
if os.path.exists("assets"): app.mount("/assets", StaticFiles(directory="assets"), name="assets")

try:
    from api.routes_stats import router as stats_router
    app.include_router(stats_router, prefix="/api/v1/stats", tags=["Statistics"])
    logger.info("✅ [System]: Stats Router mounted successfully.")
except Exception as e:
    logger.warning(f"⚠️ [System Warning]: Stats Router not found or skipped -> {e}")

# ==========================================
# ⚡ 5. ZERO-TIMEOUT LINE WEBHOOK (Architecture Upgrade)
# ==========================================
def verify_line_signature(body: bytes, signature: str) -> bool:
    """🛡️ ตรวจสอบความถูกต้องของคำสั่ง ป้องกันการปลอมแปลง (Webhook Signature Validation)"""
    if not LINE_CHANNEL_SECRET: return True 
    hash_val = hmac.new(LINE_CHANNEL_SECRET.encode('utf-8'), body, hashlib.sha256).digest()
    expected_signature = base64.b64encode(hash_val).decode('utf-8')
    return hmac.compare_digest(signature, expected_signature)

async def process_payload_background(payload: dict):
    """🧠 ฟังก์ชันประมวลผลงานหนักแบบเบื้องหลัง (ไม่ล็อกการตอบกลับของ LINE)"""
    try:
        from core_services.swarm_dispatcher import swarm_hub
        await swarm_hub.dispatch_line_event(payload)
    except Exception as e:
        logger.error(f"❌ [Background Process Error]: {e}", exc_info=True)

@app.post("/api/v1/line/webhook", tags=["LINE OA"])
async def line_webhook_gateway(request: Request, background_tasks: BackgroundTasks):
    """
    🚦 API Gateway ด่านหน้า: รับข้อมูล -> ยืนยันความปลอดภัย -> คืนค่า 200 OK ทันที -> โยนงานลงระบบคิว
    """
    signature = request.headers.get("x-line-signature", "")
    body_bytes = await request.body()

    if not verify_line_signature(body_bytes, signature):
        logger.warning("🚫 [Security]: Invalid LINE Signature detected. Dropping request.")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = json.loads(body_bytes.decode('utf-8'))
        
        if CLOUD_TASKS_AVAILABLE and GCP_PROJECT:
            try:
                client = tasks_v2.CloudTasksClient()
                parent = client.queue_path(GCP_PROJECT, GCP_LOCATION, GCP_QUEUE_NAME)
                task = {
                    "http_request": {
                        "http_method": tasks_v2.HttpMethod.POST,
                        "url": f"https://{request.url.hostname}/api/v1/internal/process-task",
                        "headers": {"Content-type": "application/json"},
                        "body": body_bytes,
                    }
                }
                client.create_task(request={"parent": parent, "task": task})
                logger.info("☁️ [Cloud Tasks]: Offloaded payload to Google Cloud Tasks successfully.")
            except Exception as e:
                logger.warning(f"⚠️ [Cloud Tasks Fallback]: Failed to queue task ({e}). Falling back to BackgroundTasks.")
                background_tasks.add_task(process_payload_background, payload)
        else:
            background_tasks.add_task(process_payload_background, payload)

        return Response(content="OK", status_code=200)

    except Exception as e:
        logger.error(f"❌ [Webhook Gateway Error]: {e}")
        return Response(content="Error processing request", status_code=500)

@app.post("/api/v1/internal/process-task", include_in_schema=False)
async def internal_cloud_task_worker(request: Request):
    """⚙️ Endpoint ภายในสำหรับให้ Google Cloud Tasks เรียกกลับมาทำงานหนัก"""
    payload = await request.json()
    await process_payload_background(payload)
    return {"status": "completed"}

# ==========================================
# 🌐 6. Core Endpoints
# ==========================================
@app.get("/")
def root():
    return {"status": "Online", "system": "SIRINTHANATTH PRIME", "version": "4.0.0", "mode": "Enterprise"}

@app.get("/health")
def health_check():
    return {
        "status": "success",
        "system": "SIRINTHANATTH PRIME Enterprise AI SaaS",
        "database": "connected" if supabase else "disconnected",
        "stripe": "connected" if stripe_key else "disconnected"
    }

@app.get("/wallet_menu")
def read_wallet():
    if os.path.exists("wallet_menu.html"): return FileResponse("wallet_menu.html")
    return {"status": "error", "message": "Smart Wallet layout is currently unavailable."}

@app.get("/api/user-status/{line_id}")
async def get_user_status(line_id: str):
    if not supabase: raise HTTPException(status_code=500, detail="Database Error")
    try:
        res = await asyncio.to_thread(supabase.table("prime_clients").select("*").eq("line_user_id", line_id).execute)
        if not res.data:
            return {"tier": "GUEST", "balance": 0, "message": "ยินดีต้อนรับสู่ SIRINTHANATTH PRIME! ลงทะเบียนวันนี้เพื่อสัมผัสประสบการณ์ AI ระดับโลกครับ"}
            
        user_data = res.data[0]
        tier = user_data.get("package_tier", "ESSENTIAL").upper()
        balance = float(user_data.get("token_balance", 0.0))
        
        msg = f"ยินดีต้อนรับกลับครับ ท่านผู้บริหารระดับ {tier}"
        if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]: msg = "👑 ยินดีต้อนรับท่านประธาน! ระบบ VVIP ทำงานเต็มประสิทธิภาพพร้อมให้บริการทุกมิติครับ"
        elif tier == "ENTERPRISE":
            if balance < 2000: msg = "🏢 ท่านผู้บริหารครับ เพื่อให้ระบบคลังข้อมูลทำงานอย่างราบรื่น ขอแนะนำให้เติม PRIME CREDITS สำรองไว้ครับ"
        elif tier == "PRIME":
            if balance < 1000: msg = "💡 เพื่อให้การวิเคราะห์กลยุทธ์ธุรกิจและสร้างสื่อ 4K ดำเนินไปอย่างต่อเนื่อง ขอแนะนำให้เติม PRIME CREDITS ครับ"
        elif tier == "ESSENTIAL":
            if balance < 500: msg = "🚀 ธุรกิจของคุณกำลังเติบโต! อัปเกรดเป็นแพ็กเกจ PRIME เพื่อปลดล็อกที่ปรึกษาระดับสากลได้ทันทีครับ"
        else: msg = "✨ ยินดีต้อนรับครับ! ยกระดับธุรกิจด้วยแพ็กเกจ PRIME หรือ ENTERPRISE เพื่อรับสิทธิพิเศษขั้นสูงสุดได้เสมอครับ"
                
        return {"tier": tier, "balance": balance, "message": msg}
    except Exception as e:
        logger.error(f"Error fetching user status: {e}", exc_info=True)
        return {"tier": "ERROR", "balance": 0, "message": "ระบบกำลังปรับปรุงข้อมูลชั่วคราวครับ"}

class UserProfile(BaseModel):
    line_user_id: str
    display_name: str
    picture_url: str

@app.post("/api/sync-user")
async def sync_user_profile(profile: UserProfile, background_tasks: BackgroundTasks):
    if not supabase: raise HTTPException(status_code=500, detail="Database not available")
    
    def _sync():
        try:
            supabase.table("users").upsert({
                "line_user_id": profile.line_user_id,
                "display_name": profile.display_name,
                "picture_url": profile.picture_url,
                "status": "active"
            }, on_conflict="line_user_id").execute()
        except Exception as err:
            logger.error(f"❌ [Sync System DB Error]: {err}")
            
    background_tasks.add_task(_sync)
    return {"status": "success", "message": "ซิงค์ข้อมูลผู้ใช้สำเร็จ"}

# ==========================================
# 💰 7. Financial Engine (Stripe Webhook)
# ==========================================
@app.post("/api/stripe-webhook")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("⚠️ STRIPE_WEBHOOK_SECRET is missing. Rejecting webhook.")
        return Response(content="Webhook secret missing", status_code=400)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        logger.error("❌ Stripe Signature Invalid (Potential Replay Attack)!")
        return Response(content="Invalid signature", status_code=400)
    except Exception as e:
        logger.error(f"❌ Stripe Event Parsing Error: {e}")
        return Response(content=str(e), status_code=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        client_ref = session.get('client_reference_id', '') 
        amount_paid_thb = session.get('amount_total', 0) / 100.0
        
        logger.info(f"💰 [Stripe Revenue]: ยอดชำระ {amount_paid_thb} THB สำเร็จ! (Ref: {client_ref})")

        def _process_financials():
            if not supabase or not client_ref: return
            
            user_id = ""
            agent_code = "NOAGENT"
            package_tier = "ESSENTIAL"
            is_subscription = False
            base_tokens = amount_paid_thb * 10 
            bonus_tokens = 0
            
            match = re.match(r'([A-Z_]+)_AGENT_([A-Z0-9]+)_LINE_([A-Za-z0-9]+)', client_ref)
            if match:
                plan_name = match.group(1)
                agent_code = match.group(2)
                user_id = match.group(3)
                
                if plan_name in ["ESSENTIAL", "PRIME", "ENTERPRISE", "VIP"]:
                    is_subscription = True
                    package_tier = plan_name if plan_name != "VIP" else "VIP_FOUNDER"
            elif client_ref.startswith('topup_'):
                user_id = client_ref.replace('topup_', '')

            if not user_id: return

            try:
                if is_subscription:
                    if package_tier == "ESSENTIAL": bonus_tokens = 1000
                    elif package_tier == "PRIME": bonus_tokens = 3000
                    elif package_tier == "ENTERPRISE": bonus_tokens = 10000
                    elif package_tier == "VIP_FOUNDER": base_tokens = 49000; bonus_tokens = 0 
                
                total_tokens_to_add = base_tokens + bonus_tokens

                res = supabase.table("prime_clients").select("token_balance").eq("line_user_id", user_id).execute()
                current_balance = float(res.data[0].get("token_balance", 0)) if res.data else 0.0
                new_balance = current_balance + total_tokens_to_add
                
                update_data = {"token_balance": new_balance}
                if is_subscription:
                    update_data["package_tier"] = package_tier
                    if package_tier in ["ENTERPRISE", "VIP_FOUNDER"]: update_data["role"] = "vip"
                
                supabase.table("prime_clients").upsert({"line_user_id": user_id, **update_data}, on_conflict="line_user_id").execute()
                logger.info(f"✅ [Financial Engine]: อัปเดตบัญชี {user_id} ระดับ {package_tier} รับ {total_tokens_to_add} Credits (ยอดใหม่: {new_balance})")

                if agent_code and agent_code != "NOAGENT":
                    commission_rate = 0.30 if package_tier == "VIP_FOUNDER" else 0.15 
                    commission_amount = amount_paid_thb * commission_rate
                    
                    supabase.table("affiliate_transactions").insert({
                        "agent_code": agent_code,
                        "buyer_line_id": user_id,
                        "package_bought": package_tier,
                        "amount_paid": amount_paid_thb,
                        "commission_amount": commission_amount,
                        "status": "pending"
                    }).execute()
                    logger.info(f"🤝 [Affiliate System]: บันทึก Commission {commission_amount} THB ให้ Agent: {agent_code}")

            except Exception as db_err:
                logger.error(f"❌ [Financial Engine Error]: {db_err}", exc_info=True)

        background_tasks.add_task(_process_financials)
        
    return {"status": "success"}

# ==========================================
# 🚀 8. Server Ignition
# ==========================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 IGNITING SIRINTHANATTH PRIME CORE ENGINE ON PORT {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)