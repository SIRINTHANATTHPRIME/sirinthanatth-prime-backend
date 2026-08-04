from datetime import datetime
from core_services.db_supabase import SupabaseDatabase

class PDPAShield:
    """ระบบบันทึกความยินยอมและปกป้องข้อมูลส่วนบุคคล (PDPA) ตามกฎหมาย"""
    def __init__(self):
        # เรียกใช้งานคลาสฐานข้อมูลที่เราสร้างไว้
        self.db = SupabaseDatabase()

    def log_user_consent(self, line_user_id: str, consent_type: str = "TOS_AND_PDPA"):
        if not self.db.client:
            return False
            
        try:
            # เก็บเฉพาะ Log การยินยอม โดยไม่เก็บข้อมูลแชทลูกค้าไว้ถาวร (Zero-Data Retention)
            log_data = {
                "line_user_id": line_user_id,
                "consent_type": consent_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.db.client.table("pdpa_consent_logs").insert(log_data).execute()
            print(f"🛡️ [PDPA Shield]: บันทึกการยินยอม (Consent) ของ User '{line_user_id}' สำเร็จ")
            return True
        except Exception as e:
            print(f"⚠️ [PDPA Error]: ไม่สามารถบันทึก Log ได้ - {e}")
            return False