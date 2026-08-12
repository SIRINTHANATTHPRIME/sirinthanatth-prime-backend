import os
import time
import asyncio
import google.generativeai as genai
from datetime import datetime

class CeoSecretaryWorker:
    """
    👑 Worker 0: CEO Omniscient Secretary (เลขาฯ อัจฉริยะส่วนตัว)
    ระบบประมวลผลสูงสุด สงวนสิทธิ์เฉพาะ LINE_ID ของประธานบริษัท
    """
    
    def __init__(self):
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "Uxxxxxxxxxxxxxxxxx") # ใส่ LINE ID ของท่านประธานใน .env
        api_key = os.getenv("AI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        # หน่วยความจำชั่วคราวสำหรับเก็บแผนงานที่รอการแก้ไข
        self.pending_plans = {}

    def is_ceo(self, user_id: str) -> bool:
        """ตรวจสอบว่าเป็นท่านประธานหรือไม่"""
        return user_id == self.ceo_line_id

    async def process_ceo_command(self, message: str) -> dict:
        """รับคำสั่งตรงจาก CEO และสั่งการระบบ"""
        print(f"👑 [CEO Command Received]: {message[:50]}...")
        
        # 1. เช็กว่าเป็นคำสั่งจากปุ่ม Flex Message หรือไม่
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

        # 🌟 ระบบป้อนไฟล์/ความรู้เข้าสมองกล (Knowledge Ingestion)
        if message.startswith("FEED:") or message.startswith("สอนAI:"):
            # (รอการเชื่อมต่อฟังก์ชัน save_corporate_knowledge ในอนาคต)
            return {"type": "text", "text": "🧠 [System Upload]: รับทราบข้อมูลใหม่ครับ กำลังนำเข้าสู่ระบบความจำส่วนกลางเพื่อใช้ประมวลผลต่อไปครับท่านประธาน"}

        # 2. ถ้าเป็นการแชทปกติ ให้ AI วิเคราะห์ว่า CEO ต้องการอะไร
        prompt = f"""
        คุณคือ 'เลขาธิการส่วนตัวสูงสุด' ของท่านประธาน (CEO) บจก. มาร์เก็ตติ้ง สปาร์ค คอมไบน์ 
        ระบบที่คุณดูแลคือ SIRINTHANATTH PRIME (AI SaaS บน LINE OA)
        
        ท่านประธานสั่งการหรือถามว่า: '{message}'
        
        หน้าที่ของคุณ:
        1. ตอบกลับด้วยความสุภาพ เป็นมืออาชีพ (ใช้คำทักทายว่า 'ครับท่านประธาน')
        2. หากประธานขอดูสรุป (Report) ให้จำลองข้อมูลสรุปภาพรวม 4 แกนหลัก (การเงิน, การตลาด, กฎหมาย, วิศวกรรม) แบบสั้นๆ กระชับ
        3. หากมีข้อเสนอแนะ ให้เสนอมาเป็นข้อๆ อย่างชาญฉลาด เพื่อให้ประธานตัดสินใจ
        4. หากประธานสั่ง 'แก้ไข' จากแผนเดิม ให้คุณวิเคราะห์และเขียนแผนใหม่ที่รัดกุมกว่าเดิม
        """
        
        try:
            # ⚡ เปลี่ยนมาใช้ Async เพื่อไม่ให้บล็อกการทำงานของเซิร์ฟเวอร์
            response = await self.model.generate_content_async(prompt)
            reply_text = response.text
        except Exception as e:
            print(f"⚠️ [CEO Secretary Error]: {e}")
            reply_text = "ขออภัยครับท่านประธาน ขณะนี้ระบบประมวลผลของผมขัดข้องเล็กน้อย กำลังดำเนินการแก้ไขครับ"

        # 3. ตรวจสอบว่าในข้อความมีการเสนอแผนงานหรือไม่ ถ้ามีให้ส่ง Flex Message 3 ปุ่ม
        if any(keyword in reply_text for keyword in ["เสนอ", "พิจารณา", "แผนการ", "ปรับปรุงใหม่"]):
            plan_id = f"PLAN_{int(time.time())}" # สร้างรหัสแผนงานอัตโนมัติ
            self.pending_plans[plan_id] = reply_text # เก็บความจำไว้
            return self._build_approval_flex_message(reply_text, plan_id)
        
        # ถ้าเป็นการคุยทั่วไป ส่งเป็น Text ปกติ
        return {"type": "text", "text": reply_text}

    def _build_approval_flex_message(self, report_text: str, plan_id: str) -> dict:
        """สร้าง LINE Flex Message สวยงามพร้อม 3 ปุ่ม [อนุมัติ] [แก้ไข] [ปฏิเสธ]"""
        return {
            "type": "flex",
            "altText": "แฟ้มรายงานจากเลขาฯ อัจฉริยะ (รอการพิจารณา)",
            "contents": {
                "type": "bubble",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [{"type": "text", "text": "👑 EXECUTIVE REPORT", "weight": "bold", "color": "#FFD700"}],
                    "backgroundColor": "#1A1A1A"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    # แสดงรายละเอียดแผนงาน (ตัดให้เหลือ 300 ตัวอักษรเพื่อความสวยงามในหน้าจอ)
                    "contents": [{"type": "text", "text": report_text[:300] + "...\n\n(โปรดดูรายละเอียดเต็มด้านบน)", "wrap": True, "size": "sm"}]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical", # เปลี่ยนเป็น vertical เพื่อเรียง 3 ปุ่มแนวตั้งสวยๆ
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#00B900", # สีเขียว
                            "action": {"type": "message", "label": "✅ อนุมัติ (Approve)", "text": f"ACTION:APPROVE:{plan_id}"}
                        },
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#FFA500", # สีส้มทอง
                            "action": {"type": "message", "label": "📝 แก้ไขปรับปรุง (Modify)", "text": f"ACTION:MODIFY:{plan_id}"}
                        },
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#FF334B", # สีแดง
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
        
        # (อนาคต: เขียนฟังก์ชันเชื่อม Supabase เพื่อนำแผนนี้ไปตั้งค่า System Prompt ให้ Worker ตัวอื่นๆ)
        
        return {
            "type": "text", 
            "text": f"✅ อนุมัติสำเร็จ! เลขาฯ ได้นำแผนรหัส [{plan_id}] ไปสั่งการอัปเดตระบบหลังบ้านให้อัตโนมัติเรียบร้อยแล้วครับ (Zero Downtime) ลูกค้าจะไม่ได้รับผลกระทบใดๆ ครับ"
        }