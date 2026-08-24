import os
import logging
from typing import Dict, Any
from core_services.db_supabase import SupabaseDatabase

logger = logging.getLogger("SubscriptionManager")

try:
    from supabase import create_client, Client
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
except ImportError:
    supabase = None

class SubscriptionManager:
    """
    🛡️ ระบบควบคุม Smart Wallet และสิทธิ์การใช้งาน (อัปเกรด Security 100%)
    ควบคุมการหักเงิน ตรวจสอบสิทธิ์ VVIP และจัดการฟังก์ชันที่ได้รับอนุญาต
    """

    def __init__(self):
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "")
        self._mock_wallets: Dict[str, float] = {}

    def is_unlimited_ceo(self, user_id: str) -> bool:
        """ตรวจสอบสิทธิ์ระดับบริหาร (Master Override)"""
        return user_id in [self.ceo_line_id, self.master_admin_id] if user_id else False

    def is_token_exempt(self, user_id: str) -> bool:
        """ตรวจสอบว่าผู้ใช้คนนี้ได้สิทธิ์ใช้ฟรี (VVIP / CEO) หรือไม่"""
        if self.is_unlimited_ceo(user_id):
            return True
            
        if supabase:
            try:
                res = supabase.table("users").select("is_token_exempt").eq("line_user_id", user_id).execute()
                if res.data and res.data[0].get("is_token_exempt") is True:
                    return True
            except Exception as e:
                logger.warning(f"⚠️ [VVIP Check Warning]: {e}")
                
        return False

    def check_feature_access(self, user_id: str, feature_name: str) -> bool:
        """ตรวจสอบสิทธิ์การใช้งานฟังก์ชันตามแพ็กเกจ (Feature Gate)"""
        if self.is_unlimited_ceo(user_id):
            return True
            
        if supabase:
            try:
                res = supabase.table("users").select("allowed_features").eq("line_user_id", user_id).execute()
                if res.data:
                    allowed = res.data[0].get("allowed_features", [])
                    if not allowed or "all" in allowed or feature_name in allowed:
                        return True
                    return False
            except Exception as e:
                logger.warning(f"⚠️ [Feature Access Warning]: {e}")
                
        return True # Fallback อนุญาตให้ใช้ชั่วคราวเพื่อไม่ให้ระบบสะดุด

    def get_wallet_balance(self, user_id: str) -> float:
        """ดึงยอดเงินคงเหลือจากฐานข้อมูล"""
        if self.is_token_exempt(user_id):
            return 9999999.0 # God Mode

        if supabase:
            try:
                res = supabase.table("users_wallet").select("balance").eq("user_id", user_id).execute()
                if res.data: 
                    return float(res.data[0].get("balance", 0.0))
            except Exception as e:
                logger.warning(f"⚠️ [Wallet Fetch Warning]: {e}")
        return self._mock_wallets.get(user_id, 500.0) # ค่าเริ่มต้น

    def deduct_media_fee(self, user_id: str, amount: float = 49.0) -> Dict[str, Any]:
        """หักค่าบริการผลิตสื่อ 4K"""
        if self.is_token_exempt(user_id):
            logger.info(f"👑 [God Mode]: Bypass ค่าสื่อมัลติมีเดียสำหรับ {user_id}")
            return {"status": "success", "new_balance": "UNLIMITED"}

        balance = self.get_wallet_balance(user_id)
        if balance < amount:
            return {
                "status": "error", 
                "msg": f"ยอดเงินใน Smart Wallet มี {balance:.2f} บาท ไม่เพียงพอ ({amount:.2f} บาท) กรุณากดปุ่ม 'เติมเงิน' ด้านล่างครับ"
            }
        
        new_balance = balance - amount
        if supabase:
            try:
                supabase.table("users_wallet").update({"balance": new_balance}).eq("user_id", user_id).execute()
            except Exception as e:
                logger.error(f"❌ [DB Update Error]: หักเงินไม่เข้า DB -> {e}")
        else:
            self._mock_wallets[user_id] = new_balance

        logger.info(f"🎬 [Wallet]: หักค่าเรนเดอร์สื่อ {amount} บาท สำเร็จ (คงเหลือ {new_balance:.2f})")
        return {"status": "success", "new_balance": new_balance}

    def deduct_shipping_fee(self, user_id: str, amount: float = 12.0) -> Dict[str, Any]:
        """หักเงินค่าระบบเรียกขนส่งอัตโนมัติ"""
        if self.is_token_exempt(user_id):
            logger.info(f"👑 [God Mode]: Bypass ค่าขนส่งโลจิสติกส์สำหรับ {user_id}")
            return {"status": "success", "new_balance": "UNLIMITED"}

        balance = self.get_wallet_balance(user_id)
        if balance < amount:
            return {"status": "error", "msg": f"ยอดเงินไม่พอค่าทำใบปะหน้าขนส่ง ({amount:.2f} บาท) กรุณาเติมเงินครับ"}
        
        new_balance = balance - amount
        if supabase:
            try:
                supabase.table("users_wallet").update({"balance": new_balance}).eq("user_id", user_id).execute()
            except Exception as e:
                logger.error(f"❌ [DB Update Error]: หักเงินไม่เข้า DB -> {e}")
        else:
            self._mock_wallets[user_id] = new_balance

        logger.info(f"📦 [Wallet]: หักค่าระบบโลจิสติกส์ {amount} บาท สำเร็จ (คงเหลือ {new_balance:.2f})")
        return {"status": "success", "new_balance": new_balance}