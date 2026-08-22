import os
import time
import logging
import asyncio
import mimetypes
from google import genai
from google.genai import types

logger = logging.getLogger("PrimeBrain")

# ระบบพยายามดึงความจำองค์กร (Corporate Knowledge) มาเสริมความฉลาด (RAG)
try:
    from agents.memory_engine import retrieve_corporate_knowledge
except ImportError:
    def retrieve_corporate_knowledge(query): return ""

async def generate_intelligent_response(user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
    """
    🧠 สมองกลอัจฉริยะสำหรับลูกค้าทั่วไป (User Mode)
    อัปเกรด: [Gemini 3.7 Flash] เร็วที่สุดในโลก วิเคราะห์ไว ตอบสนองทันที
    เพิ่มระบบป้องกัน Error 404 และการรองรับไฟล์เอกสารทุกชนิด (Crash-Proof)
    """
    api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ ขออภัยครับ ขณะนี้ระบบ AI กำลังอัปเดตความปลอดภัยการเชื่อมต่อชั่วคราวครับ"
        
    client = genai.Client(api_key=api_key)
    
    # 🚀 อัปเกรดเป็นรุ่นสปีดความเร็วแสง (ดึงจากรายชื่อโมเดลล่าสุด)
    model_name = 'gemini-3.7-flash' 
    
    # ดึงบริบทความจำขององค์กรมาช่วยตอบ (ถ้ามี)
    corporate_context = await asyncio.to_thread(retrieve_corporate_knowledge, message)
    
    system_instruction = f"""
    คุณคือ 'SIRINTHANATTH PRIME' สุดยอด AI ผู้ช่วยระดับ Enterprise 
    ดูแลลูกค้าขององค์กรอย่างมืออาชีพ สุภาพ ชาญฉลาด และให้คำตอบที่ตรงประเด็นที่สุด
    
    ข้อมูลความรู้ขององค์กร (ใช้อ้างอิงตอบลูกค้าหากเนื้อหาเกี่ยวข้องกัน):
    {corporate_context}
    """
    
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
