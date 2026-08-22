import os
import json
import asyncio
import logging
from google import genai
from google.genai import types
from supabase import create_client, Client

# พยายามนำเข้าระบบ Embedding จากสมองกลความจำ
try:
    from agents.memory_engine import get_text_embedding
except ImportError:
    def get_text_embedding(text): return []

# ตั้งค่า Logger สำหรับติดตามวิวัฒนาการของระบบ
logger = logging.getLogger("Worker12-EvolutionEngine")

class SelfLearningEngine:
    """
    🧠 Worker 12: Autonomous Evolution Engine (ฝ่ายวิวัฒนาการและเรียนรู้ด้วยตนเอง)
    หน้าที่: วิเคราะห์ความผิดพลาด, สกัดเป็นกฎเหล็ก (Golden Rules) และอัปเดตระบบความจำ เพื่อไม่ให้ AI ทำผิดซ้ำ
    """
    
    def __init__(self):
        # 🚀 โหลด API Key และตั้งค่าโมเดล
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        
        # ใช้รุ่น Pro ที่ฉลาดที่สุดในการวิเคราะห์ความผิดพลาดและสะท้อนความคิด (Self-Reflection)
        self.model_name = 'gemini-3.1-pro-preview' 
        
        # 💾 เชื่อมต่อฐานข้อมูล Supabase (ความจำระยะยาว)
        supa_url = os.environ.get("SUPABASE_URL")
        supa_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
        self.supabase: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None

    async def analyze_and_learn(self, user_query: str, bad_ai_response: str, user_correction: str):
        """1. วิเคราะห์ความผิดพลาดและสกัดบทเรียน (Self-Reflection)"""
        logger.info("🧠 [Evolution Engine]: เริ่มกระบวนการวิเคราะห์ความผิดพลาดและเรียนรู้ด้วยตนเอง...")
        
        system_instruction = """
        คุณคือ 'หัวหน้าฝ่ายควบคุมคุณภาพและวิวัฒนาการ AI (Head of AI Evolution)' ของ SIRINTHANATTH PRIME
        หน้าที่ของคุณคือ วิเคราะห์ความผิดพลาดที่เกิดขึ้นจากการตอบคำถามของ AI ตัวเก่า และสกัดออกมาเป็น "กฎเหล็ก (Golden Rule)"
        
        กฎการทำงาน:
        1. วิเคราะห์ว่าทำไม AI ถึงตอบผิด หรือตอบไม่ตรงใจลูกค้า
        2. สร้าง "กฎเหล็ก" 1 ข้อ ที่ชัดเจน กระชับ เพื่อให้ AI ตัวใหม่จำไว้ใช้และไม่ทำผิดซ้ำ
        3. ห้ามมีคำเกริ่นนำ หรือคำอธิบายเพิ่มเติม ให้ตอบกลับมาเป็นข้อความกฎเหล็กล้วนๆ 
        (ตัวอย่าง: "ห้ามใช้คำว่า 'รักษาหายขาด' ให้ใช้ 'ดูแลอาการ' แทน", หรือ "เมื่อลูกค้าถามถึงค่าส่ง Flash Express ให้แจ้งราคา 12 บาทเสมอ")
        """
        
        prompt = f"""
        เหตุการณ์ความผิดพลาดที่ต้องวิเคราะห์:
        1. ลูกค้าถามว่า: "{user_query}"
        2. AI ตอบไปว่า: "{bad_ai_response}"
        3. ลูกค้าติติง/สั่งแก้ไขว่า: "{user_correction}"
        """
        
        try:
            if not self.client: 
                return False, "⚠️ [System]: ระบบ Evolution Offline (ไม่พบ API Key)"
            
            # ⚡ ใช้ asyncio.to_thread เพื่อไม่ให้บล็อกเซิร์ฟเวอร์ขณะ AI กำลังคิด
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1 # อุณหภูมิต่ำมาก เพื่อให้การตั้งกฎมีเหตุผลตายตัว ไม่เพ้อฝัน
                )
            )
            
            golden_rule = response.text.strip() if response.text else ""
            
            if not golden_rule:
                return False, "Failed to extract golden rule."
            
            # บันทึกลงความจำส่วนกลาง
            return await asyncio.to_thread(self._save_golden_rule, user_query, golden_rule)
            
        except Exception as e:
            logger.error(f"⚠️ [Evolution Engine Error]: {e}")
            return False, str(e)

    def _save_golden_rule(self, category: str, golden_rule: str):
        """2. บันทึกกฎเหล็กลงฐานข้อมูลเพื่อปรับปรุงระบบ (Supabase Vector DB)"""
        if not self.supabase:
            logger.warning("⚠️ ไม่ได้เชื่อมต่อ Supabase ข้ามการบันทึก Golden Rule")
            return False, "Database connection failed"
            
        try:
            # วิเคราะห์บริบทของคำถามเพื่อแปลงเป็น Vector สำหรับการค้นหาในอนาคต (ถ้าระบบเปิดใช้งาน)
            vector_data = get_text_embedding(category)
            
            data_to_insert = {
                "category": category,
                "rule_content": golden_rule,
                "impact_score": 100, # กฎระดับสูงต้องปฏิบัติตามเสมอ
                "status": "active"
            }
            
            # ถ้ามีระบบ Vector ฝังอยู่
            if vector_data:
                data_to_insert["embedding"] = vector_data
                
            # สมมติฐานว่ามีตาราง 'ai_golden_rules' ใน Supabase
            self.supabase.table("ai_golden_rules").insert(data_to_insert).execute()
            
            logger.info(f"✅ [SYSTEM EVOLVED]: วิวัฒนาการสำเร็จ! ระบบเรียนรู้กฎใหม่ -> {golden_rule}")
            return True, golden_rule
            
        except Exception as e:
            logger.error(f"❌ [Save Rule Error]: {e}")
            return False, f"Failed to save rule: {e}"

    async def get_rules_for_context(self, current_user_query: str) -> str:
        """3. ดึงกฎเหล็กมาเตือนสติ AI ก่อนตอบคำถามลูกค้าคนปัจจุบัน"""
        if not self.supabase: 
            return ""
            
        try:
            # ทำงานเบื้องหลังเพื่อดึงข้อมูลกฎ
            def fetch_rules():
                vector_data = get_text_embedding(current_user_query)
                # ค้นหาด้วย Vector (RPC) หากมีการตั้งค่าในฐานข้อมูลไว้
                if vector_data:
                    res = self.supabase.rpc('match_golden_rules', {
                        'query_embedding': vector_data, 'match_threshold': 0.75, 'match_count': 2
                    }).execute()
                    if res.data:
                        return " | ".join([item['rule_content'] for item in res.data])
                return ""

            matched_rules = await asyncio.to_thread(fetch_rules)
            
            if matched_rules:
                return f"⚠️ [คำเตือนจากกฎเหล็กของระบบ (Golden Rules)]: {matched_rules}"
            return ""
            
        except Exception as e:
            logger.warning(f"⚠️ [Recall Rules Error]: {e}")
            return ""