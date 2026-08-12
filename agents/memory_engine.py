import os
import google.generativeai as genai
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def get_text_embedding(text: str) -> list:
    """แปลงข้อความเป็น Vector ผ่าน Gemini"""
    result = genai.embed_content(
        model="models/text-embedding-004",
        content=text,
        task_type="retrieval_document"
    )
    return result['embedding']

# ==========================================
# 🧠 ฟังก์ชันเดิม: จัดการความจำลูกค้า
# ==========================================
def save_memory(line_user_id: str, chat_summary: str):
    if not supabase: return
    vector_data = get_text_embedding(chat_summary)
    supabase.table('chat_memories').insert({
        "line_user_id": line_user_id, "chat_summary": chat_summary, "embedding": vector_data
    }).execute()

def recall_memory(line_user_id: str, current_message: str) -> str:
    if not supabase: return ""
    query_vector = get_text_embedding(current_message)
    response = supabase.rpc('match_memories', {
        'query_embedding': query_vector, 'match_threshold': 0.7, 'match_count': 3, 'p_line_user_id': line_user_id
    }).execute()
    if not response.data: return ""
    return "\n".join([item['chat_summary'] for item in response.data])

# ==========================================
# 🏢 ฟังก์ชันใหม่: จัดการฐานข้อมูลความรู้บริษัท (Corporate Knowledge Base)
# ==========================================
def save_corporate_knowledge(title: str, content: str):
    """(สำหรับ CEO) ป้อนไฟล์/ความรู้ใหม่เข้าสู่สมองกลส่วนกลาง"""
    if not supabase: return False
    try:
        vector_data = get_text_embedding(content)
        supabase.table('corporate_knowledge').insert({
            "title": title, "content": content, "embedding": vector_data
        }).execute()
        return True
    except Exception as e:
        print(f"❌ [Knowledge Ingestion Error]: {e}")
        return False

def recall_corporate_knowledge(query: str) -> str:
    """ดึงความรู้เฉพาะของบริษัทที่ CEO ป้อนไว้ มาใช้ประมวลผล"""
    if not supabase: return ""
    try:
        query_vector = get_text_embedding(query)
        response = supabase.rpc('match_corporate_knowledge', { # ต้องสร้าง Function นี้ใน Supabase SQL
            'query_embedding': query_vector, 'match_threshold': 0.75, 'match_count': 2
        }).execute()
        
        if not response.data: return "ไม่พบสูตรหรือนโยบายบริษัทที่เกี่ยวข้อง"
        return "\n\n".join([f"📌 อ้างอิงจากไฟล์: {item['title']}\n{item['content']}" for item in response.data])
    except Exception:
        return ""