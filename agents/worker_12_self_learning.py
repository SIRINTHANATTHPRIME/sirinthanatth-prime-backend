import os
import json
from google import genai
from google.genai import types
from supabase import create_client, Client

class SelfLearningEngine:
    """
    🧠 Worker 12: Autonomous Evolution Engine (ฝ่ายวิวัฒนาการและเรียนรู้ด้วยตนเอง)
    หน้าที่: วิเคราะห์ความผิดพลาด, สกัดเป็นกฎเหล็ก (Golden Rules) และอัปเดตระบบความจำ
    """
    
    def __init__(self):
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model_name = 'gemini-3.1-pro-preview' # ใช้โมเดลที่ฉลาดที่สุดในการวิเคราะห์ตัวเอง
        
        supa_url = os.environ.get("SUPABASE_URL")
        supa_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        self.supabase: Client = create_client(supa_url, supa_key) if supa_url else None

    async def analyze_and_learn(self, user_query: str, bad_ai_response: str, user_correction: str):
        """1. วิเคราะห์ความผิดพลาดและสกัดบทเรียน"""
        
        prompt = f"""
        คุณคือ 'หัวหน้าฝ่ายควบคุมคุณภาพและวิวัฒนาการ AI' ของ SIRINTHANATTH PRIME
        
        เหตุการณ์ความผิดพลาด:
        1. ลูกค้าถามว่า: "{user_query}"
        2. AI ของเราตอบไปว่า: "{bad_ai_response}"
        3. ลูกค้าติติง/สั่งแก้ไขว่า: "{user_correction}"
        
        หน้าที่ของคุณ:
        จงวิเคราะห์ว่า AI พลาดตรงไหน และสกัดออกมาเป็น "กฎเหล็ก (Golden Rule)" สั้นๆ กระชับ 
        เพื่อให้ AI ตัวอื่นนำกฎนี้ไปใช้ และไม่มีวันทำผิดซ้ำอีกในอนาคต
        (ตอบกลับมาเฉพาะเนื้อหากฎเหล็กเท่านั้น)
        """
        
        try:
            if not self.client: return False, "System Offline"
            
            # สั่งให้ AI ทบทวนตัวเอง (Self-Reflection)
            response = await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.2) # อุณหภูมิต่ำเพื่อให้วิเคราะห์อย่างมีเหตุผล
            )
            golden_rule = response.text.strip()
            
            # บันทึกลงความจำส่วนกลาง
            return self._save_golden_rule(user_query, golden_rule)
            
        except Exception as e:
            print(f"⚠️ [Evolution Engine Error]: {e}")
            return False, str(e)

    def _save_golden_rule(self, category: str, golden_rule: str):
        """2. บันทึกกฎเหล็กลงฐานข้อมูลเพื่อปรับปรุงระบบ (Supabase)"""
        if not self.supabase:
            return False, "Database connection failed"
            
        try:
            # สมมติฐานว่าเราสร้างตาราง 'ai_golden_rules' ไว้ใน Supabase
            self.supabase.table("ai_golden_rules").insert({
                "category": category,
                "rule_content": golden_rule,
                "impact_score": 100, # กฎระดับสูงต้องปฏิบัติตามเสมอ
                "status": "active"
            }).execute()
            
            print(f"✅ [SYSTEM EVOLVED]: เรียนรู้กฎใหม่สำเร็จ -> {golden_rule}")
            return True, golden_rule
            
        except Exception as e:
            return False, f"Failed to save rule: {e}"

    def get_rules_for_context(self, current_user_query: str) -> str:
        """3. ดึงกฎเหล็กมาเตือนสติ AI ก่อนตอบคำถามลูกค้าคนปัจจุบัน"""
        # (ระบบจะวิ่งไปค้นหาความจำใน DB ที่เกี่ยวข้องกับคำถามลูกค้า แล้วนำมาแนบใน Prompt)
        # ตัวอย่างผลลัพธ์ที่ส่งกลับ: "คำเตือนจากอดีต: ห้ามใช้ภาษาทางการเกินไปเมื่อคุยเรื่อง TikTok"
        pass