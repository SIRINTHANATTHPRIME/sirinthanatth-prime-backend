import os
import logging
from typing import Dict, Any

logger = logging.getLogger("SubscriptionManager")

try:
    from supabase import create_client, Client
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY", "")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
except ImportError:
    supabase = None

class SubscriptionManager:
    """
    🛡️ ระบบควบคุม Smart Wallet และสิทธิ์การใช้งาน (Subscription & Access Control)
    อัปเกรด: ผสานระบบฐานข้อมูล prime_clients ให้ตรงกับ Core Engine 100% 
    และเพิ่มระบบวิเคราะห์สิทธิ์การเข้าถึงระดับ Enterprise
    """

    def __init__(self):
        # 👑 รับค่า LINE ID ผู้บริหารสูงสุด
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self._mock_wallets: Dict[str, float] = {}

    def is_unlimited_ceo(self, user_id: str) -> bool:
        """🔒 ตรวจสอบสิทธิ์ระดับบริหารสูงสุด (Master Override)"""
        return user_id in [self.ceo_line_id, self.master_admin_id] if user_id else False

    def is_token_exempt(self, user_id: str) -> bool:
        """👑 ตรวจสอบว่าผู้ใช้คนนี้ได้สิทธิ์ใช้ฟรี (VVIP / CEO / ADMIN) หรือไม่"""
        if self.is_unlimited_ceo(user_id):
            return True
            
        if supabase:
            try:
                res = supabase.table("prime_clients").select("package_tier, role").eq("line_user_id", user_id).execute()
                if res.data:
                    tier = res.data[0].get("package_tier", "").upper()
                    role = res.data[0].get("role", "").lower()
                    if tier in ["VIP_FOUNDER", "VIP", "ADMIN"] or role in ["admin", "vip", "founder"]:
                        return True
            except Exception as e:
                logger.warning(f"⚠️ [VVIP Check Warning]: {e}")
                
        return False

    def check_feature_access(self, user_id: str, feature_name: str) -> bool:
        """🚦 ตรวจสอบสิทธิ์การใช้งานฟังก์ชันตามแพ็กเกจ (Feature Gate)"""
        if self.is_unlimited_ceo(user_id):
            return True
            
        if supabase:
            try:
                res = supabase.table("prime_clients").select("allowed_features, package_tier").eq("line_user_id", user_id).execute()
                if res.data:
                    # 1. เช็กสิทธิ์ฟีเจอร์แบบเจาะจงรายบุคคล (Custom Whitelist)
                    allowed = res.data[0].get("allowed_features") or []
                    if "all" in allowed or feature_name in allowed:
                        return True
                    
                    # 2. เช็กสิทธิ์ตาม Package Tier (Dynamic Fallback Rules)
                    tier = res.data[0].get("package_tier", "ESSENTIAL").upper()
                    
                    # ตัวอย่าง: สงวนงานหนักอย่าง media_render ไว้ให้แพ็กเกจระดับบน
                    if feature_name == "media_render" and tier not in ["ENTERPRISE", "VIP_FOUNDER", "VIP"]:
                        return False 
                    
                    return True
            except Exception as e:
                logger.warning(f"⚠️ [Feature Access Warning]: {e}")
                
        return True # Fallback: อนุญาตให้ใช้ชั่วคราวเพื่อไม่ให้ระบบลูกค้าสะดุด (Graceful Degradation)

    def get_wallet_balance(self, user_id: str) -> float:
        """💰 ดึงยอดเงินคงเหลือ (PRIME CREDITS) จากฐานข้อมูลกลาง"""
        if self.is_token_exempt(user_id):
            return 9999999.0 # God Mode (Unlimited Credits)

        if supabase:
            try:
                # อัปเกรด: เปลี่ยนมาดึงค่าจากตาราง prime_clients เพื่อให้ซิงก์กับ Stripe Webhook
                res = supabase.table("prime_clients").select("token_balance").eq("line_user_id", user_id).execute()
                if res.data: 
                    return float(res.data[0].get("token_balance", 0.0))
            except Exception as e:
                logger.error(f"❌ [Wallet Fetch Error]: {e}")
        
        return self._mock_wallets.get(user_id, 0.0) # ค่าเริ่มต้น

    def deduct_media_fee(self, user_id: str, amount: float = 49.0) -> Dict[str, Any]:
        """🎬 หักค่าบริการผลิตสื่อหนัก (เช่น วิดีโอ 4K) โดยซิงก์กับ Smart Wallet"""
        if self.is_token_exempt(user_id):
            logger.info(f"👑 [God Mode]: Bypass ตัดเครดิตสื่อมัลติมีเดียสำหรับ {user_id}")
            return {"status": "success", "new_balance": "UNLIMITED"}

        balance = self.get_wallet_balance(user_id)
        if balance < amount:
            return {
                "status": "error", 
                "msg": f"⚠️ ยอด PRIME CREDITS ใน Smart Wallet มี {balance:.2f} ไม่เพียงพอ ({amount:.2f} เครดิต) กรุณาเติมเครดิตผ่านเมนูครับ"
            }
        
        new_balance = balance - amount
        if supabase:
            try:
                supabase.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
            except Exception as e:
                logger.error(f"❌ [DB Update Error]: ระบบตัดเครดิตล่าช้า -> {e}")
        else:
            self._mock_wallets[user_id] = new_balance

        logger.info(f"🎬 [Wallet Engine]: หักค่าเรนเดอร์สื่อ 4K จำนวน {amount} เครดิต สำเร็จ (คงเหลือ {new_balance:.2f})")
        return {"status": "success", "new_balance": new_balance}

    def deduct_shipping_fee(self, user_id: str, amount: float = 12.0) -> Dict[str, Any]:
        """📦 หักเงินค่าระบบออกใบปะหน้าและเรียกขนส่งอัตโนมัติ (Flash Express)"""
        if self.is_token_exempt(user_id):
            logger.info(f"👑 [God Mode]: Bypass ตัดเครดิตค่าขนส่งโลจิสติกส์สำหรับ {user_id}")
            return {"status": "success", "new_balance": "UNLIMITED"}

        balance = self.get_wallet_balance(user_id)
        if balance < amount:
            return {
                "status": "error", 
                "msg": f"⚠️ ยอดเครดิตไม่พอค่าออกใบปะหน้าขนส่ง ({amount:.2f} เครดิต) กรุณาเติมเงินเข้าระบบครับ"
            }
        
        new_balance = balance - amount
        if supabase:
            try:
                supabase.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
            except Exception as e:
                logger.error(f"❌ [DB Update Error]: ระบบตัดเครดิตขนส่งล่าช้า -> {e}")
        else:
            self._mock_wallets[user_id] = new_balance

        logger.info(f"📦 [Wallet Engine]: หักค่าบริการ Logistics จำนวน {amount} เครดิต สำเร็จ (คงเหลือ {new_balance:.2f})")
        return {"status": "success", "new_balance": new_balance}