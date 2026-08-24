import os
import logging
import stripe
import uvicorn
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

# =========================================================
# 👑 SIRINTHANATTH PRIME - Enterprise Main Server API
# =========================================================

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SIRINTHANATTH_PRIME_CORE")

# 1. โหลดตัวแปรสภาพแวดล้อม (Environment & API Keys)
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
MASTER_ADMIN_LINE_ID = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
CEO_LINE_ID = os.getenv("CEO_LINE_ID", MASTER_ADMIN_LINE_ID)
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

stripe_key = os.getenv("STRIPE_SECRET_KEY")
if stripe_key:
    stripe.api_key = stripe_key

# 2. เชื่อมต่อฐานข้อมูล (Supabase Vault)
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
# 🚀 Lifespan Architecture & FastAPI Initialization
# =========================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """กระบวนการ Boot & Shutdown ของเซิร์ฟเวอร์แบบมาตรฐาน Enterprise"""
    logger.info("🚀 [System Ignition]: Booting SIRINTHANATTH PRIME Core Engine...")
    
    # Auto-Provisioning: สร้างโฟลเดอร์อัตโนมัติป้องกันเซิร์ฟเวอร์แครช
    required_directories = ["static", "static/audio", "static/images", "css", "assets", "templates"]
    for directory in required_directories:
        os.makedirs(directory, exist_ok=True)
        
    yield # เซิร์ฟเวอร์กำลังทำงาน...
    
    logger.info("🛑 [System Shutdown]: Gracefully shutting down services...")

app = FastAPI(
    title="SIRINTHANATTH PRIME Core Engine",
    description="Enterprise-grade AI SaaS supporting financial, logistics, voice AI, and heavy media workloads.",
    version="3.0.1",
    lifespan=lifespan
)

# 🛡️ Security Protocols & CORS (เกราะป้องกันขั้นสูง)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """เพิ่มเกราะป้องกัน Clickjacking และ MIME Sniffing"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

# การจัดการ Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")
if os.path.exists("css"): app.mount("/css", StaticFiles(directory="css"), name="css")
if os.path.exists("assets"): app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# =========================================================
# 🌐 Dynamic Imports (นำเข้า Modules & Routers ภายใน)
# =========================================================
try:
    from api.routes_line import router as line_router
    app.include_router(line_router) # Mount ที่ Root
    app.include_router(line_router, prefix="/api/v1/line") # Mount ที่ API v1
    logger.info("✅ [System]: LINE Webhook Router mounted successfully.")
except ImportError as e:
    logger.error(f"❌ [System Error]: Failed to mount line_router -> {e}")

try: from services.task_dispatcher import HybridTaskDispatcher; task_dispatcher = HybridTaskDispatcher()
except ImportError:
    try: from task_dispatcher import HybridTaskDispatcher; task_dispatcher = HybridTaskDispatcher()
    except ImportError: task_dispatcher = None

# =========================================================
# 🌍 Frontend & Health Check Endpoints
# =========================================================
@app.get("/")
def root():
    return {"status": "Online", "system": "SIRINTHANATTH PRIME", "version": "3.0.1"}

@app.get("/health")
def health_check():
    """ตรวจสอบสถานะชีพจรของเซิร์ฟเวอร์หลัก (Load Balancer Health Check)"""
    return {
        "status": "success",
        "system": "SIRINTHANATTH PRIME Enterprise AI SaaS",
        "database": "connected" if supabase else "disconnected",
        "message": "Executive Backend engine is running smoothly."
    }

@app.get("/wallet_menu")
def read_wallet():
    if os.path.exists("wallet_menu.html"): return FileResponse("wallet_menu.html")
    return {"status": "error", "message": "Smart Wallet layout is currently unavailable."}

@app.get("/live-call", response_class=HTMLResponse)
async def open_live_call_room():
    if os.path.exists("templates/call_ai.html"):
        with open("templates/call_ai.html", "r", encoding="utf-8") as f: return f.read()
    return "<h1>System Updating. Voice Room is temporarily unavailable.</h1>"

# =========================================================
# 👑 VIP Invitation & Licensing System (Pydantic V2 Strict)
# =========================================================
class InviteRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    line_id: str = Field(..., min_length=1)
    invite_code: str = Field(..., min_length=1)

@app.post("/api/verify-invite")
async def verify_invite(req: InviteRequest):
    """ระบบลงทะเบียนคำเชิญ (Single-Use Invitation)"""
    if not supabase: raise HTTPException(status_code=500, detail="Database connection not available")

    # 👑 ปลดล็อกสิทธิ์ CEO ทันทีโดยไม่ต้องใช้โค้ด
    if req.line_id in [MASTER_ADMIN_LINE_ID, CEO_LINE_ID]:
        return {"status": "success", "role": "admin", "message": "ยินดีต้อนรับท่านประธาน! สิทธิ์ผู้ดูแลระบบสูงสุดทำงานเต็มรูปแบบ"}

    response = supabase.table("invite_codes").select("*").eq("code", req.invite_code).execute()
    if not response.data: raise HTTPException(status_code=400, detail="ไม่พบรหัสคำเชิญนี้ในระบบ กรุณาติดต่อผู้ดูแล")
        
    invite_data = response.data[0]
    
    if invite_data.get("is_used"):
        if invite_data.get("used_by_line_id") == req.line_id:
            return {"status": "success", "role": "user", "message": "ยินดีต้อนรับกลับสู่ระบบ SIRINTHANATTH PRIME"}
        raise HTTPException(status_code=403, detail="❌ รหัสคำเชิญนี้ถูกใช้งานโดยบุคคลอื่นไปแล้ว ไม่อนุญาตให้ใช้ซ้ำ")
            
    # อัปเดตสถานะโค้ดแบบรัดกุม
    supabase.table("invite_codes").update({"is_used": True, "used_by_line_id": req.line_id}).eq("code", req.invite_code).execute()
    
    # เปิดบัญชีผู้ใช้ใหม่
    supabase.table("prime_clients").upsert({"line_user_id": req.line_id, "role": "user", "token_balance": 0.00}, on_conflict="line_user_id").execute()
    
    return {"status": "success", "role": "user", "message": "ยืนยันรหัสเชิญสำเร็จ! เปิดสิทธิ์การใช้งานระบบให้คุณเรียบร้อยแล้ว"}

# =========================================================
# ⚙️ Core Execution Engine
# =========================================================
class ExecutionRequest(BaseModel):
    user_id: str
    task_type: str
    payload: Dict[str, Any]

@app.post("/api/v1/execute")
async def execute_task(request_data: ExecutionRequest):
    """ท่อประมวลผลหลัก รองรับงานหนักเอกสาร, ภาพ, เสียง และวิดีโอ (Hybrid Dispatcher)"""
    try:
        if supabase and request_data.user_id not in [MASTER_ADMIN_LINE_ID, CEO_LINE_ID]:
            client_res = supabase.table("prime_clients").select("token_balance, role").eq("line_user_id", request_data.user_id).execute()
            if not client_res.data:
                raise HTTPException(status_code=403, detail="กรุณาลงทะเบียนหรือรับสิทธิ์ใช้งานระบบก่อนเข้าถึงฟังก์ชันนี้")
            
            client_info = client_res.data[0]
            if client_info.get("role") != "admin" and float(client_info.get("token_balance", 0)) <= 0:
                raise HTTPException(status_code=402, detail="PRIME CREDITS คงเหลือไม่เพียงพอ กรุณาอัปเกรดแพ็กเกจ")

        if task_dispatcher:
            dispatch_result = await task_dispatcher.route_and_execute(task_type=request_data.task_type, payload=request_data.payload)
            if dispatch_result.get("status") == "error":
                raise HTTPException(status_code=500, detail=dispatch_result.get("message", "Task execution failed"))
            return {"status": "success", "user_id": request_data.user_id, "execution_info": dispatch_result}
        else:
            return {"status": "success", "message": "System routing offline. Mock completed.", "payload": request_data.payload}

    except HTTPException as he: raise he
    except Exception as e:
        logger.error(f"❌ API Exception: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error during execution")

# =========================================================
# 🔄 Profile Synchronization System
# =========================================================
class UserProfile(BaseModel):
    line_user_id: str
    display_name: str
    picture_url: str

@app.post("/api/sync-user")
async def sync_user_profile(profile: UserProfile):
    """อัปเดตข้อมูลโปรไฟล์ผู้ใช้ล่าสุดเข้าฐานข้อมูล"""
    if not supabase: raise HTTPException(status_code=500, detail="Database connection not available")
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
# 💳 Automated Stripe Revenue Engine (ระบบรับเงินและเติม Token อัตโนมัติ)
# =========================================================
@app.post("/api/stripe-webhook")
async def stripe_webhook(request: Request):
    """แจ้งเตือนจาก Stripe และอัปเดตฐานข้อมูลการเงินให้อัตโนมัติ 100%"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("⚠️ STRIPE_WEBHOOK_SECRET ไม่ได้ถูกตั้งค่า การเชื่อมต่อถูกปฏิเสธ")
        return Response(content="Webhook secret missing", status_code=400)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"❌ Stripe Signature Error: {e}")
        return Response(content="Invalid signature", status_code=400)
    except Exception as e:
        logger.error(f"❌ Stripe Webhook Error: {e}")
        return Response(content=str(e), status_code=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        client_ref = session.get('client_reference_id', '')
        amount_paid_thb = session.get('amount_total', 0) / 100 # ค่าที่ส่งมาเป็นหน่วยสตางค์
        
        logger.info(f"💰 [Stripe Incoming]: ยอดชำระ {amount_paid_thb} THB สำเร็จ! (Ref: {client_ref})")

        # 🌟 ฟังก์ชันเติม Token เข้ากระเป๋าลูกค้าอัตโนมัติ (1 THB = 10 Credits)
        if supabase and client_ref:
            if client_ref.startswith('topup_'):
                user_id = client_ref.replace('topup_', '')
                credits_to_add = amount_paid_thb * 10
                
                # ดึงยอดเดิม และบวกยอดใหม่เข้าไป
                try:
                    res = supabase.table("users_wallet").select("balance").eq("user_id", user_id).execute()
                    current_balance = float(res.data[0].get("balance", 0)) if res.data else 0.0
                    new_balance = current_balance + credits_to_add
                    
                    supabase.table("users_wallet").upsert({"user_id": user_id, "balance": new_balance}, on_conflict="user_id").execute()
                    
                    # อัปเดตในตารางหลักด้วย
                    supabase.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                    logger.info(f"✅ [Revenue Engine]: เติม {credits_to_add} Credits ให้ผู้ใช้ {user_id} สำเร็จ!")
                except Exception as db_err:
                    logger.error(f"❌ [DB Topup Error]: ไม่สามารถเติมเครดิตได้ -> {db_err}")

            elif client_ref.startswith('sub_') or 'VIP' in client_ref:
                # กรณีสมัครแพ็กเกจ (เช่น VIP) ให้เปลี่ยนสถานะเป็น Token Exempt (ฟรีไม่อั้น)
                user_id = client_ref.split("_")[-1] # ดึง user_id ออกมาจากรูปแบบ sub_{user_id} หรือ VIP-XX_AGENT_XX
                try:
                    supabase.table("users").update({"is_token_exempt": True}).eq("line_user_id", user_id).execute()
                    supabase.table("prime_clients").update({"role": "vip"}).eq("line_user_id", user_id).execute()
                    logger.info(f"👑 [Revenue Engine]: อัปเกรดสถานะ VVIP ให้ผู้ใช้ {user_id} สำเร็จ!")
                except Exception as db_err:
                    logger.error(f"❌ [DB Upgrade Error]: ไม่สามารถอัปเกรด VVIP ได้ -> {db_err}")

    return {"status": "success"}

# =========================================================
# 🚀 Server Ignition (จุดสตาร์ทเครื่องยนต์ Cloud Run)
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 IGNITING SIRINTHANATTH PRIME CORE ENGINE ON PORT {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)