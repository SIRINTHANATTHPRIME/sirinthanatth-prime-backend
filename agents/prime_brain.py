import os
import time
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

# 🌐 นำเข้าศูนย์บัญชาการ AI ส่วนกลาง (รองรับ Zero Downtime Fallback)
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        CORE_MODEL = "gemini-3.7-flash" # Fallback Model มาตรฐานสูงสุด
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            return genai.Client(api_key=api_key) if api_key else None

# นำเข้าระบบความจำองค์กรและประวัติลูกค้า (Corporate & Chat Memory RAG)
try:
    from agents.memory_engine import recall_corporate_knowledge, recall_memory, save_memory
except ImportError:
    def recall_corporate_knowledge(q): return ""
    def recall_memory(uid, msg): return ""
    def save_memory(uid, summary): pass

logger = logging.getLogger("PrimeBrain")

# 1. 🔑 ตั้งค่าการเชื่อมต่อ AI จากส่วนกลาง
client = PrimeAIConfig.get_client()
MODEL_NAME = PrimeAIConfig.CORE_MODEL

# ==========================================
# 🧠 2. SYSTEM PROMPT: กฎเหล็กของสมองกลระดับประธาน
# ==========================================
SYSTEM_PROMPT = """คุณคือ "SIRINTHANATTH PRIME" สุดยอด AI ผู้ช่วยผู้บริหารและที่ปรึกษาธุรกิจระดับโลก 

กฎเหล็กพิเศษในการประมวลผลข้อมูล (Cross-Reference & Multimodal Engine):
1. การจัดการไฟล์ที่แนบมา (ถ้ามี):
   - ภาพ/เอกสาร (Image/File): อ่านและถอดรหัสข้อความ (OCR), ตัวเลข, เลขโฉนด, ตาราง, หรือสลิปโอนเงินอย่างแม่นยำ
   - เสียง (Audio): ฟังเสียง ถอดความ และวิเคราะห์ความต้องการ หรืออารมณ์จากน้ำเสียง
   - วิดีโอ (Video): ดูวิดีโอ สรุปเหตุการณ์ ถอดสคริปต์ หรือจับผิดรายละเอียดในคลิป
2. ระบบจะแนบ "ข้อมูลจากฐานความรู้ของบริษัท (Corporate DB)" และ "ประวัติการสนทนา" มาให้คุณด้านล่างนี้
3. ⚖️ การเทียบข้อมูล: 
   - หากเป็น "สูตรคำนวณ", "ราคา", "ตรรกะเฉพาะ" หรือ "นโยบายบริษัท" ให้ยึดถือข้อมูลจาก Corporate DB เป็นหลัก (ถือเป็นความจริงสูงสุด)
   - นำข้อมูลทั้งแหล่งความรู้ภายในและบริบทมาประมวลผลร่วมกัน เลือกสิ่งที่ถูกต้อง มีคุณภาพ และแม่นยำที่สุดมาเป็นคำตอบ
4. 🎭 Predictive Empathy: ตอบด้วยความนุ่มนวล เป็นมืออาชีพ ไม่แข็งกระด้าง
5. 🛡️ Legal Shield: ป้องกันความเสี่ยงทางกฎหมาย (สคบ./อย./ก.ล.ต.) อย่างเคร่งครัด
"""

# ==========================================
# ⚙️ 3. แกนประมวลผลเชิงลึก (Deep Reasoning Logic)
# ==========================================
async def generate_intelligent_response(user_id: str, incoming_message: str, file_path: str = None, file_type: str = None) -> str:
    """ฟังก์ชันสมองกลประมวลผลเชิงลึก ดึงความจำ ดึงไฟล์ และผสาน RAG แบบ Asynchronous 100%"""
    
    if not client:
        return "⚠️ System Offline: ไม่พบการเชื่อมต่อ AI_API_KEY ในระบบ"

    uploaded_file = None
    content_to_send = []
    
    try:
        # ==========================================
        # 1. ดึงความรู้จาก Corporate DB และประวัติลูกค้า (RAG Engine)
        # ==========================================
        corporate_context = ""
        user_history = ""
        
        if incoming_message:
            try:
                # ดึงความรู้บริษัทที่เกี่ยวข้องกับคำถาม
                corporate_context = await asyncio.to_thread(recall_corporate_knowledge, incoming_message)
                # ดึงความจำบทสนทนากับลูกค้ารายนี้
                user_history = await asyncio.to_thread(recall_memory, user_id, incoming_message)
            except Exception as rag_err:
                logger.warning(f"⚠️ [RAG Fetch Warning]: {rag_err}")

        # ==========================================
        # 2. ระบบจัดการไฟล์และมัลติมีเดีย (Multimodal)
        # ==========================================
        if file_path and os.path.exists(file_path):
            logger.info(f"🧠 [Prime Brain]: กำลังประมวลผลไฟล์ {file_type} เพื่อบริการลูกค้า...")
            
            mime_type, _ = mimetypes.guess_type(file_path)
            if file_path.lower().endswith('.xlsx'): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            elif file_path.lower().endswith('.xls'): mime_type = "application/vnd.ms-excel"
            elif file_path.lower().endswith('.csv'): mime_type = "text/csv"
            if not mime_type: mime_type = "application/octet-stream"

            try:
                upload_config = types.UploadFileConfig(mime_type=mime_type)
                uploaded_file = await asyncio.to_thread(client.files.upload, file=file_path, config=upload_config)
            except Exception as e:
                logger.warning(f"File upload rejected by AI: {e}")
                return "⚠️ ระบบสามารถประมวลผลได้เฉพาะไฟล์รูปภาพ เสียง วิดีโอ หรือ PDF ครับ รบกวนคุณลูกค้าบันทึกไฟล์เป็น PDF แล้วส่งมาใหม่อีกครั้งนะครับ"

            # ⏳ รอจนกว่าระบบ AI จะแกะไฟล์เสร็จ (จำกัดเวลา 60 วินาทีป้องกันระบบค้าง)
            timeout = 60
            start_time = time.time()
            while uploaded_file.state.name == "PROCESSING":
                if time.time() - start_time > timeout:
                    raise TimeoutError("การประมวลผลไฟล์ใช้เวลานานเกินกำหนด")
                await asyncio.sleep(2)
                uploaded_file = await asyncio.to_thread(client.files.get, name=uploaded_file.name)
                
            if uploaded_file.state.name == "FAILED":
                return "⚠️ ขออภัยครับ โครงสร้างไฟล์มีความซับซ้อนเกินไป ระบบไม่สามารถอ่านได้ครับ"
                
            content_to_send.append(uploaded_file)
            
            if not incoming_message or incoming_message.startswith("[System Alert:"):
                content_to_send.append("ช่วยวิเคราะห์ อธิบาย และสรุปรายละเอียดจากไฟล์นี้ให้ลูกค้าเข้าใจอย่างสุภาพครับ")
            else:
                content_to_send.append(incoming_message)
        else:
            # ประกอบร่าง Prompt พร้อมฉีดข้อมูล RAG เข้าไปให้ AI ทราบ
            final_prompt = f"คำถามจากลูกค้า: {incoming_message}"
            if corporate_context:
                final_prompt += f"\n\n[ข้อมูลจากฐานความรู้บริษัท (Corporate DB)]:\n{corporate_context}"
            if user_history:
                final_prompt += f"\n\n[ประวัติการสนทนาเดิมกับลูกค้า]:\n{user_history}"
                
            content_to_send.append(final_prompt)

        # ==========================================
        # 3. สั่งรันโมเดลเรือธง (Gemini 3.7 Flash)
        # ==========================================
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL_NAME,
            contents=content_to_send,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7
            )
        )
        
        reply_text = response.text if response.text else "รับทราบข้อมูลเรียบร้อยครับ มีอะไรให้ผมช่วยเหลือเพิ่มเติมแจ้งได้เลยครับ"
        
        # บันทึกความจำการสนทนารายบุคคลเก็บไว้เบื้องหลัง (Background Memory)
        if incoming_message:
            asyncio.create_task(asyncio.to_thread(save_memory, user_id, f"Q: {incoming_message} | A: {reply_text[:150]}"))
            
        return reply_text
        
    except Exception as e:
        logger.error(f"❌ [Prime Brain Error]: {e}")
        return "ขออภัยครับคุณลูกค้า ขณะนี้ระบบประมวลผลหลักมีผู้ใช้งานหนาแน่น กรุณาลองส่งข้อความใหม่อีกครั้งในสักครู่ครับ"
        
    finally:
        # 🧹 ระบบทำลายไฟล์ทิ้งเพื่อ PDPA และความปลอดภัยของลูกค้า
        if uploaded_file:
            try:
                await asyncio.to_thread(client.files.delete, name=uploaded_file.name)
            except:
                pass