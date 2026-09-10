import logging
import asyncio
import inspect
import uuid
import time
from typing import Any, Dict, Optional, List

# ตั้งค่า Logger ให้ดูเป็นมืออาชีพและระบุต้นทางชัดเจน
logger = logging.getLogger("SwarmDispatcher")

class SwarmDispatcher:
    """
    🌐 Enterprise P2P Agentic Swarm Hub (ศูนย์กลางสับรางงานอัจฉริยะขั้นสูงสุด)
    อัปเกรด: Signature Introspection, Auto-Healing (Retry), Smart Parameter Injection, Concurrent LINE Webhook
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

    async def dispatch_line_event(self, payload: Dict[str, Any], entry_worker: str = "core_agent") -> List[Any]:
        """
        📥 จุดรับข้อมูลจาก LINE Webhook (แก้ปัญหา AttributeError)
        สกัดข้อมูลจาก Payload และกระจายงานแบบคู่ขนาน (Concurrent) ไปยัง Agent ตัวแรก
        
        :param payload: ข้อมูล JSON ที่ได้จาก LINE Messaging API
        :param entry_worker: ชื่อของ Agent ที่จะรับจบเป็นด่านแรก (เช่น 'core_agent', 'ceo_agent')
        """
        events = payload.get("events", [])
        if not events:
            logger.warning("⚠️ [Swarm Hub]: ได้รับ Payload จาก LINE แต่ไม่มี events (อาจเป็นการ Verify Webhook)")
            return []

        tasks = []
        for event in events:
            try:
                user_id = event.get("source", {}).get("userId", "unknown_user")
                event_type = event.get("type", "unknown")

                # กรองรับเฉพาะ Event ประเภทข้อความ (ขยายต่อได้ในอนาคต)
                if event_type == "message":
                    message_data = event.get("message", {})
                    msg_type = message_data.get("type", "unknown")
                    
                    if msg_type == "text":
                        message_text = message_data.get("text", "")
                        logger.info(f"📨 [Swarm Hub]: รับข้อความจาก {user_id} -> '{message_text[:30]}...'")
                        
                        task = asyncio.create_task(
                            self.delegate_task(
                                from_worker="LINE_Gateway",
                                to_worker=entry_worker,
                                user_id=user_id,
                                message=message_text
                            )
                        )
                        tasks.append(task)

                    # เพิ่ม Block นี้เพื่อให้บอทอ่านสติกเกอร์ออก
                    elif msg_type == "sticker":
                        package_id = message_data.get("packageId", "")
                        sticker_id = message_data.get("stickerId", "")
                        logger.info(f"✨ [Swarm Hub]: รับสติกเกอร์จาก {user_id} (Package: {package_id}, Sticker: {sticker_id})")
                        
                        # แปลงสติกเกอร์เป็นข้อความเพื่อให้ Agent นำไปประมวลผลต่อได้ง่ายๆ
                        simulated_message = "[ผู้ใช้ส่งสติกเกอร์ทักทาย]" 
                        
                        task = asyncio.create_task(
                            self.delegate_task(
                                from_worker="LINE_Gateway",
                                to_worker=entry_worker,
                                user_id=user_id,
                                message=simulated_message
                            )
                        )
                        tasks.append(task)
                        
                    else:
                        logger.info(f"📎 [Swarm Hub]: ได้รับข้อความประเภท '{msg_type}' จาก {user_id} (ระบบรอการขยายผล)")
                else:
                    logger.debug(f"ℹ️ [Swarm Hub]: ข้าม Event ประเภท '{event_type}'")
                    
            except Exception as e:
                logger.error(f"❌ [Swarm Hub]: เกิดข้อผิดพลาดขณะแกะ Payload ของ LINE: {e}", exc_info=True)

        # รอให้ทุก Task ที่แยกไปทำงานเสร็จสิ้น และป้องกันไม่ให้ Error ย่อยทำให้ระบบล่มทั้งหมด (return_exceptions=True)
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results
        
        return []

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

# สร้าง Singleton Instance เผื่อถูก Import ไปใช้ในไฟล์อื่น
swarm_hub = SwarmDispatcher.get_instance()