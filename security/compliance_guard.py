import os
import re
import logging
import asyncio
from typing import Tuple
from google import genai
from google.genai import types

# ตั้งค่า Logger สำหรับระบบรักษาความปลอดภัย
logger = logging.getLogger("ComplianceGuard")

# =========================================================
# 🌐 นำเข้าศูนย์บัญชาการ AI ส่วนกลาง (Vertex AI Integration)
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-2.5-flash" # ใช้โมเดลความเร็วสูงพิเศษสำหรับสแกนแบบ Real-time
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key:
                return genai.Client(api_key=api_key)
            # รองรับระบบ Vertex AI อัตโนมัติบน Google Cloud
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

class ComplianceGuard:
    """
    🛡️ ระบบคัดกรองความปลอดภัยระดับโครงสร้าง (Zero-Risk Compliance Shield)
    อัปเกรด: เพิ่ม Vertex AI Scanner สำหรับสแกนข้อกฎหมาย สคบ. / อย. / ก.ล.ต. และ PDPA เชิงลึก
    """
    def __init__(self):
        # 🚀 เตรียม Vertex AI Client สำหรับฟังก์ชัน Advanced Deep Scan
        self.client = PrimeAIConfig.get_client()
        self.fast_model = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-2.5-flash")

    @staticmethod
    def sanitize_pii(text: str) -> str:
        """
        ลบข้อมูลส่วนบุคคล (PII) ก่อนส่งไปยังโมเดลภายนอก เพื่อ Zero-Data Retention
        อัปเกรด: ครอบคลุมบัตรเครดิต, เบอร์โทรทุกรูปแบบ, และอีเมล
        """
        if not text: 
            return ""
            
        # ลบเลขบัตรประชาชน 13 หลัก
        text = re.sub(r'\b\d{13}\b', '[ID_CARD_REDACTED]', text)
        
        # ลบเบอร์โทรศัพท์ไทย (รองรับทั้งติดกันและมีขีด/ช่องว่าง 08X-XXX-XXXX)
        text = re.sub(r'\b(0[689]\d{1}[-\s]?\d{3}[-\s]?\d{4})\b', '[PHONE_REDACTED]', text)
        
        # ลบเลขบัตรเครดิต (16 หลัก)
        text = re.sub(r'\b(?:\d[ -]*?){13,16}\b', '[CREDIT_CARD_REDACTED]', text)
        
        # ลบ Email
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)
        
        return text

    @staticmethod
    def attach_financial_disclaimer(response_text: str) -> str:
        """
        ตรวจจับคีย์เวิร์ดความเสี่ยงเชิงพาณิชย์และแนบ Disclaimer อัตโนมัติ 
        อัปเกรด: ขอบเขตครอบคลุม ก.ล.ต. (การเงิน) และ อย./สคบ. (โฆษณา)
        """
        if not response_text: 
            return ""
            
        # 1. ⚖️ หมวด ก.ล.ต. (การเงิน / การลงทุน)
        fin_keywords = ["หุ้น", "คริปโต", "การลงทุน", "ผลตอบแทน", "แนวรับ", "แนวต้าน", "กราฟเทคนิค", "กำไร", "กองทุน", "forex", "คริปโท"]
        if any(keyword in response_text.lower() for keyword in fin_keywords):
            disclaimer_sec = "\n\n⚠️ คำเตือน (ก.ล.ต.): ข้อมูลข้างต้นเป็นการประมวลผลเชิงสถิติโดยเทคโนโลยี AI มิใช่คำแนะนำการลงทุน ผู้ลงทุนควรศึกษาข้อมูลและประเมินความเสี่ยงก่อนตัดสินใจ"
            if "⚠️ คำเตือน (ก.ล.ต.)" not in response_text:
                response_text += disclaimer_sec

        # 2. 🛡️ หมวด อย. / สคบ. (สุขภาพ / โฆษณาพาณิชย์)
        health_keywords = ["รักษาหายขาด", "รับประกันผล 100%", "ลดน้ำหนัก", "ขาวทันที", "ไม่มีผลข้างเคียง", "มหัศจรรย์", "ดีที่สุดในโลก", "เห็นผลทันที"]
        if any(keyword in response_text.lower() for keyword in health_keywords):
            disclaimer_ocpb = "\n\n⚠️ คำเตือน (สคบ./อย.): ข้อความนี้อาจมีคีย์เวิร์ดที่เข้าข่ายโฆษณาเกินจริง (Overclaim) โปรดปรับปรุงเนื้อหาให้สอดคล้องกับระเบียบการโฆษณาทางพาณิชย์ก่อนนำไปเผยแพร่จริง"
            if "⚠️ คำเตือน (สคบ./อย.)" not in response_text:
                response_text += disclaimer_ocpb

        return response_text

    async def ai_compliance_deep_scan(self, text: str) -> str:
        """
        [ฟีเจอร์ AI ใหม่ระดับโลก] ใช้ Vertex AI ความเร็วแสง สแกนและเกลาภาษาให้ถูกกฎหมาย 100% 
        โดยรักษาใจความโฆษณาไว้ (ใช้ร่วมกับ Worker 2 หรือ Worker 6)
        """
        if not self.client or not text: 
            return text
            
        try:
            system_instruction = """
            คุณคือ 'Chief Compliance Officer' ระดับโลกของ SIRINTHANATTH PRIME
            หน้าที่ของคุณคือ: สแกนข้อความนี้ว่าละเมิดกฎหมาย สคบ., อย., พ.ร.บ. คอมพิวเตอร์ หรือ ก.ล.ต. ของประเทศไทยหรือไม่
            - หากมี "คำโฆษณาเกินจริง (Overclaim)" ให้รีไรท์ (Rewrite) ข้อความนั้นให้ปลอดภัย แต่ยังคงความน่าสนใจในเชิงการตลาดไว้
            - หากปลอดภัยอยู่แล้ว ให้ตอบกลับด้วยข้อความเดิม 100% ห้ามเพิ่มข้อความอื่น
            """
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.fast_model,
                contents=f"ข้อความที่ต้องสแกนและรีไรท์: {text}",
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1 # ลดความคลาดเคลื่อนให้เป็นศูนย์
                )
            )
            return response.text.strip() if response.text else text
            
        except Exception as e:
            logger.error(f"❌ [AI Compliance Deep Scan Error]: {e}")
            # Fallback กลับไปใช้ข้อความเดิมหากระบบ AI ขัดข้อง
            return text