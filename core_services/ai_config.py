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
    IMAGE_MODEL = "imagen-4.0-ultra-generate-001"
    VIDEO_MODEL = "veo-3.1-generate-preview"

    @classmethod
    def get_client(cls) -> genai.Client:
        """สร้างและส่งออก GenAI Client ผ่าน SDK google-genai มาตรฐานใหม่"""
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("❌ ไม่พบ AI_API_KEY ใน Environment Variables")
            return None
        return genai.Client(api_key=api_key)