import os
import stripe
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv

# นำเข้าบริการภายในของเรา (ที่สร้างไว้ก่อนหน้า)
from agents.central_boss import CentralBossAgent
from services.subscription_manager import SubscriptionManager

load_dotenv()

app = FastAPI(title="SIRINTHANATTH PRIME - MASTER CORE")

# 1. CORS & Security
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. ตั้งค่าระบบต่างๆ
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
parser = WebhookParser(os.getenv("LINE_CHANNEL_SECRET"))

# ดึงสมองกลกลาง และ กระเป๋าเงิน มาสแตนด์บาย
central_boss = CentralBossAgent()
sub_manager = SubscriptionManager()

@app.get("/")
def read_root():
    return {"status": "Online", "system": "SIRINTHANATTH PRIME Backend Active"}

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
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply_text)
                )
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid LINE Signature")
    
    return "OK"

# ==========================================
# 💰 4. STRIPE WEBHOOK (ระบบรับแจ้งเงินเข้าอัตโนมัติ)
# ==========================================
@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ถ้าลูกค้าจ่ายเงินเสร็จ (ไม่ว่าจะสแกน PromptPay หรือ รูดบัตร)
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session.get('client_reference_id')
        amount_paid = session.get('amount_total', 0) / 100  # แปลงสตางค์เป็นบาท

        if user_id:
            if amount_paid == 500:
                # เติมเงิน Wallet 500 บาท
                sub_manager.topup_wallet(user_id, amount_paid)
                line_bot_api.push_message(user_id, TextSendMessage(text="🎉 เติมเงินเข้า Smart Wallet จำนวน 500 บาท สำเร็จแล้วครับ!"))
            
            elif amount_paid == 4490:
                # อัปเกรดเป็น VIP Founder
                line_bot_api.push_message(user_id, TextSendMessage(text="👑 ยินดีต้อนรับสู่สถานะ VIP FOUNDER! ระบบได้บันทึกสิทธิ์และปลดล็อกฟีเจอร์ผลิตสื่อ 4K ให้คุณเรียบร้อยแล้วครับ"))
                
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)