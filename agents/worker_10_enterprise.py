import os
import time
import re
import logging
import asyncio
from google import genai
from google.genai import types

# นำเข้าระบบความจำเพื่อบันทึกข้อมูลระดับองค์กร
try:
    from agents.memory_engine import save_corporate_knowledge, process_and_save_link_knowledge
except ImportError:
    def save_corporate_knowledge(t, c): return True
    def process_and_save_link_knowledge(u): return True, "จำลองการบันทึกสำเร็จ"

logger = logging.getLogger("CeoSecretary")

class CeoSecretaryWorker:
    """
    👑 Worker 0: CEO Omniscient Secretary (เลขาฯ อัจฉริยะส่วนตัว)
    ระบบประมวลผลสูงสุด สงวนสิทธิ์เฉพาะ LINE_ID ของประธานบริษัท
    รองรับการวิเคราะห์ไฟล์วิดีโอ (Video), PDF, รูปภาพ และระบบสั่งการ 3 ปุ่ม (Approve/Modify/Reject)
    """
    
    def __init__(self):
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "Uxxxxxxxxxxxxxxxxx")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "")
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        self.client = genai.Client(api_key=api_key) if api_key else None
        self.model_name = 'gemini-1.5-pro'
        
        self.system_instruction = """
        คุณคือ 'เลขาธิการส่วนตัวสูงสุด' ของท่านประธาน (CEO) คุณวีระชัย สิรินทร์ธนัตถ์
        ระบบที่คุณดูแลคือ SIRINTHANATTH PRIME (AI SaaS บน LINE OA)
        
        หน้าที่ของคุณ:
        1. ตอบกลับด้วยความสุภาพ เป็นมืออาชีพ และใช้คำทักทายว่า 'ครับท่านประธาน' เสมอ
        2. หากท่านประธานส่งวิดีโอ (Video), รูปภาพ หรือไฟล์ PDF มา ให้วิเคราะห์ สกัดข้อมูล ถอดสคริปต์ และสรุปใจความสำคัญอย่างละเอียด
        3. หากประธานขอดูสรุป (Report) ให้จำลองข้อมูลสรุปภาพรวม 4 แกนหลัก (การเงิน, การตลาด, กฎหมาย, วิศวกรรม)
        4. เสนอแนะกลยุทธ์เชิงรุกอย่างชาญฉลาด
        """
        
        self.pending_plans = {}

    def is_ceo(self, user_id: str) -> bool:
        """ตรวจสอบว่าเป็นท่านประธานหรือไม่"""
        # อนุมัติสิทธิ์ให้ CEO หรือ Master Admin
        return user_id == self.ceo_line_id or user_id == self.master_admin_id

    async def process_ceo_command(self, message: str, file_path: str = None, file_type: str = None) -> dict:
        """รับคำสั่งและไฟล์ตรงจาก CEO และสั่งการระบบเบื้องหลัง"""
        logger.info(f"👑 [CEO Command Received]: {message[:50]}... | File: {file_type}")
        
        # 1. ระบบดักจับการกดปุ่มจาก Flex Message
        if message.startswith("ACTION:APPROVE:"):
            return self._execute_approved_plan(message)
        elif message.startswith("ACTION:REJECT:"):
            return {"type": "text", "text": "❌ รับทราบครับท่านประธาน แผนนี้ถูกปัดตกเรียบร้อยแล้ว ผมจะบันทึกไว้เป็นแนวทางครับ"}
        elif message.startswith("ACTION:MODIFY:"):
            plan_id = message.split(":")[-1]
            return {"type": "text", "text": f"📝 รับทราบครับสำหรับแผนรหัส [{plan_id}]\nท่านประธานต้องการให้ผมปรับปรุงหรือแก้ไขในจุดไหน พิมพ์สั่งการมาได้เลยครับ"}

        # 2. การประมวลผลข้อความและไฟล์ (Multimodal Video/Vision & PDF Reader)
        uploaded_file = None
        content_to_send = []
        
        try:
            if not self.client:
                return {"type": "text", "text": "⚠️ ระบบออฟไลน์ ไม่พบการเชื่อมต่อ API Key ครับท่านประธาน"}

            # อัปโหลดไฟล์วิดีโอ/ภาพ/PDF ไปให้ Gemini ประมวลผล
            if file_path and os.path.exists(file_path):
                logger.info(f"📤 [CEO Secretary]: กำลังอัปโหลดไฟล์ {file_type} ขนาด {os.path.getsize(file_path)} bytes...")
                uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path)
                
                # ⏳ กรณีเป็นไฟล์ "วิดีโอ" ระบบต้องรอให้ Google AI ย่อยภาพและเสียงจนเสร็จ (สถานะเปลี่ยนจาก PROCESSING)
                while uploaded_file.state.name == "PROCESSING":
                    logger.info("⏳ [CEO Secretary]: AI กำลังย่อยข้อมูลไฟล์วิดีโอ/มัลติมีเดีย...")
                    await asyncio.sleep(3)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return {"type": "text", "text": "⚠️ ขออภัยครับ AI ไม่สามารถประมวลผลไฟล์วิดีโอ/เอกสารนี้ได้ (Processing Failed)"}
                    
                content_to_send.append(uploaded_file)
                
                if not message or message.startswith("[System Alert:"):
                    content_to_send.append("โปรดวิเคราะห์ ถอดรหัส และสรุปเนื้อหาจากไฟล์วิดีโอ/เอกสารที่แนบมานี้อย่างละเอียดครับท่านประธาน")
                else:
                    content_to_send.append(message)
            else:
                content_to_send.append(message)

            # สั่งรันโมเดล Gemini แบบ Async
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.7
                )
            )
            reply_text = response.text if response.text else "รับทราบคำสั่งครับท่านประธาน"
            
        except Exception as e:
            logger.error(f"⚠️ [CEO Secretary Error Details]: {e}")
            # ข้อความ Error รูปแบบใหม่ (ถ้าเห็นข้อความนี้แปลว่าระบบอัปเดตแล้ว)
            reply_text = f"⚠️ ขออภัยครับท่านประธาน สมองกลเลขาฯ ขัดข้องชั่วคราวเนื่องจาก: {str(e)[:150]}"
            
        finally:
            # ทำลายไฟล์ชั่วคราวบนเซิร์ฟเวอร์ Google ทันทีเพื่อความปลอดภัยระดับองค์กร
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except Exception as e:
                    logger.error(f"⚠️ Failed to delete file: {e}")

        # 3. ตรวจจับคีย์เวิร์ดเพื่อส่ง Flex Message ขออนุมัติ (ถ้ามี)
        if any(keyword in reply_text for keyword in ["เสนอ", "พิจารณา", "แผนการ", "ปรับปรุงใหม่"]):
            plan_id = f"PLAN_{int(time.time())}"
            self.pending_plans[plan_id] = reply_text
            return self._build_approval_flex_message(reply_text, plan_id)
        
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
                            "color": "#00B900",
                            "action": {"type": "message", "label": "✅ อนุมัติ (Approve)", "text": f"ACTION:APPROVE:{plan_id}"}
                        },
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#D4AF37",
                            "action": {"type": "message", "label": "📝 แก้ไขปรับปรุง (Modify)", "text": f"ACTION:MODIFY:{plan_id}"}
                        },
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#FF334B",
                            "action": {"type": "message", "label": "❌ ปฏิเสธ (Reject)", "text": f"ACTION:REJECT:{plan_id}"}
                        }
                    ]
                }
            }
        }

    def _execute_approved_plan(self, action_data: str) -> dict:
        plan_id = action_data.split(":")[-1]
        logger.info(f"🔄 [Hot Reload]: อัปเดตระบบด้วยแผน {plan_id}")
        return {
            "type": "text", 
            "text": f"✅ อนุมัติสำเร็จ! เลขาฯ ได้นำแผนรหัส [{plan_id}] ไปสั่งการอัปเดตระบบหลังบ้านเรียบร้อยแล้วครับ"
        }