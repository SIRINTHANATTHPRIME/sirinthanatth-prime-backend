import os
import logging
import stripe
import uvicorn
import asyncio
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

# 2. เชื่อมต่อฐานข้อมูล (Supabase Vault - ระบบจัดการข้อมูล VVIP)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("✅ [System Database]: Supabase Vault initialized successfully.")
    except Exception as e:
        logger.error(f"❌ [System Critical Error]: Failed to unlock Supabase Vault: {e}")

# =========================================================
# 🚀 Lifespan Architecture & FastAPI Initialization
# =========================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """กระบวนการ Boot & Shutdown ของเซิร์ฟเวอร์แบบมาตรฐาน Enterprise (Zero Downtime)"""
    logger.info("🚀 [System Ignition]: Booting SIRINTHANATTH PRIME Core Engine...")
    
    # Auto-Provisioning: สร้างโฟลเดอร์อัตโนมัติป้องกันเซิร์ฟเวอร์แครช
    required_directories = ["static", "static/audio", "static/images", "css", "assets", "templates"]
    for directory in required_directories:
        os.makedirs(directory, exist_ok=True)
        
    yield # เซิร์ฟเวอร์กำลังทำงาน...
    
    logger.info("🛑 [System Shutdown]: Gracefully shutting down services. Saving states...")

app = FastAPI(
    title="SIRINTHANATTH PRIME Core Engine",
    description="Enterprise-grade AI SaaS supporting financial, logistics, voice AI, and heavy media workloads.",
    version="4.0.0", # อัปเกรดเวอร์ชันสูงสุดระดับโลก
    lifespan=lifespan
)

# 🛡️ Security Protocols & CORS (เปิดรับหน้าเว็บ Agent สำหรับดึงข้อมูล)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """เพิ่มเกราะป้องกัน Clickjacking, MIME Sniffing และ XSS (Cybersecurity Shield)"""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# การจัดการ Static Files อย่างมีประสิทธิภาพ
app.mount("/static", StaticFiles(directory="static"), name="static")
if os.path.exists("css"): app.mount("/css", StaticFiles(directory="css"), name="css")
if os.path.exists("assets"): app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# =========================================================
# 🌐 Dynamic Imports (นำเข้า Modules & Routers อย่างปลอดภัย)
# =========================================================
try:
    from api.routes_line import router as line_router
    app.include_router(line_router) 
    app.include_router(line_router, prefix="/api/v1/line", tags=["LINE OA"])
    logger.info("✅ [System]: LINE Webhook Router mounted successfully.")
except Exception as e:
    logger.error(f"❌ [System Error]: Failed to mount line_router. Fallback mode activated -> {e}")

try:
    from api.routes_stats import router as stats_router
    app.include_router(stats_router, prefix="/api/v1/stats", tags=["Statistics"])
    logger.info("✅ [System]: Stats Router mounted successfully.")
except Exception as e:
    logger.warning(f"⚠️ [System Warning]: Stats Router not found or skipped -> {e}")

# =========================================================
# 🌍 Frontend & Health Check Endpoints
# =========================================================
@app.get("/")
def root():
    return {"status": "Online", "system": "SIRINTHANATTH PRIME", "version": "4.0.0", "mode": "Enterprise"}

@app.get("/health")
def health_check():
    """ตรวจสอบสถานะชีพจรของเซิร์ฟเวอร์หลัก (Load Balancer Health Check)"""
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

# =========================================================
# 🧠 Psychological LIFF API (ระบบสื่อสารเชิงจิตวิทยาให้หน้าเว็บ LIFF)
# =========================================================
@app.get("/api/user-status/{line_id}")
async def get_user_status(line_id: str):
    """API สำหรับหน้าเว็บ Smart Wallet เพื่อดึง Tier และ Token พร้อมข้อความเชิงจิตวิทยา (Predictive Empathy)"""
    if not supabase: raise HTTPException(status_code=500, detail="Database Error")
    
    try:
        res = await asyncio.to_thread(supabase.table("prime_clients").select("*").eq("line_user_id", line_id).execute)
        if not res.data:
            return {"tier": "GUEST", "balance": 0, "message": "ยินดีต้อนรับสู่ SIRINTHANATTH PRIME! ลงทะเบียนวันนี้เพื่อสัมผัสประสบการณ์ AI ระดับโลกครับ"}
            
        user_data = res.data[0]
        tier = user_data.get("package_tier", "ESSENTIAL").upper()
        balance = float(user_data.get("token_balance", 0.0))
        
        # 💎 กฎจิตวิทยาการแจ้งเตือนและการ Upsell (Psychological Hook)
        msg = f"ยินดีต้อนรับกลับครับ ท่านผู้บริหารระดับ {tier}"
        
        if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]:
            msg = "👑 ยินดีต้อนรับท่านประธาน! ระบบ 100VIP ทำงานเต็มประสิทธิภาพพร้อมให้บริการทุกมิติครับ"
        elif tier == "ENTERPRISE":
            if balance < 2000:
                msg = "🏢 ท่านผู้บริหารครับ เพื่อให้ระบบ Big Data และขนส่งดำเนินไปอย่างราบรื่น ขอแนะนำให้ฝ่ายบัญชีเติม PRIME CREDITS สำรองไว้ครับ"
        elif tier == "PRIME":
            if balance < 1000:
                msg = "💡 เพื่อให้การวิเคราะห์กลยุทธ์ธุรกิจและสื่อ 4K ดำเนินไปอย่างต่อเนื่องไร้รอยต่อ ขออนุญาตแนะนำให้เติม PRIME CREDITS ครับ"
        elif tier == "ESSENTIAL":
            if balance < 500:
                msg = "🚀 ธุรกิจของคุณกำลังเติบโต! อัปเกรดเป็นแพ็กเกจ PRIME วันนี้ เพื่อปลดล็อกที่ปรึกษาเชิงลึกระดับ CFO และ CTO ได้ทันทีครับ"
            else:
                msg = "✨ ยินดีต้อนรับครับ! หากต้องการยกระดับธุรกิจ อัปเกรดเป็นแพ็กเกจ PRIME หรือ ENTERPRISE เพื่อรับสิทธิพิเศษขั้นสูงสุดได้เสมอครับ"
                
        return {"tier": tier, "balance": balance, "message": msg}
    except Exception as e:
        logger.error(f"Error fetching user status: {e}")
        return {"tier": "ERROR", "balance": 0, "message": "ระบบกำลังปรับปรุงข้อมูลชั่วคราวครับ"}

# =========================================================
# 🔄 Profile Synchronization System
# =========================================================
class UserProfile(BaseModel):
    line_user_id: str
    display_name: str
    picture_url: str

@app.post("/api/sync-user")
async def sync_user_profile(profile: UserProfile, background_tasks: BackgroundTasks):
    """อัปเดตข้อมูลโปรไฟล์ผู้ใช้ล่าสุดเข้าฐานข้อมูล (Non-Blocking via BackgroundTasks)"""
    if not supabase: raise HTTPException(status_code=500, detail="Database not available")
    
    def _sync():
        try:
            supabase.table("users").upsert({
                "line_user_id": profile.line_user_id,
                "display_name": profile.display_name,
                "picture_url": profile.picture_url,
                "status": "active"
            }, on_conflict="line_user_id").execute()
            logger.info(f"🔄 [Sync System]: User profile ({profile.display_name}) securely synced.")
        except Exception as err:
            logger.error(f"❌ [Sync System DB Error]: {err}")

    # โยนเข้า Background Tasks เพื่อให้ API ตอบกลับเร็วที่สุด
    background_tasks.add_task(_sync)
    return {"status": "success", "message": "ซิงค์ข้อมูลผู้ใช้สำเร็จ"}

# =========================================================
# 💳 Automated Stripe Revenue & Tokenomics Engine
# =========================================================
@app.post("/api/stripe-webhook")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    💰 ระบบบริหารการเงินหลังบ้าน: ตัดจ่าย Token, คำนวณ Tier และบันทึก Commission
    *อัปเกรด: ใช้ BackgroundTasks เพื่อป้องกัน Stripe Timeout อย่างสมบูรณ์แบบ*
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not STRIPE_WEBHOOK_SECRET:
        logger.warning("⚠️ STRIPE_WEBHOOK_SECRET is missing. Rejecting webhook.")
        return Response(content="Webhook secret missing", status_code=400)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        logger.error("❌ Stripe Signature Invalid!")
        return Response(content="Invalid signature", status_code=400)
    except Exception as e:
        return Response(content=str(e), status_code=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        client_ref = session.get('client_reference_id', '') # รูปแบบ: PLAN_AGENT_CODE_LINE_USERID
        amount_paid_thb = session.get('amount_total', 0) / 100 
        
        logger.info(f"💰 [Stripe Revenue]: ยอดชำระ {amount_paid_thb} THB สำเร็จ! (Ref: {client_ref})")

        # ฟังก์ชันทำงานหลังบ้านเพื่อคุมกำไร (Tokenomics) และแบ่งคอมมิชชัน
        def _process_financials():
            if not supabase or not client_ref: return
            
            user_id = ""
            agent_code = "NOAGENT"
            package_tier = "ESSENTIAL"
            is_subscription = False
            base_tokens = amount_paid_thb * 10 # อัตราแลกเปลี่ยนคลาวด์พื้นฐาน 1 ฿ = 10 Credits
            bonus_tokens = 0
            
            # 1. 🔍 ถอดรหัส Payload (Data Extraction)
            if "_LINE_" in client_ref:
                parts = client_ref.split("_LINE_")
                user_id = parts[1]
                prefix_parts = parts[0].split("_AGENT_")
                plan_name = prefix_parts[0].upper()
                
                if len(prefix_parts) > 1:
                    agent_code = prefix_parts[1]
                
                if plan_name in ["ESSENTIAL", "PRIME", "ENTERPRISE", "VIP"]:
                    is_subscription = True
                    package_tier = plan_name if plan_name != "VIP" else "VIP_FOUNDER"
            elif client_ref.startswith('topup_'):
                user_id = client_ref.replace('topup_', '') # กรณีซื้อ Token เปล่าๆ

            if not user_id: return

            try:
                # 2. 🧮 คำนวณ Tokenomics (บริหารให้ได้กำไรสูงสุด ไม่ขาดทุน)
                if is_subscription:
                    if package_tier == "ESSENTIAL": bonus_tokens = 1000
                    elif package_tier == "PRIME": bonus_tokens = 3000
                    elif package_tier == "ENTERPRISE": bonus_tokens = 10000
                    elif package_tier == "VIP_FOUNDER": base_tokens = 49000; bonus_tokens = 0 # Fix Token สำหรับ VIP
                
                total_tokens_to_add = base_tokens + bonus_tokens

                # 3. 🏦 อัปเดตสมุดบัญชีลูกค้า (Update Wallet)
                res = supabase.table("prime_clients").select("token_balance").eq("line_user_id", user_id).execute()
                current_balance = float(res.data[0].get("token_balance", 0)) if res.data else 0.0
                new_balance = current_balance + total_tokens_to_add
                
                update_data = {"token_balance": new_balance}
                if is_subscription:
                    update_data["package_tier"] = package_tier
                    # อัปเกรด Role สำหรับการเข้าถึงคำสั่ง VVIP
                    if package_tier in ["ENTERPRISE", "VIP_FOUNDER"]: update_data["role"] = "vip"
                
                supabase.table("prime_clients").upsert({"line_user_id": user_id, **update_data}, on_conflict="line_user_id").execute()
                logger.info(f"✅ [Financial Engine]: อัปเดตบัญชี {user_id} เป็นระดับ {package_tier} รับ {total_tokens_to_add} Credits")

                # 4. 🤝 ระบบคำนวณ Commission พันธมิตร (Affiliate Split)
                if agent_code and agent_code != "NOAGENT":
                    # โบนัส 30% สำหรับ 100 VIP, เรทปกติ 15%
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
                logger.error(f"❌ [Financial Engine Error]: {db_err}")

        # ⚡ โยนเข้า Background Tasks ของ FastAPI เพื่อให้ Stripe ได้รับ 200 OK ทันที (ป้องกัน Timeout)
        background_tasks.add_task(_process_financials)

    return {"status": "success"}

# =========================================================
# 🚀 Server Ignition (จุดสตาร์ทเครื่องยนต์ Cloud Run)
# =========================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 IGNITING SIRINTHANATTH PRIME CORE ENGINE ON PORT {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)