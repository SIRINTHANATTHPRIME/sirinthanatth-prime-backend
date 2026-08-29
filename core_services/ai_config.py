import os
import logging
from google import genai

logger = logging.getLogger("PrimeAIConfig")

class PrimeAIConfig:
    """ศูนย์บัญชาการกำหนดค่าโมเดล AI ระดับโลกสำหรับ SIRINTHANATTH PRIME"""
    
    # กำหนดเวอร์ชันโมเดล AI มาตรฐานล่าสุด
    CORE_MODEL = "gemini-3.7-flash"
    EXECUTIVE_MODEL = "gemini-3.1-pro-preview"
    EMBEDDING_MODEL = "gemini-embedding-2-preview"
    PRIMARY_MODEL = os.getenv("EXECUTIVE_MODEL", "gemini-3.1-pro")
    FALLBACK_MODEL = os.getenv("FAST_MODEL", "gemini-3.7-flash")
    IMAGE_MODEL = "imagen-4.0-ultra-generate-001"
    VIDEO_MODEL = "veo-3.1-generate-preview"

    @classmethod
    def get_client(cls) -> genai.Client:
        """สร้างและส่งออก GenAI Client ผ่าน SDK google-genai มาตรฐานใหม่"""
        cls.client = genai.Client(
            vertexai=True, 
            project="swift-area-503915-a1", 
            location="asia-southeast3"
        )
        return cls.client