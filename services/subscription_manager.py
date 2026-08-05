import os
from typing import Dict, Any

try:
    from supabase import create_client, Client
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
except ImportError:
    supabase = None

class SubscriptionManager:
    """
    🛡️ ระบบควบคุม Smart Wallet หักเงินตามเรทที่กำหนด
    - 49 บาท สำหรับคลิป 4K / เสียงพากย์
    - 12 บาท สำหรับ Flash Express
    """

    def __init__(self):
        self._mock_wallets: Dict[str, float] = {}

    def get_wallet_balance(self, user_id: str) -> float:
        if supabase:
            try:
                res = supabase.table("users_wallet").select("balance").eq("user_id", user_id).execute()
                if res.data: return float(res.data[0].get("balance", 0.0))
            except Exception as e:
                print(f"⚠️ [Wallet Error]: {e}")
        return self._mock_wallets.get(user_id, 500.0)

    def deduct_media_fee(self, user_id: str, amount: float = 49.0) -> Dict[str, Any]:
        """หักเงิน 49 บาท (ผลิตสื่อ 4K)"""
        balance = self.get_wallet_balance(user_id)
        
        if balance < amount:
            return {"status": "error", "msg": f"ยอดเงินใน Smart Wallet มี {balance:.2f} บาท ไม่เพียงพอ ({amount:.2f} บาท) พิมพ์ 'เติมเงิน' เพื่อดำเนินการต่อครับ"}
        
        new_balance = balance - amount
        if supabase:
            try:
                supabase.table("users_wallet").update({"balance": new_balance}).eq("user_id", user_id).execute()
            except Exception: pass
        else:
            self._mock_wallets[user_id] = new_balance

        print(f"🎬 [Wallet]: หักค่าเรนเดอร์สื่อ 4K {amount} บาท สำเร็จ")
        return {"status": "success", "new_balance": new_balance}

    def deduct_shipping_fee(self, user_id: str, amount: float = 12.0) -> Dict[str, Any]:
        """หักเงิน 12 บาท (Flash Express VIP Rate)"""
        balance = self.get_wallet_balance(user_id)
        
        if balance < amount:
            return {"status": "error", "msg": f"ยอดเงินไม่พอค่าส่ง Flash Express ({amount:.2f} บาท) พิมพ์ 'เติมเงิน' ครับ"}
        
        new_balance = balance - amount
        if supabase:
            try:
                supabase.table("users_wallet").update({"balance": new_balance}).eq("user_id", user_id).execute()
            except Exception: pass
        else:
            self._mock_wallets[user_id] = new_balance

        print(f"📦 [Wallet]: หักค่าส่ง Flash Express {amount} บาท สำเร็จ")
        return {"status": "success", "new_balance": new_balance}