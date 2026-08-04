# services/task_dispatcher.py
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class HybridTaskDispatcher:
    def __init__(self):
        # กำหนดอัตราส่วนน้ำหนัก Token (Weight Multiplier) สำหรับซ่อนเรตหลังบ้าน
        self.STANDARD_WEIGHT = 1.0
        self.MEDIA_HEAVY_WEIGHT = 8.5  # อ้างอิงสเปกเทียบเคียง 32 GiB / 8 vCPU

    async def route_and_execute(self, task_type: str, payload: Dict[Any, Any]) -> Dict[str, Any]:
        """
        ฟังก์ชันสลับทิศทางงาน (Hybrid Switching) 
        - task_type: 'document_process' หรือ 'media_render'
        """
        try:
            if task_type == "media_render":
                logger.info("⚡ [Hybrid Switcher] Switching to HEAVY WORKLOAD (32 GiB / 8 vCPU profile)")
                result = await self._run_heavy_media_engine(payload)
                token_cost = self._calculate_tokens(base_cost=10, weight=self.MEDIA_HEAVY_WEIGHT)
                return {"status": "success", "engine": "prime-media-engine", "cost": token_cost, "data": result}
            
            else:
                logger.info("🧠 [Hybrid Switcher] Routing to STANDARD WORKLOAD (Core Agent)")
                result = await self._run_standard_agent(payload)
                token_cost = self._calculate_tokens(base_cost=1, weight=self.STANDARD_WEIGHT)
                return {"status": "success", "engine": "prime-core-agent", "cost": token_cost, "data": result}

        except Exception as e:
            logger.error(f"❌ Error in HybridTaskDispatcher: {str(e)}")
            raise e

    async def _run_standard_agent(self, payload: Dict[Any, Any]) -> Dict[str, Any]:
        # จำลองการทำงานของ Core Agent (เช่น ตอบแชท, ดึงข้อมูล Flash Express, เช็ก Supabase)
        return {"message": "Standard document processing completed.", "payload_received": payload}

    async def _run_heavy_media_engine(self, payload: Dict[Any, Any]) -> Dict[str, Any]:
        # จำลองการทำงานของ Media Engine หนักๆ (เช่น เรียกใช้ FFmpeg / ImageMagick เรนเดอร์วิดีโอ)
        return {"message": "Media rendering completed via heavy worker.", "media_url": "https://storage.googleapis.com/.../output.mp4"}

    def _calculate_tokens(self, base_cost: int, weight: float) -> int:
        # คำนวณ Token แบบ Single-Rate แต่ซ่อนเรตคูณน้ำหนักหลังบ้านไว้
        return int(base_cost * weight)

task_dispatcher = HybridTaskDispatcher()