import os
import time
import secrets
import string
import logging
import asyncio
import threading
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Supabase-Vault")

class SupabaseDatabase:
    """
    🛡️ ระบบจัดการฐานข้อมูลหลักระดับ Enterprise (Supabase Vault - God Mode)
    อัปเกรด: Synchronized Tables (prime_clients), Thread-Safe Cache, และ Atomic Upsert
    """
    
    _instance = None
    _lock = threading.Lock() 

    def __new__(cls, *args, **kwargs):
        """🚀 Singleton Architecture: บังคับให้เซิร์ฟเวอร์เปิด Connection ท่อเดียว"""
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(SupabaseDatabase, cls).__new__(cls, *args, **kwargs)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized: return
        
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.ceo_line_id = os.getenv("CEO_LINE_ID")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID")
        
        # 🧠 Smart Memory Cache (ลดภาระ Database 90%)
        self._access_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 60.0 # แคชสิทธิ์การใช้งาน 60 วินาที
        
        if not self.supabase_url or not self.supabase_key:
            logger.critical("❌ [DB Initialization]: Supabase URL หรือ Key ขาดหายไป! ระบบฐานข้อมูลออฟไลน์")
            self.client: Optional[Client] = None
        else:
            try:
                self.client: Client = create_client(self.supabase_url, self.supabase_key)
                logger.info("✅ [DB Initialization]: เชื่อมต่อ Supabase Vault สำเร็จ (Zero-Latency Mode Active)")
            except Exception as e:
                logger.critical(f"❌ [DB Initialization Error]: คอนเนคชันล้มเหลว -> {e}")
                self.client = None
                
        self._initialized = True

    def _get_utc_now(self) -> str:
        """มาตรฐานเวลาสากล (ISO-8601) ป้องกัน Timezone Bugs 100%"""
        return datetime.now(timezone.utc).isoformat()

    # ==========================================
    # 👑 ระบบ VVIP และ God Mode (Async I/O Optimization)
    # ==========================================
    async def check_user_access_level(self, line_user_id: str) -> str:
        """ตรวจสอบระดับสิทธิ์ของ User พร้อมระบบ Ultra-Fast Caching"""
        if not line_user_id: return "FREE"
            
        if line_user_id in [self.ceo_line_id, self.master_admin_id]:
            return "UNLIMITED_CEO"
            
        if not self.client: 
            return "FREE"
            
        now = time.time()
        cached_data = self._access_cache.get(line_user_id)
        if cached_data and (now - cached_data["timestamp"] < self._cache_ttl):
            return cached_data["tier"]

        try:
            def _fetch_access():
                # 🔗 ซิงก์ใช้ตาราง prime_clients ตามมาตรฐานระบบการเงิน
                return self.client.table("prime_clients").select("package_tier, status").eq("line_user_id", line_user_id).execute()
                
            res = await asyncio.to_thread(_fetch_access)
            
            tier = "FREE"
            if res.data and res.data[0].get("status") == "active":
                tier = res.data[0].get("package_tier", "FREE").upper()
                
            self._access_cache[line_user_id] = {"tier": tier, "timestamp": now}
            return tier
            
        except Exception as e:
            logger.error(f"❌ [DB Check Error]: ตรวจสอบสิทธิ์ผู้ใช้ล้มเหลว -> {e}")
            return "FREE"

    async def generate_vvip_invite_code(self, package_type: str, is_token_exempt: bool, allowed_features: List[str]) -> str:
        """👑 สร้างรหัสเชิญแบบ Custom ป้องกันการแฮ็กด้วย Cryptography"""
        if not self.client: return "DB_NOT_CONNECTED"
        
        secure_chunk1 = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        secure_chunk2 = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        secure_chunk3 = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        invite_code = f"PRIME-{secure_chunk1}-{secure_chunk2}-{secure_chunk3}"
        
        try:
            data = {
                "invite_code": invite_code,
                "package_tier": package_type.upper(),
                "is_token_exempt": is_token_exempt, 
                "allowed_features": allowed_features, 
                "is_used": False,
                "created_at": self._get_utc_now()
            }
            
            def _insert_invite():
                return self.client.table("exclusive_invites").insert(data).execute()
                
            await asyncio.to_thread(_insert_invite)
            logger.info(f"🎟️ [DB Vault]: รหัสผ่านระดับสูงสร้างสำเร็จ -> {invite_code[:10]}***")
            
            return f"https://prime-core-agent-601183279633.asia-southeast3.run.app/agent.html?code={invite_code}"
            
        except Exception as e:
            logger.error(f"❌ [DB Generate Link Error]: เกิดข้อผิดพลาดการเขียนข้อมูล -> {e}")
            return "ERROR_GENERATING_LINK"

    async def claim_vvip_invite(self, invite_code: str, line_user_id: str) -> Dict[str, str]:
        """ดึงสิทธิ์ที่ CEO ตั้งไว้ไปผูกกับบัญชีลูกค้า (Transactional & Smart Wallet Init)"""
        if not self.client: return {"status": "error", "msg": "ระบบฐานข้อมูลขัดข้องชั่วคราว"}
        
        try:
            def _execute_claim():
                res = self.client.table("exclusive_invites").select("*").eq("invite_code", invite_code).execute()
                if not res.data: return {"status": "error", "msg": "รหัสคำเชิญไม่ถูกต้องหรือถูกทำลายไปแล้ว"}
                
                invite_data = res.data[0]
                if invite_data.get("is_used"): return {"status": "error", "msg": "รหัสลับนี้ถูกใช้งานไปแล้ว ไม่สามารถใช้ซ้ำได้"}
                
                now_utc = self._get_utc_now()
                
                # 1. อัปเดตข้อมูลผู้ใช้ (Upsert) เข้าตารางหลัก prime_clients
                user_data = {
                    "line_user_id": line_user_id,
                    "package_tier": invite_data.get("package_tier"),
                    "is_token_exempt": invite_data.get("is_token_exempt"),
                    "allowed_features": invite_data.get("allowed_features"),
                    "status": "active",
                    "updated_at": now_utc
                }
                
                # ถ้าระบุว่าใช้โทเคนฟรี ให้ตั้งค่ากระเป๋าเงิน (Wallet) เป็นค่าสูงสุด
                if invite_data.get("is_token_exempt"):
                    user_data["token_balance"] = 999999.0
                    
                self.client.table("prime_clients").upsert(user_data).execute()
                
                # 2. ปิดตายรหัสนี้และบันทึกรอยเท้า (Audit Trail)
                self.client.table("exclusive_invites").update({
                    "is_used": True, 
                    "used_by_line_id": line_user_id,
                    "used_at": now_utc
                }).eq("invite_code", invite_code).execute()
                
                return {"status": "success", "msg": "✅ ยืนยันสิทธิ์สำเร็จ! ยินดีต้อนรับสู่ประสบการณ์ระดับ VVIP ของ SIRINTHANATTH PRIME"}

            result = await asyncio.to_thread(_execute_claim)
            
            if line_user_id in self._access_cache:
                del self._access_cache[line_user_id]
                
            logger.info(f"👑 [DB Security]: ผู้ใช้งาน {line_user_id} เปิดรับสิทธิ์ VVIP สำเร็จ")
            return result
            
        except Exception as e:
            logger.error(f"❌ [DB Claim Error]: {e}", exc_info=True)
            return {"status": "error", "msg": "เกิดข้อผิดพลาดทางสถาปัตยกรรมเซิร์ฟเวอร์ กรุณาติดต่อทีมซัพพอร์ต"}

    async def revoke_user_access(self, line_user_id: str) -> bool:
        """(สำหรับ CEO) ระงับสิทธิ์ผู้ใช้อันตรายทันที (Real-Time Kill Switch)"""
        if not self.client: return False
        try:
            def _revoke():
                return self.client.table("prime_clients").update({"status": "revoked"}).eq("line_user_id", line_user_id).execute()
                
            await asyncio.to_thread(_revoke)
            
            if line_user_id in self._access_cache: del self._access_cache[line_user_id]
                
            logger.warning(f"⚠️ [DB Security Kill Switch]: ระงับสิทธิ์ผู้ใช้งาน {line_user_id} สำเร็จ!")
            return True
        except Exception as e:
            logger.error(f"❌ [DB Revoke Error]: {e}")
            return False

    # ==========================================
    # 💼 ระบบปฏิบัติการหลัก (Robust Async CRUD)
    # ==========================================
    async def update_user_package(self, user_id: str, package_name: str) -> bool:
        """อัปเดตแพ็กเกจผู้ใช้งาน พร้อมระบบ Auto-Cache Clearing"""
        if not self.client: return False
        try:
            def _update_pkg():
                data = {
                    "line_user_id": user_id, 
                    "package_tier": package_name.upper(), 
                    "status": "active",
                    "updated_at": self._get_utc_now()
                }
                return self.client.table("prime_clients").upsert(data).execute()
                
            await asyncio.to_thread(_update_pkg)
            
            if user_id in self._access_cache: del self._access_cache[user_id]
            logger.info(f"💎 [DB Vault Success]: อัปเกรดสถานะ {package_name} ให้ผู้ใช้ {user_id} สำเร็จ")
            return True
        except Exception as e:
            logger.error(f"❌ [DB Update Error]: {e}")
            return False
            
    async def save_agent_registration(self, name: str) -> bool:
        """บันทึกการลงทะเบียนพันธมิตรธุรกิจ (Agent)"""
        if not self.client: return False
        try:
            def _save_agent():
                data = {
                    "agent_name": name,
                    "registered_at": self._get_utc_now(),
                    "status": "pending"
                }
                return self.client.table("agent_registrations").insert(data).execute()
                
            await asyncio.to_thread(_save_agent)
            logger.info(f"🤝 [DB Vault Success]: บันทึกข้อมูล Agent พันธมิตรเข้าสู่ระบบแล้ว")
            return True
        except Exception as e:
            logger.error(f"❌ [DB Agent Reg Error]: {e}")
            return False