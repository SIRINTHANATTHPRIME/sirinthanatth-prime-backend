import os
import logging
import stripe
from pydantic import BaseModel
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv
from typing import Optional, Dict, Any

# Import ตัวสลับท่อ Hybrid Switching
try:
    from services.task_dispatcher import task_dispatcher
except ImportError:
    from task_dispatcher import task_dispatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SIRINTHANATTH_PRIME_MAIN")

# นำเข้าบริการภายในของเรา
from agents.central_boss import CentralBossAgent
from services.subscription_manager import SubscriptionManager

load_dotenv()

app = FastAPI(
    title="SIRINTHANATTH PRIME Backend API",
    description="Enterprise-grade AI SaaS supporting financial, logistics, and heavy media workloads.",
    version="1.0.0"
)

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
# 2. ตั้งค่าระบบต่างๆ (เพิ่ม Defensive Check)
# ==========================================
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# ป้องกันแอปแครชหากลืมตั้งค่า Environment Variables ใน Cloud Run
LINE_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")

if LINE_ACCESS_TOKEN and LINE_SECRET:
    line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
    parser = WebhookParser(LINE_SECRET)
else:
    logger.warning("⚠️ ขาดการตั้งค่า LINE_CHANNEL_ACCESS_TOKEN หรือ LINE_CHANNEL_SECRET ระบบอาจไม่สามารถตอบกลับ LINE ได้")

# ดึงสมองกลกลาง และ กระเป๋าเงิน มาสแตนด์บาย
central_boss = CentralBossAgent()
sub_manager = SubscriptionManager()

# Schema สำหรับรับข้อมูลจาก LINE Webhook หรือ API
class CoreRequestPayload(BaseModel):
    user_id: str
    task_type: str = "document_process"  # 'document_process' หรือ 'media_render'
    payload: Optional[Dict[str, Any]] = {}

@app.get("/")
async def root_health_check():
    """Health check endpoint สำหรับ Google Cloud Run"""
    return {
        "status": "online",
        "service": "SIRINTHANATTH PRIME Backend",
        "environment": os.getenv("ENV", "production")
    }

# ==========================================
# 🟢 3. LINE WEBHOOK (หูและปากของระบบ)
# ==========================================
@app.post("/webhook/line_ai")
async def line_webhook(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers.get('X-Line-Signature', '')
    body = await request.body()
    
    try:
        events = parser.parse(body.decode('utf-8'), signature)
        for event in events:
            if isinstance(event, MessageEvent) and isinstance(event.message, TextMessage):
                user_id = event.source.user_id
                user_msg = event.message.text
                
                # โยนข้อความให้ Central Boss คิดและทำงาน
                reply_text = central_boss.route_task(user_id, user_msg, background_tasks)
                
                # ตอบกลับไปใน LINE ของลูกค้า
                if 'line_bot_api' in globals():
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=reply_text)
                    )
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid LINE Signature")
    except Exception as e:
        logger.error(f"❌ LINE Webhook Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    return "OK"

# ==========================================
# 💰 4. STRIPE WEBHOOK (ระบบรับแจ้งเงินเข้าอัตโนมัติ)
# ==========================================
@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ถ้าลูกค้าจ่ายเงินเสร็จ
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('client_reference_id')
        amount_paid = session.get('amount_total', 0) / 100  # แปลงสตางค์เป็นบาท

        if user_id and 'line_bot_api' in globals():
            if amount_paid == 500:
                # เติมเงิน Wallet 500 บาท
                sub_manager.topup_wallet(user_id, amount_paid)
                line_bot_api.push_message(user_id, TextSendMessage(text="🎉 เติมเงินเข้า Smart Wallet จำนวน 500 บาท สำเร็จแล้วครับ!"))
            
            elif amount_paid == 4490:
                # อัปเกรดเป็น VIP Founder
                line_bot_api.push_message(user_id, TextSendMessage(text="👑 ยินดีต้อนรับสู่สถานะ VIP FOUNDER! ระบบได้บันทึกสิทธิ์และปลดล็อกฟีเจอร์ผลิตสื่อ 4K ให้คุณเรียบร้อยแล้วครับ"))
                
    return {"status": "success"}

# ==========================================
# ⚡ 5. HYBRID SWITCHING & API ENDPOINTS
# ==========================================
@app.post("/api/v1/execute")
async def execute_task(request_data: CoreRequestPayload, background_tasks: BackgroundTasks):
    """
    Endpoint หลักที่รองรับ Single-Rate Interface กับ Hybrid Switching
    """
    try:
        # สลับท่อประมวลผลและคำนวณ Token อัตโนมัติหลังบ้าน
        dispatch_result = await task_dispatcher.route_and_execute(
            task_type=request_data.task_type,
            payload=request_data.payload
        )

        if not dispatch_result["success"]:
            raise HTTPException(status_code=500, detail=dispatch_result.get("error", "Task execution failed"))

        # ตอบกลับหน้าบ้านในรูปแบบ Single-Rate ที่สะอาด อ่านง่าย ไม่จุกจิก
        return {
            "status": "success",
            "user_id": request_data.user_id,
            "tokens_used": dispatch_result["tokens_deducted"],
            "execution_info": {
                "engine": dispatch_result["engine_used"],
                "details": dispatch_result["result"]
            }
        }

    except Exception as e:
        logger.error(f"❌ API Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/line/webhook")
async def line_webhook_entry(request: Request):
    """Webhook สำรองสำหรับการรับ Event จาก LINE OA โดยตรง"""
    body = await request.json()
    logger.info(f"📩 Received LINE Webhook event")
    return {"status": "received", "data": body}

# ==========================================
# 🚀 6. SERVER INITIALIZATION
# ==========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)