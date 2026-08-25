import os
from google import genai

class PrimeAIConfig:
    """
    🧠 ศูนย์บัญชาการสมองกลส่วนกลาง SIRINTHANATTH PRIME (อัปเดตล่าสุด: ส.ค. 2026)
    """
    # สมองกลหลัก: เร็ว ฉลาด และจัดการ Workflow ซับซ้อนได้ดีที่สุด
    CORE_MODEL = "gemini-3.7-flash" 
    
    # สมองกลระดับสูง: สำหรับงานวิเคราะห์ขั้นสุดยอดของ CEO
    EXECUTIVE_MODEL = "gemini-3.1-pro-preview"
    
    # สมองกลสำหรับจัดการฐานข้อมูลความรู้องค์กร (Memory/RAG)
    EMBEDDING_MODEL = "gemini-embedding-2-preview"

    @staticmethod
    def get_client():
        """ตัวเชื่อมต่อ API ระดับองค์กร"""
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        return genai.Client(api_key=api_key) if api_key else None