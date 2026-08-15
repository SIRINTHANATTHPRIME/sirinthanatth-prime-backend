import os
import time
import google.generativeai as genai
from agents.memory_engine import recall_memory, save_memory, recall_corporate_knowledge

MODEL_NAME = "gemini-1.5-pro-latest"

# 🧠 อัปเดต SYSTEM PROMPT ให้มีคำสั่ง Cross-Reference และการวิเคราะห์มัลติมีเดีย (หูตาอัจฉริยะ)
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

# เปลี่ยนพารามิเตอร์ให้รับ file_path แทน file_uri เพื่อให้ตรงกับ routes_line.py
def generate_intelligent_response(line_user_id: str, current_message: str, file_path: str = None, file_type: str = None) -> str:
    uploaded_file = None
    try:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("AI_API_KEY")
        genai.configure(api_key=api_key)

        # ==========================================
        # 1. จัดการอัปโหลดไฟล์ไปให้สมองกล Gemini (ถ้าลูกค้าส่งมา)
        # ==========================================
        content_to_send = []
        if file_path and os.path.exists(file_path):
            print(f"⬆️ [Prime Brain]: กำลังอัปโหลดไฟล์ประเภท [{file_type}] ขึ้นเซิร์ฟเวอร์ AI...")
            
            # อัปโหลดไฟล์เข้าสู่สมอง Gemini (รองรับ ภาพ, เสียง, วิดีโอ, PDF)
            uploaded_file = genai.upload_file(path=file_path)
            
            # ถ้าเป็นวิดีโอ ต้องรอให้ Gemini ประมวลผลเฟรมต่อเฟรมให้เสร็จก่อน (อาจใช้เวลา 2-10 วินาที)
            if file_type == 'video':
                print(f"⏳ [Prime Brain]: ระบบกำลังดูและประมวลผลวิดีโอ กรุณารอสักครู่...")
                while uploaded_file.state.name == 'PROCESSING':
                    time.sleep(2)
                    uploaded_file = genai.get_file(uploaded_file.name)
                if uploaded_file.state.name == 'FAILED':
                    raise ValueError("วิดีโอไม่สามารถประมวลผลได้ รูปแบบไฟล์อาจไม่รองรับ")

            # นำไฟล์ไปใส่เป็นข้อมูลก้อนแรก (ตาม Best Practice ของโมเดล Multimodal)
            content_to_send.append(uploaded_file)
            print(f"✅ [Prime Brain]: ส่งไฟล์ให้สมองกลรับรู้เรียบร้อยแล้ว")

        # ==========================================
        # 2. ดึงความจำลูกค้าและฐานข้อมูลบริษัท (RAG System)
        # ==========================================
        past_context = recall_memory(line_user_id, current_message)
        corp_knowledge = recall_corporate_knowledge(current_message)
        
        full_prompt = f"""
        [ความจำประวัติการสนทนากับลูกค้ารายนี้]:
        {past_context}
        
        [ฐานข้อมูลความรู้/สูตรลับของบริษัท SIRINTHANATTH PRIME (อัปเดตโดย CEO)]:
        {corp_knowledge}
        
        [คำสั่งล่าสุดจากลูกค้า]:
        {current_message}
        
        กรุณาวิเคราะห์ เปรียบเทียบข้อมูลฐานความรู้กับข้อมูลออนไลน์ (และประมวลผลไฟล์มัลติมีเดียที่แนบมา หากมี) และสร้างคำตอบที่ถูกต้องที่สุด
        """
        
        # แนบคำสั่ง Text ต่อท้ายไฟล์
        content_to_send.append(full_prompt)

        # ==========================================
        # 3. สั่งรันโมเดล (Gemini 1.5 Pro + Google Search + File API)
        # ==========================================
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=SYSTEM_PROMPT,
            tools='google_search_retrieval' # สั่งให้ AI วิ่งออกไปเช็ก Google ทันที
        )
        
        print(f"🧠 [Prime Brain]: กำลังประมวลผล (Cross-Reference + Multimodal) ให้ User: {line_user_id}")
        response = model.generate_content(content_to_send)
        
        # บันทึกความจำ
        save_memory(line_user_id, f"User: {current_message} | PRIME: {response.text[:200]}")
        return response.text
        
    except Exception as e:
        print(f"❌ [Prime Brain Critical Error]: เกิดข้อผิดพลาดในสมองกล ({str(e)})")
        return "ขออภัยครับคุณลูกค้า ขณะนี้สมองกลส่วนกลางกำลังประมวลผลไฟล์มัลติมีเดียระดับสูง และเกิดข้อขัดข้องชั่วคราว กรุณารอสักครู่นะครับ"
    finally:
        # ==========================================
        # 4. ทำลายไฟล์บนเซิร์ฟเวอร์ Google หลังใช้งานเสร็จ (Zero-Data Retention)
        # ==========================================
        if uploaded_file:
            try:
                genai.delete_file(uploaded_file.name)
                print(f"🗑️ [Prime Brain Security]: ทำลายไฟล์ออกจากเซิร์ฟเวอร์ AI เรียบร้อย (Data Protected)")
            except Exception as e:
                print(f"⚠️ [Prime Brain Error]: ไม่สามารถลบไฟล์บนเซิร์ฟเวอร์ AI ได้ ({e})")