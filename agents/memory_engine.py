import os
import google.generativeai as genai
from supabase import create_client, Client

# ตั้งค่า Supabase และ Gemini
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_text_embedding(text: str) -> list:
    """แปลงข้อความเป็น Vector ผ่าน Gemini"""
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document"
    )
    return result['embedding']

def save_memory(line_user_id: str, chat_summary: str):
    """บันทึกความจำใหม่ลง Supabase"""
    # ตรวจสอบและสร้างโปรไฟล์ลูกค้าถ้ายังไม่มี
    supabase.table('customer_profiles').upsert({"line_user_id": line_user_id}).execute()
    
    # แปลงข้อความเป็น Vector
    vector_data = get_text_embedding(chat_summary)
    
    # บันทึกลงตาราง
    supabase.table('chat_memories').insert({
        "line_user_id": line_user_id,
        "chat_summary": chat_summary,
        "embedding": vector_data
    }).execute()

def recall_memory(line_user_id: str, current_message: str) -> str:
    """ดึงความจำในอดีตที่เกี่ยวข้องกับข้อความปัจจุบัน"""
    query_vector = get_text_embedding(current_message)
    
    # ค้นหาผ่าน SQL Function ที่เราสร้างไว้ใน Supabase
    response = supabase.rpc(
        'match_memories', 
        {
            'query_embedding': query_vector,
            'match_threshold': 0.7, # ความแม่นยำ 70% ขึ้นไป
            'match_count': 3, # ดึงมา 3 เรื่องที่ใกล้เคียงสุด
            'p_line_user_id': line_user_id
        }
    ).execute()
    
    memories = response.data
    if not memories:
        return "ไม่มีข้อมูลในอดีตที่เกี่ยวข้อง"
    
    # นำความจำมาต่อกันเพื่อส่งให้สมองหลัก
    recalled_text = "ข้อมูลในอดีตของลูกค้าคนนี้:\n"
    for m in memories:
        recalled_text += f"- {m['chat_summary']}\n"
    return recalled_text