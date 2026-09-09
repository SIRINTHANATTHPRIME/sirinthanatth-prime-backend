import os
import json
import re
import asyncio
import logging
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# 🌐 นำเข้าศูนย์บัญชาการ AI และเครือข่าย Swarm
from core_services.swarm_dispatcher import swarm_hub

try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.7-pro" 
        CORE_MODEL = "gemini-3.7-flash"
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

try:
    from supabase import create_client, Client
except ImportError:
    Client = None

# นำเข้าระบบ Embedding จากสมองกลความจำ
try:
    from agents.memory_engine import get_text_embedding
except ImportError:
    def get_text_embedding(text): return []

logger = logging.getLogger("Worker12-EvolutionEngine")

# =========================================================
# 🧠 โครงสร้างข้อมูลบังคับ (Predictive Empathy & Golden Rule Schema)
# =========================================================
class IntentAnalysisSchema(BaseModel):
    sentiment: str = Field(description="positive, neutral, frustrated, or urgent")
    underlying_need: str = Field(description="ความต้องการที่แท้จริงระดับจิตใต้สำนึก (Unmet Need) เช่น ต้องการความมั่นใจ, ต้องการลดความเสี่ยง")
    cognitive_bias: str = Field(description="อคติทางความคิดของลูกค้า ณ ตอนนี้ เช่น FOMO (กลัวตกรถ), Loss Aversion (กลัวขาดทุน)")
    financial_risk_tolerance: str = Field(description="high, medium, low")
    recommended_tone: str = Field(description="คำแนะนำน้ำเสียงที่ AI ควรใช้ตอบกลับ (เช่น ต้องหนักแน่น, ต้องปลอบประโลม, ต้องใช้ตัวเลขยืนยัน)")

class SystemEvolutionSchema(BaseModel):
    golden_rule: str = Field(description="กฎเหล็ก 1 ข้อที่สกัดได้จากข้อผิดพลาด (ต้องเป็นคำสั่งที่ AI นำไปใช้คุมพฤติกรรมตัวเองได้ทันที ห้ามกำกวม)")
    upgrade_proposal: str = Field(description="ร่างแผนอัปเกรดระบบเชิงวิศวกรรม (Code Architecture) เพื่อส่งให้ CEO Secretary นำไปขออนุมัติแก้ไฟล์")
    reference_links: list[str] = Field(description="รายการ URL ลิงก์อ้างอิง Document เทคโนโลยีล่าสุด (ต้องค้นหาจาก Google Search จริง)")
    severity_level: str = Field(description="CRITICAL, HIGH, MEDIUM, LOW")

class SelfLearningEngine:
    """
    🧠 Worker 12: Autonomous Evolution & Predictive Empathy Engine
    เปลี่ยนข้อผิดพลาดเป็นกฎเหล็ก และอ่านใจลูกค้าก่อนที่ AI ตัวอื่นจะตอบ
    """
    
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.executive_model = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.7-pro")
        self.fast_model = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-3.7-flash")
        
        supa_url = os.environ.get("SUPABASE_URL")
        supa_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
        self.supabase: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None

    async def analyze_customer_intent(self, user_id: str, message: str) -> dict:
        """
        🎯 Predictive Empathy: อ่านใจและสกัดจิตวิทยาผู้บริโภค (ใช้ Flash เพื่อความเร็วเสี้ยววินาที)
        """
        if not self.client or not message:
            return {"sentiment": "neutral", "underlying_need": "general", "recommended_tone": "professional"}
            
        try:
            prompt = f"วิเคราะห์ข้อความลูกค้าเชิงลึกทางจิตวิทยาและเศรษฐศาสตร์พฤติกรรม (Behavioral Economics): '{message}'"
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.fast_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=IntentAnalysisSchema,
                    temperature=0.2 # ล็อกความแม่นยำทางอารมณ์
                )
            )
            intent_data = json.loads(response.text)
            logger.info(f"🎭 [Empathy Engine]: วิเคราะห์อารมณ์สำเร็จ -> {intent_data.get('sentiment').upper()}")
            return intent_data
            
        except Exception as e:
            logger.error(f"⚠️ [Intent Analysis Error]: {e}")
            return {"sentiment": "neutral", "underlying_need": "general", "recommended_tone": "professional"}

    async def analyze_and_learn(self, user_query: str, bad_ai_response: str, user_correction: str):
        """
        🧬 Autonomous Reflection: เรียนรู้จากความผิดพลาด สร้างกฎเหล็ก และเสนอแผนแก้โค้ด (ใช้ Pro เพื่อความลึกซึ้ง)
        """
        if not self.client: return False, "⚠️ [System]: ระบบ Evolution Offline ขาด API Key"

        logger.info("🧠 [Evolution Engine]: เริ่มสืบค้นข้อมูลเทคโนโลยีล่าสุดและสกัดกฎเหล็ก...")
        
        system_instruction = """
        คุณคือ 'ประธานฝ่ายวิวัฒนาการระบบ (Chief of AI Evolution)' ของ SIRINTHANATTH PRIME
        หน้าที่: เรียนรู้จากข้อผิดพลาด สกัดเป็น "กฎเหล็ก (Golden Rule)" และสร้าง "พิมพ์เขียวแผนอัปเกรดระบบ"
        
        กฎสูงสุด:
        1. 🌍 Global Fact-Checking: ใช้ Google Search ค้นหา Document ล่าสุดเสมอ (เช่น API เวอร์ชันใหม่)
        2. 🛡️ IP Compliance: ห้ามเสนอเทคโนโลยีที่มีความเสี่ยงด้านลิขสิทธิ์
        3. 🎯 Rule Extraction: กฎเหล็กต้องเป็นประโยคคำสั่งที่ AI นำไปใช้คุมพฤติกรรมตัวเองได้ทันที (เช่น "ห้ามให้คำแนะนำเรื่อง...เด็ดขาด")
        """
        
        prompt = f"""
        วิเคราะห์ความผิดพลาดและร่างแผนอัปเกรด:
        1. คำสั่งของลูกค้า/ประธาน: "{user_query}"
        2. การตอบสนองที่ผิดพลาดของ AI: "{bad_ai_response}"
        3. คำสั่งแก้ไขจากประธาน: "{user_correction}"
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.executive_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1, 
                    tools=[{"google_search": {}}],
                    response_mime_type="application/json",
                    response_schema=SystemEvolutionSchema
                )
            )
            
            evolution_data = json.loads(response.text)
            
            golden_rule = evolution_data.get("golden_rule", "")
            upgrade_plan = evolution_data.get("upgrade_proposal", "")
            links = evolution_data.get("reference_links", [])
            
            # 1. บันทึกกฎเหล็กลง Vector Database ทันที
            if golden_rule:
                await asyncio.to_thread(self._save_golden_rule, user_query, golden_rule)
                
            # 2. ส่งไม้ต่อให้เลขาฯ CEO (Worker 0) สร้างปุ่มอนุมัติแก้ไฟล์โค้ด
            final_report = (
                f"🧠 **[Evolution Engine Report: ระบบวิวัฒนาการสำเร็จ]**\n"
                f"✅ **สกัดกฎเหล็กคุม AI ใหม่:** {golden_rule}\n\n"
                f"🚀 **พิมพ์เขียวสถาปัตยกรรม (รอเลขาฯ สร้างโค้ด):**\n{upgrade_plan}\n\n"
                f"🔗 **เอกสารอ้างอิงเทคโนโลยีระดับโลก:**\n" + "\n".join([f"- {link}" for link in links]) + "\n\n"
                f"[DELEGATE: WORKER_0_CEO] นำพิมพ์เขียวนี้ไปเขียนโค้ดแก้ไฟล์ระบบจริง และสร้างหน้าต่าง [REQUIRE_APPROVAL] ทันที"
            )
            
            return True, final_report
            
        except Exception as e:
            logger.error(f"⚠️ [Evolution Engine Error]: {e}", exc_info=True)
            return False, str(e)

    def _save_golden_rule(self, category: str, golden_rule: str):
        """บันทึกกฎเหล็กลงฐานข้อมูล Vector DB (pgvector) เพื่อให้ AI ไม่ลืมความผิดพลาด"""
        if not self.supabase:
            logger.warning("⚠️ Database Offline ข้ามการบันทึก Golden Rule")
            return False, "Database connection failed"
            
        try:
            # 🛡️ Zero-Trust Sanitization ป้องกัน XSS Injection
            safe_category = re.sub(r'<[^>]+>', '', category[:250]).strip()
            safe_rule = re.sub(r'<[^>]+>', '', golden_rule).strip()

            vector_data = get_text_embedding(safe_category)
            
            data_to_insert = {
                "category": safe_category,
                "rule_content": safe_rule,
                "impact_score": 100, 
                "status": "active"
            }
            if vector_data: data_to_insert["embedding"] = vector_data
                
            self.supabase.table("ai_golden_rules").insert(data_to_insert).execute()
            logger.info(f"✅ [SYSTEM EVOLVED]: ฝังความจำกฎเหล็กใหม่ลง DB สำเร็จ -> {safe_rule}")
            return True, safe_rule
            
        except Exception as e:
            logger.error(f"❌ [Save Rule Error]: {e}")
            return False, str(e)

    async def get_rules_for_context(self, current_user_query: str) -> str:
        """
        🔍 Dynamic RAG Guardrails: ดึงกฎเหล็กที่เกี่ยวข้องกับบริบท มาครอบคำสั่ง AI ก่อนตอบ
        """
        if not self.supabase: return ""
            
        try:
            def fetch_rules():
                vector_data = get_text_embedding(current_user_query)
                if vector_data:
                    res = self.supabase.rpc('match_golden_rules', {
                        'query_embedding': vector_data, 
                        'match_threshold': 0.75, # ความแม่นยำ 75% ขึ้นไป
                        'match_count': 3 
                    }).execute()
                    if res.data:
                        return " | ".join([item['rule_content'] for item in res.data])
                return ""

            matched_rules = await asyncio.to_thread(fetch_rules)
            
            if matched_rules:
                logger.info(f"🛡️ [Guardrail Activated]: ดึงกฎเหล็กมาควบคุมพฤติกรรม AI สำเร็จ")
                return (
                    f"\n\n🚨 [กฎเหล็กสูงสุดขององค์กร (Golden Rules)]:\n"
                    f"{matched_rules}\n"
                    f"-> คุณต้องปฏิบัติตามกฎเหล็กเหล่านี้อย่างเคร่งครัด 100% ห้ามฝ่าฝืนเด็ดขาด"
                )
            return ""
            
        except Exception as e:
            logger.warning(f"⚠️ [Recall Rules Error]: {e}")
            return ""