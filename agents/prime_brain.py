import os
import time
import logging
from google import genai
from google.genai import types

# นำเข้าระบบความจำ (Hippocampus)
from agents.memory_engine import recall_memory, save_memory, recall_corporate_knowledge

# ตั้งค่า Logger
logger = logging.getLogger("PrimeBrain")

# 1. 🔑 ตั้งค่าการเชื่อมต่อ AI
GEMINI_KEY = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# 🚀 อัปเกรดเป็นโมเดล Pro รุ่นเสถียรที่สุดเพื่อป้องกัน Error 404
MODEL_NAME = "gemini-1.5-pro" 

# ==========================================
# 🧠 2. SYSTEM PROMPT: กฎเหล็กของสมองกลระดับประธาน
# ==========================================
SYSTEM_PROMPT = """คุณคือ "SIRINTHANATTH PRIME" สุดยอด AI ผู้ช่วยผู้บริหารและที่ปรึกษาธุรกิจระดับโลก 

กฎเหล็กพิเศษในการประมวลผลข้อมูล (Cross-Reference & Multimodal Engine):
1. การจัดการไฟล์ที่แนบมา (ถ้ามี):
   - ภาพ/เอกสาร (Image/File): อ่านและถอดรหัสข้อความ (OCR), ตัวเลข, เลขโฉนด, ตาราง, หรือสลิปโอนเงินอย่างแม่นยำ
   - เสียง (Audio): ฟังเสียง ถอดความ และวิเคราะห์ความต้องการ หรืออารมณ์จากน้ำเสียง
   - วิดีโอ (Video): ดูวิดีโอ สรุปเหตุการณ์ ถอดสคริปต์ หรือจับผิดรายละเอียดในคลิป
2. ระบบจะแนบ "ข้อมูลจากฐานความรู้ของบริษัท (Corporate DB)" มาให้คุณ
3. ให้คุณเชื่อมต่อข้อมูลออนไลน์ (Google Search) เพื่อดูเทรนด์หรืออัปเดตล่าสุด
4. ⚖️ การเทียบข้อมูล: 
   - หากเป็น "สูตรคำนวณ", "ราคา", "ตรรกะเฉพาะ" หรือ "นโยบาย" ให้ยึดถือข้อมูลจาก Corporate DB เป็นหลัก (ถือเป็นความจริงสูงสุด)
   - หากเป็น "ข่าวสาร", "สภาวะตลาด", "เทรนด์" ให้ยึดข้อมูลจากออนไลน์ที่สดใหม่ที่สุด
   - นำข้อมูลทั้ง 2 แหล่งมาประมวลผลร่วมกัน เลือกสิ่งที่ถูกต้อง มีคุณภาพ และแม่นยำที่สุดมาเป็นคำตอบ
5. 🎭 Predictive Empathy: ตอบด้วยความนุ่มนวล เป็นมืออาชีพ ไม่แข็งกระด้าง
6. 🛡️ Legal Shield: ป้องกันความเสี่ยงทางกฎหมาย (สคบ./อย./ก.ล.ต.) อย่างเคร่งครัด
"""

# ==========================================
# ⚙️ 3. แกนประมวลผลเชิงลึก (Deep Reasoning Logic)
# ==========================================
async def generate_intelligent_response(user_id: str, incoming_message: str, file_path: str = None, file_type: str = None) -> str:
    """ฟังก์ชันสมองกลประมวลผลเชิงลึก ดึงความจำ ดึงไฟล์ และสืบค้น Google"""
    
    if not client:
        return "⚠️ System Offline: ไม่พบการเชื่อมต่อ AI_API_KEY ในระบบ"

    uploaded_file = None
    content_to_send = []

    try:
        # ==========================================
        # STEP 1: จัดการไฟล์มัลติมีเดีย (ถ้ามี)
        # ==========================================
        if file_path and os.path.exists(file_path):
            logger.info(f"📤 [Prime Brain]: กำลังอัปโหลดไฟล์ {file_type} เพื่อวิเคราะห์...")
            uploaded_file = client.files.upload(file=file_path)
            
            # รอกรณีเป็นไฟล์วิดีโอใหญ่ๆ
            while uploaded_file.state.name == "PROCESSING":
                logger.info("⏳ [Prime Brain]: AI กำลังย่อยข้อมูลไฟล์วิดีโอ...")
                time.sleep(2)
                uploaded_file = client.files.get(name=uploaded_file.name)
            
            if uploaded_file.state.name == "FAILED":
                raise ValueError("AI ไม่สามารถประมวลผลไฟล์นี้ได้")
                
            content_to_send.append(uploaded_file)

        # ==========================================
        # STEP 2: ดึงความจำลูกค้าและฐานข้อมูลบริษัท (RAG System)
        # ==========================================
        logger.info(f"🧠 [Prime Brain]: กำลังเชื่อมต่อความจำ (RAG) สำหรับ User: {user_id}")
        past_context = recall_memory(user_id, incoming_message)
        corp_knowledge = recall_corporate_knowledge(incoming_message)
        
        full_prompt = f"""
        [ความจำประวัติการสนทนากับลูกค้ารายนี้]:
        {past_context if past_context else "ไม่มีประวัติการคุยมาก่อน"}
        
        [ฐานข้อมูลความรู้/สูตรลับของบริษัท SIRINTHANATTH PRIME]:
        {corp_knowledge if corp_knowledge else "ไม่มีข้อมูลที่เกี่ยวข้องในฐานระบบ"}
        
        [คำสั่งล่าสุดจากลูกค้า]:
        {incoming_message}
        
        กรุณาวิเคราะห์ เปรียบเทียบข้อมูลฐานความรู้กับข้อมูลออนไลน์ (และประมวลผลไฟล์มัลติมีเดียที่แนบมา หากมี) และสร้างคำตอบที่ถูกต้องที่สุด
        """
        
        # นำ Text คำสั่งไปต่อท้ายไฟล์ (ถ้ามีไฟล์)
        content_to_send.append(full_prompt)

        # ==========================================
        # STEP 3: สั่งรันโมเดล (Gemini 1.5 Pro + Google Search)
        # ==========================================
        logger.info(f"🌐 [Prime Brain]: กำลังประมวลผลและสืบค้นข้อมูลออนไลน์ (Search Grounding)...")
        
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=content_to_send,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                # 🌐 เปิดใช้งานให้ AI วิ่งออกไปค้น Google ทันที (Search Grounding)
                tools=[{"google_search": {}}] 
            )
        )
        
        # บันทึกความจำลงสมองกล (RAG)
        save_memory(user_id, f"User: {incoming_message} | PRIME: {response.text[:200]}...")
        return response.text
        
    except Exception as e:
        logger.error(f"❌ [Prime Brain Critical Error]: {str(e)}")
        return "ขออภัยครับคุณลูกค้า ขณะนี้สมองกลส่วนกลางกำลังประมวลผลข้อมูลระดับสูง และเกิดข้อขัดข้องชั่วคราว กรุณารอสักครู่นะครับ"
        
    finally:
        # ==========================================
        # STEP 4: ทำลายไฟล์บนเซิร์ฟเวอร์ Google หลังใช้งานเสร็จ (Zero-Data Retention)
        # ==========================================
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
                logger.info(f"🗑️ [Prime Brain Security]: ทำลายไฟล์ออกจากเซิร์ฟเวอร์ AI เรียบร้อย (Data Protected)")
            except Exception as e:
                logger.error(f"⚠️ [Prime Brain Security Error]: ไม่สามารถลบไฟล์บนเซิร์ฟเวอร์ AI ได้ ({e})")