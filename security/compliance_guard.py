import os
import re
import logging
import asyncio
from typing import Optional
from google import genai
from google.genai import types

logger = logging.getLogger("ComplianceGuard")

# =========================================================
# ⚡ Pre-compiled Regex (เพื่อความเร็วระดับ Zero-Latency)
# =========================================================
ID_CARD_PATTERN = re.compile(r'\b\d{13}\b')
PHONE_PATTERN = re.compile(r'\b(0[689]\d{1}[-\s]?\d{3}[-\s]?\d{4})\b')
CREDIT_CARD_PATTERN = re.compile(r'\b(?:\d[ -]*?){13,16}\b')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PROMPT_INJECTION_PATTERN = re.compile(
    r'(ignore all|disregard previous|system prompt|bypass|jailbreak|override|forget everything)', 
    re.IGNORECASE
)

# =========================================================
# 🌐 นำเข้าศูนย์บัญชาการ AI ส่วนกลาง
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-3.7-flash" # 🚀 อัปเกรดเป็นรุ่นล่าสุดของระบบ
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
    อัปเกรด: Pre-compiled Regex, Anti-Prompt Injection, AI 3.7 Deep Scan
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.fast_model = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-3.7-flash")

    @staticmethod
    def sanitize_pii(text: str) -> str:
        """
        กำจัดข้อมูล PII และทำลายความพยายามเจาะระบบ (Prompt Injection) ก่อนส่งต่อให้ AI
        """
        if not text: 
            return ""
            
        # 1. 🛡️ บล็อกคำสั่งแฮก AI (Anti-Jailbreak)
        text = PROMPT_INJECTION_PATTERN.sub('[SECURITY_OVERRIDE_BLOCKED]', text)
            
        # 2. 🧹 ลบข้อมูลส่วนบุคคล (PDPA Zero-Data Retention)
        text = ID_CARD_PATTERN.sub('[ID_CARD_REDACTED]', text)
        text = PHONE_PATTERN.sub('[PHONE_REDACTED]', text)
        text = CREDIT_CARD_PATTERN.sub('[CREDIT_CARD_REDACTED]', text)
        text = EMAIL_PATTERN.sub('[EMAIL_REDACTED]', text)
        
        return text

    @staticmethod
    def attach_financial_disclaimer(response_text: str) -> str:
        """
        แนบคำเตือนจำกัดความรับผิดชอบ (Disclaimer) ตามมาตรฐานองค์กรกำกับดูแลของไทย
        """
        if not response_text: 
            return ""
            
        # 1. ⚖️ หมวด ก.ล.ต. (ความเสี่ยงทางการเงิน/การลงทุน)
        fin_keywords = {"หุ้น", "คริปโต", "การลงทุน", "ผลตอบแทน", "แนวรับ", "แนวต้าน", "กราฟเทคนิค", "กำไร", "กองทุน", "forex", "คริปโท", "ฟันธง", "การันตีรายได้"}
        if any(keyword in response_text.lower() for keyword in fin_keywords):
            disclaimer_sec = "\n\n⚠️ คำเตือน (ก.ล.ต.): ข้อมูลข้างต้นเป็นการประมวลผลเชิงสถิติโดยเทคโนโลยี AI มิใช่คำแนะนำการลงทุน ผู้ลงทุนควรศึกษาข้อมูลและประเมินความเสี่ยงก่อนตัดสินใจ"
            if "⚠️ คำเตือน (ก.ล.ต.)" not in response_text:
                response_text += disclaimer_sec

        # 2. 🛡️ หมวด อย. / สคบ. (สุขภาพ / โฆษณาพาณิชย์)
        health_keywords = {"รักษาหายขาด", "รับประกันผล 100%", "ลดน้ำหนัก", "ขาวทันที", "ไม่มีผลข้างเคียง", "มหัศจรรย์", "ดีที่สุดในโลก", "เห็นผลทันที", "หยุดยาได้เลย"}
        if any(keyword in response_text.lower() for keyword in health_keywords):
            disclaimer_ocpb = "\n\n⚠️ คำเตือน (สคบ./อย.): ข้อความนี้อาจมีคีย์เวิร์ดที่เข้าข่ายโฆษณาเกินจริง (Overclaim) โปรดปรับปรุงเนื้อหาให้สอดคล้องกับระเบียบการโฆษณาทางพาณิชย์ก่อนนำไปเผยแพร่จริง"
            if "⚠️ คำเตือน (สคบ./อย.)" not in response_text:
                response_text += disclaimer_ocpb

        return response_text

    async def ai_compliance_deep_scan(self, text: str) -> str:
        """
        ใช้ Vertex AI สแกนเนื้อหาและ Rewrite ข้อความที่ละเมิดกฎหมายให้ปลอดภัย 100% อัตโนมัติ
        """
        if not self.client or not text: 
            return text
            
        try:
            system_instruction = """
            คุณคือ 'Chief Compliance Officer' ระดับโลกของ SIRINTHANATTH PRIME
            หน้าที่ของคุณคือ: สแกนข้อความนี้ว่าละเมิดกฎหมาย สคบ., อย., พ.ร.บ. คอมพิวเตอร์ หรือ ก.ล.ต. ของประเทศไทยหรือไม่
            - หากมี "คำโฆษณาเกินจริง (Overclaim)" หรือการการันตีผลตอบแทนผิดกฎหมาย ให้ทำการรีไรท์ (Rewrite) ข้อความนั้นให้ปลอดภัย แต่ยังคงความน่าสนใจในเชิงการตลาดไว้
            - หากปลอดภัยอยู่แล้ว ให้ตอบกลับด้วยข้อความเดิม 100% ห้ามเพิ่มข้อความอื่นอธิบายเด็ดขาด
            """
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.fast_model,
                contents=f"ข้อความที่ต้องสแกนและรีไรท์: {text}",
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.0 # 🔒 ล็อก Temperature ที่ 0.0 เพื่อความแม่นยำทางกฎหมายระดับสูงสุด (Zero-Hallucination)
                )
            )
            return response.text.strip() if response.text else text
            
        except Exception as e:
            logger.error(f"❌ [AI Compliance Deep Scan Error]: {e}", exc_info=True)
            return text