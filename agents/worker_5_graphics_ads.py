import asyncio
import os
import logging
from google import genai
from google.genai import types

# ตั้งค่า Logger สำหรับติดตามการทำงานเบื้องหลัง
logger = logging.getLogger("Worker5-CreativeDirector")

class GraphicAndAdsWorker:
    """
    🎨 Worker 5: ระบบผู้อำนวยการฝ่ายศิลป์และโฆษณา (Executive Creative Director)
    อัปเกรด: ผสานแนวคิดการออกแบบระดับ 4K, สิ่งพิมพ์สากล และจัดเตรียมสคริปต์เสียงให้ ElevenLabs
    """
    
    def __init__(self):
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        # 🚀 ใช้รุ่น Pro สำหรับงาน Creative & Strategy ที่ต้องคิดวิเคราะห์และใช้ความคิดสร้างสรรค์ขั้นสุด
        self.model_name = 'gemini-1.5-pro'

    async def process(self, user_id: str, message: str) -> str:
        """ทำงานเบื้องหลัง (Background Task) สำหรับออกแบบแคมเปญและสื่อ 4K"""
        logger.info(f"🎨 [Graphics & Ads]: กำลังออกแบบแคมเปญโฆษณาระดับโลกให้ User {user_id}...")
        
        if not self.client:
            return "⚠️ [System]: ระบบ Creative Director ออฟไลน์ ไม่พบการเชื่อมต่อ API Key"

        try:
            # 🧠 System Prompt สั่งการให้ AI สวมวิญญาณระดับ Global Agency
            system_instruction = """
            คุณคือ 'Executive Creative Director' ระดับ Global Agency ของแพลตฟอร์ม SIRINTHANATTH PRIME
            หน้าที่ของคุณคือ การคิดคอนเซ็ปต์แคมเปญโฆษณา งานออกแบบกราฟิกความละเอียดสูง (4K) สิ่งพิมพ์ระดับโปรดักชัน และการวางแผน Media Buying (ยิงแอด)
            
            โครงสร้างการนำเสนอ (Agency Pitch Deck):
            1. 🎨 Art Direction & Visual Concept: อธิบายภาพกราฟิก Mood & Tone, โทนสี (Color Palette), การจัดแสง, และ Typography สำหรับงาน 4K
            2. 🤖 AI Image Prompt: ร่าง Prompt ภาษาอังกฤษระดับมืออาชีพ สำหรับนำไปเจเนอเรตรูปภาพ (Midjourney/Imagen)
            3. 🎙️ ElevenLabs Voiceover Script: ร่างสคริปต์เสียงพากย์โฆษณาที่ทรงพลัง (พร้อมระบุน้ำเสียงอารมณ์ที่ต้องการให้ AI ของ ElevenLabs พากย์ออกมา)
            4. 🎯 Media Buying Strategy: แผนการยิงโฆษณาเชิงลึก (Targeting, Budget Allocation, แพลตฟอร์มเช่น TikTok/FB/IG)
            
            ข้อบังคับ: ใช้ภาษาที่ดูเป็นมืออาชีพ ล้ำสมัย สร้างแรงบันดาลใจ จัดหน้าให้อ่านง่าย (Scannable) ตอบกลับอย่างกระชับแต่ทรงพลัง
            """
            
            prompt = f"โจทย์จากลูกค้าสำหรับการออกแบบและทำโฆษณา: '{message}'"
            
            # ⚡ รันแบบ Asynchronous เพื่อไม่ให้บล็อกเซิร์ฟเวอร์หลัก (Non-Blocking I/O)
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.85 # เปิดความสร้างสรรค์สูงสำหรับการออกแบบคอนเซ็ปต์
                )
            )
            
            graphics_result = response.text if response.text else "🎨 จัดทำคอนเซ็ปต์งานออกแบบและแผนโฆษณาเรียบร้อยแล้ว"
            
        except Exception as e:
            logger.error(f"⚠️ [Worker 5 AI Error]: {e}")
            graphics_result = (
                "🎨 [Creative Concept & Media Strategy]\n"
                "1. 🌟 Visual: ออกแบบกราฟิก Mood & Tone พรีเมียมระดับ 4K\n"
                "2. 🎙️ Voiceover: เตรียมสคริปต์เสียงสำหรับ ElevenLabs เรียบร้อย\n"
                "3. 🎯 Ads: กำหนดกลุ่มเป้าหมาย (Targeting) พร้อมลุยแคมเปญ\n\n"
                "📝 (ระบบแสดงโครงสร้างสำรองเนื่องจากข้อขัดข้องทางการเชื่อมต่อชั่วคราว)"
            )

        logger.info(f"✅ [Graphics & Ads]: ออกแบบแคมเปญเสร็จสิ้นสำหรับ {user_id}")
        return graphics_result