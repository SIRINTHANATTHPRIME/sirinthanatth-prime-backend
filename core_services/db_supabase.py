import os
import time
import random
import string
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseDatabase:
    """ระบบจัดการฐานข้อมูลหลัก เชื่อมต่อกับ Smart Wallet, PDPA Memory และระบบ VVIP"""
    
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # ใช้ Role Key เพื่อสิทธิ์สูงสุด
        self.client: Client = create_client(supabase_url, supabase_key) if supabase_url else None
        
        if not supabase_url or not supabase_key:
            print("⚠️ [Warning] Supabase URL หรือ Key ขาดหายไป")
            self.client = None
        else:
            self.client: Client = create_client(supabase_url, supabase_key)
            
    # ==========================================
    # 👑 ระบบ VVIP และ God Mode สำหรับ CEO
    # ==========================================
    def check_user_access_level(self, line_user_id: str) -> str:
        """ตรวจสอบระดับสิทธิ์ของ User (UNLIMITED / VIP / ESSENTIAL / FREE)"""
        # 1. เช็กว่าเป็นท่านประธาน (CEO) หรือไม่
        if line_user_id == os.getenv("CEO_LINE_ID"):
            return "UNLIMITED_CEO"
            
        if not self.client: return "FREE"
        
        # 2. เช็กสถานะในตาราง
        try:
            res = self.client.table("users").select("package_tier, status").eq("line_user_id", line_user_id).execute()
            if res.data and res.data[0].get("status") == "active":
                return res.data[0].get("package_tier", "FREE")
        except Exception as e:
            print(f"⚠️ [DB Check Error]: {e}")
            
        return "FREE"

    def generate_vvip_invite_code(self, package_type: str, is_token_exempt: bool, allowed_features: list) -> str:
        """👑 (สำหรับ CEO) สร้างรหัสเชิญแบบ Custom กำหนดสิทธิ์การจ่ายเงินและฟีเจอร์ได้"""
        if not self.client: return "DB_NOT_CONNECTED"
        
        invite_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        try:
            data = {
                "invite_code": invite_code,
                "package_tier": package_type,
                "is_token_exempt": is_token_exempt, # True = ใช้ฟรีตลอด, False = ต้องเติม Token
                "allowed_features": allowed_features, # เช่น ["chat", "marketing"] หรือ ["all"]
                "is_used": False,
                "created_at": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            self.client.table("exclusive_invites").insert(data).execute()
            return f"https://www.sirinthanatthprime.com/invite?code={invite_code}"
        except Exception as e:
            print(f"❌ [DB Error]: {e}")
            return "ERROR_GENERATING_LINK"

    def claim_vvip_invite(self, invite_code: str, line_user_id: str) -> dict:
        """เมื่อแขก VIP กดลิงก์ ระบบจะดึงสิทธิ์ที่ CEO ตั้งไว้ไปผูกกับบัญชีคนนั้น"""
        if not self.client: return {"status": "error", "msg": "DB Not Connected"}
        try:
            res = self.client.table("exclusive_invites").select("*").eq("invite_code", invite_code).execute()
            if not res.data: return {"status": "error", "msg": "รหัสคำเชิญไม่ถูกต้อง"}
            
            invite_data = res.data[0]
            if invite_data.get("is_used"): return {"status": "error", "msg": "รหัสนี้ถูกใช้ไปแล้ว"}
            
            # 1. อัปเดตข้อมูลผู้ใช้ พร้อมฝังเงื่อนไข "หักเงินไหม?" และ "ใช้ฟังก์ชันอะไรได้บ้าง"
            user_data = {
                "package_tier": invite_data.get("package_tier"),
                "is_token_exempt": invite_data.get("is_token_exempt"),
                "allowed_features": invite_data.get("allowed_features"),
                "status": "active"
            }
            self.client.table("users").upsert({"line_user_id": line_user_id, **user_data}).execute()
            
            # 2. ปิดตายรหัสนี้
            self.client.table("exclusive_invites").update({"is_used": True, "used_by_line_id": line_user_id}).eq("invite_code", invite_code).execute()
            
            return {"status": "success", "msg": "ยินดีต้อนรับ! คุณได้รับสิทธิ์พิเศษเรียบร้อยแล้ว"}
        except Exception as e:
            return {"status": "error", "msg": "เกิดข้อผิดพลาดในการรับสิทธิ์"}

    def revoke_user_access(self, line_user_id: str) -> bool:
        """(สำหรับ CEO) ยกเลิกสิทธิ์ผู้ใช้ทันที (เตะออกจากระบบ)"""
        if not self.client: return False
        try:
            self.client.table("users").update({"status": "revoked"}).eq("line_user_id", line_user_id).execute()
            print(f"⚠️ [DB Action] ยกเลิกสิทธิ์ User: {line_user_id} เรียบร้อยแล้ว")
            return True
        except Exception as e:
            return False

    # ==========================================
    # 💼 ระบบพื้นฐาน (ยังคงไว้เหมือนเดิม)
    # ==========================================
    def update_user_package(self, user_id: str, package_name: str) -> bool:
        if not self.client: return False
        try:
            data = {"package_tier": package_name, "status": "active"}
            # ใช้ upsert เพื่อให้ทั้งสร้างใหม่หรืออัปเดตคนเก่าได้
            self.client.table("users").upsert({"line_user_id": user_id, **data}).execute()
            print(f"👑 [DB Success] อัปเดตสถานะ {package_name} ให้ User: {user_id}")
            return True
        except Exception as e:
            return False
            
    def save_agent_registration(self, name: str, timestamp: str) -> bool:
        # โค้ดเดิม
        pass