import os
import logging
from google import genai

logger = logging.getLogger("PrimeAIConfig")

class PrimeAIConfig:
    """
    🌐 ศูนย์บัญชาการกำหนดค่าโมเดล AI ระดับโลกสำหรับ SIRINTHANATTH PRIME
    Single Source of Truth: จุดเดียวที่ควบคุมเวอร์ชันและสถาปัตยกรรมของสมองกลทั้งระบบ
    """
    
# ==========================================
    # 🧠 กำหนดเวอร์ชันโมเดล AI มาตรฐานล่าสุด (อัปเดตสอดคล้องกับระบบ Swarm)
    # ==========================================
    # 1. CORE_MODEL: ด่านหน้าความเร็วแสง สำหรับ Chat, Routing และงานตอบกลับรวดเร็ว
    CORE_MODEL = "gemini-3.7-flash"
    
    # 2. EXECUTIVE_MODEL: รุ่นเรือธงสำหรับวิเคราะห์งบการเงิน, เขียนโค้ด, สัญญา และประมวลผลวิดีโอ
    EXECUTIVE_MODEL = "gemini-3.1-pro"
    
    # 3. EMBEDDING_MODEL: รุ่นล่าสุดสำหรับทำ Vector Database และระบบความจำ RAG
    EMBEDDING_MODEL = "gemini-embedding-2-preview"
    
    # 4. MULTIMEDIA_MODELS: โมเดลผลิตสื่อ 4K ระดับสตูดิโอ (Imagen & Veo)
    PRIMARY_MODEL = os.getenv("EXECUTIVE_MODEL", "gemini-3.1-pro")
    FALLBACK_MODEL = os.getenv("FAST_MODEL", "gemini-3.7-flash")
    IMAGE_MODEL = "imagen-4.0-ultra-generate-001"
    VIDEO_MODEL = "veo-3.1-generate-preview"
    
    # ตัวแปรสำหรับเก็บ Instance เพื่อทำ Connection Pooling (Singleton)
    _client = None

    @classmethod
    def get_client(cls) -> genai.Client:
        """
        สร้างและส่งออก GenAI Client ด้วยสถาปัตยกรรม Singleton 
        ประหยัดหน่วยความจำและสลับโหมด Local/Cloud อัตโนมัติ
        """
        # หากมีการเชื่อมต่อแล้ว ให้ส่งคืนตัวเดิมทันที (ลดเวลา Latency)
        if cls._client is not None:
            return cls._client

        # ดึงค่าจาก Environment Variables (รองรับทั้ง API Key และ Vertex AI IAM)
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "asia-southeast3")

        try:
            if api_key:
                # โหมด Local Development หรือใช้ API Key โดยตรง
                logger.info("🔐 [AI Config]: Initializing GenAI Client via Standard API Key.")
                cls._client = genai.Client(api_key=api_key)
            else:
                # โหมด Enterprise (Vertex AI) พึ่งพา Google Cloud IAM 100%
                logger.info(f"☁️ [AI Config]: Initializing Vertex AI (Project: {project_id}, Region: {location}).")
                cls._client = genai.Client(
                    vertexai=True, 
                    project=project_id, 
                    location=location
                )
            
            logger.info("✅ [AI Config]: ศูนย์บัญชาการ AI เริ่มทำงานสมบูรณ์ 100%")
            return cls._client
            
        except Exception as e:
            logger.error(f"❌ [AI Config Critical Error]: ไม่สามารถเชื่อมต่อระบบ AI ได้ -> {e}")
            return None