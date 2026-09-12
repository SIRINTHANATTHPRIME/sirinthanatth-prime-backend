import os
import re
import json
import base64
import hashlib
import httpx
import hmac
import logging
import stripe
import uvicorn
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Response, Header, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from supabase import create_client, Client

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
logger = logging.getLogger("PRIME_SUPREME_CORE")

def safe_get_secret(secret_name: str, fallback_env: str = "") -> str:
    """🛡️ Safe Secret Loading: ป้องกันเซิร์ฟเวอร์พังตอน Startup"""
    try:
        from core_services.secret_manager import PrimeSecretVault
        val = PrimeSecretVault.get_secret(secret_name)
        return val if val else os.getenv(secret_name, fallback_env)
    except Exception as e:
        logger.warning(f"⚠️ [Secret Vault Fallback]: ใช้ค่าสำรอง (.env) สำหรับ {secret_name} -> {e}")
        return os.getenv(secret_name, fallback_env)

# 🔑 ดึงกุญแจความปลอดภัย
LINE_CHANNEL_ACCESS_TOKEN = safe_get_secret("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = safe_get_secret("LINE_CHANNEL_SECRET")
LINE_LOGIN_CLIENT_ID = safe_get_secret("LINE_LOGIN_CHANNEL_ID")
LINE_LOGIN_SECRET = safe_get_secret("LINE_LOGIN_CHANNEL_SECRET")
MASTER_ADMIN_LINE_ID = safe_get_secret("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
CEO_LINE_ID = safe_get_secret("CEO_LINE_ID", MASTER_ADMIN_LINE_ID)
STRIPE_WEBHOOK_SECRET = safe_get_secret("STRIPE_WEBHOOK_SECRET")

# ☁️ Google Cloud Infrastructure
GCP_PROJECT = safe_get_secret("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1")
GCP_LOCATION = safe_get_secret("GOOGLE_CLOUD_LOCATION", "asia-southeast3")
GCP_QUEUE_NAME = safe_get_secret("CLOUD_TASKS_QUEUE_NAME", "prime-heavy-workers")
SERVICE_ACCOUNT_EMAIL = safe_get_secret("SERVICE_ACCOUNT_EMAIL", f"github-actions-deployer@{GCP_PROJECT}.iam.gserviceaccount.com")

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
    logger.info("🚀 [System Ignition]: Booting SIRINTHANATTH PRIME Supreme Engine...")
    
    required_directories = ["static", "static/audio", "static/images", "static/reports", "css", "assets", "templates"]
    for directory in required_directories:
        os.makedirs(directory, exist_ok=True)
    
    try:
        from core_services.swarm_dispatcher import swarm_hub
        logger.info("✅ [Swarm Network]: All AI Agents are online and synchronized with the Mastermind.")
    except Exception as e:
        logger.error(f"❌ [Swarm Network Error]: AI Engine failed to ignite -> {e}", exc_info=True)

    yield 
    logger.info("🛑 [System Shutdown]: Gracefully shutting down services. Disconnecting databases...")

# ==========================================
# 🛡️ 3. FastAPI Core & Security Middlewares
# ==========================================
app = FastAPI(
    title="SIRINTHANATTH PRIME Supreme Core",
    description="Enterprise AI SaaS architecture supporting 14-Agent Swarm, Financial Ledgers, and 4K Media.",
    version="5.0.0-ENTERPRISE",
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
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://static.line-scdn.net https://js.stripe.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://*.supabase.co https://api.stripe.com https://*.line-scdn.net; "
        "frame-src 'self' https://js.stripe.com;"
    )
    response.headers["Content-Security-Policy"] = csp
    return response

# ==========================================
# 📂 4. Static Files & Routers Mount
# ==========================================
# 🛠️ บังคับสร้างโฟลเดอร์ก่อน mount เสมอ ป้องกัน FastAPI Crash 100%
required_directories = ["static", "static/audio", "static/images", "static/reports", "css", "assets", "templates"]
for directory in required_directories:
    os.makedirs(directory, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

try:
    from api.routes_stats import router as stats_router
    app.include_router(stats_router, prefix="/api/v1/stats", tags=["Statistics"])
    logger.info("✅ [System]: Stats Router mounted successfully.")
except Exception as e:
    logger.warning(f"⚠️ [System Warning]: Stats Router not found -> {e}")
# ==========================================
# ⚡ 5. ZERO-TIMEOUT LINE WEBHOOK (OIDC Upgrade)
# ==========================================
def verify_line_signature(body: bytes, signature: str, secret: str) -> bool:
    if not secret or not signature: return False
    hash_val = hmac.new(secret.encode('utf-8'), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(hash_val).decode('utf-8'), signature)

async def send_line_reply(reply_token: str, text: str):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }
    data = {"replyToken": reply_token, "messages": [{"type": "text", "text": text}]}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=data, headers=headers)

async def process_payload_background(payload: dict):
    try:
        from core_services.swarm_dispatcher import swarm_hub
        if hasattr(swarm_hub, 'dispatch_line_event'):
            await swarm_hub.dispatch_line_event(payload)
        else:
            # Fallback Central Boss
            from agents.central_boss import CentralBossAgent
            boss = CentralBossAgent()
            events = payload.get("events", [])
            for event in events:
                if event.get("type") == "message":
                    u_id = event.get("source", {}).get("userId", "")
                    msg = event.get("message", {}).get("text", "")
                    await boss.route_task(u_id, msg, BackgroundTasks())
    except Exception as e:
        logger.error(f"❌ [Background Process Error]: {e}", exc_info=True)

@app.post("/webhook", tags=["LINE OA Master Gateway"])
@app.post("/api/v1/line/webhook", tags=["LINE OA Master Gateway"])
async def line_webhook_gateway(request: Request, background_tasks: BackgroundTasks):
    """🚦 Single-Source Gateway รองรับทั้ง 2 Endpoint ป้องกันการชนกัน"""
    signature = request.headers.get("x-line-signature", "")
    body_bytes = await request.body()

    if not verify_line_signature(body_bytes, signature, LINE_CHANNEL_SECRET):
        logger.warning("🚫 [Security]: Invalid LINE Signature detected.")
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
                        "oidc_token": {"service_account_email": SERVICE_ACCOUNT_EMAIL}
                    }
                }
                client.create_task(request={"parent": parent, "task": task})
                logger.info("☁️ [Cloud Tasks]: Offloaded payload to Google Cloud Tasks successfully.")
            except Exception as e:
                logger.warning(f"⚠️ [Cloud Tasks Fallback]: Failed to queue task ({e}). Using BackgroundTasks.")
                background_tasks.add_task(process_payload_background, payload)
        else:
            background_tasks.add_task(process_payload_background, payload)

        return Response(content="OK", status_code=200)

    except Exception as e:
        logger.error(f"❌ [Webhook Gateway Error]: {e}")
        return Response(content="Error processing request", status_code=500)

@app.post("/api/v1/internal/process-task", include_in_schema=False)
async def internal_cloud_task_worker(request: Request):
    try:
        payload = await request.json()
        await process_payload_background(payload)
        return JSONResponse(content={"status": "completed"})
    except Exception as e:
        logger.error(f"❌ [Internal Task Error]: {e}")
        raise HTTPException(status_code=500, detail="Internal processing failed")

class LiffVerifyRequest(BaseModel):
    id_token: str

@app.post("/api/line/verify-liff")
async def verify_liff_user(payload: LiffVerifyRequest):
    url = "https://api.line.me/oauth2/v2.1/verify"
    data = {"id_token": payload.id_token, "client_id": LINE_LOGIN_CLIENT_ID}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=data)
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid LINE Login ID Token")
        
        user_info = response.json()
        return {
            "status": "authenticated",
            "line_user_id": user_info.get("sub"),
            "name": user_info.get("name"),
            "picture": user_info.get("picture")
        }

# ==========================================
# 🌐 6. Core Endpoints & Health Probes
# ==========================================
@app.get("/")
def root():
    return {"status": "Online", "system": "SIRINTHANATTH PRIME", "version": "5.0.0-ENTERPRISE", "mode": "Supreme"}

@app.get("/health")
async def health_check():
    db_status = "disconnected"
    if supabase:
        try:
            await asyncio.to_thread(supabase.table("prime_clients").select("id").limit(1).execute)
            db_status = "connected"
        except Exception:
            pass
            
    return {
        "status": "success",
        "system": "SIRINTHANATTH PRIME Enterprise AI SaaS",
        "database": db_status,
        "stripe": "connected" if stripe_key else "disconnected"
    }

@app.get("/wallet_menu")
def read_wallet():
    if os.path.exists("wallet_menu.html"): return FileResponse("wallet_menu.html")
    return JSONResponse(content={"status": "error", "message": "Smart Wallet layout unavailable."}, status_code=404)

@app.get("/api/user-status/{line_id}")
async def get_user_status(line_id: str):
    if not supabase: raise HTTPException(status_code=503, detail="Database Offline")
    try:
        res = await asyncio.to_thread(supabase.table("prime_clients").select("*").eq("line_user_id", line_id).execute)
        if not res.data:
            return {"tier": "GUEST", "balance": 0, "message": "ยินดีต้อนรับสู่ SIRINTHANATTH PRIME! ลงทะเบียนวันนี้เพื่อสัมผัสประสบการณ์ AI ระดับโลกครับ"}
            
        user_data = res.data[0]
        tier = user_data.get("package_tier", "ESSENTIAL").upper()
        balance = float(user_data.get("token_balance", 0.0))
        
        msg = f"ยินดีต้อนรับกลับครับ ท่านผู้บริหารระดับ {tier}"
        if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]: msg = "👑 ยินดีต้อนรับท่านประธาน! ระบบ VVIP ทำงานเต็มประสิทธิภาพพร้อมให้บริการทุกมิติครับ"
        elif tier == "ENTERPRISE" and balance < 2000: msg = "🏢 ขอแนะนำให้เติม PRIME CREDITS สำรองไว้เพื่อการทำงานที่ราบรื่นครับ"
        elif tier == "PRIME" and balance < 1000: msg = "💡 ขอแนะนำให้เติม PRIME CREDITS เพื่อรักษาสถานะการประมวลผลขั้นสูงครับ"
        elif tier == "ESSENTIAL" and balance < 500: msg = "🚀 ธุรกิจของคุณกำลังเติบโต! อัปเกรดเป็นแพ็กเกจ PRIME เพื่อปลดล็อกฟีเจอร์เพิ่มเติมครับ"
                
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
    if not supabase: raise HTTPException(status_code=503, detail="Database not available")
    
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
        return Response(content="Webhook secret missing", status_code=400)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        logger.error(f"❌ Stripe Event Parsing Error: {e}")
        return Response(content=str(e), status_code=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        client_ref = session.get('client_reference_id', '') 
        amount_paid_thb = session.get('amount_total', 0) / 100.0
        
        logger.info(f"💰 [Stripe Revenue]: ยอดชำระ {amount_paid_thb:,.2f} THB สำเร็จ! (Ref: {client_ref})")

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
                plan_name, agent_code, user_id = match.group(1), match.group(2), match.group(3)
                if plan_name in ["ESSENTIAL", "PRIME", "ENTERPRISE", "VIP"]:
                    is_subscription = True
                    package_tier = "VIP_FOUNDER" if plan_name == "VIP" else plan_name
            elif client_ref.startswith('topup_'):
                user_id = client_ref.replace('topup_', '')

            if not user_id: return

            try:
                if is_subscription:
                    bonuses = {"ESSENTIAL": 1000, "PRIME": 3000, "ENTERPRISE": 10000, "VIP_FOUNDER": 0}
                    bonus_tokens = bonuses.get(package_tier, 0)
                    if package_tier == "VIP_FOUNDER": base_tokens = 49000
                
                total_tokens_to_add = base_tokens + bonus_tokens

                res = supabase.table("prime_clients").select("token_balance").eq("line_user_id", user_id).execute()
                current_balance = float(res.data[0].get("token_balance", 0)) if res.data else 0.0
                new_balance = current_balance + total_tokens_to_add
                
                update_data = {"token_balance": new_balance}
                if is_subscription:
                    update_data["package_tier"] = package_tier
                    if package_tier in ["ENTERPRISE", "VIP_FOUNDER"]: update_data["role"] = "vip"
                
                supabase.table("prime_clients").upsert({"line_user_id": user_id, **update_data}, on_conflict="line_user_id").execute()
                
                if agent_code and agent_code != "NOAGENT":
                    commission_rate = 0.30 if package_tier == "VIP_FOUNDER" else 0.15 
                    supabase.table("affiliate_transactions").insert({
                        "agent_code": agent_code,
                        "buyer_line_id": user_id,
                        "package_bought": package_tier,
                        "amount_paid": amount_paid_thb,
                        "commission_amount": amount_paid_thb * commission_rate,
                        "status": "pending"
                    }).execute()

            except Exception as db_err:
                logger.error(f"❌ [Financial Engine Error]: {db_err}", exc_info=True)

        background_tasks.add_task(_process_financials)
        
    return Response(content="success", status_code=200)

# ==========================================
# 🚀 8. Server Ignition
# ==========================================
# เพิ่มโค้ดส่วนนี้ไว้ล่างสุดของไฟล์ main.py
if __name__ == "__main__":
    import os
    import uvicorn
    # บังคับอ่านพอร์ตจากระบบคลาวด์ ถ้าไม่มีให้ใช้ 8080
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)