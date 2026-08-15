import os
import logging
import stripe
import uvicorn
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Optional, Dict, Any
from supabase import create_client, Client
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, AudioMessage, ImageMessage, 
    VideoMessage, FileMessage, TextSendMessage, AudioSendMessage, ImageSendMessage, VideoSendMessage, FileSendMessage
)

# =========================================================
# 👑 SIRINTHANATTH PRIME - Enterprise Main Server API
# =========================================================

app = FastAPI(
    title="SIRINTHANATTH PRIME Backend API",
    description="Enterprise-grade AI SaaS supporting financial, logistics, voice AI, and heavy media workloads.",
    version="3.0.0" # อัปเกรดเวอร์ชันตามสถาปัตยกรรมใหม่
)

# 🌐 นำเข้า Router ด่านหน้า (รองรับทั้งไฟล์ภาพ, เสียง, วิดีโอ 4K)
from api.routes_line import router as line_router
app.include_router(line_router)

# Import ระบบจัดการภาระงาน (Task Dispatcher)
try:
    from services.task_dispatcher import task_dispatcher
except ImportError:
    try:
        from task_dispatcher import task_dispatcher
    except ImportError:
        task_dispatcher = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SIRINTHANATTH_PRIME_CORE")

# นำเข้าบริการสมองกลระดับลึก
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

load_dotenv()

# ==========================================
# 1. Security Protocols & CORS (เกราะป้องกัน)
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 2. Database & External APIs Initialization
# ==========================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")

supabase: Client = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("✅ [System Database]: Supabase Vault initialized successfully.")
    except Exception as e:
        logger.error(f"❌ [System Error]: Failed to unlock Supabase Vault: {e}")

# กำหนดสิทธิ์ผู้บริหารสูงสุด (Master Admin)
MASTER_ADMIN_LINE_ID = os.environ.get("MASTER_ADMIN_LINE_ID", "U1234567890abcdef...")

# ตั้งค่า Payment Gateway
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

# ==========================================
# 3. Static Files & Frontend Endpoints (ระบบจัดการหน้าเว็บ)
# ==========================================
# อนุญาตให้ระบบแจกจ่ายไฟล์ภาพ เสียง และวิดีโอ 4K ได้อย่างปลอดภัย
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
if os.path.exists("css"):
    app.mount("/css", StaticFiles(directory="css"), name="css")
if os.path.exists("assets"):
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

@app.get("/")
def health_check():
    """ตรวจสอบสถานะชีพจรของเซิร์ฟเวอร์หลัก"""
    return {
        "status": "success",
        "system": "SIRINTHANATTH PRIME Enterprise AI SaaS",
        "version": "3.0.0",
        "message": "Executive Backend engine is running smoothly and ready for workloads."
    }

# Endpoint เปิดหน้าแผงควบคุมระบบ (Dashboard)
def read_index():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"status": "online", "system": "SIRINTHANATTH PRIME API Engine"}

# Endpoint สำหรับระบบกระเป๋าเงิน (Executive Smart Wallet)
@app.get("/wallet_menu")
def read_wallet():
    if os.path.exists("wallet_menu.html"):
        return FileResponse("wallet_menu.html")
    return {"status": "error", "message": "Smart Wallet layout is currently unavailable."}

# 🎙️ Endpoint พิเศษ: สำหรับเปิดหน้า "ห้องโทรคุยสด (Executive Voice Room)"
@app.get("/live-call", response_class=HTMLResponse)
async def open_live_call_room():
    """เปิดหน้าต่าง LIFF สำหรับคุยสดกับ AI (ธนัตถ์ / สิรินทร์ ไพรม์)"""
    file_path = "templates/call_ai.html"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>System Updating. Voice Room is temporarily unavailable.</h1>"

# ==========================================
# 4. VIP Invitation & Licensing System
# ==========================================
class InviteRequest(BaseModel):
    line_id: str
    invite_code: str

@app.post("/api/verify-invite")
async def verify_invite(req: InviteRequest):
    """ระบบลงทะเบียนคำเชิญ (Single-Use Invitation)"""
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not available")

    # 👑 ปลดล็อกสิทธิ์ CEO ทันทีโดยไม่ต้องใช้โค้ด
    if req.line_id == MASTER_ADMIN_LINE_ID:
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

# ==========================================
# 5. Core Execution Engine
# ==========================================
class ExecutionRequest(BaseModel):
    user_id: str
    task_type: str
    payload: Dict[str, Any]

@app.post("/api/v1/execute")
async def execute_task(request_data: ExecutionRequest):
    """ท่อประมวลผลหลัก รองรับงานหนักเอกสาร, ภาพ, เสียง และวิดีโอ"""
    try:
        # ระบบตัดเครดิต (Wallet Control System)
        if supabase and request_data.user_id != MASTER_ADMIN_LINE_ID:
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

# ==========================================
# 6. Profile Synchronization System
# ==========================================
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 IGNITING SIRINTHANATTH PRIME ENGINE ON PORT {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)