import os
from typing import Dict, Any, List
from core_services.db_supabase import SupabaseDatabase

try:
    from supabase import create_client, Client
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
except ImportError:
    supabase = None

class SubscriptionManager:
    """
    🛡️ ระบบควบคุม Smart Wallet และสิทธิ์การใช้งาน (อัปเกรด VVIP & God Mode)
    ควบคุมการหักเงิน ตรวจสอบสิทธิ์ CEO และจัดการฟังก์ชันที่ VVIP สามารถใช้งานได้
    """

    def __init__(self):
        self.ceo_line_id = os.getenv("CEO_LINE_ID")
        self._mock_wallets: Dict[str, float] = {}

    def is_unlimited_ceo(self, user_id: str) -> bool:
        """ตรวจสอบสิทธิ์ระดับประธานบริษัท (ฟรีทุกอย่าง)"""
        return user_id == self.ceo_line_id

    # 🌟 [เพิ่มใหม่] ตรวจสอบว่าได้รับการยกเว้น Token หรือไม่
    def is_token_exempt(self, user_id: str) -> bool:
        """ตรวจสอบว่าผู้ใช้คนนี้ได้สิทธิ์ใช้ฟรี (VVIP) หรือเป็นประธานบริษัทหรือไม่"""
        # 1. ท่านประธาน ฟรีเสมอ (God Mode)
        if self.is_unlimited_ceo(user_id):
            return True
            
        # 2. เช็กในฐานข้อมูลตาราง users ว่าได้สิทธิ์ VVIP ยกเว้นการเก็บโทเค็นหรือไม่
        if supabase:
            try:
                res = supabase.table("users").select("is_token_exempt").eq("line_user_id", user_id).execute()
                if res.data and res.data[0].get("is_token_exempt") is True:
                    return True
            except Exception as e:
                print(f"⚠️ [VVIP Check Error]: {e}")
                
        return False

    # 🌟 [เพิ่มใหม่] ตรวจสอบสิทธิ์การใช้งานฟังก์ชันแยกตามบุคคล
    def check_feature_access(self, user_id: str, feature_name: str) -> bool:
        """ตรวจสอบว่าผู้ใช้มีสิทธิ์ใช้ฟังก์ชันนี้หรือไม่ (อิงจาก allowed_features)"""
        # ประธานบริษัทใช้ได้ทุกฟังก์ชัน
        if self.is_unlimited_ceo(user_id):
            return True
            
        if supabase:
            try:
                res = supabase.table("users").select("allowed_features").eq("line_user_id", user_id).execute()
                if res.data:
                    allowed = res.data[0].get("allowed_features", [])
                    # ถ้า allowed_features เป็นค่าว่าง หรือมีคำว่า "all" หรือมีชื่อฟีเจอร์นั้นๆ อยู่
                    if not allowed or "all" in allowed or feature_name in allowed:
                        return True
                    return False
            except Exception as e:
                print(f"⚠️ [Feature Access Check Error]: {e}")
                
        # หากไม่มี Supabase อนุญาตให้ผ่านไปก่อนเพื่อไม่ให้ระบบสะดุด
        return True

    def get_wallet_balance(self, user_id: str) -> float:
        # ถ้าเป็น CEO หรือ VVIP ที่ได้สิทธิ์ฟรี ให้มองว่ามีเงินอนันต์ (Bypass)
        if self.is_token_exempt(user_id):
            return 9999999.0

        if supabase:
            try:
                res = supabase.table("users_wallet").select("balance").eq("user_id", user_id).execute()
                if res.data: return float(res.data[0].get("balance", 0.0))
            except Exception as e:
                print(f"⚠️ [Wallet Error]: {e}")
        return self._mock_wallets.get(user_id, 500.0)

    def deduct_media_fee(self, user_id: str, amount: float = 49.0) -> Dict[str, Any]:
        """หักค่าบริการผลิตสื่อ (Media / Video 4K)"""
        # 👑 ถ้าเป็นท่านประธาน หรือ VVIP ที่ได้สิทธิ์ฟรี -> ผ่านฉลุย ไม่หักเงิน
        if self.is_token_exempt(user_id):
            print(f"👑 [God Mode / VVIP Bypass]: ไม่มีการหัก Token สื่อ 4K สำหรับ {user_id}")
            return {"status": "success", "new_balance": "UNLIMITED"}

        balance = self.get_wallet_balance(user_id)
        
        if balance < amount:
            return {
                "status": "error", 
                "msg": f"ยอดเงินใน Smart Wallet มี {balance:.2f} บาท ไม่เพียงพอ ({amount:.2f} บาท) กรุณากดปุ่ม 'เติมเงิน' ที่เมนูด้านล่างครับ"
            }
        
        new_balance = balance - amount
        
        # บันทึกยอดที่หักแล้วกลับลง Supabase
        if supabase:
            try:
                supabase.table("users_wallet").update({"balance": new_balance}).eq("user_id", user_id).execute()
            except Exception: pass
        else:
            self._mock_wallets[user_id] = new_balance

        print(f"🎬 [Wallet]: หักค่าเรนเดอร์สื่อ {amount} บาท สำเร็จ (ยอดคงเหลือ {new_balance:.2f})")
        return {"status": "success", "new_balance": new_balance}

    def deduct_shipping_fee(self, user_id: str, amount: float = 12.0) -> Dict[str, Any]:
        """หักเงินค่าส่ง Flash Express"""
        # 👑 ถ้าเป็นท่านประธาน หรือ VVIP ที่ได้สิทธิ์ฟรี -> ผ่านฉลุย ไม่หักเงิน
        if self.is_token_exempt(user_id):
            print(f"👑 [God Mode / VVIP Bypass]: ไม่มีการหัก Token ค่าส่ง Flash สำหรับ {user_id}")
            return {"status": "success", "new_balance": "UNLIMITED"}

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

        print(f"📦 [Wallet]: หักค่าส่ง Flash Express {amount} บาท สำเร็จ (ยอดคงเหลือ {new_balance:.2f})")
        return {"status": "success", "new_balance": new_balance}