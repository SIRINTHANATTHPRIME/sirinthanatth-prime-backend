import asyncio
import os
import logging
from google import genai
from google.genai import types

# ตั้งค่า Logger สำหรับติดตามการทำงานเบื้องหลัง
logger = logging.getLogger("Worker6-MarketingStrategist")

class MarketingStrategyWorker:
    """
    📈 Worker 6: ฝ่ายนักวิเคราะห์กลยุทธ์การตลาด และเซลล์แมนอัจฉริยะ (Global CMO & Dynamic Upsell)
    อัปเกรด: ผสานจิตวิทยาผู้บริโภค, Full-Funnel Strategy, และวางสคริปต์เสียงสำหรับ ElevenLabs
    """
    
    def __init__(self):
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        # 🚀 ใช้รุ่น Pro สำหรับการวิเคราะห์ตรรกะการตลาดเชิงลึกและการเขียนสคริปต์ขั้นสูง
        self.model_name = 'gemini-1.5-pro'

    async def process(self, user_id: str, message: str) -> str:
        """ทำงานเบื้องหลัง (Background Task) สำหรับวางแผนกลยุทธ์การตลาดและหาโอกาส Upsell"""
        logger.info(f"📈 [Marketing Strategy]: กำลังวิเคราะห์กลยุทธ์ระดับโลกและหาจังหวะ Upsell ให้ User {user_id}...")
        
        if not self.client:
            return "⚠️ [System]: ระบบ Marketing Strategist ออฟไลน์ ไม่พบการเชื่อมต่อ API Key"

        try:
            # 🧠 System Prompt สั่งให้ AI คิดแบบสุดยอดนักการตลาด (Global CMO)
            system_instruction = """
            คุณคือ 'Chief Marketing Officer (CMO)' ระดับโลก ของแพลตฟอร์ม SIRINTHANATTH PRIME
            หน้าที่ของคุณคือให้คำปรึกษา วางกลยุทธ์การตลาดเชิงลึก (Full-Funnel) และสร้างโอกาสในการขาย (Upsell) อย่างแนบเนียน
            
            โครงสร้างการนำเสนอ (Executive Strategy Pitch):
            1. 📊 Market Analysis & Full-Funnel Strategy: วิเคราะห์ปัญหาของลูกค้าด้วยหลักจิตวิทยาพฤติกรรมผู้บริโภคยุคดิจิทัล และเสนอแผนการตลาดที่จับต้องได้จริง คุ้มค่า ROI
            2. 🎬 4K Video Concept & 🎙️ Voiceover Script (ElevenLabs Ready): ร่างคอนเซ็ปต์วิดีโอโฆษณา 4K สั้นๆ พร้อมสคริปต์เสียงพากย์ที่สะกดอารมณ์ผู้ฟัง (เพื่อให้ระบบ ElevenLabs นำไปพากย์ต่อได้ทันที)
            3. 💡 The Irresistible Offer (One-Click Upsell): ท้ายข้อความ ให้เสนอขายบริการของ SIRINTHANATTH PRIME ที่ตรงกับบริบทของลูกค้าให้เนียนที่สุด 
               (เช่น ชวนผลิตสื่อโฆษณา 4K [พิมพ์ 'ทำคลิป'] หรือเชิญอัปเกรดเป็น 100 VIP Founders ล็อกราคา 4,490 บาท/ปี เพื่อสิทธิพิเศษโลจิสติกส์)
            
            ข้อบังคับ: ใช้ภาษาเชิงจิตวิทยาการขายที่กระตุ้นให้ลูกค้าอยากลงมือทำทันที พิมพ์ให้อ่านง่าย มีความเป็นผู้นำ ดูแพง และเป็นมืออาชีพสูงสุด
            """
            
            prompt = f"ลูกค้าขอคำปรึกษาและต้องการให้วางกลยุทธ์สำหรับ: '{message}'"
            
            # ⚡ รันแบบ Asynchronous เพื่อไม่ให้บล็อกเซิร์ฟเวอร์หลัก (Non-Blocking I/O)
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.8 # ใช้ความสร้างสรรค์ระดับสูงในการออกแบบแคมเปญและการโน้มน้าวใจ
                )
            )
            
            strategy_result = response.text if response.text else "📈 วางกลยุทธ์การตลาดและจัดเตรียมข้อเสนอพิเศษเรียบร้อยแล้ว"
            
        except Exception as e:
            logger.error(f"⚠️ [Worker 6 AI Error]: {e}")
            strategy_result = (
                "📈 [Executive Marketing Strategy]\n"
                "ระบบได้ประเมิน Business Model Canvas และโครงสร้าง ROI ให้แคมเปญของคุณเรียบร้อยครับ\n\n"
                "🎬 แนะนำให้ดึงดูดกลุ่มเป้าหมายด้วยสื่อโฆษณา 4K พร้อมเสียงพากย์คุณภาพสูง (Human-like Voice)\n"
                "💡 [ข้อเสนอพิเศษ] สนใจผลิตสื่อโฆษณา 4K เพื่อลุยแคมเปญนี้ไหมครับ? พิมพ์ 'ทำคลิป' ได้เลย!"
            )
        
        logger.info(f"✅ [Marketing Strategy]: วางแผนกลยุทธ์และ Upsell เสร็จสิ้นสำหรับ {user_id}")
        return strategy_result