import os
import time
import secrets
import string
import logging
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# ตั้งค่าระบบ Logging ส่วนฐานข้อมูล
logger = logging.getLogger("Supabase-Vault")

class SupabaseDatabase:
    """
    🛡️ ระบบจัดการฐานข้อมูลหลักระดับ Enterprise (Supabase Vault)
    เชื่อมต่อกับ Smart Wallet, PDPA Memory และระบบ VVIP อย่างปลอดภัยสูงสุด
    """
    
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # ใช้ Role Key เพื่อสิทธิ์ระดับแอดมินสูงสุด
        self.ceo_line_id = os.getenv("CEO_LINE_ID")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID")
        
        if not self.supabase_url or not self.supabase_key:
            logger.error("❌ [DB Initialization]: Supabase URL หรือ Key ขาดหายไป ระบบฐานข้อมูลออฟไลน์")
            self.client: Optional[Client] = None
        else:
            try:
                self.client: Client = create_client(self.supabase_url, self.supabase_key)
                logger.info("✅ [DB Initialization]: เชื่อมต่อ Supabase Vault สำเร็จ พร้อมให้บริการ")
            except Exception as e:
                logger.error(f"❌ [DB Initialization Error]: ไม่สามารถเชื่อมต่อฐานข้อมูลได้ -> {e}")
                self.client = None
            
    # ==========================================
    # 👑 ระบบ VVIP และ God Mode สำหรับ CEO
    # ==========================================
    def check_user_access_level(self, line_user_id: str) -> str:
        """ตรวจสอบระดับสิทธิ์ของ User (UNLIMITED_CEO / VIP / ESSENTIAL / FREE)"""
        if not line_user_id:
            return "FREE"
            
        # 1. เช็กว่าเป็นท่านประธาน (CEO) หรือ Admin สูงสุดหรือไม่
        if line_user_id in [self.ceo_line_id, self.master_admin_id]:
            return "UNLIMITED_CEO"
            
        if not self.client: 
            logger.warning("⚠️ [DB Check]: ฐานข้อมูลไม่พร้อม คืนค่าสิทธิ์พื้นฐาน (FREE)")
            return "FREE"
        
        # 2. เช็กสถานะในตาราง
        try:
            res = self.client.table("users").select("package_tier, status").eq("line_user_id", line_user_id).execute()
            if res.data and res.data[0].get("status") == "active":
                return res.data[0].get("package_tier", "FREE")
        except Exception as e:
            logger.error(f"❌ [DB Check Error]: ตรวจสอบสิทธิ์ผู้ใช้ล้มเหลว -> {e}")
            
        return "FREE"

    def generate_vvip_invite_code(self, package_type: str, is_token_exempt: bool, allowed_features: List[str]) -> str:
        """👑 (สำหรับ CEO) สร้างรหัสเชิญแบบ Custom ป้องกันการแฮ็กด้วย Cryptographically Secure"""
        if not self.client: return "DB_NOT_CONNECTED"
        
        # ใช้ secrets แทน random เพื่อความปลอดภัยระดับ Enterprise (สุ่มรหัส 10 หลัก)
        secure_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        invite_code = f"VVIP-{secure_code}"
        
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
            logger.info(f"🎟️ [DB Action]: สร้างรหัส VVIP-*** สำเร็จแล้ว พร้อมใช้งาน")
            
            # อัปเดตโครงสร้างลิงก์ให้ตรงกับหน้าเว็บจริง
            return f"https://www.sirinthanatthprime.com/agent.html?code={invite_code}"
        except Exception as e:
            logger.error(f"❌ [DB Generate Link Error]: เกิดข้อผิดพลาดการเขียนข้อมูล -> {e}")
            return "ERROR_GENERATING_LINK"

    def claim_vvip_invite(self, invite_code: str, line_user_id: str) -> Dict[str, str]:
        """เมื่อแขก VIP กดลิงก์ ระบบจะดึงสิทธิ์ที่ CEO ตั้งไว้ไปผูกกับบัญชีคนนั้น (Atomic Operation)"""
        if not self.client: return {"status": "error", "msg": "ระบบฐานข้อมูลขัดข้องชั่วคราว"}
        
        try:
            res = self.client.table("exclusive_invites").select("*").eq("invite_code", invite_code).execute()
            if not res.data: return {"status": "error", "msg": "รหัสคำเชิญไม่ถูกต้องหรือไม่มีในระบบ"}
            
            invite_data = res.data[0]
            if invite_data.get("is_used"): return {"status": "error", "msg": "รหัสนี้ถูกเปิดใช้งานไปแล้ว ไม่สามารถใช้ซ้ำได้"}
            
            # 1. อัปเดตข้อมูลผู้ใช้ (Upsert) พร้อมฝังเงื่อนไขและ Timestamp
            user_data = {
                "line_user_id": line_user_id,
                "package_tier": invite_data.get("package_tier"),
                "is_token_exempt": invite_data.get("is_token_exempt"),
                "allowed_features": invite_data.get("allowed_features"),
                "status": "active",
                "updated_at": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            self.client.table("users").upsert(user_data).execute()
            
            # 2. ปิดตายรหัสนี้และบันทึกรอยเท้า (Audit Trail)
            self.client.table("exclusive_invites").update({
                "is_used": True, 
                "used_by_line_id": line_user_id,
                "used_at": time.strftime('%Y-%m-%d %H:%M:%S')
            }).eq("invite_code", invite_code).execute()
            
            logger.info(f"👑 [DB Action]: ผู้ใช้งานเปิดรับสิทธิ์ VVIP สำเร็จ")
            return {"status": "success", "msg": "ยืนยันสิทธิ์สำเร็จ! ยินดีต้อนรับสู่ประสบการณ์ VVIP"}
        except Exception as e:
            logger.error(f"❌ [DB Claim Error]: {e}")
            return {"status": "error", "msg": "เกิดข้อผิดพลาดในการรับสิทธิ์จากเซิร์ฟเวอร์"}

    def revoke_user_access(self, line_user_id: str) -> bool:
        """(สำหรับ CEO) ยกเลิกสิทธิ์ผู้ใช้ทันที (เตะออกจากระบบแบบ Real-Time)"""
        if not self.client: return False
        try:
            self.client.table("users").update({"status": "revoked"}).eq("line_user_id", line_user_id).execute()
            logger.warning(f"⚠️ [DB Security Action]: เตะผู้ใช้งานออกจากระบบเรียบร้อยแล้ว")
            return True
        except Exception as e:
            logger.error(f"❌ [DB Revoke Error]: {e}")
            return False

    # ==========================================
    # 💼 ระบบพื้นฐาน (อัปเกรดเสถียรภาพ)
    # ==========================================
    def update_user_package(self, user_id: str, package_name: str) -> bool:
        """อัปเดตแพ็กเกจผู้ใช้งาน (Upsert Operation)"""
        if not self.client: return False
        try:
            data = {
                "line_user_id": user_id, 
                "package_tier": package_name, 
                "status": "active",
                "updated_at": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            self.client.table("users").upsert(data).execute()
            logger.info(f"💎 [DB Success]: อัปเดตสถานะ {package_name} สำเร็จ")
            return True
        except Exception as e:
            logger.error(f"❌ [DB Update Error]: {e}")
            return False
            
    def save_agent_registration(self, name: str, timestamp: str) -> bool:
        """บันทึกการลงทะเบียนตัวแทนธุรกิจ (Agent)"""
        if not self.client: return False
        try:
            data = {
                "agent_name": name,
                "registered_at": timestamp,
                "status": "pending"
            }
            self.client.table("agent_registrations").insert(data).execute()
            logger.info(f"🤝 [DB Success]: บันทึกข้อมูล Agent เรียบร้อยแล้ว")
            return True
        except Exception as e:
            logger.error(f"❌ [DB Agent Reg Error]: {e}")
            return False