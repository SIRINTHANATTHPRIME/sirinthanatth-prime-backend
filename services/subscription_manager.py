import os
import time
import logging
import asyncio
import threading
from collections import defaultdict
from typing import Dict, Any, Optional
from supabase import create_client, Client

logger = logging.getLogger("SubscriptionManager")

class SubscriptionManager:
    """
    🛡️ ระบบควบคุม Smart Wallet และสิทธิ์การใช้งานระดับ Enterprise
    อัปเกรด: Per-User Locks, TTL Caching, Singleton Architecture, และ Zero-Latency Access
    """
    _instance = None
    _init_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """🚀 Singleton Architecture: บังคับใช้ท่อ Connection เดียวทั่วทั้งเซิร์ฟเวอร์"""
        if not cls._instance:
            with cls._init_lock:
                if not cls._instance:
                    cls._instance = super(SubscriptionManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # ป้องกันการ Init ซ้ำซ้อนเมื่อเรียกใช้คลาสหลายรอบ
        if getattr(self, '_initialized', False): return
        
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        
        # 🧠 ระบบ Caching ลดภาระ Database
        self._access_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 300.0 # แคชสิทธิ์การใช้งาน 5 นาที (300 วินาที)
        
        # 🔒 ระบบแยก Lock รายบุคคล ป้องกันคอขวดและ Race Condition แบบ 100%
        self._user_locks = defaultdict(asyncio.Lock)
        self._mock_wallets: Dict[str, float] = {}

        # เชื่อมต่อ Supabase
        supa_url = os.getenv("SUPABASE_URL", "")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY", "")
        self.supabase: Optional[Client] = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        self._initialized = True

    def is_unlimited_ceo(self, user_id: str) -> bool:
        """🔒 ตรวจสอบสิทธิ์ระดับบริหารสูงสุด (Master Override)"""
        return user_id in [self.ceo_line_id, self.master_admin_id] if user_id else False

    async def is_token_exempt(self, user_id: str) -> bool:
        """👑 ตรวจสอบว่าผู้ใช้คนนี้ได้สิทธิ์ใช้ฟรี (VVIP / CEO / ADMIN) หรือไม่ พร้อมระบบ Cache"""
        if self.is_unlimited_ceo(user_id):
            return True
            
        # ⚡ ตรวจสอบจาก Cache ก่อนเพื่อความเร็วระดับเสี้ยววินาที
        now = time.time()
        cached = self._access_cache.get(f"exempt_{user_id}")
        if cached and (now - cached["timestamp"] < self._cache_ttl):
            return cached["status"]
            
        if self.supabase:
            try:
                def _query():
                    return self.supabase.table("prime_clients").select("package_tier, role").eq("line_user_id", user_id).execute()
                
                res = await asyncio.to_thread(_query)
                if res.data:
                    tier = res.data[0].get("package_tier", "").upper()
                    role = res.data[0].get("role", "").lower()
                    is_exempt = tier in ["VIP_FOUNDER", "VIP", "ADMIN"] or role in ["admin", "vip", "founder"]
                    
                    # บันทึกผลลง Cache
                    self._access_cache[f"exempt_{user_id}"] = {"status": is_exempt, "timestamp": now}
                    return is_exempt
            except Exception as e:
                logger.warning(f"⚠️ [VVIP Check Warning]: {e}")
                
        return False

    async def check_feature_access(self, user_id: str, feature_name: str) -> bool:
        """🚦 ตรวจสอบสิทธิ์การใช้งานฟังก์ชันตามแพ็กเกจ (Feature Gate) พร้อมระบบ Cache"""
        if self.is_unlimited_ceo(user_id):
            return True
            
        now = time.time()
        cache_key = f"feature_{user_id}_{feature_name}"
        cached = self._access_cache.get(cache_key)
        if cached and (now - cached["timestamp"] < self._cache_ttl):
            return cached["status"]
            
        if self.supabase:
            try:
                def _query():
                    return self.supabase.table("prime_clients").select("allowed_features, package_tier").eq("line_user_id", user_id).execute()
                
                res = await asyncio.to_thread(_query)
                if res.data:
                    allowed = res.data[0].get("allowed_features") or []
                    has_access = True
                    
                    if "all" not in allowed and feature_name not in allowed:
                        tier = res.data[0].get("package_tier", "ESSENTIAL").upper()
                        if feature_name == "media_render" and tier not in ["ENTERPRISE", "VIP_FOUNDER", "VIP"]:
                            has_access = False 
                            
                    self._access_cache[cache_key] = {"status": has_access, "timestamp": now}
                    return has_access
            except Exception as e:
                logger.warning(f"⚠️ [Feature Access Warning]: {e}")
                
        return True # Graceful Degradation: หากฐานข้อมูลมีปัญหา ให้อนุญาตใช้ชั่วคราวเพื่อไม่ให้ระบบล่ม

    async def get_wallet_balance(self, user_id: str) -> float:
        """💰 ดึงยอดเงินคงเหลือ (PRIME CREDITS) แบบ Real-time (ไม่ใช้ Cache เพื่อความแม่นยำ)"""
        if await self.is_token_exempt(user_id):
            return 9999999.0 # God Mode (Unlimited Credits)

        if self.supabase:
            try:
                def _query():
                    return self.supabase.table("prime_clients").select("token_balance").eq("line_user_id", user_id).execute()
                
                res = await asyncio.to_thread(_query)
                if res.data: 
                    return float(res.data[0].get("token_balance", 0.0))
            except Exception as e:
                logger.error(f"❌ [Wallet Fetch Error]: {e}")
        
        return self._mock_wallets.get(user_id, 0.0)

    async def deduct_wallet_balance(self, user_id: str, amount: float, description: str = "Service Fee") -> Dict[str, Any]:
        """⚙️ ระบบหักเครดิตส่วนกลางแบบ Per-User Atomic Lock ป้องกันยอดติดลบเด็ดขาด"""
        if await self.is_token_exempt(user_id):
            logger.info(f"👑 [God Mode]: Bypass ตัดเครดิต ({description}) สำหรับผู้บริหาร {user_id}")
            return {"status": "success", "new_balance": "UNLIMITED"}

        # 🔒 ล็อกเฉพาะคิวของ User คนนี้เท่านั้น (คนอื่นทำรายการต่อได้ปกติ)
        async with self._user_locks[user_id]:
            balance = await self.get_wallet_balance(user_id)
            if balance < amount:
                return {
                    "status": "error", 
                    "msg": f"⚠️ ยอด PRIME CREDITS ไม่เพียงพอ ({balance:.2f}/{amount:.2f} เครดิต) กรุณาเติมเงินผ่านเมนูครับ"
                }
            
            new_balance = balance - amount

            if self.supabase:
                try:
                    def _update():
                        return self.supabase.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                    
                    await asyncio.to_thread(_update)
                except Exception as e:
                    logger.error(f"❌ [DB Update Error]: ตัดเครดิตล้มเหลว -> {e}")
                    return {"status": "error", "msg": "⚠️ ระบบฐานข้อมูลขัดข้องชั่วคราว ไม่สามารถหักเครดิตได้"}
            else:
                self._mock_wallets[user_id] = new_balance

            logger.info(f"💳 [Wallet Engine]: หักค่าบริการ '{description}' จำนวน {amount} เครดิตสำเร็จ (คงเหลือ {new_balance:.2f})")
            return {"status": "success", "new_balance": new_balance}

    async def deduct_media_fee(self, user_id: str, amount: float = 49.0) -> Dict[str, Any]:
        """🎬 หักค่าบริการผลิตสื่อหนัก (เช่น วิดีโอ 4K)"""
        return await self.deduct_wallet_balance(user_id, amount, description="Media Render 4K")

    async def deduct_shipping_fee(self, user_id: str, amount: float = 12.0) -> Dict[str, Any]:
        """📦 หักค่าบริการออกใบปะหน้าและขนส่ง (Logistics)"""
        return await self.deduct_wallet_balance(user_id, amount, description="Logistics Shipping Label")