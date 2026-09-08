import logging
import asyncio
import inspect
import uuid
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("SwarmDispatcher")

class SwarmDispatcher:
    """
    🌐 Enterprise P2P Agentic Swarm Hub (ศูนย์กลางสับรางงานอัจฉริยะขั้นสูงสุด)
    อัปเกรด: Signature Introspection, Auto-Healing (Retry), Smart Parameter Injection
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
        logger.info(f"🔗 [Swarm Hub]: ขึ้นทะเบียน '{worker_name}' สำเร็จ (Active Agents: {len(self._workers)})")

    async def delegate_task(self, from_worker: str, to_worker: str, user_id: str, message: str, 
                            file_path: Optional[str] = None, file_type: Optional[str] = None, 
                            _retry_count: int = 0) -> str:
        """🚀 สับรางงานข้ามแผนก พร้อมระบบวิเคราะห์ Method Signature และ Self-Healing"""
        trace_id = uuid.uuid4().hex[:8]
        start_time = time.time()
        
        if to_worker not in self._workers:
            logger.error(f"❌ [Swarm-Error-{trace_id}]: ไม่พบแผนก '{to_worker}' ในเครือข่าย")
            return f"⚠️ ระบบไม่สามารถส่งต่องานไปยังฝ่าย {to_worker} ได้ครับ"

        # แสดง Log การโยนงาน (พร้อมบอกสถานะหากเป็นการ Retry ซ่อมแซมตัวเอง)
        retry_tag = f" [Retry {_retry_count}]" if _retry_count > 0 else ""
        logger.info(f"🔄 [Swarm-Trace-{trace_id}]: '{from_worker}' โยนงาน -> '{to_worker}'{retry_tag}")
        
        target_agent = self._workers[to_worker]

        # 🎯 1. Smart Method Discovery (ค้นหาฟังก์ชันรับงานเรียงตาม Priority)
        target_method = None
        for m_name in ['process_command', 'process_ceo_command', 'process_task', 'execute', 'run']:
            if hasattr(target_agent, m_name):
                target_method = getattr(target_agent, m_name)
                break
                
        if not target_method:
            logger.error(f"❌ [Swarm-Error-{trace_id}]: '{to_worker}' ไม่มีฟังก์ชันรับงานระดับมาตรฐาน")
            return f"⚠️ แผนก {to_worker} ขาดสถาปัตยกรรมรองรับคำสั่ง (Method missing)"

        # 🧠 2. AI Signature Introspection (ฉีดพารามิเตอร์อัจฉริยะ)
        # ตรวจสอบว่าฟังก์ชันเป้าหมาย "ต้องการรับตัวแปรอะไรบ้าง" แล้วจ่ายให้พอดีเป๊ะ ป้องกัน TypeError
        sig = inspect.signature(target_method)
        available_payload = {
            'user_id': user_id, 
            'message': message, 
            'file_path': file_path, 
            'file_type': file_type,
            'trace_id': trace_id # ส่ง Trace ID เผื่อ Worker ต้องการนำไปลง Log ต่อ
        }
        
        kwargs = {}
        # เช็คว่า Worker เปิดรับ **kwargs แบบอิสระหรือไม่
        has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        
        if has_varkw:
            kwargs = available_payload
        else:
            # คัดกรองส่งไปเฉพาะ Parameter ที่มีประกาศไว้ในฟังก์ชันปลายทางเท่านั้น
            kwargs = {k: v for k, v in available_payload.items() if k in sig.parameters}

        # 🛡️ 3. Execution with Circuit Breaker & Auto-Healing
        try:
            async def execute_method():
                if inspect.iscoroutinefunction(target_method):
                    return await target_method(**kwargs)
                else:
                    return await asyncio.to_thread(target_method, **kwargs)

            # กำหนด Timeout 120 วินาที ป้องกัน Deadlock
            result = await asyncio.wait_for(execute_method(), timeout=120.0)
            
            elapsed = time.time() - start_time
            logger.info(f"✅ [Swarm-Success-{trace_id}]: '{to_worker}' ทำงานสำเร็จใน {elapsed:.2f}s")
            return result
            
        except asyncio.TimeoutError:
            logger.critical(f"⏳ [Swarm-Timeout-{trace_id}]: แผนก '{to_worker}' ใช้เวลาเกิน 120s (Timeout)")
            return f"⚠️ แผนก {to_worker} มีปริมาณงานหนาแน่น ระบบทำการตัดวงจรเพื่อป้องกันคอขวดครับ"
            
        except Exception as e:
            logger.error(f"💥 [Swarm-Crash-{trace_id}]: '{to_worker}' ล้มเหลว -> {e}", exc_info=True)
            
            # ♻️ Auto-Healing: หากเกิด Error ที่ไม่ใช่ Timeout ให้ลองส่งงานซ่อมแซมตัวเอง 1 ครั้ง
            if _retry_count < 1:
                logger.info(f"♻️ [Swarm-Recovery]: สั่งเดินเครื่องส่งงานให้ '{to_worker}' ใหม่อีกครั้ง...")
                await asyncio.sleep(2) # Backoff รอ 2 วินาทีให้ระบบปลายทางหายใจ
                return await self.delegate_task(
                    from_worker, to_worker, user_id, message, file_path, file_type, _retry_count=_retry_count + 1
                )
                
            return "⚠️ เกิดข้อผิดพลาดทางเทคนิคระดับลึกระหว่างประสานงานในเครือข่ายครับ"

swarm_hub = SwarmDispatcher.get_instance()