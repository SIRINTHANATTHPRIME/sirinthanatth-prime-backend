import os
import time
import logging
import asyncio
import mimetypes
from typing import Optional
from PIL import Image
from google import genai
from google.genai import types

# 🌐 นำเข้าศูนย์บัญชาการ AI (รองรับ Zero Downtime)
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-3.7-pro" # 🚀 อัปเกรดเป็นรุ่น Pro สำหรับวิเคราะห์ข้อมูลระดับลึก
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

# 🧠 นำเข้าระบบความจำ (Corporate RAG & Chat Memory)
try:
    from agents.memory_engine import save_memory, recall_memory, recall_corporate_knowledge
except ImportError:
    async def save_memory(uid, msg): pass
    async def recall_memory(uid, msg): return ""
    async def recall_corporate_knowledge(msg): return ""

logger = logging.getLogger("Prime-Brain-Engine")

class PrimeBrainEngine:
    """
    🧠 The Core Intelligence (ระบบแกนสมองหลักระดับโลก)
    ฟังก์ชัน: Hybrid RAG, Multi-Modal Vision, Google Search Grounding & Deep Reasoning
    """
    
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-3.7-pro")
        
        # 🎭 จิตวิทยาและบุคลิกภาพของ AI (Ultimate Persona)
        self.system_instruction = """
        คุณคือ 'SIRINTHANATTH PRIME' สุดยอด AI ผู้ช่วยผู้บริหารและที่ปรึกษาธุรกิจระดับโลก
        
        กฎเหล็กพิเศษในการประมวลผลข้อมูล (Cross-Reference & Multimodal Engine):
        1. การจัดการไฟล์ที่แนบมา:
           - ภาพ/เอกสาร: อ่านและถอดรหัสข้อความ (OCR), ตัวเลข, ตาราง, เลขโฉนด หรือสลิปโอนเงินอย่างแม่นยำ
           - เสียง/วิดีโอ: วิเคราะห์ความต้องการ สรุปเหตุการณ์ หรือจับอารมณ์จากไฟล์มัลติมีเดีย
        2. การเปรียบเทียบข้อมูล (Truth-Based Strategy):
           - หากเป็น "สูตรคำนวณ", "ราคา", หรือ "นโยบาย" ให้ยึดข้อมูลจาก Corporate DB เป็นความจริงสูงสุด
           - หากเป็น "ข่าวสาร", "เทรนด์", หรือ "สภาวะตลาด" ให้ยึดข้อมูลจากการค้นหา (Google Search) ที่สดใหม่ที่สุด
        3. Predictive Empathy: ตอบคำถามด้วยความฉลาด หรูหรา สุภาพ เป็นมืออาชีพ (ลงท้ายด้วย ครับ/ค่ะ เสมอ) ไม่แข็งกระด้าง
        4. Legal Shield: ป้องกันความเสี่ยงทางกฎหมาย (PDPA, ก.ล.ต., สคบ.) อย่างเคร่งครัด ห้ามให้คำแนะนำที่ละเมิดกฎหมายเด็ดขาด
        """

    async def _compress_and_save_memory(self, user_id: str, user_message: str, ai_response: str):
        """🧹 บีบอัดความจำและบันทึกลง Vector DB เบื้องหลัง (Non-Blocking)"""
        try:
            prompt = f"""
            สรุปใจความสำคัญสั้นๆ ไม่เกิน 30 คำ จากบทสนทนานี้ เพื่อใช้เป็น 'ความจำ' ในอนาคต
            User: {user_message}
            AI: {ai_response}
            """
            res = await asyncio.to_thread(
                self.client.models.generate_content,
                model="gemini-3.7-flash", # ใช้ Flash เพื่อความเร็วในการบีบอัด
                contents=prompt
            )
            summary = res.text.strip()
            if summary:
                await save_memory(user_id, summary)
                logger.info(f"🧠 [Memory Engine]: บันทึกความจำระยะยาวสำเร็จ -> {summary}")
        except Exception as e:
            logger.error(f"⚠️ [Memory Compress Error]: {e}")

    async def process_interaction(self, user_id: str, message: str, file_path: Optional[str] = None, file_type: Optional[str] = None) -> str:
        """⚡ วงจรประมวลผลหลัก (Hybrid RAG + Vision + Generation)"""
        start_time = time.time()
        logger.info(f"🧠 [Prime Brain]: กำลังประมวลผลคำสั่งเชิงลึกจาก {user_id}")

        if not self.client:
            return "ขออภัยครับ ระบบสมองกลส่วนกลางขาดการเชื่อมต่อ (Missing API Key) ทีมวิศวกรกำลังเร่งแก้ไขครับ"

        # ---------------------------------------------------------
        # 🔍 1. Parallel RAG (ดึงความจำลูกค้าและบริษัทพร้อมกัน)
        # ---------------------------------------------------------
        user_memory, corp_knowledge = "", ""
        try:
            mem_task = recall_memory(user_id, message)
            corp_task = recall_corporate_knowledge(message)
            user_memory, corp_knowledge = await asyncio.gather(mem_task, corp_task)
        except Exception as e:
            logger.warning(f"⚠️ [RAG System Error]: {e}")

        # ---------------------------------------------------------
        # 🧱 2. Context Injection (ประกอบร่างความจำเข้ากับคำสั่ง)
        # ---------------------------------------------------------
        enriched_prompt = f"คำสั่งหรือคำถามจากผู้ใช้: {message}\n\n"
        
        if corp_knowledge or user_memory:
            if corp_knowledge:
                enriched_prompt += f"--- ข้อมูล/นโยบายขององค์กร (ยึดถือเป็นหลัก) ---\n{corp_knowledge}\n\n"
            if user_memory:
                enriched_prompt += f"--- บริบท/ความจำในอดีตของผู้ใช้ท่านนี้ ---\n{user_memory}\n\n"
            enriched_prompt += "โปรดนำข้อมูลด้านบนมาประกอบการตอบคำถามอย่างแนบเนียนและถูกต้องที่สุด"

        # ---------------------------------------------------------
        # 👁️ 3. Multi-Modal Handling (จัดการไฟล์แนบระดับ Enterprise)
        # ---------------------------------------------------------
        contents_to_send = []
        uploaded_gemini_file = None
        
        if file_path and os.path.exists(file_path):
            try:
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type: mime_type = "application/octet-stream"

                # สำหรับรูปภาพ สามารถใช้ PIL ส่งให้โมเดลโดยตรงเพื่อความเร็ว
                if file_type == "image":
                    img = await asyncio.to_thread(Image.open, file_path)
                    contents_to_send.append(img)
                else:
                    logger.info(f"📁 [File API]: กำลังอัปโหลดเอกสาร/มัลติมีเดียเข้าสู่สมองกล...")
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_gemini_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                    
                    # Wait for processing (สำหรับวิดีโอหรือเอกสารขนาดใหญ่)
                    timeout = 120
                    wait_start = time.time()
                    while uploaded_gemini_file.state.name == "PROCESSING":
                        if time.time() - wait_start > timeout:
                            raise TimeoutError("หมดเวลาประมวลผลไฟล์มัลติมีเดีย")
                        await asyncio.sleep(2.5)
                        uploaded_gemini_file = await asyncio.to_thread(self.client.files.get, name=uploaded_gemini_file.name)
                        
                    if uploaded_gemini_file.state.name == "FAILED":
                        raise ValueError("AI ถอดรหัสไฟล์ล้มเหลว (File Corrupted or Unsupported)")
                        
                    contents_to_send.append(uploaded_gemini_file)
            except Exception as e:
                logger.error(f"❌ [Media Processing Error]: {e}")
                enriched_prompt += "\n[System Alert: ระบบไม่สามารถอ่านไฟล์ที่แนบมาได้ โปรดแจ้งข้อขัดข้องนี้ให้ผู้ใช้ทราบด้วยความสุภาพ]"

        contents_to_send.append(enriched_prompt)

        # ---------------------------------------------------------
        # 🚀 4. AI Generation (สร้างคำตอบด้วย Gemini Pro + Google Search)
        # ---------------------------------------------------------
        try:
            logger.info("🌐 [Prime Brain]: กำลังวิเคราะห์ข้อมูลเชิงลึกและสืบค้นความจริง (Search Grounding)...")
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=contents_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.4, # ความสมดุลระหว่างตรรกะเชิงลึกและความเป็นธรรมชาติ
                    tools=[{"google_search": {}}] # เปิดระบบตรวจสอบความจริงบนอินเทอร์เน็ต
                )
            )
            
            reply_text = response.text if response.text else "ระบบประมวลผลเสร็จสิ้นเรียบร้อยครับ มีข้อมูลส่วนใดให้ผมวิเคราะห์เพิ่มเติมไหมครับ"
            
            # 💾 สั่งบันทึกความจำลง Background
            asyncio.create_task(self._compress_and_save_memory(user_id, message, reply_text))

            logger.info(f"✅ [Prime Brain]: ปฏิบัติการสำเร็จใน {time.time() - start_time:.2f} วินาที")
            return reply_text

        except Exception as e:
            logger.error(f"❌ [Generation Error]: {e}", exc_info=True)
            return "ขออภัยครับคุณลูกค้า ขณะนี้เครือข่ายสมองกลส่วนกลางมีผู้ใช้งานหนาแน่น กรุณาลองส่งข้อความใหม่อีกครั้งในสักครู่ครับ"

        finally:
            # ---------------------------------------------------------
            # 🧹 5. Zero-Data Retention (ทำลายหลักฐานไฟล์ข้อมูลส่วนบุคคล)
            # ---------------------------------------------------------
            if uploaded_gemini_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_gemini_file.name)
                    logger.info(f"🛡️ [Cybersecurity Guard]: ทำลายเอกสารลับ {uploaded_gemini_file.name} ออกจากเซิร์ฟเวอร์คลาวด์เรียบร้อย")
                except Exception as e:
                    logger.error(f"⚠️ [Cleanup Failed]: ไม่สามารถทำลายไฟล์ได้ -> {e}")

# =========================================================
# 🔌 Global Instance & Wrapper (ทำงานร่วมกับ routes_line.py ได้ 100%)
# =========================================================
prime_engine = PrimeBrainEngine()

async def generate_intelligent_response(user_id: str, incoming_message: str, file_path: str = None, file_type: str = None) -> str:
    """ฟังก์ชันสะพานเชื่อม สำหรับถูกเรียกใช้งานจาก API Gateway ภายนอก"""
    return await prime_engine.process_interaction(user_id, incoming_message, file_path, file_type)