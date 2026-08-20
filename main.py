import os
import logging
import stripe
import uvicorn
from typing import Optional, Dict, Any

from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

# =========================================================
# 👑 SIRINTHANATTH PRIME - Enterprise Main Server API
# =========================================================

# 1. โหลดตัวแปรสภาพแวดล้อมและตั้งค่าระบบบันทึกการทำงาน (Environment & Logger)
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SIRINTHANATTH_PRIME_CORE")

# 2. เริ่มต้นค่าคงที่และเชื่อมต่อบริการภายนอก (API Keys & Integrations)
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
MASTER_ADMIN_LINE_ID = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
CEO_LINE_ID = os.getenv("CEO_LINE_ID", MASTER_ADMIN_LINE_ID)
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

stripe_key = os.getenv("STRIPE_SECRET_KEY")
if stripe_key:
    stripe.api_key = stripe_key

# LINE Messaging API SDK Initialization
try:
    from linebot import LineBotApi, WebhookHandler
    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN) if LINE_CHANNEL_ACCESS_TOKEN else None
    handler = WebhookHandler(LINE_CHANNEL_SECRET) if LINE_CHANNEL_SECRET else None
except Exception as line_err:
    logger.warning(f"⚠️ [LINE SDK Alert]: {line_err}")
    line_bot_api = None
    handler = None

# 3. เชื่อมต่อฐานข้อมูล (Supabase Vault)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("✅ [System Database]: Supabase Vault initialized successfully.")
    except Exception as e:
        logger.error(f"❌ [System Error]: Failed to unlock Supabase Vault: {e}")

# =========================================================
# 🚀 FastAPI Initialization (Core Engine)
# =========================================================
app = FastAPI(
    title="SIRINTHANATTH PRIME Core Engine",
    description="Enterprise-grade AI SaaS supporting financial, logistics, voice AI, and heavy media workloads.",
    version="3.0.0"
)

# Security Protocols & CORS (เกราะป้องกัน)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-Provisioning & Static Files (สร้างโฟลเดอร์อัตโนมัติป้องกันเซิร์ฟเวอร์แครช)
required_directories = ["static", "static/audio", "static/images", "css", "assets", "templates"]
for directory in required_directories:
    os.makedirs(directory, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
if os.path.exists("css"):
    app.mount("/css", StaticFiles(directory="css"), name="css")
if os.path.exists("assets"):
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# =========================================================
# 🌐 Dynamic Imports (นำเข้า Modules & Routers ภายใน)
# =========================================================
# 1. นำเข้า Router ด่านหน้าสำหรับ LINE (รองรับทั้งโครงสร้างแบบสลับโฟลเดอร์)
line_router_mounted = False
try:
    from routes_line import router as line_router
    app.include_router(line_router)
    app.include_router(line_router, prefix="/api/v1/line")
    line_router_mounted = True
    logger.info("✅ [System]: LINE Webhook Router (routes_line) mounted successfully.")
except ImportError:
    try:
        from api.routes_line import router as line_router
        app.include_router(line_router)
        app.include_router(line_router, prefix="/api/v1/line")
        line_router_mounted = True
        logger.info("✅ [System]: LINE Webhook Router (api.routes_line) mounted successfully.")
    except ImportError as e:
        logger.error(f"❌ [System Error]: Failed to mount line_router -> {e}")

# 2. นำเข้าระบบจัดการภาระงาน (Task Dispatcher)
try:
    from services.task_dispatcher import task_dispatcher
except ImportError:
    try:
        from task_dispatcher import task_dispatcher
    except ImportError:
        task_dispatcher = None

# 3. นำเข้าบริการสมองกลระดับลึก (AI & Agents)
try:
    from agents.central_boss import CentralBossAgent
    from services.subscription_manager import SubscriptionManager
except ImportError:
    CentralBossAgent = None
    SubscriptionManager = None

try:
    from agents.prime_brain import generate_intelligent_response
except ImportError:
    generate_intelligent_response = None

# =========================================================
# 🌍 Frontend & Health Check Endpoints
# =========================================================
@app.get("/")
def root():
    return {"status": "Online", "system": "SIRINTHANATTH PRIME", "version": "3.0.0"}

@app.get("/health")
def health_check():
    """ตรวจสอบสถานะชีพจรของเซิร์ฟเวอร์หลัก"""
    return {
        "status": "success",
        "system": "SIRINTHANATTH PRIME Enterprise AI SaaS",
        "version": "3.0.0",
        "message": "Executive Backend engine is running smoothly and ready for workloads."
    }

@app.get("/wallet_menu")
def read_wallet():
    """Endpoint สำหรับระบบกระเป๋าเงิน (Executive Smart Wallet)"""
    if os.path.exists("wallet_menu.html"):
        return FileResponse("wallet_menu.html")
    return {"status": "error", "message": "Smart Wallet layout is currently unavailable."}

@app.get("/live-call", response_class=HTMLResponse)
async def open_live_call_room():
    """🎙️ Endpoint พิเศษ: เปิดหน้า 'ห้องโทรคุยสด' (Executive Voice Room)"""
    file_path = "templates/call_ai.html"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>System Updating. Voice Room is temporarily unavailable.</h1>"

# =========================================================
# 👑 VIP Invitation & Licensing System
# =========================================================
class InviteRequest(BaseModel):
    line_id: str
    invite_code: str

@app.post("/api/verify-invite")
async def verify_invite(req: InviteRequest):
    """ระบบลงทะเบียนคำเชิญ (Single-Use Invitation)"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not available")

    # ปลดล็อกสิทธิ์ CEO ทันทีโดยไม่ต้องใช้โค้ด
    if req.line_id == MASTER_ADMIN_LINE_ID or req.line_id == CEO_LINE_ID:
        return {
            "status": "success", 
            "role": "admin",
            "message": "ยินดีต้อนรับท่านประธาน! สิทธิ์แอดมินสูงสุดปลดล็อกแล้ว (ใช้งานฟรีไร้ขีดจำกัด)"
        }

    response = supabase.table("invite_codes").select("*").eq("code", req.invite_code).execute()
    if not response.data:
        raise HTTPException(status_code=400, detail="ไม่พบรหัสคำเชิญนี้ในระบบ กรุณาติดต่อผู้ดูแล")
        
    invite_data = response.data[0]
    
    if invite_data.get("is_used"):
        if invite_data.get("used_by_line_id") == req.line_id:
            return {"status": "success", "role": "user", "message": "ยินดีต้อนรับกลับสู่ระบบ SIRINTHANATTH PRIME"}
        else:
            raise HTTPException(
                status_code=403, 
                detail="❌ รหัสคำเชิญนี้ถูกใช้งานโดยบุคคลอื่นไปแล้ว ไม่อนุญาตให้ใช้ซ้ำ"
            )
            
    # อัปเดตสถานะการใช้โค้ดและสร้างบัญชีผู้ใช้
    supabase.table("invite_codes").update({
        "is_used": True,
        "used_by_line_id": req.line_id
    }).eq("code", req.invite_code).execute()
    
    supabase.table("prime_clients").upsert({
        "line_user_id": req.line_id,
        "role": "user",
        "token_balance": 0.00
    }, on_conflict="line_user_id").execute()
    
    return {
        "status": "success", 
        "role": "user",
        "message": "ยืนยันรหัสเชิญสำเร็จ! เปิดสิทธิ์การใช้งานระบบให้คุณเรียบร้อยแล้ว"
    }

# =========================================================
# ⚙️ Core Execution Engine
# =========================================================
class ExecutionRequest(BaseModel):
    user_id: str
    task_type: str
    payload: Dict[str, Any]

@app.post("/api/v1/execute")
async def execute_task(request_data: ExecutionRequest):
    """ท่อประมวลผลหลัก รองรับงานหนักเอกสาร, ภาพ, เสียง และวิดีโอ"""
    try:
        # ระบบตัดเครดิต (Wallet Control System)
        if supabase and request_data.user_id != MASTER_ADMIN_LINE_ID and request_data.user_id != CEO_LINE_ID:
            client_res = supabase.table("prime_clients").select("token_balance, role").eq("line_user_id", request_data.user_id).execute()
            if not client_res.data:
                raise HTTPException(status_code=403, detail="กรุณาลงทะเบียนผ่านรหัสคำเชิญก่อนใช้งานระบบ")
            
            client_info = client_res.data[0]
            if client_info.get("role") != "admin" and float(client_info.get("token_balance", 0)) <= 0:
                raise HTTPException(status_code=402, detail="ทรัพยากร (PRIME CREDITS) คงเหลือไม่เพียงพอ กรุณาอัปเกรดแพ็กเกจ")

        if task_dispatcher:
            dispatch_result = await task_dispatcher.route_and_execute(
                task_type=request_data.task_type,
                payload=request_data.payload
            )
            if not dispatch_result.get("success"):
                raise HTTPException(status_code=500, detail=dispatch_result.get("error", "Task execution failed"))

            return {
                "status": "success",
                "user_id": request_data.user_id,
                "execution_info": dispatch_result.get("result")
            }
        else:
            return {"status": "success", "message": "Mock execution completed", "payload": request_data.payload}

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"❌ API Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# =========================================================
# 🔄 Profile Synchronization System
# =========================================================
class UserProfile(BaseModel):
    line_user_id: str
    display_name: str
    picture_url: str

@app.post("/api/sync-user")
async def sync_user_profile(profile: UserProfile):
    """เชื่อมต่อข้อมูลผู้ใช้งานจาก LINE เข้าระบบฐานข้อมูล"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not available")
        
    try:
        supabase.table("users").upsert({
            "line_user_id": profile.line_user_id,
            "display_name": profile.display_name,
            "picture_url": profile.picture_url,
            "status": "active"
        }, on_conflict="line_user_id").execute()
        
        logger.info(f"🔄 [Sync System]: User profile ({profile.display_name}) securely synced.")
        return {"status": "success", "message": "ซิงค์ข้อมูลผู้ใช้สำเร็จ"}
        
    except Exception as e:
        logger.error(f"❌ [Sync System Error]: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =========================================================
# 💳 Stripe Webhook Endpoint (ระบบรับชำระเงินอัตโนมัติ)
# =========================================================
@app.post("/api/stripe-webhook")
async def stripe_webhook(request: Request):
    """ระบบรับการแจ้งเตือนการชำระเงินสำเร็จจาก Stripe"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("⚠️ STRIPE_WEBHOOK_SECRET ไม่ได้ถูกตั้งค่าใน .env")
        return {"status": "error", "message": "Webhook secret missing"}

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        logger.error(f"❌ Stripe Webhook Signature Error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        client_ref = session.get('client_reference_id', '')
        logger.info(f"💳 [Stripe Payment Verified]: Ref = {client_ref}")

    return {"status": "success"}

# =========================================================
# 🚀 Server Ignition (จุดสตาร์ทเครื่องยนต์สำหรับ Cloud Run)
# =========================================================
if __name__ == "__main__":
    # บังคับให้รับค่าพอร์ตจาก Google Cloud Run อย่างสมบูรณ์แบบ
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 IGNITING SIRINTHANATTH PRIME ENGINE ON PORT {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)