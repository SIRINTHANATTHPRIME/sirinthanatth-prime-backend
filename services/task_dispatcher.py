import logging
import asyncio
from typing import Dict, Any
from services.subscription_manager import SubscriptionManager

logger = logging.getLogger("TaskDispatcher")

class HybridTaskDispatcher:
    """
    🚦 ระบบจ่ายงานอัจฉริยะ (Hybrid Task Dispatcher)
    จัดการแยกประเภทงานเบา (แชท) และงานหนัก (เรนเดอร์สื่อ 4K) เพื่อไม่ให้เซิร์ฟเวอร์หลักหน่วง
    """
    def __init__(self):
        # กำหนดอัตราส่วนน้ำหนัก Token (Weight Multiplier) สำหรับซ่อนเรตหลังบ้าน
        self.STANDARD_WEIGHT = 1.0
        self.MEDIA_HEAVY_WEIGHT = 8.5  # อ้างอิงสเปกเทียบเคียง 32 GiB / 8 vCPU
        
        # นำเข้าระบบตรวจสอบสิทธิ์และ Wallet
        self.sub_manager = SubscriptionManager()

    async def route_and_execute(self, user_id: str, task_type: str, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """ฟังก์ชันสลับทิศทางงาน (Hybrid Switching) รองรับ Async I/O 100%"""
        try:
            # 1. 🛡️ เช็กสิทธิ์ก่อนเลยว่าแพ็กเกจของลูกค้ามีสิทธิ์ใช้งานโหมดนี้ไหม
            if not self.sub_manager.check_feature_access(user_id, task_type):
                logger.warning(f"🚫 [Access Denied]: {user_id} พยายามเข้าถึง {task_type} โดยไม่มีสิทธิ์")
                return {
                    "status": "error", 
                    "engine": "none", 
                    "message": "⚠️ ขออภัยครับ แพ็กเกจของคุณยังไม่รองรับการใช้งานฟีเจอร์นี้ กรุณาติดต่อผู้ดูแลระบบเพื่ออัปเกรดสิทธิ์ครับ"
                }

            # 2. 🎬 กรณีสั่งเรนเดอร์สื่อหนักๆ (ตัดเงินแพง และใช้เวลาประมวลผลนาน)
            if task_type == "media_render":
                # เช็กและหักเงินก่อนทำคลิปแบบแยก Thread เพื่อไม่ให้บล็อกระบบ
                payment_check = await asyncio.to_thread(self.sub_manager.deduct_media_fee, user_id, 49.0)
                if payment_check["status"] == "error":
                    return {"status": "error", "message": payment_check["msg"]}

                logger.info(f"⚡ [Hybrid Switcher]: สลับโหมดเป็น HEAVY WORKLOAD สำหรับ {user_id}")
                result = await self._run_heavy_media_engine(payload)
                token_cost = self._calculate_tokens(base_cost=10, weight=self.MEDIA_HEAVY_WEIGHT)
                
                return {"status": "success", "engine": "prime-media-engine", "cost": token_cost, "data": result}
            
            # 3. 🧠 กรณีวิเคราะห์ข้อมูลทั่วไป (แชท, Excel, Flash Express)
            else:
                logger.info(f"🧠 [Hybrid Switcher]: ส่งงานเข้า STANDARD WORKLOAD สำหรับ {user_id}")
                result = await self._run_standard_agent(payload)
                token_cost = self._calculate_tokens(base_cost=1, weight=self.STANDARD_WEIGHT)
                return {"status": "success", "engine": "prime-core-agent", "cost": token_cost, "data": result}

        except Exception as e:
            logger.error(f"❌ Error in HybridTaskDispatcher: {str(e)}")
            return {"status": "error", "message": "เกิดข้อผิดพลาดในการจ่ายงานระบบ กรุณาลองใหม่อีกครั้ง"}

    async def _run_standard_agent(self, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """จำลองการทำงานของ Core Agent แบบไม่บล็อกระบบ"""
        await asyncio.sleep(0.1) # Simulate Async I/O
        return {"message": "Standard processing completed.", "payload_received": payload}

    async def _run_heavy_media_engine(self, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """จำลองการทำงานของ Media Engine หนักๆ"""
        await asyncio.sleep(0.5) # Simulate Render Delay
        return {"message": "Media rendering completed via heavy worker.", "media_url": "https://storage.googleapis.com/sirinthanatthprime/output.mp4"}

    def _calculate_tokens(self, base_cost: int, weight: float) -> float:
        return round(base_cost * weight, 2)