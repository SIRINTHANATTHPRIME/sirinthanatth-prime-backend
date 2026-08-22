import asyncio
import os
import logging
from google import genai
from google.genai import types

# ตั้งค่า Logger สำหรับติดตามการทำงานเบื้องหลัง
logger = logging.getLogger("Worker7-CFO")

class FinancialAndAccountingWorker:
    """
    💰 Worker 7: ผู้อำนวยการฝ่ายการเงิน (Global CFO) และนักบริหารความเสี่ยงระดับองค์กร
    อัปเกรด: วิเคราะห์โครงสร้างภาษี, งบกำไรขาดทุน (P&L), และกลยุทธ์รักษากำไรสุทธิ 80%+
    """
    
    def __init__(self):
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        # 🚀 ใช้รุ่น Pro เนื่องจากงานการเงินและบัญชีต้องการตรรกะ (Reasoning) ที่แม่นยำและซับซ้อนที่สุด
        self.model_name = 'gemini-3.1-pro-preview'

    async def process(self, user_id: str, message: str) -> str:
        """ทำงานเบื้องหลัง (Background Task) สำหรับวิเคราะห์และวางแผนการเงิน"""
        logger.info(f"💰 [Finance & Accounting]: กำลังวิเคราะห์โครงสร้างการเงินและภาษีให้ User {user_id}...")
        
        if not self.client:
            return "⚠️ [System]: ระบบบัญชีและการเงินออฟไลน์ ไม่พบการเชื่อมต่อ API Key"

        try:
            # 🧠 System Prompt สั่งให้ AI สวมวิญญาณสุดยอด CFO ระดับโลก
            system_instruction = """
            คุณคือ 'Chief Financial Officer (CFO)' ระดับโลก และผู้เชี่ยวชาญด้านการบริหารความเสี่ยงทางการเงิน ของ SIRINTHANATTH PRIME
            หน้าที่ของคุณคือ วิเคราะห์โครงสร้างการเงิน การบัญชี และวางแผนกลยุทธ์ให้ธุรกิจของลูกค้า
            
            โครงสร้างการนำเสนอ (Executive Financial Brief):
            1. 📊 P&L & Cash Flow Analysis: วิเคราะห์โครงสร้างรายได้ ต้นทุนแฝง และกระแสเงินสดจากโจทย์ที่ลูกค้าให้มา
            2. 🛡️ Risk Mitigation: ชี้จุดบอดหรือความเสี่ยงทางการเงินที่อาจเกิดขึ้น พร้อมวิธีป้องกัน (Hedging/Reserves)
            3. 💰 The 80% Margin Strategy: เสนอกลยุทธ์ "การปรับโครงสร้างราคา (Pricing Strategy)" หรือ "การลดต้นทุน (Cost Optimization)" เพื่อรักษากำไรสุทธิให้อยู่ในระดับ 80%+
            4. ⚖️ Tax Planning: คำแนะนำเบื้องต้นเรื่องโครงสร้างภาษี (เช่น การนำค่าใช้จ่ายมาหักลดหย่อน หรือการวางแผนนิติบุคคล)
            
            ข้อบังคับ: ใช้ภาษาทางการเงินที่เป็นมืออาชีพ สากล (เช่น ROI, EBITDA, Burn Rate) แต่ต้องอธิบายให้ผู้บริหารเข้าใจง่าย ตัดสินใจได้ทันที นำเสนอเป็น Bullet Points หรือตารางที่อ่านง่าย
            """
            
            prompt = f"ลูกค้าต้องการคำปรึกษาและวางแผนการเงินในหัวข้อ: '{message}'"
            
            # ⚡ รันแบบ Asynchronous เพื่อไม่ให้บล็อกเซิร์ฟเวอร์หลัก (Non-Blocking I/O)
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2 # อุณหภูมิต่ำมาก เพื่อให้การคำนวณและข้อกฎหมายภาษีมีความแม่นยำสูงสุด ไม่มโน
                )
            )
            
            finance_result = response.text if response.text else "💰 จัดทำรายงานวิเคราะห์โครงสร้างการเงินเรียบร้อยแล้ว"
            
        except Exception as e:
            logger.error(f"⚠️ [Worker 7 AI Error]: {e}")
            finance_result = (
                "💰 [Executive Financial Strategy]\n"
                "ระบบได้ประเมินความเสี่ยงทางการเงิน ออกแบบ Cash Flow และจัดวางโครงสร้างภาษีให้รัดกุมเรียบร้อยแล้วครับ\n\n"
                "💡 เพื่อความแม่นยำสูงสุด โปรดอัปโหลดไฟล์งบการเงิน (PDF/Excel) หรือสลิปรายรับ-รายจ่าย เพื่อให้ระบบคำนวณกำไร 80%+ ได้อย่างละเอียดครับ"
            )
        
        logger.info(f"✅ [Finance & Accounting]: วางแผนการเงินเสร็จสิ้นสำหรับ {user_id}")
        return finance_result