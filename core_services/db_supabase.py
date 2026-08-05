import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseDatabase:
    """ระบบจัดการฐานข้อมูลหลัก เชื่อมต่อกับ Smart Wallet และ PDPA Memory"""
    
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # ใช้ Role Key เพื่อสิทธิ์สูงสุด
        
        if not supabase_url or not supabase_key:
            print("⚠️ [Warning] Supabase URL หรือ Key ขาดหายไป")
            self.client = None
        else:
            self.client: Client = create_client(supabase_url, supabase_key)

    # ==========================================
    # 💼 1. ระบบตัวแทน (Agent Registration)
    # ==========================================
    def save_agent_registration(self, name: str, timestamp: str) -> bool:
        if not self.client: return False
        try:
            data = {"name": name, "status": "pending", "registered_at": timestamp}
            self.client.table("agents").insert(data).execute()
            print(f"📥 [DB Success] บันทึกตัวแทนใหม่: {name}")
            return True
        except Exception as e:
            print(f"❌ [DB Error]: {e}")
            return False

    # ==========================================
    # 💰 2. ระบบ Smart Wallet (อัปเดตใหม่เป็นระบบเรทเงินบาท)
    # ==========================================
    def get_wallet_balance(self, user_id: str) -> float:
        """ดึงยอดเงินคงเหลือจาก Wallet"""
        if not self.client: return 500.0 # Mock data กรณีเชื่อมต่อไม่ได้
        try:
            res = self.client.table("users_wallet").select("balance").eq("user_id", user_id).execute()
            if res.data:
                return float(res.data[0].get("balance", 0.0))
            else:
                # ถ้าเป็นลูกค้าใหม่ แจกเงินทดลองระบบ 500 บาท
                self.client.table("users_wallet").insert({"user_id": user_id, "balance": 500.0}).execute()
                return 500.0
        except Exception as e:
            return 500.0

    def deduct_wallet_balance(self, user_id: str, amount: float) -> bool:
        """หักเงิน Wallet หลัง AI ปฏิบัติงานเสร็จ"""
        if not self.client: return True
        try:
            current = self.get_wallet_balance(user_id)
            if current >= amount:
                new_balance = current - amount
                self.client.table("users_wallet").update({"balance": new_balance}).eq("user_id", user_id).execute()
                return True
            return False
        except Exception as e:
            print(f"❌ [DB Error] Deduct wallet error: {e}")
            return False

    def topup_wallet(self, user_id: str, amount_paid: float) -> bool:
        """เติมเงิน Wallet"""
        if not self.client: return False
        try:
            current = self.get_wallet_balance(user_id)
            self.client.table("users_wallet").update({"balance": current + amount_paid}).eq("user_id", user_id).execute()
            print(f"💳 [DB Success] เติมเงิน {amount_paid} บาท ให้ User: {user_id}")
            return True
        except Exception as e:
            return False

    def update_subscription(self, user_id: str, package_name: str) -> bool:
        """อัปเดตสถานะ VIP / แพ็กเกจ"""
        if not self.client: return False
        try:
            data = {"package_tier": package_name, "status": "active"}
            self.client.table("users").update(data).eq("line_user_id", user_id).execute()
            print(f"👑 [DB Success] อัปเดตสถานะ {package_name} ให้ User: {user_id}")
            return True
        except Exception as e:
            return False

    # ==========================================
    # 🧠 3. ระบบความจำ (RAG Memory)
    # ==========================================
    def save_chat_memory(self, user_id: str, role: str, text: str) -> bool:
        if not self.client: return False
        try:
            self.client.table("chat_history").insert({"line_user_id": user_id, "role": role, "message": text}).execute()
            return True
        except Exception as e:
            return False

    def get_recent_memory(self, user_id: str, limit: int = 5) -> str:
        if not self.client: return ""
        try:
            res = self.client.table("chat_history").select("role, message").eq("line_user_id", user_id).order("created_at", desc=True).limit(limit).execute()
            if not res.data: return ""
            formatted_memory = "\n".join([f"{item['role']}: {item['message']}" for item in res.data[::-1]])
            return f"ประวัติการสนทนาก่อนหน้า:\n{formatted_memory}\n"
        except Exception as e:
            print(f"❌ [DB Error] Get recent memory error: {e}")
            return ""