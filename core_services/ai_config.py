import os
import logging
import threading
from google import genai
from google.genai import types

logger = logging.getLogger("PrimeAIConfig")

class PrimeAIConfig:
    """
    🌐 ศูนย์บัญชาการกำหนดค่าโมเดล AI ระดับองค์กร (Enterprise-Grade AI Command Center)
    Single Source of Truth: จัดการการเชื่อมต่อ, Thread-Safe Singleton, และ Dynamic Configs
    """
    
    # ==========================================
    # 🧠 1. กำหนดเวอร์ชันโมเดล AI ล่าสุด (Future-Proof Environment Binding)
    # ==========================================
    # CORE_MODEL: ด่านหน้าความเร็วแสง สำหรับ Chat, Routing และคัดกรองเจตนา
    CORE_MODEL = os.getenv("CORE_MODEL", "gemini-3.7-flash")
    
    # EXECUTIVE_MODEL: รุ่นเรือธง (Deep Reasoning) สำหรับวิเคราะห์งบการเงิน กฎหมาย และแผนองค์กร
    EXECUTIVE_MODEL = os.getenv("EXECUTIVE_MODEL", "gemini-3.1-pro-preview")
    
    # EMBEDDING_MODEL: แปลงบริบทลูกค้าเป็น Vector สำหรับระบบ Corporate RAG
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
    
    # MULTIMEDIA_MODELS: โมเดลผลิตสื่อ 4K ระดับสตูดิโอ 
    IMAGE_MODEL = os.getenv("IMAGE_MODEL", "imagen-3.0-generate-001")
    VIDEO_MODEL = os.getenv("VIDEO_MODEL", "veo-3.1-generate-preview")

    # ==========================================
    # 🛡️ 2. Thread-Safe Connection Pooling
    # ==========================================
    _client = None
    _lock = threading.Lock() # ล็อกเกราะป้องกัน Race Condition บน Cloud Run

    @classmethod
    def get_client(cls) -> genai.Client:
        """
        สร้างและส่งออก GenAI Client ด้วยสถาปัตยกรรม Thread-Safe Singleton
        พร้อมระบบ Anti-Timeout รองรับงานวิเคราะห์ Mega Project
        """
        if cls._client is not None:
            return cls._client

        with cls._lock:
            # Double-checked locking 
            if cls._client is not None:
                return cls._client

            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1")
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "asia-southeast3")
            
            # 🚀 ปลดล็อก Timeout เป็น 300 วินาที เพื่อให้ AI คิดวิเคราะห์เชิงลึกได้เต็มประสิทธิภาพ
            timeout_val = float(os.getenv("AI_TIMEOUT", "300.0"))

            try:
                http_options = {'timeout': timeout_val}

                if api_key:
                    logger.info(f"🔐 [AI Config]: Initializing GenAI Client via API Key (Timeout: {timeout_val}s).")
                    cls._client = genai.Client(api_key=api_key, http_options=http_options)
                else:
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
        """รีเซ็ต Connection ฉุกเฉิน กรณีเกิดการเปลี่ยนแปลง Network หรือ API Key กะทันหัน"""
        with cls._lock:
            cls._client = None
            logger.warning("🔄 [AI Config]: AI Client Connection has been reset.")

    # ==========================================
    # ⚙️ 3. Dynamic Configurations Factory
    # ==========================================
    @classmethod
    def get_executive_config(cls, use_search: bool = False, temp: float = 0.1) -> types.GenerateContentConfig:
        """
        โหมด Executive: เน้นความแม่นยำทางคณิตศาสตร์และกฎหมาย ลดการเดา 100%
        """
        tools = [{"google_search": {}}] if use_search else None
        return types.GenerateContentConfig(
            temperature=temp, 
            top_p=0.8,
            top_k=20,
            tools=tools
        )

    @classmethod
    def get_creative_config(cls, use_search: bool = False, temp: float = 0.7) -> types.GenerateContentConfig:
        """
        โหมด Creative: เน้นความเป็นธรรมชาติ จินตนาการ และศิลปะการโน้มน้าวใจ
        """
        tools = [{"google_search": {}}] if use_search else None
        return types.GenerateContentConfig(
            temperature=temp,
            top_p=0.95,
            top_k=40,
            tools=tools
        )

    @classmethod
    def get_safety_settings(cls) -> list:
        """
        โหมด PDPA / Legal Shield: ป้องกันความเสี่ยงด้านกฎหมายขั้นสูงสุด
        """
        return [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
        ]