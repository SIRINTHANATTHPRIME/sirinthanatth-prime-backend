import os
import time
import logging
import asyncio
import pathlib
from PIL import Image
from typing import Optional, Dict, Any, List

from google import genai
from google.genai import types

# 🚀 นำเข้าระบบความจำแบบ Async ที่เราเพิ่งอัปเกรดไป
from agents.memory_engine import recall_memory, recall_corporate_knowledge, save_memory
from core_services.ai_config import PrimeAIConfig

logger = logging.getLogger("Prime-Brain")

# =========================================================
# 🧠 The Core Intelligence (ระบบแกนสมองหลัก)
# =========================================================
class PrimeBrainEngine:
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        # ใช้รุ่น Flash สำหรับความเร็ว หรือ Pro สำหรับการวิเคราะห์ที่ซับซ้อนสุดยอด
        self.model_name = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-3.7-flash") 
        
        # 🎭 จิตวิทยาและบุคลิกภาพของ AI (Persona)
        self.system_instruction = """
        คุณคือ 'SIRINTHANATTH PRIME' สุดยอดผู้ช่วย AI ระดับ Enterprise และที่ปรึกษาของผู้บริหารระดับสูง
        
        กฎเหล็กในการสื่อสาร:
        1. ความเป็นมืออาชีพ: ตอบคำถามอย่างชาญฉลาด สุภาพ หรูหรา อบอุ่น และกระชับตรงประเด็น (ลงท้ายด้วย ครับ/ค่ะ เสมอ)
        2. การใช้ความจำ: หากมีข้อมูลอดีต (User Memory) หรือกฎบริษัท (Corporate Knowledge) ให้ใช้ข้อมูลนั้นประกอบการตัดสินใจเสมอโดยไม่ต้องอ้างอิงว่าได้ข้อมูลมาจากไหน
        3. ความแม่นยำ: หากไม่ทราบข้อมูล ให้ตอบอย่างสุภาพว่ากำลังประสานงานตรวจสอบ ไม่แต่งเรื่องขึ้นเองเด็ดขาด
        4. การวิเคราะห์ไฟล์: หากผู้ใช้แนบรูปภาพหรือเอกสาร ให้วิเคราะห์เชิงลึกและดึง Insight ที่มีประโยชน์ที่สุดออกมา
        """

    async def _compress_and_save_memory(self, user_id: str, user_message: str, ai_response: str):
        """🧹 บีบอัดความจำ (Summarization) และบันทึกลง Vector DB เบื้องหลัง เพื่อประหยัดพื้นที่และ Token"""
        try:
            prompt = f"""
            สรุปใจความสำคัญสั้นๆ 1 ประโยค (ไม่เกิน 30 คำ) จากบทสนทนานี้ เพื่อใช้เป็น 'ความจำ' ในอนาคต
            User: {user_message}
            AI: {ai_response}
            """
            # ใช้แบบ Async เพื่อไม่ให้บล็อกระบบ
            res = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-3.7-flash",
                contents=prompt
            )
            summary = res.text.strip()
            if summary:
                await save_memory(user_id, summary)
                logger.info(f"🧠 [Memory Engine]: บีบอัดและบันทึกความจำสำเร็จ -> {summary}")
        except Exception as e:
            logger.error(f"⚠️ [Memory Compress Error]: {e}")

    async def process_interaction(self, user_id: str, message: str, file_path: Optional[str] = None, file_type: Optional[str] = None) -> str:
        """⚡ วงจรประมวลผลหลัก (RAG + Vision + Generation)"""
        
        start_time = time.time()
        logger.info(f"🧠 [Prime Brain]: กำลังประมวลผลคำสั่งจาก {user_id}")

        if not self.client:
            return "ขออภัยครับ ระบบสมองกลส่วนกลางขาดการเชื่อมต่อ (Missing API Key) ทีมวิศวกรกำลังเร่งแก้ไขครับ"

        # ---------------------------------------------------------
        # 🔍 1. Parallel RAG (ดึงความจำ 2 แหล่งพร้อมกันแบบคู่ขนาน เร็วขึ้น 2 เท่า!)
        # ---------------------------------------------------------
        mem_task = recall_memory(user_id, message)
        corp_task = recall_corporate_knowledge(message)
        
        # รอให้ทั้งคู่ดึงข้อมูลเสร็จพร้อมกัน
        user_memory, corp_knowledge = await asyncio.gather(mem_task, corp_task)

        # ---------------------------------------------------------
        # 🧱 2. Context Injection (ประกอบร่างความจำเข้ากับคำสั่ง)
        # ---------------------------------------------------------
        enriched_prompt = message
        
        if corp_knowledge or user_memory:
            enriched_prompt = f"คำสั่งของผู้บริหาร: {message}\n\n"
            if corp_knowledge:
                enriched_prompt += f"--- ข้อมูล/นโยบายขององค์กร ---\n{corp_knowledge}\n\n"
            if user_memory:
                enriched_prompt += f"--- บริบท/ความจำในอดีตของผู้บริหารท่านนี้ ---\n{user_memory}\n\n"
            enriched_prompt += "โปรดนำข้อมูลด้านบนมาประกอบการตอบคำถามอย่างแนบเนียนและเป็นธรรมชาติที่สุด"

        # ---------------------------------------------------------
        # 👁️ 3. Multi-Modal Handling (จัดการไฟล์แนบ ภาพ/เอกสาร)
        # ---------------------------------------------------------
        contents_to_send = []
        uploaded_gemini_file = None
        
        if file_path and os.path.exists(file_path):
            try:
                if file_type == "image":
                    # ใช้ PIL เปิดภาพให้ Gemini Vision
                    img = await asyncio.to_thread(Image.open, file_path)
                    contents_to_send.append(img)
                else:
                    # ถ้าเป็นไฟล์ PDF, Video, Audio ให้อัปโหลดเข้า Gemini File API
                    logger.info(f"📁 [File API]: กำลังอัปโหลดไฟล์ {file_type} เข้าสู่สมองกล...")
                    uploaded_gemini_file = await asyncio.to_thread(self.client.files.upload, file=file_path)
                    contents_to_send.append(uploaded_gemini_file)
            except Exception as e:
                logger.error(f"❌ [Media Processing Error]: {e}")
                enriched_prompt += "\n[หมายเหตุ: ระบบไม่สามารถเปิดอ่านไฟล์ที่แนบมาได้ โปรดแจ้งข้อขัดข้องนี้ให้ผู้บริหารทราบ]"

        # ใส่ข้อความลงไปเป็นชิ้นสุดท้าย
        contents_to_send.append(enriched_prompt)

        # ---------------------------------------------------------
        # 🚀 4. AI Generation (สร้างคำตอบด้วย Gemini 3.7)
        # ---------------------------------------------------------
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=contents_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.4, # ตั้งค่า 0.4 ให้มีความคิดสร้างสรรค์แต่ยังคงความแม่นยำสูง
                )
            )
            reply_text = response.text if response.text else "ระบบประมวลผลเสร็จสิ้นครับ"
            
            # ลบไฟล์ออกจาก Gemini API เพื่อรักษาความปลอดภัย (Zero-Data Retention)
            if uploaded_gemini_file:
                await asyncio.to_thread(self.client.files.delete, name=uploaded_gemini_file.name)
                logger.info(f"🧹 [Gemini API]: ลบไฟล์ลับ {uploaded_gemini_file.name} สำเร็จ")

            # ---------------------------------------------------------
            # 💾 5. Background Memory Saving (บันทึกความจำโดยไม่ให้ลูกค้าต้องรอ)
            # ---------------------------------------------------------
            asyncio.create_task(self._compress_and_save_memory(user_id, message, reply_text))

            logger.info(f"✅ [Prime Brain]: ประมวลผลสำเร็จใน {time.time() - start_time:.2f} วินาที")
            return reply_text

        except Exception as e:
            logger.error(f"❌ [Generation Error]: {e}", exc_info=True)
            return "ขออภัยครับ สมองกลส่วนกลางเกิดข้อขัดข้องระหว่างการประมวลผลขั้นสูง ทีมวิศวกรกำลังเร่งตรวจสอบให้ครับ"

# =========================================================
# 🔌 Global Instance (เรียกใช้งานได้ทันทีจาก routes_line.py)
# =========================================================
prime_engine = PrimeBrainEngine()

async def generate_intelligent_response(user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
    """ฟังก์ชัน Wrapper สำหรับถูกเรียกจากภายนอก (เข้ากันได้กับ routes_line.py แบบ 100%)"""
    return await prime_engine.process_interaction(user_id, message, file_path, file_type)