import os
import time
from google import genai
from agents.memory_engine import recall_memory, save_memory, recall_corporate_knowledge

GEMINI_KEY = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None
MODEL_NAME = "gemini-3.1-pro-preview"

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
def generate_intelligent_response(user_id, incoming_message, file_path=None, file_type=None):
    """ฟังก์ชันสมองกลประมวลผลเชิงลึก (Deep Reasoning)"""
    if not client:
        return "⚠️ System Offline: ไม่พบการเชื่อมต่อ AI_API_KEY ในระบบ"

    # 🧠 ใช้ Pro Model รุ่นเรือธง สำหรับงานที่ซับซ้อนที่สุด
    model_name = 'gemini-3.1-pro-preview'
    
    contents = [
        f"วิเคราะห์ข้อมูลและวางแผนกลยุทธ์เชิงลึกสำหรับลูกค้า ID [{user_id}]:",
        incoming_message
    ]
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents
        )
        return response.text
    except Exception as e:
        return f"⚠️ [Prime Brain Error]: ไม่สามารถประมวลผลข้อมูลระดับสูงได้เนื่องจาก {e}"

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