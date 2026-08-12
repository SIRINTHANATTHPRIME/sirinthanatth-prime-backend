import os
import logging
import stripe
import uvicorn
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Header
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from typing import Optional, Dict, Any
from supabase import create_client, Client

# 🌐 นำเข้า Router (ด่านหน้า) จากโฟลเดอร์ api
from api.routes_line import router as line_router


# Import ตัวสลับท่อ Hybrid Switching
try:
    from services.task_dispatcher import task_dispatcher
except ImportError:
    try:
        from task_dispatcher import task_dispatcher
    except ImportError:
        task_dispatcher = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SIRINTHANATTH_PRIME_MAIN")

# นำเข้าบริการภายในของเรา (เพิ่ม Prime Brain เข้ามา)
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

app = FastAPI(
    title="SIRINTHANATTH PRIME Backend API",
    description="Enterprise-grade AI SaaS supporting financial, logistics, and heavy media workloads.",
    version="2.0.0"
)

app.include_router(line_router)

# ==========================================
# 1. CORS & Security
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 2. Database & External Clients Setup
# ==========================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")

supabase: Client = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("✅ Supabase Client initialized successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase: {e}")

# กำหนด LINE ID ของ Master Admin (คุณวีระชัย ใช้ฟรีตลอดชีพ ไม่หัก Token)
MASTER_ADMIN_LINE_ID = os.environ.get("MASTER_ADMIN_LINE_ID", "U1234567890abcdef...")

# ตั้งค่า Stripe Payment
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

# ตั้งค่า LINE Bot API
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(LINE_CHANNEL_SECRET)

# ==========================================
# 3. Static Files & Frontend Mount
# ==========================================
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
if os.path.exists("css"):
    app.mount("/css", StaticFiles(directory="css"), name="css")
if os.path.exists("assets"):
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

@app.get("/")
def read_index():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"status": "online", "system": "SIRINTHANATTH PRIME API Engine"}

@app.get("/agent")
def read_agent():
    if os.path.exists("agent.html"):
        return FileResponse("agent.html")
    return {"status": "online", "page": "Agent Dashboard"}

@app.get("/wallet_menu")
def read_wallet():
    if os.path.exists("wallet_menu.html"):
        return FileResponse("wallet_menu.html")
    return {"status": "online", "page": "Smart Wallet"}

# ==========================================
# 4. Single-Use Invite Link & Admin Verification
# ==========================================
class InviteRequest(BaseModel):
    line_id: str
    invite_code: str

@app.post("/api/verify-invite")
async def verify_invite(req: InviteRequest):
    """
    ระบบตรวจสอบรหัสคำเชิญแบบใช้ได้ครั้งเดียว (Single-Use) 
    และป้องกันการแอบส่งต่อลิงก์ พร้อมปลดล็อกสิทธิ์ Master Admin ให้คุณวีระชัย
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Database connection not available")

    # 1. เช็กว่าเป็นบัญชี Master Admin หรือไม่ (ปลดล็อกสิทธิ์สูงสุดทันที)
    if req.line_id == MASTER_ADMIN_LINE_ID:
        return {
            "status": "success", 
            "role": "admin",
            "message": "ยินดีต้อนรับท่านประธาน CEO! สิทธิ์แอดมินสูงสุดปลดล็อกแล้ว (ใช้งานฟรีไร้ขีดจำกัด)"
        }

    # 2. ค้นหารหัสคำเชิญในตาราง invite_codes
    response = supabase.table("invite_codes").select("*").eq("code", req.invite_code).execute()
    
    if not response.data:
        raise HTTPException(status_code=400, detail="ไม่พบรหัสคำเชิญนี้ในระบบ กรุณาติดต่อผู้ดูแลระบบ")
        
    invite_data = response.data[0]
    
    # 3. ตรวจสอบว่ารหัสถูกใช้งานไปแล้วหรือยัง
    if invite_data.get("is_used"):
        if invite_data.get("used_by_line_id") == req.line_id:
            return {"status": "success", "role": "user", "message": "ยินดีต้อนรับกลับสู่ระบบ SIRINTHANATTH PRIME"}
        else:
            raise HTTPException(
                status_code=403, 
                detail="❌ รหัสคำเชิญนี้ถูกใช้งานโดยบุคคลอื่นไปแล้ว! ไม่อนุญาตให้นำลิงก์มาส่งต่อ"
            )
            
    # 4. ถ้ารหัสยังไม่เคยถูกใช้ ให้ทำการผูกมัด (Bind) กับ LINE ID นี้ทันที
    supabase.table("invite_codes").update({
        "is_used": True,
        "used_by_line_id": req.line_id
    }).eq("code", req.invite_code).execute()
    
    # 5. ลงทะเบียนผู้ใช้ใหม่ลงในตาราง prime_clients (ตั้งต้น Wallet ที่ 0.00 บาท)
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
# 5. Core Execution & Webhook Endpoints
# ==========================================
class ExecutionRequest(BaseModel):
    user_id: str
    task_type: str
    payload: Dict[str, Any]

@app.post("/api/v1/execute")
async def execute_task(request_data: ExecutionRequest):
    """ท่อประมวลผลหลัก รองรับงานเอกสาร, เสียง, วิดีโอ และการวิเคราะห์ตลาด"""
    try:
        # ตรวจสอบสิทธิ์ผู้ใช้ก่อนประมวลผล
        if supabase and request_data.user_id != MASTER_ADMIN_LINE_ID:
            client_res = supabase.table("prime_clients").select("token_balance, role").eq("line_user_id", request_data.user_id).execute()
            if not client_res.data:
                raise HTTPException(status_code=403, detail="กรุณาลงทะเบียนผ่านรหัสคำเชิญก่อนใช้งานระบบ")
            
            client_info = client_res.data[0]
            if client_info.get("role") != "admin" and float(client_info.get("token_balance", 0)) <= 0:
                raise HTTPException(status_code=402, detail="ยอดเงินใน Smart Wallet ของคุณหมดแล้ว กรุณาเติมเงิน (Top-up) เพื่อใช้งานต่อ")

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

# สร้าง Instance ของบอสเก่าเตรียมไว้เผื่อสมองใหม่มีปัญหา
boss_agent = CentralBossAgent() if CentralBossAgent else None

def process_ai_and_reply(user_id: str, incoming_message: str, reply_token: str):
    """ฟังก์ชันให้ AI แอบคิดคำตอบอยู่เบื้องหลัง ป้องกัน LINE หมดเวลาตัดสาย"""
    try:
        reply_msg = ""
        # 1. ลองใช้สมองอัจฉริยะ (Prime Brain)
        if generate_intelligent_response:
            try:
                reply_msg = generate_intelligent_response(user_id, incoming_message)
                logger.info("🧠 [Prime Brain]: ประมวลผลสำเร็จ")
            except Exception as e:
                logger.error(f"⚠️ [Prime Brain Error]: สมองใหม่สะดุด ({e}) กำลังสลับไปใช้ระบบ Boss")
                if boss_agent:
                    reply_msg = boss_agent.route_task(user_id, incoming_message, None)
                else:
                    reply_msg = "ขออภัยครับ ระบบกำลังประมวลผลข้อมูลระดับสถาบัน โปรดรอสักครู่นะครับ"
        else:
            # 2. ถ้าไม่มีสมองใหม่ ให้ใช้บอสตัวเก่า
            if boss_agent:
                reply_msg = boss_agent.route_task(user_id, incoming_message, None)
            else:
                reply_msg = "ระบบยังไม่พร้อมใช้งานชั่วคราวครับ"

        # 3. ส่งข้อความตอบกลับหาลูกค้า
        if reply_msg:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_msg))
            logger.info(f"📤 [LINE AI Reply]: ตอบกลับสำเร็จ")
        
    except Exception as e:
        logger.error(f"❌ [Critical Reply Error]: ไม่สามารถส่งข้อความได้ ({e})")


@app.post("/api/v1/line/webhook")
async def line_webhook_entry(request: Request, background_tasks: BackgroundTasks, x_line_signature: str = Header(None)):
    """Webhook หลักสำหรับรับ Event จาก LINE OA"""
    body = await request.body()
    body_str = body.decode('utf-8')
    logger.info(f"📩 Received LINE Webhook event: {body_str[:100]}...")
    
    try:
        events = parser.parse(body_str, x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature.")
        
    for event in events:
        # หากเป็นการพิมพ์ข้อความเข้ามา
        if isinstance(event, MessageEvent) and isinstance(event.message, TextMessage):
            user_id = event.source.user_id
            incoming_message = event.message.text
            reply_token = event.reply_token
            
            # โยนข้อความเข้าไปให้ AI คิดคำตอบเป็น Background Task ทันที
            background_tasks.add_task(process_ai_and_reply, user_id, incoming_message, reply_token)

    # รีบตอบกลับ LINE ทันทีว่า "รับเรื่องแล้ว" เพื่อไม่ให้โดนตัดสาย
    return {"status": "received", "message": "Processing in background"}

if __name__ == "__main__":
    # ดึงค่าพอร์ตแบบ Dynamic จาก Google Cloud Run (ถ้าหาไม่เจอให้ใช้ 8080)
    port = int(os.environ.get("PORT", 8080))
    
    print(f"🚀 Starting SIRINTHANATTH PRIME Backend API on port {port}...")
    
    # สตาร์ทเซิร์ฟเวอร์ด้วย uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)