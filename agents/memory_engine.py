import os
import re
import time
import requests
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from google import genai
from supabase import create_client, Client

# ตั้งค่า Logger สำหรับตรวจสอบการทำงานของความจำ
logger = logging.getLogger("MemoryEngine")

# ==========================================
# 🌐 1. ศูนย์บัญชาการ AI และฐานข้อมูล
# ==========================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EMBEDDING_MODEL = "text-embedding-004" 
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

# ดึงการเชื่อมต่อ AI จากส่วนกลางอย่างปลอดภัย (Singleton)
client = PrimeAIConfig.get_client()
EMBEDDING_MODEL_NAME = getattr(PrimeAIConfig, "EMBEDDING_MODEL", "text-embedding-004")

# เชื่อมต่อ Supabase (Vector Database)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# ==========================================
# ⚙️ 2. ระบบหั่นข้อความอัจฉริยะ (Context-Aware Sliding Window Chunking)
# ==========================================
def chunk_text(text: str, max_chars: int = 7000, overlap_paras: int = 1) -> list:
    """
    หั่นข้อความโดยใช้เทคนิค 'หน้าต่างเหลื่อมซ้อน' (Sliding Window)
    นำย่อหน้าสุดท้ายของส่วนก่อนหน้า มาเชื่อมต่อกับส่วนถัดไป ป้องกันบริบทขาดหาย 100%
    """
    if len(text) <= max_chars:
        return [text]
        
    # แยกประโยค/ย่อหน้า พร้อมล้างช่องว่างขยะ
    paragraphs = [p.strip() + "." for p in re.split(r'\n\n|\.\s+', text) if p.strip()]
    
    chunks = []
    current_chunk = []
    current_len = 0
    
    for para in paragraphs:
        # ถ้ายาวเกิน Max Chars ให้แพ็ก Chunk เดิม แล้วเริ่ม Chunk ใหม่
        if current_len + len(para) > max_chars and current_chunk:
            chunks.append(" ".join(current_chunk))
            
            # 🧠 ดึงย่อหน้าท้ายสุดมาทำ Overlap (เชื่อมรอยต่อความจำ)
            overlap_content = current_chunk[-overlap_paras:] if overlap_paras > 0 else []
            current_chunk = overlap_content + [para]
            current_len = sum(len(p) for p in current_chunk) + len(current_chunk)
        else:
            current_chunk.append(para)
            current_len += len(para) + 1
            
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

# ==========================================
# 🧠 3. แกนประมวลผลความจำ (Vector Embedding Engine)
# ==========================================
def get_text_embedding(text: str, retries: int = 3) -> list:
    """แปลงข้อความเป็นตัวเลข (Vector) พร้อมระบบป้องกัน API Rate Limit"""
    if not client or not text:
        logger.warning("⚠️ ไม่พบ API Key หรือข้อความว่างเปล่า ข้ามการสร้าง Embedding")
        return []
        
    for attempt in range(retries):
        try:
            result = client.models.embed_content(
                model=EMBEDDING_MODEL_NAME,
                contents=text,
            )
            if hasattr(result, 'embeddings') and result.embeddings:
                return result.embeddings[0].values
            else:
                logger.error("❌ [Embedding Error]: API ไม่ตอบสนองโครงสร้าง Vector ที่ถูกต้อง")
                return []
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                wait_time = (attempt + 1) * 2
                logger.warning(f"⏳ [Rate Limit Hit]: รอ {wait_time} วินาทีแล้วลองสร้าง Vector ใหม่...")
                time.sleep(wait_time)
            else:
                logger.error(f"❌ [Embedding System Error]: {e}")
                return []
    return []

# ==========================================
# 🌐 4. ระบบสกัดความรู้จากเว็บไซต์ (Enterprise Web Scraper)
# ==========================================
def extract_text_from_url(url: str) -> str:
    """ดึงข้อมูลเนื้อหาพร้อมระบบ Connection Pooling และ Binary Shield"""
    try:
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1.5, status_forcelist=[ 500, 502, 503, 504 ])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'th-TH,th;q=0.9,en-US;q=0.8',
            'Referer': 'https://www.google.com/'
        }
        
        # ใช้ stream=True เพื่อเช็ก Header ก่อนดาวน์โหลดไฟล์ขนาดใหญ่
        response = session.get(url, headers=headers, timeout=15, stream=True)
        response.raise_for_status()
        
        # 🛡️ Binary Shield: ถ้าไม่ใช่หน้าเว็บหรือ Text ให้ออกทันที ป้องกันเซิร์ฟเวอร์ค้าง
        content_type = response.headers.get('Content-Type', '').lower()
        if 'text/html' not in content_type and 'text/plain' not in content_type:
            logger.warning(f"⚠️ [Scraper Shield]: ข้าม URL นี้เนื่องจากไม่ใช่เอกสาร (Content-Type: {content_type})")
            return ""
            
        soup = BeautifulSoup(response.content, 'html.parser', from_encoding=response.encoding)
        
        # คลีนโค้ดขยะขั้นสูง (ลบ Header, Footer, เมนูนำทาง, โฆษณา)
        for element in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "iframe", "svg", "button", "form"]):
            element.extract()
            
        text = soup.get_text(separator=' ', strip=True)
        text = ' '.join(text.split())
        
        return text 
        
    except requests.exceptions.RequestException as re_err:
        logger.error(f"❌ [URL Scrape Network Error]: {re_err}")
        return ""
    except Exception as e:
        logger.error(f"❌ [URL Scrape General Error]: {e}")
        return ""

def process_and_save_link_knowledge(url: str, added_by: str = "CEO") -> tuple:
    """ดูดข้อมูลเว็บและหั่นบริบทฝังลงฐานข้อมูลอัจฉริยะ (RAG Pipeline)"""
    logger.info(f"🌐 [System]: กำลังสกัดความรู้เชิงลึกจาก {url}")
    extracted_text = extract_text_from_url(url)
    
    if not extracted_text:
        return False, "ระบบไฟร์วอลล์บล็อกการดึงข้อมูล หรือลิงก์ที่ส่งมาไม่ใช่หน้าเว็บไซต์ที่รองรับ"
        
    chunks = chunk_text(extracted_text)
    base_title = f"Knowledge_URL_{url.split('//')[-1][:30]}"
    
    success_count = 0
    for i, chunk in enumerate(chunks):
        title = f"{base_title}_Part{i+1}"
        # ฝัง Timestamp เข้าไปเพื่อให้ AI รู้ว่าข้อมูลอัปเดตเมื่อไหร่
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        content = f"[Metadata -> Source: {url} | Scraped: {current_time} | Part: {i+1}/{len(chunks)}]\n\n{chunk}"
        
        if save_corporate_knowledge(title, content):
            success_count += 1
            
    if success_count > 0:
        return True, f"นำเข้าข้อมูลและหั่นแบ่งเป็น {len(chunks)} โหนด เข้าสู่สมองกล (Corporate DB) สำเร็จ"
    return False, "ดึงข้อมูลสำเร็จ แต่ไม่สามารถเชื่อมต่อ Supabase เพื่อบันทึก Vector ได้"

# ==========================================
# 🏢 5. จัดการฐานข้อมูลความรู้บริษัท (Corporate Knowledge Base - RAG)
# ==========================================
def save_corporate_knowledge(title: str, content: str) -> bool:
    """ป้อนข้อมูลเข้าสมองกลส่วนกลาง (Vector DB)"""
    if not supabase: return False
        
    try:
        vector_data = get_text_embedding(content)
        if not vector_data: return False
            
        supabase.table('corporate_knowledge').insert({
            "title": title, 
            "content": content, 
            "embedding": vector_data
        }).execute()
        
        logger.info(f"💾 [Corporate DB]: บันทึก Node '{title}' สำเร็จ")
        return True
    except Exception as e:
        logger.error(f"❌ [Corporate DB Save Error]: {e}")
        return False

def recall_corporate_knowledge(query: str) -> str:
    """ดึงความรู้แบบ Graph RAG อัจฉริยะ (Semantic Search)"""
    if not supabase: return ""
    
    try:
        query_vector = get_text_embedding(query)
        if not query_vector: return ""

        response = supabase.rpc('match_corporate_knowledge', { 
            'query_embedding': query_vector, 
            'match_threshold': 0.70, # ปรับจูนให้อ่อนลงเล็กน้อยเพื่อให้ครอบคลุมบริบทกว้างขึ้น
            'match_count': 5 
        }).execute()
        
        if not response.data: return "ไม่พบข้อมูลอ้างอิงในฐานความจำบริษัท"
            
        return "\n\n".join([f"📌 [Corporate Knowledge Node: {item.get('title', 'Unknown')}]\n{item.get('content', '')}" for item in response.data])
    except Exception as e:
        logger.error(f"❌ [Recall Corporate DB Error]: {e}")
        return ""

# ==========================================
# 🧠 6. ระบบจัดเก็บและดึงประวัติการคุยลูกค้า (Chat Memory RAG)
# ==========================================
def save_memory(line_user_id: str, chat_summary: str):
    """บันทึกพฤติกรรมลูกค้าลง Vector DB พร้อม Timestamp"""
    if not supabase: return
    
    # ห้อย Timestamp ไว้เพื่อให้ AI วิเคราะห์ Time-Series ได้
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    enriched_summary = f"[{current_time}] {chat_summary}"
    
    vector_data = get_text_embedding(enriched_summary)
    if vector_data:
        try:
            supabase.table('chat_memories').insert({
                "line_user_id": line_user_id, 
                "chat_summary": enriched_summary, 
                "embedding": vector_data
            }).execute()
        except Exception as e:
            logger.error(f"❌ [Save Memory Error]: {e}")

def recall_memory(line_user_id: str, current_message: str) -> str:
    """ค้นหาความจำลูกค้าที่ตรงกับบริบท (Context-Aware Recall)"""
    if not supabase: return ""
    
    try:
        query_vector = get_text_embedding(current_message)
        if not query_vector: return ""
        
        response = supabase.rpc('match_memories', {
            'query_embedding': query_vector, 
            'match_threshold': 0.65, 
            'match_count': 4, 
            'p_line_user_id': line_user_id
        }).execute()
        
        if not response.data: return ""
        return "\n".join([f"- {item.get('chat_summary', '')}" for item in response.data])
    except Exception as e:
        logger.error(f"❌ [Recall Memory Error]: {e}")
        return ""