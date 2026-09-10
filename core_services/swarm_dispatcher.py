import logging
import asyncio
import inspect
import uuid
import time
from typing import Any, Dict, Optional, List

# =========================================================================
# 🧩 ENTERPRISE DYNAMIC IMPORTS: โหลด AI Agents ทั้งหมดแบบ Graceful Degradation
# ป้องกันเซิร์ฟเวอร์ล่มกรณีที่ไฟล์บางไฟล์อยู่ระหว่างการพัฒนาหรือตั้งชื่อคลาสคลาดเคลื่อน
# =========================================================================
try: from agents.central_boss import CentralBossAgent
except ImportError: CentralBossAgent = None

try: from agents.worker_0_ceo_secretary import CeoSecretaryWorker
except ImportError: CeoSecretaryWorker = None

try: from agents.worker_1_report import ReportWorker
except ImportError: ReportWorker = None

try: from agents.worker_2_risk_qa import RiskQaWorker
except ImportError: RiskQaWorker = None

try: from agents.worker_3_audio import AudioWorker
except ImportError: AudioWorker = None

try: from agents.worker_4_video import VideoWorker
except ImportError: VideoWorker = None

try: from agents.worker_5_graphics_ads import GraphicsAdsWorker
except ImportError: GraphicsAdsWorker = None

try: from agents.worker_6_strategy import StrategyWorker
except ImportError: StrategyWorker = None

try: from agents.worker_7_finance import FinanceWorker
except ImportError: FinanceWorker = None

try: from agents.worker_8_ecommerce import EcommerceWorker
except ImportError: EcommerceWorker = None

try: from agents.worker_9_prime import PrimeAdvisorWorker
except ImportError: PrimeAdvisorWorker = None

try: from agents.worker_10_enterprise import EnterpriseWorker
except ImportError: EnterpriseWorker = None

try: from agents.worker_11_media_engine import MediaEngineWorker
except ImportError: MediaEngineWorker = None

try: from agents.worker_12_self_learning import SelfLearningEngine
except ImportError: SelfLearningEngine = None

try: from agents.worker_13_it_architect import ITArchitectWorker
except ImportError: ITArchitectWorker = None


logger = logging.getLogger("SwarmDispatcher")

class SwarmDispatcher:
    """
    🌐 Enterprise P2P Agentic Swarm Hub (ศูนย์กลางสับรางงานอัจฉริยะขั้นสูงสุด)
    อัปเกรด: Full Network Auto-Discovery, Signature Introspection, Auto-Healing (Retry), Smart Parameter Injection
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
            cls._instance._auto_register_all_agents()
        return cls._instance

    def _auto_register_all_agents(self):
        """🚀 ระบบลงทะเบียน Agent อัตโนมัติ (ครอบคลุม Worker 0-13 ตามโครงสร้างโฟลเดอร์)"""
        logger.info("⚙️ [Swarm Hub]: Initiating Enterprise Auto-Registration for ALL AI Agents...")
        
        # 👑 Core & Boss
        if CeoSecretaryWorker:
            ceo_agent = CeoSecretaryWorker()
            self.register("WORKER_0_CEO", ceo_agent)
            self.register("core_agent", ceo_agent)  # Alias สำคัญสำหรับแก้บั๊กรับ Webhook
            
        if CentralBossAgent:
            boss = CentralBossAgent()
            self.register("CENTRAL_BOSS", boss)
            self.register("central_boss", boss)

        # 🤖 แผนกปฏิบัติการเฉพาะทาง (Worker 1 - 13)
        if ReportWorker: self.register("WORKER_1_REPORT", ReportWorker())
        if RiskQaWorker: self.register("WORKER_2_RISK_QA", RiskQaWorker())
        if AudioWorker: self.register("WORKER_3_AUDIO", AudioWorker())
        if VideoWorker: self.register("WORKER_4_VIDEO", VideoWorker())
        if GraphicsAdsWorker: self.register("WORKER_5_GRAPHICS_ADS", GraphicsAdsWorker())
        if StrategyWorker: self.register("WORKER_6_STRATEGY", StrategyWorker())
        if FinanceWorker: self.register("WORKER_7_FINANCE", FinanceWorker())
        if EcommerceWorker: self.register("WORKER_8_ECOMMERCE", EcommerceWorker())
        if PrimeAdvisorWorker: self.register("WORKER_9_PRIME", PrimeAdvisorWorker())
        if EnterpriseWorker: self.register("WORKER_10_ENTERPRISE", EnterpriseWorker())
        if MediaEngineWorker: self.register("WORKER_11_MEDIA_ENGINE", MediaEngineWorker())
        if SelfLearningEngine: self.register("WORKER_12_SELF_LEARNING", SelfLearningEngine())
        if ITArchitectWorker: self.register("WORKER_13_IT_ARCHITECT", ITArchitectWorker())

    def register(self, worker_name: str, worker_instance: Any) -> None:
        """ลงทะเบียน Agent เข้าสู่ระบบ Swarm Network ด้วยตนเอง (Manual Override)"""
        self._workers[worker_name] = worker_instance
        logger.info(f"🔗 [Swarm Hub]: ขึ้นทะเบียน '{worker_name}' สำเร็จ (Active Agents: {len(self._workers)})")

    async def dispatch_line_event(self, payload: Dict[str, Any], entry_worker: str = "core_agent") -> List[Any]:
        """
        📥 จุดรับข้อมูลจาก LINE Webhook (กระจายงานแบบ Concurrent คู่ขนาน)
        """
        events = payload.get("events", [])
        if not events:
            logger.warning("⚠️ [Swarm Hub]: ได้รับ Payload จาก LINE แต่ไม่มี events")
            return []

        tasks = []
        for event in events:
            try:
                user_id = event.get("source", {}).get("userId", "unknown_user")
                event_type = event.get("type", "unknown")

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

                    # ✨ บล็อกรับสติกเกอร์ (แปลงเป็นข้อความให้ AI ประมวลผล ไม่ปล่อยให้บอทเงียบ)
                    elif msg_type == "sticker":
                        package_id = message_data.get("packageId", "")
                        sticker_id = message_data.get("stickerId", "")
                        logger.info(f"✨ [Swarm Hub]: รับสติกเกอร์จาก {user_id} (Pkg: {package_id}, ID: {sticker_id})")
                        
                        simulated_message = f"[ผู้ใช้ส่งสติกเกอร์ทักทายรหัส {package_id}:{sticker_id}] โปรดตอบกลับสติกเกอร์นี้อย่างเป็นมิตร"
                        
                        task = asyncio.create_task(
                            self.delegate_task(
                                from_worker="LINE_Gateway",
                                to_worker=entry_worker,
                                user_id=user_id,
                                message=simulated_message
                            )
                        )
                        tasks.append(task)
                        
                    elif msg_type in ['image', 'video', 'audio', 'file']:
                        logger.info(f"📎 [Swarm Hub]: รับไฟล์มัลติมีเดีย '{msg_type}' จาก {user_id}")
                        task = asyncio.create_task(
                            self.delegate_task(
                                from_worker="LINE_Gateway",
                                to_worker=entry_worker,
                                user_id=user_id,
                                message=f"[ผู้ใช้อัปโหลดไฟล์ {msg_type}] โปรดดำเนินการวิเคราะห์",
                                file_type=msg_type
                            )
                        )
                        tasks.append(task)
                    else:
                        logger.debug(f"ℹ️ [Swarm Hub]: ข้อความประเภท '{msg_type}' ยังไม่รองรับการประมวลผลลึก")
                else:
                    logger.debug(f"ℹ️ [Swarm Hub]: ข้าม Event ประเภท '{event_type}'")
                    
            except Exception as e:
                logger.error(f"❌ [Swarm Hub]: เกิดข้อผิดพลาดขณะแกะ Payload ของ LINE: {e}", exc_info=True)

        # รอให้ทุก Task ทำงานเสร็จ และใช้ return_exceptions=True ป้องกัน Error จุดเดียวทำระบบล่มทั้งหมด
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
        
        # ค้นหา Worker ในระบบ
        if to_worker not in self._workers:
            logger.error(f"❌ [Swarm-Error-{trace_id}]: ไม่พบแผนก '{to_worker}' ในเครือข่าย")
            return f"⚠️ ระบบไม่สามารถส่งต่องานไปยังฝ่าย {to_worker} ได้ครับ"

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
            return f"⚠️ แผนก {to_worker} ขาดสถาปัตยกรรมรองรับคำสั่ง"

        # 🧠 2. AI Signature Introspection (ฉีดพารามิเตอร์อัตโนมัติ ไม่บังคับโครงสร้างตายตัว)
        sig = inspect.signature(target_method)
        available_payload = {
            'user_id': user_id, 
            'message': message, 
            'file_path': file_path, 
            'file_type': file_type,
            'trace_id': trace_id
        }
        
        kwargs = {}
        has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
        
        if has_varkw:
            kwargs = available_payload
        else:
            kwargs = {k: v for k, v in available_payload.items() if k in sig.parameters}

        # 🛡️ 3. Execution with Circuit Breaker & Auto-Healing (ทนทานต่อการถูกแฮ็กหรือส่งสแปม)
        try:
            async def execute_method():
                if inspect.iscoroutinefunction(target_method):
                    return await target_method(**kwargs)
                else:
                    return await asyncio.to_thread(target_method, **kwargs)

            # Timeout 120 วินาที ป้องกัน Deadlock ทำให้เซิร์ฟเวอร์ค้าง
            result = await asyncio.wait_for(execute_method(), timeout=120.0)
            
            elapsed = time.time() - start_time
            logger.info(f"✅ [Swarm-Success-{trace_id}]: '{to_worker}' ทำงานสำเร็จใน {elapsed:.2f}s")
            return result
            
        except asyncio.TimeoutError:
            logger.critical(f"⏳ [Swarm-Timeout-{trace_id}]: แผนก '{to_worker}' ใช้เวลาเกิน 120s (Timeout)")
            return f"⚠️ แผนก {to_worker} มีปริมาณงานหนาแน่น ระบบทำการตัดวงจรเพื่อป้องกันคอขวดครับ"
            
        except Exception as e:
            logger.error(f"💥 [Swarm-Crash-{trace_id}]: '{to_worker}' ล้มเหลว -> {e}", exc_info=True)
            
            # ♻️ Auto-Healing: ลองซ่อมแซมตัวเอง 1 ครั้ง ป้องกัน Network กระตุก
            if _retry_count < 1:
                logger.info(f"♻️ [Swarm-Recovery]: สั่งเดินเครื่องส่งงานให้ '{to_worker}' ใหม่อีกครั้ง...")
                await asyncio.sleep(2)
                return await self.delegate_task(
                    from_worker, to_worker, user_id, message, file_path, file_type, _retry_count=_retry_count + 1
                )
                
            return "⚠️ เกิดข้อผิดพลาดทางเทคนิคระดับลึกระหว่างประสานงานในเครือข่ายครับ"

# สร้าง Singleton Instance เพื่อให้พร้อมเรียกใช้งานจากทุกไฟล์
swarm_hub = SwarmDispatcher.get_instance()