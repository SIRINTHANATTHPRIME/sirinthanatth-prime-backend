import os
import google.generativeai as genai
from agents.memory_engine import recall_memory, save_memory

# ใช้โมเดลล่าสุดที่รองรับทั้งความเร็วและความฉลาด
MODEL_NAME = "gemini-1.5-pro-latest"

SYSTEM_PROMPT = """คุณคือ "SIRINTHANATTH PRIME" AI อัจฉริยะระดับโลกสำหรับดูแลลูกค้า VVIP 
ทำหน้าที่เป็นทั้งผู้เชี่ยวชาญด้านอสังหาริมทรัพย์เชิงพาณิชย์ และที่ปรึกษาการเงิน/ประกันชีวิต (Unit Linked)

กฎข้อบังคับในการตอบสนอง (Proactive Risk Shield & Tone):
1. การวิเคราะห์อารมณ์: สังเกตบริบทและน้ำเสียงของลูกค้าจากข้อความ หากลูกค้ามีความกังวล ให้ตอบด้วยความนุ่มนวล เข้าอกเข้าใจ หากลูกค้าเร่งรีบ ให้ตอบกระชับ ตรงประเด็น
2. ฉลาดพูดบนความจริง: ข้อมูลเรื่องราคาที่ดิน ข้อกฎหมาย หรือผลตอบแทนการลงทุน ต้องอิงหลักความจริง "ห้ามคาดเดาหรือรับปากเกินจริงเด็ดขาด"
3. เกราะป้องกันความเสี่ยง: หากลูกค้าสอบถามเกี่ยวกับการทำสัญญา หรือการลงทุนที่มีความเสี่ยงสูง ให้คุณแจ้งเตือนอย่างสุภาพเสมอ เช่น "ขออนุญาตแจ้งข้อควรระวังในจุดนี้..."
4. คาดการณ์อนาคต: ใช้ข้อมูลความจำในอดีตที่แนบไปให้ เพื่อแนะนำทางเลือกที่ดีที่สุดให้กับลูกค้าล่วงหน้า
"""

def generate_intelligent_response(line_user_id: str, current_message: str) -> str:
    # 1. ดึงความจำในอดีตของลูกค้า
    past_context = recall_memory(line_user_id, current_message)
    
    # 2. เตรียม Prompt รวมความจำและบริบทปัจจุบัน
    full_prompt = f"""
    {past_context}
    
    ข้อความล่าสุดจากลูกค้า: {current_message}
    
    กรุณาวิเคราะห์อารมณ์ คาดการณ์ความต้องการ และตอบสนองตามกฎของ SIRINTHANATTH PRIME
    """
    
    # 3. ส่งประมวลผลผ่าน Gemini
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT
    )
    
    response = model.generate_content(full_prompt)
    bot_reply = response.text
    
    # 4. บันทึกบทสนทนานี้เป็นความจำระยะยาวแบบย่อ (Summary)
    # หมายเหตุ: ในระบบจริงอาจจะรันเป็น Background Task เพื่อไม่ให้ลูกค้าต้องรอโหลดนาน
    chat_summary = f"ลูกค้าถาม: {current_message} | AI ตอบ: {bot_reply[:100]}..."
    save_memory(line_user_id, chat_summary)
    
    return bot_reply