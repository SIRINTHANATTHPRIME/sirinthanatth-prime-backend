import os
import requests
import logging
from bs4 import BeautifulSoup
from google import genai
from supabase import create_client, Client

# ตั้งค่า Logger
logger = logging.getLogger("MemoryEngine")

# ==========================================
# 🌐 1. ศูนย์บัญชาการ AI และฐานข้อมูล
# ==========================================
# ดึงการเชื่อมต่อ AI จากส่วนกลาง (รองรับ Zero Downtime Fallback)
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EMBEDDING_MODEL = "gemini-embedding-2-preview" # Fallback ไปใช้สมองกลความจำล่าสุด
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            return genai.Client(api_key=api_key) if api_key else None

client = PrimeAIConfig.get_client()
EMBEDDING_MODEL_NAME = PrimeAIConfig.EMBEDDING_MODEL

# เชื่อมต่อ Supabase (Vector Database)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# ==========================================
# 🧠 2. แกนประมวลผลความจำ (Vector Embedding Engine)
# ==========================================
def get_text_embedding(text: str) -> list:
    """
    แปลงข้อความเป็นตัวเลข (Vector) ผ่านโมเดล Embedding ล่าสุดของ Google
    อัปเกรด: ใช้ gemini-embedding-2-preview เพื่อความแม่นยำสูงระดับ Enterprise
    """
    if not client or not text:
        logger.warning("⚠️ ไม่พบ API Key หรือข้อความว่างเปล่า ข้ามการสร้าง Embedding")
        return []
        
    try:
        # ใช้โมเดล Embedding มาตรฐานเจเนอเรชันที่ 3
        result = client.models.embed_content(
            model=EMBEDDING_MODEL_NAME,
            contents=text,
        )
        
        # ตรวจสอบโครงสร้างข้อมูลที่ส่งกลับมาจาก SDK ใหม่
        if hasattr(result, 'embeddings') and result.embeddings:
            return result.embeddings[0].values
        else:
            logger.error("❌ [Embedding Error]: ไม่ได้รับข้อมูล Vector จาก Google API")
            return []
    except Exception as e:
        logger.error(f"❌ [Embedding System Error]: {e}")
        return []

# ==========================================
# 🌐 3. ระบบสกัดความรู้จากเว็บไซต์ (Live Web Scraper Advanced)
# ==========================================
def extract_text_from_url(url: str) -> str:
    """ดึงข้อมูลเนื้อหาจาก URL ที่ส่งมา พร้อมระบบป้องกัน Anti-Bot ขั้นสูง"""
    try:
        # อัปเกรด Headers สวมรอยเป็นเบราว์เซอร์ยุคใหม่ล่าสุด
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.google.com/'
        }
        # จำกัดเวลา 15 วินาทีเพื่อป้องกันระบบค้าง
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser', from_encoding=response.encoding)
        
        # คลีนข้อมูลขยะ (Script, Style, เมนู, โฆษณา, ฟุตเตอร์)
        for element in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "iframe"]):
            element.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        
        # คัดกรองเว้นวรรคส่วนเกินและปรับให้เป็นเนื้อหาบริสุทธิ์
        text = ' '.join(text.split())
        
        # ตัดข้อมูลให้พอดีกับข้อจำกัดของ Vector DB (รักษาแก่นสำคัญไว้)
        return text[:9000] 
        
    except requests.exceptions.RequestException as re_err:
        logger.error(f"❌ [URL Scrape Network Error]: {re_err}")
        return ""
    except Exception as e:
        logger.error(f"❌ [URL Scrape General Error]: {e}")
        return ""

def process_and_save_link_knowledge(url: str, added_by: str = "CEO"):
    """ดึงข้อมูลจากลิงก์และบันทึกลงสมองกลองค์กร (Corporate DB)"""
    logger.info(f"🌐 [System]: กำลังดึงความรู้จากลิงก์ {url}")
    extracted_text = extract_text_from_url(url)
    
    if not extracted_text:
        return False, "ไม่สามารถดึงข้อมูลจากลิงก์นี้ได้ อาจถูกบล็อกหรือมีระบบป้องกันจากเว็บไซต์ปลายทาง"
        
    title = f"Knowledge_From_URL_{url.split('//')[-1][:30]}"
    
    # บันทึกลงฐานข้อมูลความรู้บริษัท
    success = save_corporate_knowledge(title, f"อ้างอิงจาก URL: {url}\n\n{extracted_text}")
    if success:
        return True, "ดึงข้อมูลจากลิงก์และนำเข้าสู่ระบบสมองกล (Vector Database) สำเร็จ"
    else:
        return False, "ดึงข้อมูลได้สำเร็จ แต่เกิดข้อผิดพลาดในการนำเข้าสู่ระบบฐานข้อมูลเวกเตอร์"

# ==========================================
# 🏢 4. จัดการฐานข้อมูลความรู้บริษัท (Corporate Knowledge Base - RAG)
# ==========================================
def save_corporate_knowledge(title: str, content: str) -> bool:
    """ป้อนไฟล์/ความรู้ใหม่เข้าสู่สมองกลส่วนกลาง (Vector DB)"""
    if not supabase: 
        logger.warning("⚠️ ข้ามการบันทึกความรู้บริษัท (ไม่พบการเชื่อมต่อ Supabase)")
        return False
        
    try:
        vector_data = get_text_embedding(content)
        if not vector_data: 
            return False
            
        supabase.table('corporate_knowledge').insert({
            "title": title, 
            "content": content, 
            "embedding": vector_data
        }).execute()
        
        logger.info(f"💾 [Corporate DB]: บันทึกความรู้ '{title}' สำเร็จ")
        return True
    except Exception as e:
        logger.error(f"❌ [Corporate DB Save Error]: {e}")
        return False

def recall_corporate_knowledge(query: str) -> str:
    """ดึงความรู้เฉพาะของบริษัท (รวมถึงที่ได้จากลิงก์) มาใช้ประมวลผล (Semantic Search)"""
    if not supabase: return ""
    
    try:
        query_vector = get_text_embedding(query)
        if not query_vector: return ""

        # รัน RPC Function ที่ฝังไว้ใน Supabase (ค้นหาข้อมูลที่ใกล้เคียงที่สุด)
        response = supabase.rpc('match_corporate_knowledge', { 
            'query_embedding': query_vector, 
            'match_threshold': 0.70, # ความแม่นยำ 70% ขึ้นไป
            'match_count': 3 # ดึงมา 3 บริบทที่เกี่ยวข้องกันที่สุด
        }).execute()
        
        if not response.data: 
            return "ไม่พบข้อมูลในฐานความจำบริษัท"
            
        # ประกอบร่างข้อมูลที่หาเจอ
        return "\n\n".join([f"📌 {item.get('title', 'ข้อมูลอ้างอิง')}\n{item.get('content', '')}" for item in response.data])
    except Exception as e:
        logger.error(f"❌ [Recall Corporate DB Error]: {e}")
        return ""

# ==========================================
# 🧠 5. ระบบจัดเก็บและดึงประวัติการคุยลูกค้า (Chat Memory RAG)
# ==========================================
def save_memory(line_user_id: str, chat_summary: str):
    """บันทึกบริบทการคุยรายบุคคลแบบฝังเวกเตอร์ (Vectorized Personal Memory)"""
    if not supabase: return
    
    vector_data = get_text_embedding(chat_summary)
    if vector_data:
        try:
            supabase.table('chat_memories').insert({
                "line_user_id": line_user_id, 
                "chat_summary": chat_summary, 
                "embedding": vector_data
            }).execute()
        except Exception as e:
            logger.error(f"❌ [Save Memory Error]: {e}")

def recall_memory(line_user_id: str, current_message: str) -> str:
    """รื้อฟื้นความจำก่อนหน้าของลูกค้าคนนั้นๆ ออกมาช่วยตอบคำถามอย่างเป็นธรรมชาติ"""
    if not supabase: return ""
    
    try:
        query_vector = get_text_embedding(current_message)
        if not query_vector: return ""
        
        # ค้นหาประวัติการคุยเฉพาะของ User คนนั้น ที่ตรงกับบริบทคำถามปัจจุบัน
        response = supabase.rpc('match_memories', {
            'query_embedding': query_vector, 
            'match_threshold': 0.65, # ลด Threshold เล็กน้อยเพื่อให้ดึงประวัติได้ง่ายขึ้น
            'match_count': 3, 
            'p_line_user_id': line_user_id
        }).execute()
        
        if not response.data: return ""
        return "\n".join([item.get('chat_summary', '') for item in response.data])
    except Exception as e:
        logger.error(f"❌ [Recall Memory Error]: {e}")
        return ""