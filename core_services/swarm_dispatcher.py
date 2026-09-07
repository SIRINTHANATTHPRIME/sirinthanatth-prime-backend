import logging
import asyncio
import inspect
import uuid
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("SwarmDispatcher")

class SwarmDispatcher:
    """
    🌐 Enterprise P2P Agentic Swarm Hub (ศูนย์กลางสับรางงานอัจฉริยะ)
    อัปเกรด: Auto Async/Sync, Circuit Breaker, Traceability & Fault-Tolerance
    """
    _instance = None
    _workers: Dict[str, Any] = {}

    def __new__(cls):
        # Thread-Safe Singleton instantiation
        if cls._instance is None:
            cls._instance = super(SwarmDispatcher, cls).__new__(cls)
            cls._instance._workers = {}
        return cls._instance

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def register(self, worker_name: str, worker_instance: Any) -> None:
        """ลงทะเบียน Agent เข้าสู่ระบบ Swarm Network"""
        self._workers[worker_name] = worker_instance
        logger.info(f"🔗 [Swarm Hub]: ขึ้นทะเบียน '{worker_name}' เข้าสู่เครือข่าย (Active Agents: {len(self._workers)})")

    async def delegate_task(self, from_worker: str, to_worker: str, user_id: str, message: str, file_path: Optional[str] = None, file_type: Optional[str] = None) -> str:
        """🚀 สับรางงานระหว่าง Agent พร้อมระบบป้องกันความล้มเหลวระดับองค์กร"""
        trace_id = uuid.uuid4().hex[:8]
        start_time = time.time()
        
        if to_worker not in self._workers:
            logger.error(f"❌ [Swarm-Error-{trace_id}]: ไม่พบแผนก '{to_worker}' ในเครือข่าย")
            return f"⚠️ ระบบไม่สามารถส่งต่องานไปยังฝ่าย {to_worker} ได้ครับ"

        logger.info(f"🔄 [Swarm-Trace-{trace_id}]: '{from_worker}' โยนงานไปให้ -> '{to_worker}'")
        target_agent = self._workers[to_worker]

        # 🎯 Dynamic Method Resolution (ค้นหาและจัดเตรียมพารามิเตอร์อัตโนมัติ)
        target_method = None
        kwargs = {}
        
        if hasattr(target_agent, 'process_command'):
            target_method = target_agent.process_command
            kwargs = {'user_id': user_id, 'message': message, 'file_path': file_path, 'file_type': file_type}
        elif hasattr(target_agent, 'process_ceo_command'):
            target_method = target_agent.process_ceo_command
            kwargs = {'message': message, 'file_path': file_path, 'file_type': file_type}
        elif hasattr(target_agent, 'process_task'):
            target_method = target_agent.process_task
            kwargs = {'user_id': user_id, 'message': message, 'file_path': file_path}
        
        if not target_method:
            logger.error(f"❌ [Swarm-Error-{trace_id}]: '{to_worker}' ไม่มีฟังก์ชันรับงานที่รองรับ")
            return f"⚠️ แผนก {to_worker} ยังไม่พร้อมรับคำสั่งในขณะนี้"

        # 🛡️ Execution with Circuit Breaker & Auto Async/Sync Handling
        try:
            async def execute_method():
                # ตรวจสอบว่าเป็น Async Function หรือไม่ เพื่อป้องกัน Event Loop พัง
                if inspect.iscoroutinefunction(target_method):
                    return await target_method(**kwargs)
                else:
                    return await asyncio.to_thread(target_method, **kwargs)

            # กำหนด Timeout 120 วินาที ป้องกัน Agent ค้างและดึงระบบล่ม (Deadlock)
            result = await asyncio.wait_for(execute_method(), timeout=120.0)
            
            elapsed = time.time() - start_time
            logger.info(f"✅ [Swarm-Success-{trace_id}]: '{to_worker}' ทำงานสำเร็จใน {elapsed:.2f}s")
            return result
            
        except asyncio.TimeoutError:
            logger.critical(f"⏳ [Swarm-Timeout-{trace_id}]: แผนก '{to_worker}' ใช้เวลาทำงานเกินขีดจำกัด (120s)")
            return f"⚠️ แผนก {to_worker} มีปริมาณงานหนาแน่น ระบบจึงทำการยกเลิกคำสั่งเพื่อป้องกันความล่าช้าครับ"
        except Exception as e:
            logger.error(f"💥 [Swarm-Crash-{trace_id}]: '{to_worker}' ล้มเหลวระหว่างทำงาน -> {e}", exc_info=True)
            return "⚠️ เกิดข้อผิดพลาดทางเทคนิคระหว่างส่งต่องานในระบบเครือข่ายครับ"

swarm_hub = SwarmDispatcher.get_instance()