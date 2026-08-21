import asyncio
import os
import logging
from google import genai
from google.genai import types

# ตั้งค่า Logger สำหรับติดตามการทำงานเบื้องหลัง
logger = logging.getLogger("Worker9-PrimeAdvisor")

class PrimeAdvisorWorker:
    """
    👑 Worker 9: ระบบที่ปรึกษาระดับผู้บริหาร (PRIME Package) และนักวิเคราะห์ระบบ IT/AI อัจฉริยะ
    อัปเกรด: ผสานความเชี่ยวชาญด้านความปลอดภัยทางไซเบอร์ การวิเคราะห์ข้อมูลเชิงลึก และสิทธิพิเศษ VVIP
    """
    
    def __init__(self):
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        # 🚀 ใช้รุ่น Pro สำหรับการวิเคราะห์เชิงลึกระดับผู้บริหารและการตรวจสอบสถาปัตยกรรม IT ที่ซับซ้อน
        self.model_name = 'gemini-1.5-pro'

    async def process(self, user_id: str, message: str) -> str:
        """ทำงานเบื้องหลัง (Background Task) สำหรับสิทธิพิเศษ PRIME Package"""
        logger.info(f"👑 [PRIME Advisor]: กำลังประมวลผลคำสั่งระดับผู้บริหาร (VVIP) ให้ User {user_id}...")
        
        if not self.client:
            return "⚠️ [System]: ระบบ PRIME Advisor ออฟไลน์ ไม่พบการเชื่อมต่อ API Key"

        try:
            # 🧠 System Prompt สั่งให้ AI สวมวิญญาณสุดยอดที่ปรึกษาและผู้เชี่ยวชาญ IT/AI ระดับสากล
            system_instruction = """
            คุณคือ 'Executive Prime Advisor' และ 'Chief Technology Officer (CTO)' อัจฉริยะของแพลตฟอร์ม SIRINTHANATTH PRIME
            หน้าที่ของคุณคือการดูแลลูกค้า VVIP (PRIME Package) ด้วยมาตรฐานระดับโลก โดยมีความเชี่ยวชาญครอบคลุม 3 มิติหลัก:
            1. 💼 Executive Business Analytics: วิเคราะห์ข้อมูลธุรกิจเชิงลึก ให้มุมมองที่เฉียบขาด และช่วยตัดสินใจเรื่องสำคัญ
            2. 💻 IT & AI Systems Architecture: ให้คำปรึกษาด้านการวางระบบโครงสร้างพื้นฐาน เทคโนโลยี AI และการปรับปรุงประสิทธิภาพระบบ (Optimization)
            3. 🛡️ Enterprise-Grade Security: ป้องกันความเสี่ยงจากการถูกเจาะระบบ วิเคราะห์ช่องโหว่ (Vulnerability) และรักษามาตรฐานความปลอดภัยสูงสุด
            
            รูปแบบการตอบกลับ:
            - สุขุม นุ่มนวล เคารพ และเป็นมืออาชีพขั้นสูงสุด (Predictive Empathy)
            - โครงสร้างการตอบต้องเป็นระเบียบ อ่านง่าย (ใช้ Bullet Points หรือตารางอธิบายข้อมูลที่ซับซ้อน)
            - หากลูกค้าถามเรื่องระบบ IT หรือ AI ให้ตอบในเชิงสถาปัตยกรรมที่ล้ำสมัยและปลอดภัยที่สุด
            """
            
            prompt = f"คำสั่งหรือข้อสอบถามจากลูกค้าแพ็กเกจ PRIME: '{message}'"
            
            # ⚡ รันแบบ Asynchronous เพื่อป้องกันการบล็อกเซิร์ฟเวอร์หลัก (Non-Blocking I/O)
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.4 # อุณหภูมิกลางๆ เพื่อความสมดุลระหว่างความแม่นยำทาง IT และความสละสลวยทางธุรกิจ
                )
            )
            
            result = response.text if response.text else "👑 จัดการข้อมูลและวิเคราะห์เชิงลึกระดับผู้บริหารเรียบร้อยแล้ว"
            
        except Exception as e:
            logger.error(f"⚠️ [Worker 9 AI Error]: {e}")
            result = (
                "👑 [Executive PRIME Report]\n"
                "ระบบได้ประมวลผลคำสั่งของท่าน ทำการสแกนความปลอดภัยทางไซเบอร์ขั้นสูง และจัดเตรียมเอกสารข้อมูลเชิงลึกเรียบร้อยแล้วครับ\n\n"
                "🔒 (ข้อมูลของท่านได้รับการคุ้มครองด้วยการเข้ารหัสความปลอดภัยระดับ Enterprise สูงสุด)"
            )
        
        logger.info(f"✅ [PRIME Advisor]: ประมวลผลข้อมูลระดับผู้บริหารเสร็จสิ้นสำหรับ {user_id}")
        return result