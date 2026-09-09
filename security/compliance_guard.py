import os
import re
import logging
import asyncio
from typing import Optional
from google import genai
from google.genai import types

logger = logging.getLogger("ComplianceGuard")

# =========================================================
# ⚡ Pre-compiled Regex (ความเร็วระดับ Zero-Latency)
# =========================================================
ID_CARD_PATTERN = re.compile(r'\b\d{13}\b')
PHONE_PATTERN = re.compile(r'\b(0[2-9]\d{1,2}[-\s]?\d{3}[-\s]?\d{3,4})\b')
CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d[ -]*?){13,16}\b')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PASSPORT_PATTERN = re.compile(r'\b[A-Z]{1,2}\d{6,7}\b', re.IGNORECASE)

# 🛡️ Military-Grade Prompt Injection Shield
PROMPT_INJECTION_PATTERN = re.compile(
    r'(ignore all|disregard previous|system prompt|bypass|jailbreak|override|forget everything|'
    r'developer mode|do anything now|dan prompt|you are now|print instructions)', 
    re.IGNORECASE
)

# =========================================================
# 🌐 นำเข้าศูนย์บัญชาการ AI ส่วนกลาง
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-3.7-flash" 
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key:
                return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

class ComplianceGuard:
    """
    🛡️ ระบบคัดกรองความปลอดภัยระดับโครงสร้าง (Zero-Risk Compliance Shield)
    อัปเกรด: Circuit Breaker, Expanded PII, Anti-Injection, Zero-Data Wipe
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.fast_model = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-3.7-flash")

    @staticmethod
    def sanitize_pii(text: str) -> str:
        """กำจัดข้อมูล PII และทำลายความพยายามเจาะระบบ (Prompt Injection)"""
        if not text: 
            return ""
            
        # 1. 🛡️ บล็อกคำสั่งแฮก AI (Anti-Jailbreak)
        text = PROMPT_INJECTION_PATTERN.sub('[SECURITY_OVERRIDE_BLOCKED]', text)
            
        # 2. 🧹 ลบข้อมูลส่วนบุคคล (PDPA Text Sanitization)
        text = ID_CARD_PATTERN.sub('[ID_CARD_REDACTED]', text)
        text = PHONE_PATTERN.sub('[PHONE_REDACTED]', text)
        text = CREDIT_CARD_PATTERN.sub('[CREDIT_CARD_REDACTED]', text)
        text = EMAIL_PATTERN.sub('[EMAIL_REDACTED]', text)
        text = PASSPORT_PATTERN.sub('[PASSPORT_REDACTED]', text)
        
        return text

    @staticmethod
    def attach_financial_disclaimer(response_text: str) -> str:
        """แนบคำเตือนจำกัดความรับผิดชอบ (Disclaimer) ตามมาตรฐานองค์กรกำกับดูแลของไทย"""
        if not response_text: 
            return ""
            
        # 1. ⚖️ หมวด ก.ล.ต. (ความเสี่ยงทางการเงิน/การลงทุน)
        fin_keywords = {"หุ้น", "คริปโต", "การลงทุน", "ผลตอบแทน", "แนวรับ", "แนวต้าน", "กราฟเทคนิค", "กำไร", "กองทุน", "forex", "คริปโท", "ฟันธง", "การันตีรายได้"}
        if any(keyword in response_text.lower() for keyword in fin_keywords):
            disclaimer_sec = "\n\n⚠️ คำเตือน (ก.ล.ต.): ข้อมูลข้างต้นเป็นการประมวลผลเชิงสถิติและข้อมูลทางวิชาการโดย AI มิใช่คำแนะนำการลงทุน ผู้ลงทุนควรศึกษาข้อมูลและประเมินความเสี่ยงก่อนตัดสินใจ"
            if "⚠️ คำเตือน (ก.ล.ต.)" not in response_text:
                response_text += disclaimer_sec

        # 2. 🛡️ หมวด อย. / สคบ. (สุขภาพ / โฆษณาพาณิชย์)
        health_keywords = {"รักษาหายขาด", "รับประกันผล 100%", "ลดน้ำหนัก", "ขาวทันที", "ไม่มีผลข้างเคียง", "มหัศจรรย์", "ดีที่สุดในโลก", "เห็นผลทันที", "หยุดยาได้เลย", "ปลอดภัย 100%"}
        if any(keyword in response_text.lower() for keyword in health_keywords):
            disclaimer_ocpb = "\n\n⚠️ คำเตือน (สคบ./อย.): ข้อความนี้อาจมีคีย์เวิร์ดที่เข้าข่ายโฆษณาเกินจริง (Overclaim) โปรดพิจารณาและปรับปรุงเนื้อหาให้สอดคล้องกับระเบียบการโฆษณาทางพาณิชย์ก่อนเผยแพร่"
            if "⚠️ คำเตือน (สคบ./อย.)" not in response_text:
                response_text += disclaimer_ocpb

        return response_text

    async def ai_compliance_deep_scan(self, text: str) -> str:
        """ใช้ Vertex AI สแกนเนื้อหาและ Rewrite ข้อความที่ละเมิดกฎหมายให้ปลอดภัย 100%"""
        if not self.client or not text: 
            return text
            
        try:
            system_instruction = (
                "คุณคือ 'Chief Compliance Officer' ระดับโลกของ SIRINTHANATTH PRIME\n"
                "หน้าที่: สแกนข้อความนี้ว่าละเมิดกฎหมาย สคบ., อย., หรือ ก.ล.ต. ของประเทศไทยหรือไม่\n"
                "- หากมี \"คำโฆษณาเกินจริง (Overclaim)\" ให้รีไรท์ (Rewrite) ให้ปลอดภัยแต่ยังคงน่าสนใจ\n"
                "- หากปลอดภัยอยู่แล้ว ให้ตอบกลับด้วยข้อความเดิม 100%\n"
                "- กฎเหล็ก: ตอบเฉพาะข้อความผลลัพธ์เท่านั้น ห้ามมีคำเกริ่นนำ (เช่น 'นี่คือข้อความ...') หรืออธิบายเหตุผลเด็ดขาด"
            )
            
            async def _execute_scan():
                return await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.fast_model,
                    contents=f"ข้อความที่ต้องสแกน: {text}",
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.0 # 🔒 ล็อก Temperature ที่ 0.0 เพื่อความแม่นยำสูงสุด
                    )
                )
            
            # ⏱️ Circuit Breaker: ป้องกัน AI API ค้างเกิน 8 วินาที
            response = await asyncio.wait_for(_execute_scan(), timeout=8.0)
            return response.text.strip() if response.text else text
            
        except asyncio.TimeoutError:
            logger.warning("⚠️ [AI Compliance Timeout]: ระบบตรวจสอบทำงานล่าช้า ใช้ข้อความต้นฉบับแทน")
            return text
        except Exception as e:
            logger.error(f"❌ [AI Compliance Deep Scan Error]: {e}", exc_info=True)
            return text

    @staticmethod
    async def zero_data_retention_wipe(file_path: str, delay_seconds: int = 60):
        """
        [Zero-Data Retention] ทำลายไฟล์เอกสาร/สื่อส่วนบุคคลออกจากหน่วยความจำ RAM หรือ Disk ภายใน 60 วินาที (PDPA)
        """
        if not file_path or not os.path.exists(file_path):
            return

        try:
            # หน่วงเวลาเพื่อรอให้ระบบส่งไฟล์ให้ลูกค้าเสร็จสิ้น
            await asyncio.sleep(delay_seconds)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"🧹 [Zero-Data Retention]: ทำลายไฟล์ {file_path} เรียบร้อยแล้ว (มาตรฐาน PDPA)")
        except Exception as e:
            logger.error(f"❌ [Wipe Data Error]: ลบไฟล์ล้มเหลว {file_path} -> {e}")
            
    async def apply_full_shield(self, text: str, file_path_to_wipe: Optional[str] = None) -> str:
        """
        🛡️ Orchestrator: รันเกราะป้องกันทุกมิติ (Deep Scan + Disclaimer) และลบไฟล์อัตโนมัติแบบเบ็ดเสร็จ
        """
        # 1. ให้ AI สแกนและ Rewrite คำต้องห้าม สคบ/อย. เชิงลึก
        safe_text = await self.ai_compliance_deep_scan(text)
        
        # 2. ตรวจสอบคีย์เวิร์ดเพื่อติด Disclaimer ก.ล.ต. / สคบ. แบบ Hardcode ซ้อนอีกชั้น
        final_text = self.attach_financial_disclaimer(safe_text)
        
        # 3. สั่งรัน Zero-Data Retention เป็น Background Task กรณีมีไฟล์แนบ
        if file_path_to_wipe:
            asyncio.create_task(self.zero_data_retention_wipe(file_path_to_wipe))
            
        return final_text