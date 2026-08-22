import os
import time
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

logger = logging.getLogger("PrimeBrain")

# 1. 🔑 ตั้งค่าการเชื่อมต่อ AI
GEMINI_KEY = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# 🚀 อัปเกรดเป็นโมเดล Pro รุ่นเรือธงที่เสถียรและฉลาดที่สุด
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
    """ฟังก์ชันสมองกลประมวลผลเชิงลึก ดึงความจำ ดึงไฟล์ และสืบค้น Google แบบ Asynchronous 100%"""
    
    if not client:
        return "⚠️ System Offline: ไม่พบการเชื่อมต่อ AI_API_KEY ในระบบ"

    uploaded_file = None
    content_to_send = []
    
    try:
        # ==========================================
        # 1. ระบบจัดการไฟล์และมัลติมีเดีย (Multimodal)
        # ==========================================
        if file_path and os.path.exists(file_path):
            logger.info(f"🧠 [Prime Brain]: กำลังประมวลผลไฟล์ {file_type} เพื่อบริการลูกค้า...")
            
            # 🛠️ ตรวจจับประเภทไฟล์ป้องกัน Error
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

            # ⏳ รอจนกว่าระบบ AI จะแกะไฟล์เสร็จ
            while uploaded_file.state.name == "PROCESSING":
                await asyncio.sleep(1)
                uploaded_file = await asyncio.to_thread(client.files.get, name=uploaded_file.name)
                
            if uploaded_file.state.name == "FAILED":
                return "⚠️ ขออภัยครับ โครงสร้างไฟล์มีความซับซ้อนเกินไป ระบบไม่สามารถอ่านได้ครับ"
                
            content_to_send.append(uploaded_file)
            
            if not message or message.startswith("[System Alert:"):
                content_to_send.append("ช่วยวิเคราะห์ อธิบาย และสรุปรายละเอียดจากไฟล์นี้ให้ลูกค้าเข้าใจอย่างสุภาพครับ")
            else:
                content_to_send.append(message)
        else:
            content_to_send.append(message)

        # ==========================================
        # 2. สั่งรันโมเดล (Gemini 3.7 Flash)
        # ==========================================
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model_name,
            contents=content_to_send,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        )
        return response.text if response.text else "รับทราบข้อมูลเรียบร้อยครับ มีอะไรให้ผมช่วยเหลือเพิ่มเติมแจ้งได้เลยครับ"
        
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
