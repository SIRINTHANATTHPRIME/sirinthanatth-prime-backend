import os
import google.generativeai as genai
from fastapi import BackgroundTasks

# 🏢 นำเข้าทีมผู้บริหารทั้ง 10 ฝ่ายและ Worker 11 (รองรับ Fallback หากบางไฟล์ยังไม่ถูกสร้างในระบบ)
try:
    from agents.worker_1_report import DocumentEngineeringWorker
except ImportError:
    class DocumentEngineeringWorker:
        async def process(self, u, m): pass

try:
    from agents.worker_2_risk_qa import RiskAndLegalWorker
except ImportError:
    class RiskAndLegalWorker:
        async def process(self, u, m): pass

try:
    from agents.worker_3_audio import AudioProductionWorker
except ImportError:
    class AudioProductionWorker:
        async def process(self, u, m): pass

try:
    from agents.worker_4_video import VideoProductionWorker
except ImportError:
    class VideoProductionWorker:
        async def process(self, u, m): pass

try:
    from agents.worker_5_graphics_ads import GraphicAndAdsWorker
except ImportError:
    class GraphicAndAdsWorker:
        async def process(self, u, m): pass

try:
    from agents.worker_6_strategy import MarketingStrategyWorker
except ImportError:
    class MarketingStrategyWorker:
        async def process(self, u, m): pass

try:
    from agents.worker_7_finance import FinancialAndAccountingWorker
except ImportError:
    class FinancialAndAccountingWorker:
        async def process(self, u, m): pass

try:
    from agents.worker_8_ecommerce import EcommerceAndLogisticsWorker
except ImportError:
    class EcommerceAndLogisticsWorker:
        async def process(self, u, m): pass

try:
    from agents.worker_9_prime import PrimeAdvisorWorker
except ImportError:
    class PrimeAdvisorWorker:
        async def process(self, u, m): pass

try:
    from agents.worker_10_enterprise import EnterprisePartnerWorker
except ImportError:
    class EnterprisePartnerWorker:
        async def process(self, u, m): pass

try:
    from agents.worker_11_media_engine import Worker11MediaEngine
except ImportError:
    class Worker11MediaEngine:
        def process_media_production(self, u, s, m): pass

# 🛡️ นำเข้าระบบความปลอดภัยและการเงิน
from services.subscription_manager import SubscriptionManager
from services.payment_gateway import PaymentGatewayService


class CentralBossAgent:
    """
    🧠 สมองกลผู้บริหารส่วนกลาง (Dynamic Intent Router, Approval Workflow & Smart Wallet Safeguard)
    """
    
    def __init__(self):
        api_key = os.getenv("AI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Initialize Workers
        self.report_worker = DocumentEngineeringWorker()
        self.legal_worker = RiskAndLegalWorker()
        self.audio_worker = AudioProductionWorker()
        self.video_worker = VideoProductionWorker()
        self.graphics_worker = GraphicAndAdsWorker()
        self.strategy_worker = MarketingStrategyWorker()
        self.finance_worker = FinancialAndAccountingWorker()
        self.ecommerce_worker = EcommerceAndLogisticsWorker()
        self.prime_worker = PrimeAdvisorWorker()              
        self.enterprise_worker = EnterprisePartnerWorker()    
        
        self.worker_11 = Worker11MediaEngine()
        self.sub_manager = SubscriptionManager()
        self.payment_gateway = PaymentGatewayService()

        # 🧠 หน่วยความจำชั่วคราวเก็บสคริปต์วิดีโอที่รออนุมัติ (Draft Memory)
        self.pending_approvals = {}

    def route_task(self, user_id: str, message: str, bg_tasks: BackgroundTasks) -> str:
        message_lower = message.lower()

        # ==========================================
        # 💳 โหมดชำระเงิน / สมัครแพ็กเกจ / เติมเงิน Wallet / VIP Presale
        # ==========================================
        if any(kw in message_lower for kw in ["สมัคร", "แพ็กเกจ", "อัปเกรด"]):
            link = self.payment_gateway.create_subscription_checkout(user_id, "PRIME") 
            return (f"ยินดีต้อนรับสู่ระดับท็อปของ SIRINTHANATTH PRIME ครับ! 🚀\n"
                    f"คุณสามารถชำระเงินผ่านบัตรเครดิต หรือ QR Code พร้อมเพย์ เพื่อเปิดระบบได้ที่นี่:\n{link}")
            
        elif any(kw in message_lower for kw in ["เติมเงิน", "wallet", "เติมกระเป๋า", "token"]):
            link = self.payment_gateway.create_wallet_topup_checkout(user_id, 500) 
            return (f"💰 สามารถเติมเงินเข้า Smart Wallet (ขั้นต่ำ 500 บาท) \n"
                    f"เพื่อใช้ตัดค่าบริการผลิตสื่อ 4K หรือค่าส่งพัสดุ Flash Express ได้ที่นี่ครับ:\n{link}")

        elif any(kw in message_lower for kw in ["vip", "founders", "4490"]):
            link = self.payment_gateway.create_subscription_checkout(user_id, "VIP_FOUNDER")
            return (f"👑 [100 VIP Founders Presale Offer]\n"
                    f"ชำระรายปี 4,490 บาท การันตีล็อกราคานี้ตลอดชีพ (Lifetime Price Lock) \n"
                    f"รับเครดิตผลิตสื่อ 4K 50 คลิป/เดือน และเตรียมปลดล็อกเรทส่ง Flash 12฿\n"
                    f"ชำระเงินเพื่อจองสิทธิ์ด่วนได้ที่นี่:\n{link}")

        # ==========================================
        # 🎬 STEP 2: ลูกค้ากด "ยืนยันการสร้างคลิป" (Approval Workflow)
        # ==========================================
        elif "ยืนยันการสร้างคลิป" in message_lower:
            if user_id not in self.pending_approvals:
                return "❌ ไม่พบสคริปต์ที่รอการอนุมัติครับ กรุณาสั่งทำคลิปใหม่อีกครั้ง"
            
            draft_data = self.pending_approvals[user_id]
            total_price = draft_data["price"]
            
            # เช็กและหักเงินใน Smart Wallet
            wallet_check = self.sub_manager.deduct_media_fee(user_id, amount=total_price)
            if wallet_check.get("status") == "error":
                return f"⚠️ {wallet_check.get('msg')}"
            
            # ส่งงานให้ Worker 11 ลุยงานในเบื้องหลัง
            bg_tasks.add_task(
                self.worker_11.process_media_production, 
                user_id, 
                draft_data["script"], 
                "video_4k"
            )
            
            del self.pending_approvals[user_id]
            
            return (f"✅ อนุมัติสำเร็จ! ระบบตัดเงิน {total_price:.2f} บาท เรียบร้อยครับ (หักตามความยาวจริง)\n"
                    f"🎬 Worker 11 กำลังเรนเดอร์คลิป 4K ความยาว {draft_data['minutes']} นาทีให้อยู่ครับ\n"
                    f"☕ กรุณารอสักครู่ เมื่อเรนเดอร์เสร็จแล้วระบบจะส่งลิงก์ดาวน์โหลดให้ทันทีครับ")

        # ==========================================
        # 🎬 STEP 1: ลูกค้าสั่งทำคลิป / สร้างวิดีโอ 4K (Draft First)
        # ==========================================
        elif any(kw in message_lower for kw in ["ทำคลิป", "สร้างวิดีโอ", "สื่อโฆษณา", "คลิป 4k"]):
            estimated_minutes = 3 if "3 นาที" in message_lower else (5 if "5 นาที" in message_lower else 1)
            total_price = estimated_minutes * 49.0  # เรท 49 บาท/นาที
            
            draft_script = f"สคริปต์วิดีโอโฆษณา 4K ({estimated_minutes} นาที): นำเสนอจุดเด่นแบรนด์อย่างทรงพลัง ปิดการขายประทับใจ"
            
            self.pending_approvals[user_id] = {
                "script": draft_script,
                "minutes": estimated_minutes,
                "price": total_price
            }
            
            return (f"📝 [ร่างสคริปต์สื่อโฆษณา 4K สำหรับคุณ]\n{draft_script}\n\n"
                    f"⏱️ ความยาวคลิป: {estimated_minutes} นาที\n"
                    f"💰 ประเมินค่าบริการ (49฿/นาที): {total_price:.2f} บาท\n\n"
                    f"หากคุณพอใจ พิมพ์ตอบกลับว่า 👉 'ยืนยันการสร้างคลิป'\n"
                    f"เพื่อเริ่มเรนเดอร์และหักเงินจาก Smart Wallet ครับ")

        # ==========================================
        # 🚚 โหมด E-Commerce & Flash Express
        # ==========================================
        elif any(kw in message_lower for kw in ["สั่งของ", "ออเดอร์", "สลิป", "flash", "ส่งของ"]):
            bg_tasks.add_task(self.ecommerce_worker.process, user_id, message) 
            return "📦 [Smart E-Commerce]: กำลังตรวจสอบออเดอร์/สลิป และเตรียมระบบออกใบปะหน้า Flash Express ให้ครับ"

        # ==========================================
        # 💼 โหมด Worker อื่นๆ
        # ==========================================
        elif any(kw in message_lower for kw in ["กฎหมาย", "สคบ", "อย", "pdpa", "ตรวจโฆษณา"]):
            bg_tasks.add_task(self.legal_worker.process, user_id, message)
            return "🛡️ ทีม 360° Legal Shield กำลังสแกนความเสี่ยงกฎหมาย อย./สคบ. ให้คุณครับ"
            
        elif any(kw in message_lower for kw in ["เสียง", "เสียงพากย์", "tts"]):
            bg_tasks.add_task(self.audio_worker.process, user_id, message)
            return "🎙️ ทีม Audio Production กำลังสังเคราะห์เสียงพากย์ AI พรีเมียมให้ครับ"
            
        elif any(kw in message_lower for kw in ["ตาราง", "รายงาน", "excel", "pdf"]):
            bg_tasks.add_task(self.report_worker.process, user_id, message)
            return "📊 ทีม Document Engineering กำลังจัดทำเอกสารและผูกสูตรคำนวณให้ครับ"
            
        elif any(kw in message_lower for kw in ["กราฟิก", "แบนเนอร์", "ออกแบบ"]):
            bg_tasks.add_task(self.graphics_worker.process, user_id, message)
            return "🎨 ทีม Graphics & Ads กำลังออกแบบสื่อให้ครับ"
            
        elif any(kw in message_lower for kw in ["กลยุทธ์", "แผนธุรกิจ", "ยิงแอด"]):
            bg_tasks.add_task(self.strategy_worker.process, user_id, message)
            return "📈 ทีม Marketing Strategist กำลังวางแผนกลยุทธ์เจาะตลาดให้ครับ"
            
        elif any(kw in message_lower for kw in ["บัญชี", "การเงิน", "ภาษี", "งบการเงิน"]):
            bg_tasks.add_task(self.finance_worker.process, user_id, message)
            return "💰 ทีม Financial & Accounting กำลังวิเคราะห์งบการเงินและวางแผนภาษีให้ครับ"
            
        elif any(kw in message_lower for kw in ["prime"]):
            bg_tasks.add_task(self.prime_worker.process, user_id, message)
            return "👑 ระบบ [PRIME] กำลังวิเคราะห์ข้อมูลระดับผู้บริหารและจัดการหลังบ้านให้ครับ"
            
        elif any(kw in message_lower for kw in ["enterprise"]):
            bg_tasks.add_task(self.enterprise_worker.process, user_id, message)
            return "🏢 ระบบ [ENTERPRISE] เปิดใช้งานโพรโทคอลความปลอดภัยองค์กรครับ"
            
        else:
            return f"SIRINTHANATTH PRIME ได้รับข้อความ: '{message}' หากต้องการผลิตสื่อโฆษณา 4K หรือเติมเงิน Smart Wallet พิมพ์แจ้งได้เลยครับ"