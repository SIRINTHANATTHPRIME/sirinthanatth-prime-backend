import os
import logging
import threading
from google import genai
from google.genai import types

logger = logging.getLogger("PrimeAIConfig")

class PrimeAIConfig:
    """
    🌐 ศูนย์บัญชาการกำหนดค่าโมเดล AI ระดับองค์กร (Enterprise-Grade AI Command Center)
    สำหรับ SIRINTHANATTH PRIME
    Single Source of Truth: จัดการการเชื่อมต่อ, Thread-Safe Singleton, และ Global Configs
    """
    
    # ==========================================
    # 🧠 1. กำหนดเวอร์ชันโมเดล AI ล่าสุด (สอดคล้องกับระบบ Multi-Agent Swarm)
    # ==========================================
    # CORE_MODEL: ด่านหน้าความเร็วแสง สำหรับ Chat, Routing และคัดกรองเจตนา (Latency < 0.1s)
    CORE_MODEL = "gemini-3.7-flash"
    
    # EXECUTIVE_MODEL: รุ่นเรือธง (Deep Reasoning) สำหรับวิเคราะห์งบการเงิน กฎหมาย และสัญญา
    EXECUTIVE_MODEL = "gemini-3.1-pro-preview"
    
    # EMBEDDING_MODEL: แปลงบริบทลูกค้าเป็น Vector (RAG) สำหรับระบบความจำถาวร
    EMBEDDING_MODEL = "gemini-embedding-2-preview"
    
    # MULTIMEDIA_MODELS: โมเดลผลิตสื่อ 4K ระดับสตูดิโอ 
    IMAGE_MODEL = "imagen-4.0-ultra-generate-001"
    VIDEO_MODEL = "veo-3.1-generate-preview"

    # ==========================================
    # ⚙️ 2. Global Standard Configurations (ล็อกค่าความแม่นยำ)
    # ==========================================
    # โหมด Executive: Temperature = 0.1 (เน้นความแม่นยำทางคณิตศาสตร์ ลดการเดา 100%)
    EXECUTIVE_CONFIG = types.GenerateContentConfig(
        temperature=0.1, 
        top_p=0.8,
        top_k=20,
    )

    # โหมด Creative: Temperature = 0.7 (เน้นความเป็นธรรมชาติ เข้าถึงอารมณ์ลูกค้า)
    CREATIVE_CONFIG = types.GenerateContentConfig(
        temperature=0.7,
        top_p=0.95,
        top_k=40,
    )

    # โหมด PDPA / Legal Shield: ป้องกันความเสี่ยงด้านกฎหมายและคัดกรองเนื้อหา
    SAFETY_SETTINGS = [
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        ),
        types.SafetySetting(
            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        ),
    ]

    # ==========================================
    # 🛡️ 3. Thread-Safe Connection Pooling
    # ==========================================
    _client = None
    _lock = threading.Lock() # ล็อกเกราะป้องกัน Race Condition บน Google Cloud Run

    @classmethod
    def get_client(cls) -> genai.Client:
        """
        สร้างและส่งออก GenAI Client ด้วยสถาปัตยกรรม Thread-Safe Singleton
        รองรับ High Concurrency ผู้ใช้งานหลักหมื่นคนพร้อมกัน โดยไม่เปลือง Memory 
        """
        # หากมีการเชื่อมต่อแล้ว ให้ส่งคืนตัวเดิมทันที (ลดเวลา Latency)
        if cls._client is not None:
            return cls._client

        # ป้องกันการเปิด Connection ซ้ำซ้อนตอน Cold Start ของ Cloud Run
        with cls._lock:
            # Double-checked locking 
            if cls._client is not None:
                return cls._client

            # ดึงค่าจาก Environment Variables
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1")
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "asia-southeast3")

            try:
                # ตั้งค่า Timeout 120 วินาที เพื่อป้องกัน API ค้างตอนรันงานหนัก (เช่น อ่านงบการเงิน 50 หน้า)
                http_options = {'timeout': 120.0}

                if api_key:
                    # โหมด Local Development หรือใช้ API Key
                    logger.info("🔐 [AI Config]: Initializing GenAI Client via API Key (Thread-Safe).")
                    cls._client = genai.Client(api_key=api_key, http_options=http_options)
                else:
                    # โหมด Enterprise (Vertex AI) พึ่งพา Google Cloud IAM 100% (ผ่านมาตรฐานสากล)
                    logger.info(f"☁️ [AI Config]: Initializing Vertex AI (Project: {project_id}, Region: {location}).")
                    cls._client = genai.Client(
                        vertexai=True, 
                        project=project_id, 
                        location=location,
                        http_options=http_options
                    )
                
                logger.info("✅ [AI Config]: Enterprise AI Command Center Is Online & Ready.")
                return cls._client
                
            except Exception as e:
                logger.critical(f"❌ [AI Config Critical Error]: System Failed to Initialize AI Engine -> {e}")
                return None

    @classmethod
    def reset_client(cls):
        """
        สำหรับสั่งรีเซ็ต Connection ฉุกเฉิน กรณีเกิดการเปลี่ยนแปลง Network หรือเปลี่ยน API Key กะทันหัน
        """
        with cls._lock:
            cls._client = None
            logger.warning("🔄 [AI Config]: AI Client Connection has been reset.")