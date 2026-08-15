import os
import re
import requests
from bs4 import BeautifulSoup
from google import genai
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL else None

GEMINI_KEY = os.environ.get("AI_API_KEY") or os.environ.get("GEMINI_API_KEY") or ""
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

def get_text_embedding(text: str) -> list:
    """แปลงข้อความเป็น Vector ผ่าน Gemini Embedding 2 (ล่าสุด)"""
    if not client: return []
    try:
        result = client.models.embed_content(
            model="gemini-embedding-2",
            contents=text,
        )
        return result.embeddings[0].values
    except Exception as e:
        print(f"❌ [Embedding Error]: {e}")
        return []

# ==========================================
# 🌐 1. ระบบดึงความรู้จากลิงก์ออนไลน์ (Live Web Scraper)
# ==========================================
def extract_text_from_url(url: str) -> str:
    """ดึงข้อมูลเนื้อหาจาก URL ที่ส่งมา"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        # ลบ Script และ Style ออกเพื่อเอาแต่เนื้อหา
        for script in soup(["script", "style"]):
            script.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        # สรุปย่อเนื้อหาหากยาวเกินไป
        return text[:5000] # จำกัดเบื้องต้นเพื่อไม่ให้โทเค็นล้น
    except Exception as e:
        print(f"❌ [URL Scrape Error]: {e}")
        return ""

def process_and_save_link_knowledge(url: str, added_by: str = "CEO"):
    """ดึงข้อมูลจากลิงก์และบันทึกลงสมองกล (Corporate DB)"""
    print(f"🌐 [System]: กำลังดึงความรู้จากลิงก์ {url}")
    extracted_text = extract_text_from_url(url)
    
    if not extracted_text:
        return False, "ไม่สามารถดึงข้อมูลจากลิงก์นี้ได้"
        
    title = f"Knowledge_From_URL_{url.split('//')[-1][:30]}"
    
    # บันทึกลงฐานข้อมูลความรู้บริษัท
    success = save_corporate_knowledge(title, f"อ้างอิงจาก URL: {url}\n\n{extracted_text}")
    return success, "ดึงข้อมูลจากลิงก์และเรียนรู้สำเร็จ"

# ==========================================
# 🏢 2. จัดการฐานข้อมูลความรู้บริษัท (Corporate Knowledge Base)
# ==========================================
def save_corporate_knowledge(title: str, content: str):
    """ป้อนไฟล์/ความรู้ใหม่เข้าสู่สมองกลส่วนกลาง"""
    if not supabase: return False
    try:
        vector_data = get_text_embedding(content)
        if not vector_data: return False
        
        supabase.table('corporate_knowledge').insert({
            "title": title, "content": content, "embedding": vector_data
        }).execute()
        return True
    except Exception as e:
        print(f"❌ [DB Error]: {e}")
        return False

def recall_corporate_knowledge(query: str) -> str:
    """ดึงความรู้เฉพาะของบริษัท (รวมถึงที่ได้จากลิงก์) มาใช้ประมวลผล"""
    if not supabase: return ""
    try:
        query_vector = get_text_embedding(query)
        if not query_vector: return ""

        response = supabase.rpc('match_corporate_knowledge', { 
            'query_embedding': query_vector, 'match_threshold': 0.70, 'match_count': 3
        }).execute()
        
        if not response.data: return "ไม่พบข้อมูลในฐานความจำบริษัท"
        return "\n\n".join([f"📌 {item['title']}\n{item['content']}" for item in response.data])
    except Exception as e:
        print(f"❌ [Recall DB Error]: {e}")
        return ""

# ==========================================
# 🧠 3. ฟังก์ชันจัดเก็บและเรียกคืนความจำลูกค้าทั่วไป (RAG - Chat History)
# ==========================================
def save_memory(line_user_id: str, chat_summary: str):
    if not supabase: return
    vector_data = get_text_embedding(chat_summary)
    if vector_data:
        supabase.table('chat_memories').insert({
            "line_user_id": line_user_id, "chat_summary": chat_summary, "embedding": vector_data
        }).execute()

def recall_memory(line_user_id: str, current_message: str) -> str:
    if not supabase: return ""
    try:
        query_vector = get_text_embedding(current_message)
        response = supabase.rpc('match_memories', {
            'query_embedding': query_vector, 'match_threshold': 0.7, 'match_count': 3, 'p_line_user_id': line_user_id
        }).execute()
        if not response.data: return ""
        return "\n".join([item['chat_summary'] for item in response.data])
    except Exception:
        return ""