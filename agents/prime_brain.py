import os
import google.generativeai as genai
from agents.memory_engine import recall_memory, save_memory, recall_corporate_knowledge

MODEL_NAME = "gemini-1.5-pro-latest"

# 🧠 อัปเดต SYSTEM PROMPT ให้มีคำสั่ง Cross-Reference (เทียบข้อมูล)
SYSTEM_PROMPT = """คุณคือ "SIRINTHANATTH PRIME" สุดยอด AI ผู้ช่วยผู้บริหารและที่ปรึกษาธุรกิจระดับโลก 

กฎเหล็กพิเศษในการประมวลผลข้อมูล (Cross-Reference Engine):
1. ระบบจะแนบ "ข้อมูลจากฐานความรู้ของบริษัท (Corporate DB)" มาให้คุณ
2. ให้คุณเชื่อมต่อข้อมูลออนไลน์ (Google Search) เพื่อดูเทรนด์หรืออัปเดตล่าสุด
3. ⚖️ การเทียบข้อมูล: 
   - หากเป็น "สูตรคำนวณ", "ราคา", "ตรรกะเฉพาะ" หรือ "นโยบาย" ให้ยึดถือข้อมูลจาก Corporate DB เป็นหลัก (ถือเป็นความจริงสูงสุด)
   - หากเป็น "ข่าวสาร", "สภาวะตลาด", "เทรนด์" ให้ยึดข้อมูลจากออนไลน์ที่สดใหม่ที่สุด
   - นำข้อมูลทั้ง 2 แหล่งมาประมวลผลร่วมกัน เลือกสิ่งที่ถูกต้อง มีคุณภาพ และแม่นยำที่สุดมาเป็นคำตอบ
4. 🎭 Predictive Empathy: ตอบด้วยความนุ่มนวล เป็นมืออาชีพ ไม่แข็งกระด้าง
5. 🛡️ Legal Shield: ป้องกันความเสี่ยงทางกฎหมาย (สคบ./อย.) อย่างเคร่งครัด
"""

def generate_intelligent_response(line_user_id: str, current_message: str, file_uri: str = None, file_type: str = None) -> str:
    try:
        # 1. ดึงความจำลูกค้า (RAG - User History)
        past_context = recall_memory(line_user_id, current_message)
        
        # 2. 🏢 ดึงความรู้และสูตรคำนวณจากไฟล์ที่ CEO อัปโหลดไว้ (RAG - Corporate Knowledge)
        corp_knowledge = recall_corporate_knowledge(current_message)
        
        full_prompt = f"""
        [ความจำประวัติการสนทนากับลูกค้ารายนี้]:
        {past_context}
        
        [ฐานข้อมูลความรู้/สูตรลับของบริษัท SIRINTHANATTH PRIME (อัปเดตโดย CEO)]:
        {corp_knowledge}
        
        [คำสั่งล่าสุดจากลูกค้า]:
        {current_message}
        
        กรุณาวิเคราะห์ เปรียบเทียบข้อมูลฐานความรู้กับข้อมูลออนไลน์ และสร้างคำตอบที่ถูกต้องที่สุด
        """

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("AI_API_KEY")
        genai.configure(api_key=api_key)
        
        # 🌟 ฟีเจอร์ลับ: เปิดใช้งาน Google Search Grounding อัตโนมัติ เพื่อดึงข้อมูล Real-time
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=SYSTEM_PROMPT,
            tools='google_search_retrieval' # สั่งให้ AI วิ่งออกไปเช็ก Google ทันที
        )
        
        content_to_send = [full_prompt]
        if file_uri and file_type:
            content_to_send[0] += f"\n\n[ลูกค้าแนบไฟล์: {file_type}]"

        print(f"🧠 [Prime Brain]: กำลัง Cross-Reference ข้อมูลภายในและออนไลน์ให้ User: {line_user_id}")
        response = model.generate_content(content_to_send)
        
        save_memory(line_user_id, f"User: {current_message} | PRIME: {response.text[:200]}")
        return response.text
        
    except Exception as e:
        print(f"❌ [Prime Brain Critical Error]: {str(e)}")
        return "ขออภัยครับคุณลูกค้า ขณะนี้สมองกลส่วนกลางกำลังตรวจสอบและเทียบฐานข้อมูลระดับสูง กรุณารอสักครู่นะครับ"