import re
from typing import Tuple

class ComplianceGuard:
    """
    🛡️ ระบบคัดกรองความปลอดภัยระดับโครงสร้าง (Input Sanitizer & Output Interceptor)
    """

    @staticmethod
    def sanitize_pii(text: str) -> str:
        """ลบข้อมูลส่วนบุคคล (PII) ก่อนส่งไปยังโมเดลภายนอก เพื่อ Zero-Data Retention"""
        # ลบเลขบัตรประชาชน 13 หลัก
        text = re.sub(r'\b\d{13}\b', '[ID_CARD_REDACTED]', text)
        # ลบเบอร์โทรศัพท์ไทย
        text = re.sub(r'\b(0\d{8,9})\b', '[PHONE_REDACTED]', text)
        return text

    @staticmethod
    def attach_financial_disclaimer(response_text: str) -> str:
        """ตรวจจับคีย์เวิร์ดการเงินและแนบ Disclaimer ตามเกณฑ์ ก.ล.ต."""
        keywords = ["หุ้น", "คริปโต", "การลงทุน", "ผลตอบแทน", "แนวรับ", "แนวต้าน", "กราฟเทคนิค", "กำไร"]
        if any(keyword in response_text for keyword in keywords):
            disclaimer = "\n\n⚠️ คำเตือน: ข้อมูลข้างต้นเป็นการวิเคราะห์เชิงสถิติและข้อมูลเบื้องต้นเท่านั้น มิใช่คำแนะนำการลงทุน ผู้ลงทุนควรศึกษาข้อมูลก่อนตัดสินใจ"
            if disclaimer.strip() not in response_text:
                return response_text + disclaimer
        return response_text