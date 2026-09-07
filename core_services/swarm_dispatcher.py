import logging
import asyncio

logger = logging.getLogger("SwarmDispatcher")

class SwarmDispatcher:
    """🌐 ศูนย์กลางสับรางงานแบบ P2P (Peer-to-Peer Agentic Swarm)"""
    _instance = None
    _workers = {}

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def register(self, worker_name: str, worker_instance):
        self._workers[worker_name] = worker_instance
        logger.info(f"🔗 [Swarm Hub]: ลงทะเบียน {worker_name} เข้าสู่เครือข่ายเรียบร้อย")

    async def delegate_task(self, from_worker: str, to_worker: str, user_id: str, message: str, file_path: str = None, file_type: str = None):
        if to_worker not in self._workers:
            logger.error(f"❌ [Swarm Error]: ไม่พบแผนก {to_worker} ในเครือข่าย")
            return f"⚠️ ระบบไม่สามารถส่งต่องานไปยังฝ่าย {to_worker} ได้ครับ"

        logger.info(f"🔄 [Swarm Transfer]: '{from_worker}' โยนงานไปให้ -> '{to_worker}'")
        target_agent = self._workers[to_worker]

        # เพิ่ม process_task เข้าไปในระบบตรวจจับ
        if hasattr(target_agent, 'process_command'):
            return await target_agent.process_command(user_id, message, file_path, file_type)
        elif hasattr(target_agent, 'process_ceo_command'):
            return await target_agent.process_ceo_command(message, file_path, file_type)
        elif hasattr(target_agent, 'process_task'):
            return await target_agent.process_task(user_id, message, file_path)
        else:
            return f"⚠️ {to_worker} ไม่พร้อมรับงานในขณะนี้"

swarm_hub = SwarmDispatcher.get_instance()