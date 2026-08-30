import os
import time
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

# =========================================================
# 🌐 นำเข้าศูนย์บัญชาการ AI ส่วนกลาง (ระบบอมตะ Zero Downtime Fallback)
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-2.5-pro" # 🚀 ใช้โมเดล Pro สำหรับสมองกลวิเคราะห์เชิงลึก
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            return genai.Client(api_key=api_key) if api_key else None

# =========================================================
# 🧠 นำเข้าระบบความจำองค์กรและประวัติลูกค้า (Graph RAG & Vector Memory)
# =========================================================
try:
    from agents.memory_engine import recall_corporate_knowledge, recall_memory, save_memory
except ImportError:
    def recall_corporate_knowledge(q): return ""
    def recall_memory(uid, msg): return ""
    def save_memory(uid, summary): pass

logger = logging.getLogger("PrimeBrain")

# 1. 🔑 ตั้งค่าการเชื่อมต่อ AI จากส่วนกลาง
client = PrimeAIConfig.get_client()

# ดึงชื่อโมเดลระดับ Pro สำหรับงานซับซ้อน (ถ้าไม่มีให้ใช้ default)
MODEL_NAME = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-2.5-pro")

# =========================================================
# 👑 2. SYSTEM PROMPT: กฎเหล็กของสมองกลระดับ VVIP (Predictive Empathy & Graph RAG)
# =========================================================
SYSTEM_PROMPT = """คุณคือ "SIRINTHANATTH PRIME" สุดยอด AI ผู้ช่วยผู้บริหารและที่ปรึกษาธุรกิจระดับโลก 

หน้าที่ของคุณคือการคิดวิเคราะห์เชิงลึก (Deep Reasoning) และเชื่อมโยงข้อมูล (Graph RAG) เพื่อให้คำปรึกษาระดับ VVIP

กฎเหล็กพิเศษในการประมวลผลข้อมูล:
1. 🧠 การเชื่อมโยงความจำ (Relational Memory): 
   - ระบบจะแนบ [ข้อมูลบริษัท] และ [ประวัติลูกค้า] มาให้คุณด้านล่าง 
   - ให้คุณเชื่อมโยงประวัติลูกค้าเข้ากับความต้องการปัจจุบัน เพื่อพยากรณ์สิ่งที่ลูกค้าต้องการ (Predictive Empathy) และนำเสนอโซลูชันแบบ "รู้ใจ" ก่อนที่ลูกค้าจะร้องขอ
2. 🧠 Predictive Empathy (การอ่านใจเชิงลึก): 
   - วิเคราะห์น้ำเสียงและอารมณ์ (Sentiment) จากประวัติการสนทนาและข้อความล่าสุด หากลูกค้าเร่งรีบให้ตอบกระชับ หากกังวลให้ตอบด้วยความเข้าอกเข้าใจอย่างนุ่มนวล
   - เสนอแนวทางแก้ปัญหาเชิงรุก (Proactive) ก่อนที่ลูกค้าจะเอ่ยปากร้องขอ เช่น แจ้งเตือนความล่าช้าล่วงหน้าพร้อมเสนอสิทธิพิเศษ
3. 👁️ การจัดการไฟล์แบบผสมผสาน (Omni-Modal):
   - ภาพ/เอกสาร: สกัดข้อความ (OCR), ตัวเลข, ตาราง, งบการเงิน, หรือสลิป อย่างแม่นยำ 100%
   - เสียง/วิดีโอ: ถอดสคริปต์ สรุปเหตุการณ์ และประเมิน "อารมณ์" (Sentiment) จากเนื้อหา
4. ⚖️ ความถูกต้องสูงสุด: 
   - หากคำถามเกี่ยวข้องกับ "สูตรคำนวณ", "ราคา", หรือ "นโยบายบริษัท" ให้ยึดถือข้อมูลจาก [ข้อมูลบริษัท] เป็นความจริงสูงสุด (Single Source of Truth)
5. 🎭 จิตวิทยาการบริการ (Executive Persona): 
   - ตอบด้วยความนุ่มนวล เป็นมืออาชีพ ทรงพลัง เคารพลูกค้าเสมอ 
   - หากลูกค้ามีปัญหา ให้แสดงความเข้าอกเข้าใจ (Empathy) และเสนอทางแก้ทันที
6. 🕒 ความรวดเร็วในการตอบสนอง:
   - ตอบกลับลูกค้าภายใน 5 วินาที เพื่อให้ได้รับประสบการณ์การบริการที่ยอดเยี่ยม
7. 🕸️ Graph RAG (การเชื่อมโยงข้อมูลซับซ้อน):
   - เมื่อดึงข้อมูลจาก Corporate DB และประวัติลูกค้า ให้วิเคราะห์ความสัมพันธ์เชิงลึก (เช่น โฉนดที่ดินแปลง A เชื่อมโยงกับ กฎหมายผังเมืองสีแดง และ กฎหมายควบคุมอาคาร)
8. 🛡️ เกราะป้องกันทางกฎหมาย (Legal Shield): 
   - ห้ามออกคำแนะนำการลงทุน (Buy/Sell) โดยตรง และหลีกเลี่ยงการการันตีผลลัพธ์ 100% เพื่อป้องกันกฎหมาย ก.ล.ต. / สคบ. / อย.
"""

# =========================================================
# ⚙️ 3. แกนประมวลผลเชิงลึก (Deep Reasoning Logic)
# =========================================================
async def generate_intelligent_response(user_id: str, incoming_message: str, file_path: str = None, file_type: str = None) -> str:
    """ฟังก์ชันสมองกลประมวลผลเชิงลึก ดึงความจำ ดึงไฟล์ และผสาน Graph RAG แบบ Asynchronous 100%"""
    
    if not client:
        return "⚠️ System Offline: ไม่พบการเชื่อมต่อ API Key ในระบบส่วนกลางครับ"

    uploaded_file = None
    content_to_send = []
    
    try:
        # ==========================================
        # 1. ดึงความรู้จาก Corporate DB และประวัติลูกค้า (Graph RAG Engine)
        # ==========================================
        corporate_context = ""
        user_history = ""
        
        if incoming_message:
            try:
                # ดึงความรู้บริษัทที่เกี่ยวข้อง (Corporate Rules)
                corporate_context = await asyncio.to_thread(recall_corporate_knowledge, incoming_message)
                # ดึงความจำบทสนทนากับลูกค้ารายนี้ (Predictive Empathy Data)
                user_history = await asyncio.to_thread(recall_memory, user_id, incoming_message)
            except Exception as rag_err:
                logger.warning(f"⚠️ [RAG Fetch Warning]: {rag_err}")

        # ==========================================
        # 2. ระบบจัดการไฟล์และมัลติมีเดียขั้นสูง (Multimodal Processing)
        # ==========================================
        if file_path and os.path.exists(file_path):
            logger.info(f"🧠 [Prime Brain]: กำลังอัปโหลดและประมวลผลไฟล์ {file_type} เพื่อบริการลูกค้า...")
            
            mime_type, _ = mimetypes.guess_type(file_path)
            if file_path.lower().endswith('.xlsx'): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            elif file_path.lower().endswith('.xls'): mime_type = "application/vnd.ms-excel"
            elif file_path.lower().endswith('.csv'): mime_type = "text/csv"
            elif file_path.lower().endswith('.pdf'): mime_type = "application/pdf"
            if not mime_type: mime_type = "application/octet-stream"

            try:
                upload_config = types.UploadFileConfig(mime_type=mime_type)
                uploaded_file = await asyncio.to_thread(client.files.upload, file=file_path, config=upload_config)
            except Exception as e:
                logger.warning(f"⚠️ File upload rejected by AI: {e}")
                return "⚠️ ระบบสามารถประมวลผลได้เฉพาะไฟล์รูปภาพ เสียง วิดีโอ หรือ PDF ครับ รบกวนคุณลูกค้าบันทึกไฟล์เป็น PDF หรือเปลี่ยนชนิดไฟล์แล้วส่งมาใหม่อีกครั้งนะครับ"

            # ⏳ ระบบรอคอยการถอดรหัสแบบปลอดภัย (Anti-Freeze Guardrail)
            timeout = 60 # จำกัดเวลา 60 วินาที
            start_time = time.time()
            while uploaded_file.state.name == "PROCESSING":
                if time.time() - start_time > timeout:
                    raise TimeoutError("การประมวลผลไฟล์ใช้เวลานานเกินกำหนดเพื่อความปลอดภัยของเซิร์ฟเวอร์")
                await asyncio.sleep(2)
                uploaded_file = await asyncio.to_thread(client.files.get, name=uploaded_file.name)
                
            if uploaded_file.state.name == "FAILED":
                return "⚠️ ขออภัยครับ โครงสร้างไฟล์มีความซับซ้อนเกินไป ระบบความปลอดภัย AI ไม่สามารถถอดรหัสไฟล์นี้ได้ครับ"
                
            content_to_send.append(uploaded_file)
            
            if not incoming_message or incoming_message.startswith("[System Alert:"):
                content_to_send.append("โปรดวิเคราะห์ สกัดข้อมูลสำคัญ และอธิบายรายละเอียดเชิงลึกจากไฟล์นี้อย่างมืออาชีพครับ")
            else:
                content_to_send.append(incoming_message)
        else:
            content_to_send.append(incoming_message)

        # ==========================================
        # 3. ประกอบร่าง Graph RAG Context (ฉีดความจำเข้าสมองกล)
        # ==========================================
        # หากมี Context จะฉีดเข้าไปใน Prompt เพื่อให้ AI นำไปประกอบการตัดสินใจ
        final_prompt = ""
        if corporate_context or user_history:
            final_prompt += "\n\n--- [ข้อมูลสนับสนุนจากระบบความจำ Graph RAG] ---\n"
            if corporate_context:
                final_prompt += f"🏢 [กฎบริษัท/ข้อมูลสินค้า]:\n{corporate_context}\n"
            if user_history:
                final_prompt += f"👤 [ประวัติและความชอบของลูกค้ารายนี้]:\n{user_history}\n"
            final_prompt += "--------------------------------------------------\nโปรดใช้ข้อมูลข้างต้นประกอบการวิเคราะห์และตอบคำถามอย่างเป็นธรรมชาติ"
            
            content_to_send.append(final_prompt)

        # ==========================================
        # 4. สั่งรันโมเดลเรือธง (Gemini 2.5 Pro - Deep Reasoning)
        # ==========================================
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL_NAME,
            contents=content_to_send,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.4 # อุณหภูมิ 0.4 เหมาะสมที่สุดสำหรับงานวิเคราะห์เชิงลึกที่ต้องการความถูกต้องแต่ยังคงความเป็นมนุษย์
            )
        )
        
        reply_text = response.text if response.text else "รับทราบข้อมูลเรียบร้อยครับ มีข้อมูลส่วนไหนให้ผมช่วยเหลือเพิ่มเติม แจ้งได้เลยครับ"
        
        # ==========================================
        # 5. บันทึกความจำการสนทนารายบุคคลเก็บไว้เบื้องหลัง (Background Memory)
        # ==========================================
        if incoming_message and not incoming_message.startswith("[System Alert:"):
            # ดึงใจความสำคัญเพื่อไม่ให้เปลืองพื้นที่ Vector DB
            memory_snippet = f"User: {incoming_message[:200]}... | AI: {reply_text[:200]}..."
            asyncio.create_task(asyncio.to_thread(save_memory, user_id, memory_snippet))
            
        return reply_text
        
    except TimeoutError:
        logger.error("❌ [Prime Brain Timeout]: ไฟล์มีขนาดใหญ่หรือซับซ้อนเกินไป")
        return "ขออภัยครับคุณลูกค้า ไฟล์มีขนาดใหญ่หรือซับซ้อนเกินไป ทำให้ระบบประมวลผลนานกว่าปกติ รบกวนแบ่งไฟล์หรือย่อขนาดลงนิดนึงนะครับ"
    except Exception as e:
        logger.error(f"❌ [Prime Brain Error]: {e}")
        return "ขออภัยครับคุณลูกค้า ขณะนี้ระบบประมวลผลหลักระดับลึกมีผู้ใช้งานหนาแน่น กรุณาลองส่งข้อความใหม่อีกครั้งในสักครู่ครับ"
        
    finally:
        # ==========================================
        # 🧹 6. Zero-Data Retention (ทำลายไฟล์ทิ้งเพื่อ PDPA 100%)
        # ==========================================
        if uploaded_file:
            try:
                await asyncio.to_thread(client.files.delete, name=uploaded_file.name)
                logger.info(f"🛡️ [Zero-Data Security]: ลบไฟล์ {uploaded_file.name} ออกจากระบบ AI Cloud เรียบร้อยแล้ว")
            except Exception as e:
                logger.error(f"⚠️ [File Deletion Error]: ไม่สามารถลบไฟล์จาก AI Cloud ได้ -> {e}")