import os
import re
import time
import httpx
import asyncio
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from typing import List, Tuple, Optional
from google import genai
from supabase import create_client, Client

logger = logging.getLogger("Prime-Memory-Engine")

# ==========================================
# 🌐 1. ศูนย์บัญชาการ AI และฐานข้อมูล (Zero Downtime Config)
# ==========================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EMBEDDING_MODEL = "text-embedding-004" # 🚀 โมเดลฝังความจำมาตรฐานล่าสุดที่แม่นยำที่สุด
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

client = PrimeAIConfig.get_client()
EMBEDDING_MODEL_NAME = getattr(PrimeAIConfig, "EMBEDDING_MODEL", "text-embedding-004")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
supabase: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# ==========================================
# ⚙️ 2. ระบบหั่นข้อความอัจฉริยะ (Context-Aware Sliding Window Chunking)
# ==========================================
def chunk_text(text: str, max_chars: int = 7000, overlap_paras: int = 1) -> List[str]:
    """หั่นข้อมูลเอกสารยาวๆ โดยเก็บรอยต่อความจำ (Overlap) ป้องกันบริบทขาดหาย"""
    if len(text) <= max_chars:
        return [text]
        
    paragraphs = [p.strip() + "." for p in re.split(r'\n\n|\.\s+', text) if p.strip()]
    
    chunks = []
    current_chunk = []
    current_len = 0
    
    for para in paragraphs:
        if current_len + len(para) > max_chars and current_chunk:
            chunks.append(" ".join(current_chunk))
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
# 🧠 3. แกนประมวลผลความจำ (Async Vector Embedding Engine)
# ==========================================
async def get_text_embedding(text: str, retries: int = 3) -> list:
    """แปลงข้อความเป็น Vector พร้อมระบบ Healing อัตโนมัติ ป้องกันคอขวด (Rate Limit)"""
    if not client or not text.strip():
        logger.warning("⚠️ [Memory]: ข้ามการสร้าง Embedding (ข้อมูลว่างเปล่าหรือไม่พบ API Key)")
        return []
        
    for attempt in range(retries):
        try:
            # ⚡ Asynchronous Threading เพื่อไม่บล็อกการทำงานของเซิร์ฟเวอร์หลัก
            result = await asyncio.to_thread(
                client.models.embed_content,
                model=EMBEDDING_MODEL_NAME,
                contents=text
            )
            if hasattr(result, 'embeddings') and result.embeddings:
                return result.embeddings[0].values
            
            logger.error("❌ [Embedding Error]: API คืนค่าโครงสร้าง Vector ไม่สมบูรณ์")
            return []
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "quota" in err_str or "unavailable" in err_str:
                wait_time = (attempt + 1) * 2.5
                logger.warning(f"⏳ [Rate Limit]: รอ {wait_time} วินาทีเพื่อหลบหลีกคอขวด...")
                await asyncio.sleep(wait_time)
            else:
                logger.error(f"❌ [Embedding System Error]: {e}")
                return []
    return []

# ==========================================
# 🌐 4. ระบบสกัดความรู้จากเว็บไซต์ (Async Enterprise Web Scraper)
# ==========================================
async def extract_text_from_url(url: str) -> str:
    """ระบบเจาะข้อมูลเว็บไซต์ความเร็วสูงผ่าน HTTP/2 ป้องกันการโดนบล็อก (Anti-Bot Bypass)"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'th-TH,th;q=0.9,en-US;q=0.8',
        'Referer': 'https://www.google.com/'
    }
    
    try:
        # ⚡ HTTP/2 Async Connection
        async with httpx.AsyncClient(http2=True, follow_redirects=True) as http_client:
            response = await http_client.get(url, headers=headers, timeout=20.0)
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' not in content_type and 'text/plain' not in content_type:
                logger.warning(f"⚠️ [Scraper Shield]: ปฏิเสธการดาวน์โหลด Binary/Media (Content-Type: {content_type})")
                return ""
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 🛡️ Zero-Trust Sanitization: คลีนโค้ดขยะ โฆษณา และสคริปต์แฝงออก 100%
            for element in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "iframe", "svg", "button", "form"]):
                element.extract()
                
            text = soup.get_text(separator=' ', strip=True)
            clean_text = ' '.join(text.split())
            
            # บล็อกเนื้อหาที่ยาวผิดปกติเพื่อป้องกัน Database Overflow
            return clean_text[:50000]
            
    except httpx.TimeoutException:
        logger.error(f"❌ [URL Scrape Timeout]: เซิร์ฟเวอร์ปลายทาง ({url}) ตอบสนองช้าเกินกำหนด")
        return ""
    except Exception as e:
        logger.error(f"❌ [URL Scrape Error]: ขัดข้องขณะดึงข้อมูล ({e})")
        return ""

async def process_and_save_link_knowledge(url: str, added_by: str = "CEO") -> Tuple[bool, str]:
    """สกัดข้อมูลลิงก์และยิงเข้าสู่ Vector DB แบบคู่ขนาน (Parallel Upload)"""
    logger.info(f"🌐 [Enterprise Scraper]: สกัดความรู้เชิงลึกจาก {url}")
    extracted_text = await extract_text_from_url(url)
    
    if not extracted_text:
        return False, "ระบบไฟร์วอลล์ของเว็บไซต์เป้าหมายบล็อกการดึงข้อมูล หรือเนื้อหาไม่ใช่หน้าเว็บปกติ"
        
    chunks = chunk_text(extracted_text)
    base_title = f"Knowledge_URL_{url.split('//')[-1][:30]}"
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 🚀 Parallel Processing: สาดข้อมูลเข้าฐานข้อมูลพร้อมกันทั้งหมด (ไม่บล็อกคิว)
    tasks = []
    for i, chunk in enumerate(chunks):
        title = f"{base_title}_Part{i+1}"
        content = f"[Metadata -> Source: {url} | Scraped: {current_time} | Part: {i+1}/{len(chunks)}]\n\n{chunk}"
        tasks.append(save_corporate_knowledge(title, content))
        
    results = await asyncio.gather(*tasks, return_exceptions=True)
    success_count = sum(1 for res in results if res is True)
            
    if success_count > 0:
        return True, f"นำเข้าข้อมูลองค์ความรู้ {success_count}/{len(chunks)} โหนด เข้าสู่สมองกล (Corporate DB) สำเร็จ"
    return False, "ดึงข้อมูลสำเร็จ แต่ไม่สามารถเชื่อมต่อระบบฐานข้อมูลเวกเตอร์เพื่อจัดเก็บได้"

# ==========================================
# 🏢 5. จัดการฐานข้อมูลความรู้บริษัท (Corporate Knowledge Base - RAG)
# ==========================================
async def save_corporate_knowledge(title: str, content: str) -> bool:
    """ประทับความรู้บริษัทลงสมองกลระยะยาว"""
    if not supabase: return False
        
    try:
        vector_data = await get_text_embedding(content)
        if not vector_data: return False
            
        def _insert_db():
            return supabase.table('corporate_knowledge').insert({
                "title": title, 
                "content": content, 
                "embedding": vector_data
            }).execute()
            
        await asyncio.to_thread(_insert_db)
        logger.info(f"💾 [Corporate DB]: ฝัง Node ความรู้ '{title}' ลง DNA สำเร็จ")
        return True
    except Exception as e:
        logger.error(f"❌ [Corporate DB Save Error]: {e}")
        return False

async def recall_corporate_knowledge(query: str) -> str:
    """ดึงข้อมูลกลยุทธ์/ความรู้องค์กรเพื่อประกอบการตัดสินใจของ AI"""
    if not supabase: return ""
    
    try:
        query_vector = await get_text_embedding(query)
        if not query_vector: return ""

        def _rpc_search():
            return supabase.rpc('match_corporate_knowledge', { 
                'query_embedding': query_vector, 
                'match_threshold': 0.70, 
                'match_count': 4 # ดึงข้อมูลที่เกี่ยวข้องกันมากที่สุด 4 ส่วนประกอบร่าง
            }).execute()

        response = await asyncio.to_thread(_rpc_search)
        if not response.data: return ""
            
        return "\n\n".join([f"📌 [Corporate DB -> {item.get('title', 'Unknown')}]:\n{item.get('content', '')}" for item in response.data])
    except Exception as e:
        logger.error(f"❌ [Recall Corporate DB Error]: {e}")
        return ""

# ==========================================
# 🧠 6. ระบบจัดเก็บและดึงประวัติการคุยลูกค้า (Chat Memory RAG)
# ==========================================
async def save_memory(line_user_id: str, chat_summary: str):
    """บันทึกบริบทประวัติส่วนตัวของลูกค้า (Personal Vector Memory)"""
    if not supabase: return
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    enriched_summary = f"[{current_time}] {chat_summary}"
    
    vector_data = await get_text_embedding(enriched_summary)
    if vector_data:
        try:
            def _insert_memory():
                return supabase.table('chat_memories').insert({
                    "line_user_id": line_user_id, 
                    "chat_summary": enriched_summary, 
                    "embedding": vector_data
                }).execute()
            await asyncio.to_thread(_insert_memory)
        except Exception as e:
            logger.error(f"❌ [Save Memory Error]: {e}")

async def recall_memory(line_user_id: str, current_message: str) -> str:
    """รื้อฟื้นความจำก่อนหน้าเพื่อสร้างบทสนทนาที่เป็นธรรมชาติไร้รอยต่อ"""
    if not supabase: return ""
    
    try:
        query_vector = await get_text_embedding(current_message)
        if not query_vector: return ""
        
        def _rpc_memory():
            return supabase.rpc('match_memories', {
                'query_embedding': query_vector, 
                'match_threshold': 0.65, 
                'match_count': 4, 
                'p_line_user_id': line_user_id
            }).execute()
            
        response = await asyncio.to_thread(_rpc_memory)
        
        if not response.data: return ""
        return "\n".join([f"- {item.get('chat_summary', '')}" for item in response.data])
    except Exception as e:
        logger.error(f"❌ [Recall Memory Error]: {e}")
        return ""