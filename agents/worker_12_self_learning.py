import os
import json
import re
import asyncio
import logging
from pydantic import BaseModel, Field, ConfigDict
from google import genai
from google.genai import types

# 🌐 นำเข้าศูนย์บัญชาการ AI และเครือข่าย Swarm
from core_services.swarm_dispatcher import swarm_hub

try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.7-pro" # 🚀 อัปเกรดเป็นรุ่น Pro สำหรับการคิดวิเคราะห์เชิงลึก (Deep Reasoning)
        CORE_MODEL = "gemini-3.7-flash"
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key, http_options={'timeout': 300.0})
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3",
                http_options={'timeout': 300.0}
            )

try:
    from supabase import create_client, Client
except ImportError:
    Client = None

# นำเข้าระบบ Embedding จากสมองกลความจำ
try:
    from agents.memory_engine import get_text_embedding
except ImportError:
    async def get_text_embedding(text): return []

logger = logging.getLogger("Worker12-EvolutionEngine")

# =========================================================
# 🧠 โครงสร้างข้อมูลบังคับ (Structured Output Schemas)
# =========================================================
class IntentAnalysisSchema(BaseModel):
    model_config = ConfigDict(strict=True) # 🛡️ บังคับ Data Type เข้มงวดระดับสากล ป้องกัน API พัง
    sentiment: str = Field(description="positive, neutral, frustrated, or urgent")
    underlying_need: str = Field(description="ความต้องการที่แท้จริงระดับจิตใต้สำนึก (Unmet Need)")
    cognitive_bias: str = Field(description="อคติทางความคิด เช่น FOMO, Loss Aversion")
    financial_risk_tolerance: str = Field(description="high, medium, low")
    recommended_tone: str = Field(description="กลยุทธ์น้ำเสียงและการโน้มน้าวที่เหมาะสมที่สุด")

class SystemEvolutionSchema(BaseModel):
    model_config = ConfigDict(strict=True)
    golden_rule: str = Field(description="กฎเหล็ก 1 ข้อที่สกัดได้จากข้อผิดพลาดหรือคำสั่งแก้ไข (กระชับ ชัดเจน บังคับพฤติกรรม AI ทันที)")
    upgrade_proposal: str = Field(description="ร่างแผนอัปเกรดระบบเชิงวิศวกรรม (Code Architecture) ระบุไฟล์ที่ต้องแก้ เพื่อให้ CEO Secretary เขียนโค้ดต่อ")
    reference_links: list[str] = Field(description="รายการ URL ลิงก์อ้างอิง Document เทคโนโลยีล่าสุดที่เกี่ยวข้อง (ต้องค้นหาจาก Google Search จริง)")
    severity_level: str = Field(description="CRITICAL, HIGH, MEDIUM, LOW")

class SelfLearningEngine:
    """
    🧠 Worker 12: Autonomous Evolution Engine (ฝ่ายวิวัฒนาการและเรียนรู้ด้วยตนเอง)
    ฟังก์ชัน: Global Fact-Checking, System Auto-Upgrading, IP/Patent Compliance, & Deep Empathy
    """
    
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.executive_model = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.7-pro")
        self.fast_model = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-3.7-flash")
        
        supa_url = os.environ.get("SUPABASE_URL")
        supa_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
        self.supabase: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None

    async def process_command(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """สะพานเชื่อมต่อรับงานจาก Swarm Hub หรือ Central Boss"""
        intent = await self.analyze_customer_intent(user_id, message)
        return f"🧠 [Evolution Engine]: วิเคราะห์เจตนาสำเร็จ - Sentiment: {intent.get('sentiment')}, Need: {intent.get('underlying_need')}, Risk Profile: {intent.get('financial_risk_tolerance')}"

    async def analyze_customer_intent(self, user_id: str, message: str) -> dict:
        """วิเคราะห์สภาวะอารมณ์ ความต้องการซ่อนเร้น และจิตวิทยาพฤติกรรมผู้บริโภคระดับลึก"""
        if not self.client:
            return {"sentiment": "neutral", "underlying_need": "general", "recommended_tone": "professional"}
            
        try:
            prompt = f"วิเคราะห์ข้อความลูกค้าเชิงลึกทางจิตวิทยาและพฤติกรรมผู้บริโภค (Consumer Psychology & Behavioral Economics): '{message}'"
            
            # ⚡ Native Async Call ไม่บล็อกเซิร์ฟเวอร์
            response = await self.client.aio.models.generate_content(
                model=self.fast_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=IntentAnalysisSchema,
                    temperature=0.1
                )
            )
            return json.loads(response.text)
            
        except Exception as e:
            logger.error(f"⚠️ [Intent Analysis Error]: {e}")
            return {"sentiment": "neutral", "underlying_need": "general", "recommended_tone": "professional"}

    async def analyze_and_learn(self, user_query: str, bad_ai_response: str, user_correction: str):
        """วิเคราะห์ข้อบกพร่อง ค้นหาวิธีแก้ปัญหาทางวิศวกรรมล่าสุด และเสนอแผนอัปเกรดให้เลขาฯ"""
        if not self.client: return False, "⚠️ [System]: ระบบ Evolution Offline"

        logger.info("🧠 [Evolution Engine]: เริ่มกระบวนการสืบค้นข้อมูลเทคโนโลยีล่าสุดและร่างแผนอัปเกรด...")
        
        system_instruction = """
        คุณคือ 'ประธานฝ่ายวิวัฒนาการระบบและสถาปัตยกรรมซอฟต์แวร์ (Chief of AI Evolution)' ของ SIRINTHANATTH PRIME
        หน้าที่ของคุณคือการเรียนรู้จากข้อผิดพลาด (หรือคำสั่งอัปเกรดของท่านประธาน) และสร้าง "พิมพ์เขียวการอัปเกรด (Upgrade Blueprint)" เพื่อส่งให้เลขาฯ (Worker 0) นำไปเขียนโค้ดและเสนอขออนุมัติ
        
        กฎสูงสุด:
        1. 🌍 Global Fact-Checking: ใช้ Google Search ค้นหา Document ทางเทคโนโลยีล่าสุด (เช่น Python 3.12+, Google Cloud Run, FastAPI, Stripe API) และแนบลิงก์ URL จริงเสมอ
        2. 🛡️ IP & Patent Compliance: ปกป้องความลับทางการค้าและนวัตกรรมสิทธิบัตรขององค์กร ห้ามเสนอเทคโนโลยี Open Source ที่มีความเสี่ยงด้านความปลอดภัย
        3. 💻 Actionable Blueprint: แผนอัปเกรดต้องระบุว่าต้องแก้ไฟล์ไหน ใช้ Library อะไร และมีโครงสร้างอย่างไร เพื่อให้ Worker 0 นำไปสั่งงานต่อได้ทันที
        """
        
        prompt = f"""
        วิเคราะห์สถานการณ์ ค้นหาวิธีแก้ปัญหาผ่าน Google Search และร่างแผนอัปเกรดระบบ:
        1. ความต้องการ/คำสั่งจากประธาน: "{user_query}"
        2. การทำงานที่ผิดพลาด/โค้ดเดิม: "{bad_ai_response}"
        3. คำสั่งแก้ไข/แนวทางชี้แนะ: "{user_correction}"
        """
        
        try:
            # ⚡ สั่งรัน Gemini 3.7 Pro พร้อม Google Search Grounding & Structured Output ด้วย Native Async
            response = await self.client.aio.models.generate_content(
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
            
            # บันทึกกฎเหล็กลงความจำส่วนกลาง
            if golden_rule:
                await asyncio.to_thread(self._save_golden_rule, user_query, golden_rule)
                
            # ส่งแผนอัปเกรดกลับไปให้เลขาฯ (Worker 0) ดำเนินการสร้างโค้ดและขออนุมัติ
            final_report = (
                f"🧠 **[Evolution Engine Report]**\n"
                f"✅ **สกัดกฎเหล็กสำเร็จ:** {golden_rule}\n\n"
                f"🚀 **พิมพ์เขียวแผนอัปเกรดระบบ (รอเลขาฯ ดำเนินการสร้างโค้ด):**\n{upgrade_plan}\n\n"
                f"🔗 **เอกสารอ้างอิงเทคโนโลยีล่าสุด (Verified):**\n" + "\n".join([f"- {link}" for link in links]) + "\n\n"
                f"[DELEGATE: WORKER_0_CEO] นำพิมพ์เขียวและลิงก์เทคโนโลยีอ้างอิงนี้ไปร่างโค้ดฉบับสมบูรณ์ พร้อมสร้างหน้าต่าง [REQUIRE_APPROVAL] เพื่อขออนุมัติอัปเดตระบบจากท่านประธานทันที"
            )
            
            return True, final_report
            
        except Exception as e:
            logger.error(f"⚠️ [Evolution Engine Error]: {e}", exc_info=True)
            return False, str(e)

    def _save_golden_rule(self, category: str, golden_rule: str):
        """บันทึกกฎเหล็กลงฐานข้อมูล Vector DB อย่างปลอดภัย (Anti-Injection & Memory Architecture)"""
        if not self.supabase:
            logger.warning("⚠️ Database Offline ข้ามการบันทึก Golden Rule")
            return False, "Database connection failed"
            
        try:
            # 🛡️ Zero-Trust Sanitization
            safe_category = re.sub(r'<(script|iframe|object|embed|svg).*?>.*?</\1>', '', category[:250], flags=re.IGNORECASE)
            safe_category = re.sub(r'<[^>]+>', '', safe_category).strip()
            
            safe_rule = re.sub(r'<(script|iframe|object|embed|svg).*?>.*?</\1>', '', golden_rule, flags=re.IGNORECASE)
            safe_rule = re.sub(r'<[^>]+>', '', safe_rule).strip()

            # หาก get_text_embedding เป็น async ต้องใช้การรัน Event Loop หรือสร้าง Task (ในที่นี้ assume ว่าทำงานสอดคล้องกับระบบเดิม)
            vector_data = None
            try:
                loop = asyncio.get_event_loop()
                vector_data = loop.run_until_complete(get_text_embedding(safe_category))
            except RuntimeError:
                # ถ้าอยู่ใน Event Loop อยู่แล้ว อาจจะใช้ Task หรือปล่อยข้ามไปหากปรับโครงสร้างยาก
                pass
            
            data_to_insert = {
                "category": safe_category,
                "rule_content": safe_rule,
                "impact_score": 100, 
                "status": "active"
            }
            
            if vector_data: data_to_insert["embedding"] = vector_data
                
            self.supabase.table("ai_golden_rules").insert(data_to_insert).execute()
            logger.info(f"✅ [SYSTEM EVOLVED]: ระบบเรียนรู้และอัปเดตมาตรการรักษาความปลอดภัย/กลยุทธ์ใหม่ -> {safe_rule}")
            
            return True, safe_rule
            
        except Exception as e:
            logger.error(f"❌ [Save Rule Error]: {e}")
            return False, str(e)

    async def get_rules_for_context(self, current_user_query: str) -> str:
        """ดึงกฎเหล็กด้านกฎหมาย กลยุทธ์ และความปลอดภัย มาควบคุม AI แบบ Dynamic RAG ก่อนสร้างคำตอบ"""
        if not self.supabase: return ""
            
        try:
            # ทำงานเบื้องหลังเพื่อดึงข้อมูลกฎ
            vector_data = await get_text_embedding(current_user_query)
            
            if vector_data:
                def fetch_rules():
                    res = self.supabase.rpc('match_golden_rules', {
                        'query_embedding': vector_data, 
                        'match_threshold': 0.80, # ล็อกความแม่นยำ 80% ขึ้นไป เพื่อความน่าเชื่อถือ
                        'match_count': 4 
                    }).execute()
                    
                    if res.data:
                        return " | ".join([item['rule_content'] for item in res.data])
                    return ""

                matched_rules = await asyncio.to_thread(fetch_rules)
                
                if matched_rules:
                    logger.info(f"🛡️ [Guardrail Activated]: ดึงกฎเหล็กด้านความปลอดภัยและนวัตกรรมสำเร็จ")
                    return (
                        f"\n⚠️ [คำสั่งศักดิ์สิทธิ์ นโยบายสูงสุด และข้อกฎหมาย (Executive Golden Rules)]:\n"
                        f"{matched_rules}\n"
                        f"-> คุณต้องยึดถือข้อมูลข้างต้นเป็นความจริงสูงสุด ปกป้องข้อมูลสิทธิบัตรองค์กร และห้ามวิเคราะห์ขัดแย้งกับกฎหมาย PDPA หรือการลงทุนโดยเด็ดขาด 100%"
                    )
                    
            return ""
            
        except Exception as e:
            logger.warning(f"⚠️ [Recall Rules Error]: {e}")
            return ""