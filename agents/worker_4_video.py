import asyncio
import os
import logging
from google import genai
from google.genai import types

# ตั้งค่า Logger สำหรับติดตามการทำงานเบื้องหลัง
logger = logging.getLogger("Worker4-VideoDirector")

class VideoProductionWorker:
    """
    🎬 Worker 4: ระบบวางแผนและออกแบบสคริปต์วิดีโอระดับภาพยนตร์ (Cinematic 4K Video Storyboard)
    อัปเกรด: ผสานการคิดบทแบบผู้กำกับมืออาชีพ พร้อมระบบ Proof-up ส่งสคริปต์ให้ลูกค้ายืนยันก่อนตัดเงิน
    """
    
    def __init__(self):
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        # ใช้รุ่น Pro สำหรับงานความคิดสร้างสรรค์ การเขียนบท และออกแบบฉากที่ซับซ้อน
        self.model_name = 'gemini-1.5-pro'

    async def process(self, user_id: str, message: str) -> str:
        """ทำงานเบื้องหลัง (Background Task) สำหรับออกแบบ Storyboard"""
        logger.info(f"🎬 [Video Production]: กำลังวางแผนและสร้าง Storyboard วิดีโอ 4K ให้ User {user_id}...")
        
        if not self.client:
            return "⚠️ [System]: ระบบ Video Director ออฟไลน์ ไม่พบการเชื่อมต่อ API Key"
        
        try:
            # 🧠 System Prompt สั่งการให้ AI สวมวิญญาณผู้กำกับโฆษณา
            system_instruction = """
            คุณคือ 'Executive Video Director' ระดับโลก ของ SIRINTHANATTH PRIME
            หน้าที่ของคุณคือ ออกแบบ Storyboard และสคริปต์สำหรับวิดีโอโฆษณาความละเอียด 4K และเสียงพากย์คุณภาพสูง
            
            โครงสร้างที่ต้องจัดทำนำเสนอให้ลูกค้าดู (Proof-up):
            1. แนวคิดหลัก (Concept & Tone): ระบุ Mood & Tone ให้ชัดเจน
            2. Storyboard แบ่งฉาก:
               - Scene 1: Hook (ดึงดูดความสนใจใน 3 วินาทีแรก)
               - Scene 2: Pain Point (ขยี้ปัญหา)
               - Scene 3: Solution (นำเสนอทางออกของโปรดักส์)
               - Scene 4: Call-to-Action (ปิดการขาย)
            3. บทพากย์ (Voiceover Script): คำพูดที่สละสลวย เตรียมไว้ให้ AI พากย์เสียง
            
            ข้อบังคับ: ตบท้ายข้อความของคุณด้วยประโยคนี้เสมอ เพื่อเข้าสู่ระบบ Automation:
            "📝 [ตรวจสอบสคริปต์]: หากพึงพอใจกับโครงสร้างนี้ โปรดพิมพ์คำว่า 'ยืนยันการสร้างคลิป' เพื่อให้ระบบประเมินราคา ตัดเครดิตจาก Smart Wallet และส่งเข้าสู่กระบวนการเรนเดอร์ 4K ทันทีครับ"
            """

            prompt = f"ลูกค้าต้องการสร้างวิดีโอเกี่ยวกับ: '{message}'"

            # ⚡ รันแบบ Asynchronous (to_thread) เพื่อไม่ให้บล็อกเซิร์ฟเวอร์หลัก
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.75 # ใช้ความคิดสร้างสรรค์สูงในการเขียนบทโฆษณา
                )
            )
            
            video_plan = response.text if response.text else "สร้างโครงสร้างและสคริปต์วิดีโอเรียบร้อยแล้ว"
            
        except Exception as e:
            logger.error(f"⚠️ [Worker 4 AI Error]: {e}")
            video_plan = (
                "🎬 [ร่างสคริปต์วิดีโอ 4K เบื้องต้น]\n"
                "Scene 1: Hook เปิดตัวดึงดูดสายตา\n"
                "Scene 2: ขยี้ Pain Point ของลูกค้า\n"
                "Scene 3: นำเสนอ Solution ของแบรนด์\n"
                "Scene 4: Call to Action ปิดการขาย\n\n"
                "📝 หากพอใจ พิมพ์ 'ยืนยันการสร้างคลิป' เพื่อให้ระบบประเมินราคาและเรนเดอร์ได้เลยครับ"
            )

        logger.info(f"✅ [Video Production]: วางแผนวิดีโอเสร็จสิ้นสำหรับ {user_id}")
        return video_plan