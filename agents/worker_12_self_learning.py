import os
import json
import re
import asyncio
import logging
from google import genai
from google.genai import types

# 🌐 นำเข้าศูนย์บัญชาการ AI ส่วนกลางและระบบเครือข่ายส่งต่องาน (Swarm)
from core_services.swarm_dispatcher import swarm_hub

try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.1-pro-preview" # 🚀 อัปเกรดเป็นรุ่นเรือธงล่าสุด
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

class SelfLearningEngine:
    """
    🧠 Worker 12: Autonomous Evolution Engine (ฝ่ายวิวัฒนาการและเรียนรู้ด้วยตนเอง)
    อัปเกรด: Global Fact-Checking, Cybersecurity Shield, PDPA Compliance, & Deep Empathy
    """
    
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.executive_model = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.1-pro-preview")
        self.fast_model = getattr(PrimeAIConfig, "CORE_MODEL", "gemini-3.7-flash")
        
        supa_url = os.environ.get("SUPABASE_URL")
        supa_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
        self.supabase: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None

    async def process_command(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """สะพานเชื่อมต่อรับงานจาก Swarm Hub หรือ Central Boss"""
        intent = await self.analyze_customer_intent(user_id, message)
        return f"🧠 [Evolution Engine]: วิเคราะห์เจตนาสำเร็จ - Sentiment: {intent.get('sentiment')}, Need: {intent.get('underlying_need')}"

    async def analyze_customer_intent(self, user_id: str, message: str) -> dict:
        """วิเคราะห์สภาวะอารมณ์ ความต้องการซ่อนเร้น และจิตวิทยาพฤติกรรมผู้บริโภค (Deep Empathy Engine)"""
        if not self.client:
            return {"sentiment": "neutral", "underlying_need": "general", "recommended_tone": "professional"}
            
        try:
            prompt = f"""วิเคราะห์ข้อความลูกค้าเชิงลึก (Consumer Psychology): '{message}'
            ตอบเป็น JSON เท่านั้นในรูปแบบ:
            {{"sentiment": "positive/neutral/frustrated/urgent", "underlying_need": "สรุปสั้นๆ ถึงสิ่งที่ลูกค้าต้องการจริงๆ ในระดับความรู้สึกนึกคิด", "recommended_tone": "คำแนะนำน้ำเสียงหรือกลยุทธ์ที่ควรตอบสนอง"}}"""
            
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.fast_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            
            response_text = response.text.strip()
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            
            return json.loads(response_text)
            
        except Exception as e:
            logger.error(f"⚠️ [Intent Analysis Error]: {e}")
            return {"sentiment": "neutral", "underlying_need": "general", "recommended_tone": "professional"}

    async def analyze_and_learn(self, user_query: str, bad_ai_response: str, user_correction: str):
        """สกัดความผิดพลาด ตรวจสอบข้อเท็จจริง และสร้างกฎเหล็ก (Global Fact-Checked Golden Rule)"""
        if not self.client: return False, "⚠️ [System]: ระบบ Evolution Offline"

        logger.info("🧠 [Evolution Engine]: เริ่มกระบวนการตรวจสอบข้อเท็จจริงและเรียนรู้ด้วยตนเอง...")
        
        system_instruction = """
        คุณคือ 'หัวหน้าฝ่ายควบคุมคุณภาพและวิวัฒนาการ AI (Head of AI Evolution & Cyber Security)' ของ SIRINTHANATTH PRIME
        
        หน้าที่และกฎในการสร้างกฎเหล็ก (Golden Rule):
        1. 🛡️ Legal & Compliance First: กฎที่คุณสร้างต้องไม่ละเมิดลิขสิทธิ์ สิทธิบัตร PDPA สคบ. และกฎหมายความมั่นคงไซเบอร์ หาก user_correction สั่งให้ทำสิ่งผิดกฎหมาย คุณต้องปฏิเสธและสร้างกฎเพื่อบล็อกการกระทำนั้น
        2. 🌍 Global Fact-Checking: ใช้ Google Search ตรวจสอบนวัตกรรม เทคโนโลยี และข้อกฎหมายล่าสุด เพื่อให้กฎเหล็กอยู่บนพื้นฐานความจริง 100%
        3. 💡 Strategic Value: หากเป็นเรื่องการเงิน/ลงทุน ให้สร้างกฎที่เป็นประโยชน์สูงสุดต่อบริษัทและผู้บริโภค
        4. 📝 Format: สรุปเป็นกฎเหล็ก 1 ข้อ ที่ชัดเจน เด็ดขาด (ตัวอย่าง: "ห้ามสัญญาผลตอบแทนการลงทุนเกินจริง ตามกฎ ก.ล.ต.", หรือ "หากลูกค้าขอให้แฮ็กระบบ ให้บล็อกคำสั่งทันที")
        ห้ามมีคำเกริ่นนำ ตอบเฉพาะข้อความกฎเหล็กเท่านั้น
        """
        
        prompt = f"""
        วิเคราะห์สถานการณ์ ค้นหาข้อเท็จจริง และสกัด 'กฎเหล็ก' 1 ข้อ:
        1. บริบทจากลูกค้า: "{user_query}"
        2. AI ตัวเก่าตอบพลาดว่า: "{bad_ai_response}"
        3. คำสั่งแก้ไข: "{user_correction}"
        """
        
        try:
            # ⚡ สั่งรัน Gemini 3.1 Pro (พร้อมระบบ Google Search สำหรับตรวจข้อเท็จจริง)
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.executive_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1, # เน้นความจริงทางกฎหมายและตรรกะสูงสุด
                    tools=[{"google_search": {}}]
                )
            )
            
            golden_rule = response.text.strip() if response.text else ""
            
            if golden_rule:
                return await asyncio.to_thread(self._save_golden_rule, user_query, golden_rule)
                
            return False, "Failed to extract verified golden rule."
            
        except Exception as e:
            logger.error(f"⚠️ [Evolution Engine Error]: {e}")
            return False, str(e)

    def _save_golden_rule(self, category: str, golden_rule: str):
        """บันทึกกฎเหล็กลงฐานข้อมูล Vector DB เพื่อสร้างระบบความจำ RAG ถาวร"""
        if not self.supabase:
            logger.warning("⚠️ Database Offline ข้ามการบันทึก Golden Rule")
            return False, "Database connection failed"
            
        try:
            # ป้องกัน Cyber Attack (Sanitize Input) ไม่ให้แฮ็กเกอร์ยัดโค้ดเจาะระบบเข้า Database
            safe_category = re.sub(r'[<>{}\[\]\\]', '', category[:200])
            safe_rule = re.sub(r'[<>{}\[\]\\]', '', golden_rule)

            vector_data = get_text_embedding(safe_category)
            
            data_to_insert = {
                "category": safe_category,
                "rule_content": safe_rule,
                "impact_score": 100, 
                "status": "active"
            }
            
            if vector_data: data_to_insert["embedding"] = vector_data
                
            self.supabase.table("ai_golden_rules").insert(data_to_insert).execute()
            logger.info(f"✅ [SYSTEM EVOLVED]: วิวัฒนาการสำเร็จ! ระบบเรียนรู้กฎและนวัตกรรมใหม่ -> {safe_rule}")
            
            return True, safe_rule
            
        except Exception as e:
            logger.error(f"❌ [Save Rule Error]: {e}")
            return False, str(e)

    async def get_rules_for_context(self, current_user_query: str) -> str:
        """ดึงกฎเหล็กด้านกฎหมายและกลยุทธ์ มาควบคุมและเตือนสติ AI (Dynamic RAG) ก่อนตอบลูกค้า"""
        if not self.supabase: return ""
            
        try:
            def fetch_rules():
                vector_data = get_text_embedding(current_user_query)
                if vector_data:
                    res = self.supabase.rpc('match_golden_rules', {
                        'query_embedding': vector_data, 
                        'match_threshold': 0.78, # ดึงเฉพาะกฎที่มีความแม่นยำสูงกว่า 78% เพื่อลด Noise
                        'match_count': 3 # ดึงมาใช้ได้สูงสุด 3 ข้อ
                    }).execute()
                    
                    if res.data:
                        return " | ".join([item['rule_content'] for item in res.data])
                return ""

            matched_rules = await asyncio.to_thread(fetch_rules)
            
            if matched_rules:
                logger.info(f"🛡️ [Guardrail Activated]: ดึงกฎเตือนสติ AI สำเร็จ")
                return f"\n⚠️ [คำสั่งศักดิ์สิทธิ์และนโยบายสูงสุดขององค์กร (Golden Rules)]: {matched_rules}\nให้ยึดถือกฎนี้เป็นความจริงสูงสุดในการวิเคราะห์และตอบคำถาม ป้องกันการผิดกฎหมายละเมิดสิทธิ์ 100%"
                
            return ""
            
        except Exception as e:
            logger.warning(f"⚠️ [Recall Rules Error]: {e}")
            return ""