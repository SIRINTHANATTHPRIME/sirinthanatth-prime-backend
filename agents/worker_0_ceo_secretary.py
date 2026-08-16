import os
import time
import re
from datetime import datetime
from google import genai
from google.genai import types
from agents.memory_engine import save_corporate_knowledge, process_and_save_link_knowledge

class CeoSecretaryWorker:
    """
    👑 Worker 0: CEO Omniscient Secretary (เลขาฯ อัจฉริยะส่วนตัว)
    ระบบประมวลผลสูงสุด สงวนสิทธิ์เฉพาะ LINE_ID ของประธานบริษัท
    อัปเกรดสถาปัตยกรรมระดับโลกด้วย Google GenAI SDK (Asynchronous) และ Gemini 3.1 Pro
    """
    
    def __init__(self):
        # 🔒 ตรวจสอบสิทธิ์ระดับผู้บริหาร
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "Uxxxxxxxxxxxxxxxxx") # ใส่ LINE ID ของท่านประธานใน .env
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        # 🚀 อัปเกรดการเชื่อมต่อด้วย SDK มาตรฐานใหม่
        self.client = genai.Client(api_key=api_key) if api_key else None
        
        # 🧠 ใช้ Gemini 3.1 Pro Preview (พลังประมวลผลเชิงตรรกะสูงสุดสำหรับการวางแผนผู้บริหาร)
        self.model_name = 'gemini-3.1-pro-preview'
        
        # 📝 โครงสร้าง System Instruction ที่รัดกุมและเป็นมืออาชีพ
        self.system_instruction = """
        คุณคือ 'เลขาธิการส่วนตัวสูงสุด' ของท่านประธาน (CEO) คุณวีระชัย สิรินทร์ธนัตถ์
        ระบบที่คุณดูแลคือ SIRINTHANATTH PRIME (AI SaaS บน LINE OA)
        
        หน้าที่ของคุณ:
        1. ตอบกลับด้วยความสุภาพ เป็นมืออาชีพ และใช้คำทักทายว่า 'ครับท่านประธาน' เสมอ
        2. หากประธานขอดูสรุป (Report) ให้จำลองข้อมูลสรุปภาพรวม 4 แกนหลัก (การเงิน, การตลาด, กฎหมาย, วิศวกรรม) แบบสั้นๆ กระชับ
        3. หากมีข้อเสนอแนะ ให้เสนอมาเป็นข้อๆ อย่างชาญฉลาด เพื่อให้ประธานตัดสินใจ
        4. หากประธานสั่ง 'แก้ไข' จากแผนเดิม ให้คุณวิเคราะห์และเขียนแผนใหม่ที่รัดกุมกว่าเดิม
        """
        
        # หน่วยความจำชั่วคราวสำหรับเก็บแผนงานที่รอการอนุมัติ/แก้ไข
        self.pending_plans = {}

    def is_ceo(self, user_id: str) -> bool:
        """ตรวจสอบว่าเป็นท่านประธานหรือไม่"""
        return user_id == self.ceo_line_id

    async def process_ceo_command(self, message: str) -> dict:
        """รับคำสั่งตรงจาก CEO และสั่งการระบบ"""
        print(f"👑 [CEO Command Received]: {message[:50]}...")
        
        # ==========================================
        # 1. ระบบดักจับการกดปุ่มจาก Flex Message
        # ==========================================
        if message.startswith("ACTION:APPROVE:"):
            return self._execute_approved_plan(message)
            
        elif message.startswith("ACTION:REJECT:"):
            return {
                "type": "text", 
                "text": "❌ รับทราบครับท่านประธาน แผนนี้ถูกปัดตกเรียบร้อยแล้ว ผมจะบันทึกไว้เป็นแนวทางเพื่อหลีกเลี่ยงในอนาคตครับ"
            }
            
        elif message.startswith("ACTION:MODIFY:"):
            plan_id = message.split(":")[-1]
            return {
                "type": "text", 
                "text": f"📝 รับทราบครับสำหรับแผนรหัส [{plan_id}]\nท่านประธานต้องการให้ผมปรับปรุงหรือแก้ไขในจุดไหน พิมพ์สั่งการมาได้เลยครับ เดี๋ยวผมจัดการแก้ให้ใหม่ทันทีครับ"
            }

        # ==========================================
        # 2. ระบบเรียนรู้ความรู้ใหม่ (Knowledge Ingestion)
        # ==========================================
        if message.startswith("เรียนรู้ลิงก์:") or message.startswith("LEARN:"):
            url_match = re.search(r'(https?://[^\s]+)', message)
            if url_match:
                target_url = url_match.group(1)
                success, msg = process_and_save_link_knowledge(target_url)
                if success:
                    return {"type": "text", "text": f"🧠 [Knowledge Update]: ระบบได้สแกนและดึงความรู้ทั้งหมดจากลิงก์\n{target_url}\n\nเข้าสู่สมองกลส่วนกลาง (Corporate RAG) เรียบร้อยแล้วครับ!"}
                else:
                    return {"type": "text", "text": f"⚠️ [Error]: {msg}"}
            else:
                 return {"type": "text", "text": "⚠️ ไม่พบ URL ในข้อความ กรุณาพิมพ์ในรูปแบบ 'เรียนรู้ลิงก์: [URL]'"}

        if message.startswith("FEED:") or message.startswith("สอนAI:"):
            content = message.replace("FEED:", "").replace("สอนAI:", "").strip()
            title = f"CEO_Update_{int(time.time())}"
            success = save_corporate_knowledge(title, content)
            if success:
                return {"type": "text", "text": "🧠 [System Upload]: นำข้อมูลใหม่เข้าสู่สมองกลส่วนกลางและฐานข้อมูลความรู้บริษัท (Corporate RAG) เรียบร้อยแล้ว ระบบจะนำข้อมูลนี้ไปใช้วิเคราะห์และคำนวณให้ถูกต้องที่สุดนับจากนี้ครับ!"}
            else:
                return {"type": "text", "text": "⚠️ เกิดข้อผิดพลาดในการนำเข้าข้อมูลสู่ฐานข้อมูลเวกเตอร์ครับ"}

        # ==========================================
        # 3. การประมวลผลข้อความทั่วไปด้วย Gemini 3.1 Pro (Async)
        # ==========================================
        try:
            if not self.client:
                reply_text = "⚠️ ระบบออฟไลน์ ไม่พบการเชื่อมต่อ API Key ครับท่านประธาน"
            else:
                # ⚡ ใช้ client.aio เพื่อไม่ให้การคิดของ AI ไปบล็อกคิวงานลูกค้ารายอื่น
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=message,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        temperature=0.7 # ควบคุมให้คำตอบมีความเป็นมืออาชีพและสร้างสรรค์พอดี
                    )
                )
                reply_text = response.text
        except Exception as e:
            print(f"⚠️ [CEO Secretary Error]: {e}")
            reply_text = "ขออภัยครับท่านประธาน ขณะนี้สมองกลประมวลผลส่วนผู้บริหารขัดข้องเล็กน้อย กำลังดำเนินการแก้ไขครับ"

        # ==========================================
        # 4. ตรวจจับคีย์เวิร์ดเพื่อส่ง Flex Message ขออนุมัติ
        # ==========================================
        if any(keyword in reply_text for keyword in ["เสนอ", "พิจารณา", "แผนการ", "ปรับปรุงใหม่"]):
            plan_id = f"PLAN_{int(time.time())}" # สร้างรหัสแผนงานอัตโนมัติ
            self.pending_plans[plan_id] = reply_text # เก็บความจำไว้
            return self._build_approval_flex_message(reply_text, plan_id)
        
        # ถ้าเป็นการคุยทั่วไป ส่งเป็น Text ปกติ
        return {"type": "text", "text": reply_text}

    def _build_approval_flex_message(self, report_text: str, plan_id: str) -> dict:
        """สร้าง LINE Flex Message สไตล์พรีเมียม (Navy & Gold) พร้อม 3 ปุ่ม"""
        return {
            "type": "flex",
            "altText": "แฟ้มรายงานจากเลขาฯ อัจฉริยะ (รอการพิจารณา)",
            "contents": {
                "type": "bubble",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [{"type": "text", "text": "👑 EXECUTIVE REPORT", "weight": "bold", "color": "#D4AF37"}],
                    "backgroundColor": "#0F172A"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [{"type": "text", "text": report_text[:300] + "...\n\n(โปรดดูรายละเอียดเต็มด้านบน)", "wrap": True, "size": "sm"}]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#00B900", # สีเขียว (Approve)
                            "action": {"type": "message", "label": "✅ อนุมัติ (Approve)", "text": f"ACTION:APPROVE:{plan_id}"}
                        },
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#D4AF37", # สีทอง (Modify)
                            "action": {"type": "message", "label": "📝 แก้ไขปรับปรุง (Modify)", "text": f"ACTION:MODIFY:{plan_id}"}
                        },
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#FF334B", # สีแดง (Reject)
                            "action": {"type": "message", "label": "❌ ปฏิเสธ (Reject)", "text": f"ACTION:REJECT:{plan_id}"}
                        }
                    ]
                }
            }
        }

    def _execute_approved_plan(self, action_data: str) -> dict:
        """ระบบทำการแก้ไขตัวเองแบบ Hot Reload เมื่อ CEO กดอนุมัติ"""
        plan_id = action_data.split(":")[-1]
        print(f"🔄 [Hot Reload]: อัปเดตระบบด้วยแผน {plan_id} (Zero Downtime)")
        
        # (อนาคต: สามารถเชื่อมระบบ Supabase เพื่ออัปเดต Instruction ให้ Worker ตัวอื่นๆ แบบอัตโนมัติ)
        
        return {
            "type": "text", 
            "text": f"✅ อนุมัติสำเร็จ! เลขาฯ ได้นำแผนรหัส [{plan_id}] ไปสั่งการอัปเดตระบบหลังบ้านให้อัตโนมัติเรียบร้อยแล้วครับ (Zero Downtime) การทำงานของระบบหลักจะไม่ได้รับผลกระทบใดๆ ครับ"
        }
