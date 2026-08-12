# services/task_dispatcher.py
import logging
from typing import Dict, Any
from services.subscription_manager import SubscriptionManager

logger = logging.getLogger(__name__)

class HybridTaskDispatcher:
    def __init__(self):
        # กำหนดอัตราส่วนน้ำหนัก Token (Weight Multiplier) สำหรับซ่อนเรตหลังบ้าน
        self.STANDARD_WEIGHT = 1.0
        self.MEDIA_HEAVY_WEIGHT = 8.5  # อ้างอิงสเปกเทียบเคียง 32 GiB / 8 vCPU
        
        # นำเข้าระบบตรวจสอบสิทธิ์
        self.sub_manager = SubscriptionManager()

    async def route_and_execute(self, user_id: str, task_type: str, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """
        ฟังก์ชันสลับทิศทางงาน (Hybrid Switching) 
        - task_type: 'document_process', 'media_render', หรือชื่อฟีเจอร์อื่นๆ
        """
        try:
            # 1. 🛡️ เช็กสิทธิ์ก่อนเลยว่า VVIP คนนี้มีสิทธิ์ใช้งานโหมดนี้ไหม
            if not self.sub_manager.check_feature_access(user_id, task_type):
                return {
                    "status": "error", 
                    "engine": "none", 
                    "message": "⚠️ ขออภัยครับ แพ็กเกจของคุณยังไม่รองรับการใช้งานฟีเจอร์นี้ กรุณาติดต่อท่านประธานเพื่อขออัปเกรดสิทธิ์ครับ"
                }

            # 2. 🎬 กรณีสั่งเรนเดอร์สื่อหนักๆ (ตัดเงินแพง)
            if task_type == "media_render":
                # เช็กและหักเงินก่อนทำคลิป
                payment_check = self.sub_manager.deduct_media_fee(user_id, amount=49.0)
                if payment_check["status"] == "error":
                    return {"status": "error", "message": payment_check["msg"]}

                logger.info("⚡ [Hybrid Switcher] Switching to HEAVY WORKLOAD (32 GiB / 8 vCPU profile)")
                result = await self._run_heavy_media_engine(payload)
                token_cost = self._calculate_tokens(base_cost=10, weight=self.MEDIA_HEAVY_WEIGHT)
                
                return {"status": "success", "engine": "prime-media-engine", "cost": token_cost, "data": result}
            
            # 3. 🧠 กรณีวิเคราะห์ข้อมูลทั่วไป (แชท, Excel)
            else:
                logger.info("🧠 [Hybrid Switcher] Routing to STANDARD WORKLOAD (Core Agent)")
                result = await self._run_standard_agent(payload)
                token_cost = self._calculate_tokens(base_cost=1, weight=self.STANDARD_WEIGHT)
                return {"status": "success", "engine": "prime-core-agent", "cost": token_cost, "data": result}

        except Exception as e:
            logger.error(f"❌ Error in HybridTaskDispatcher: {str(e)}")
            return {"status": "error", "message": "เกิดข้อผิดพลาดในการจ่ายงานระบบ"}

    async def _run_standard_agent(self, payload: Dict[Any, Any]) -> Dict[str, Any]:
        # จำลองการทำงานของ Core Agent (เช่น ตอบแชท, ดึงข้อมูล Flash Express)
        return {"message": "Standard document processing completed.", "payload_received": payload}

    async def _run_heavy_media_engine(self, payload: Dict[Any, Any]) -> Dict[str, Any]:
        # จำลองการทำงานของ Media Engine หนักๆ (เช่น เรียกใช้ FFmpeg / ImageMagick)
        return {"message": "Media rendering completed via heavy worker.", "media_url": "https://storage.googleapis.com/.../output.mp4"}

    def _calculate_tokens(self, base_cost: int, weight: float) -> float:
        return round(base_cost * weight, 2)