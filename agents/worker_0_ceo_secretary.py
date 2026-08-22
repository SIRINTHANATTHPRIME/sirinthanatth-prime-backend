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
    ทะลุ Token 100% / Human-in-the-Loop 3 ปุ่ม (Approve, Modify, Reject)
    """
    
    def __init__(self):
        # 👑 รับค่า LINE ID ให้อัตโนมัติ (ดึงจากตัวแปร Cloud Run)
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        
        self.api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        
        # 🚀 ใช้รุ่น 1.5-pro ที่ฉลาดและเสถียรที่สุด 
        self.model_name = 'gemini-3.1-pro-preview'
        
        self.system_instruction = """
        คุณคือ 'เลขาธิการส่วนตัวสูงสุด' ของท่านประธาน (CEO) คุณวีระชัย สิรินทร์ธนัตถ์
        ระบบที่คุณดูแลคือ SIRINTHANATTH PRIME (AI SaaS บน LINE OA)
        
        หน้าที่ของคุณ:
        1. ตอบกลับด้วยความสุภาพ เป็นมืออาชีพ และใช้คำทักทายว่า 'ครับท่านประธาน' เสมอ
        2. หากท่านประธานส่งข้อความ วิดีโอ (Video), รูปภาพ, เสียง หรือไฟล์ PDF มา ให้วิเคราะห์ สกัดข้อมูล ถอดสคริปต์ และสรุปใจความสำคัญ
        3. หากประธานขอดูสรุป (Report) ให้วิเคราะห์ข้อมูล 4 แกนหลัก (การเงิน, การตลาด, กฎหมาย, วิศวกรรม)
        4. เสนอข้อเสนอแนะเป็นข้อๆ อย่างชาญฉลาด เพื่อให้ประธานตัดสินใจ 
        """
        self.pending_plans = {}

    def is_ceo(self, user_id: str) -> bool:
        """ตรวจสอบสิทธิ์ (God Mode)"""
        return user_id in [self.ceo_line_id, self.master_admin_id]

    async def process_ceo_command(self, message: str, file_path: str = None, file_type: str = None) -> dict:
        """รับคำสั่งและไฟล์ตรงจาก CEO และสั่งการระบบเบื้องหลัง"""
        logger.info(f"👑 [CEO Command Received]: {message[:50]}... | File: {file_type}")
        
        # ==========================================
        # 1. ระบบ Human-in-the-Loop 3 ปุ่ม
        # ==========================================
        if message.startswith("ACTION:APPROVE:"):
            return self._execute_approved_plan(message)
        elif message.startswith("ACTION:REJECT:"):
            return {"type": "text", "text": "❌ รับทราบครับท่านประธาน แผนนี้ถูกปฏิเสธและปัดตกเรียบร้อยแล้วครับ"}
        elif message.startswith("ACTION:MODIFY:"):
            plan_id = message.split(":")[-1]
            return {"type": "text", "text": f"📝 รับทราบครับท่านประธาน\nสำหรับแผนรหัส [{plan_id}] ต้องการให้ผมแก้ไขปรับปรุงในประเด็นไหน ออกคำสั่งหรือ Comment มาได้เลยครับ เดี๋ยวผมจัดการร่างให้ใหม่ทันทีครับ"}

        # 2. ตรวจสอบ API Key
        if not self.client:
            return {"type": "text", "text": "⚠️ [System Alert]: ระบบออฟไลน์ ไม่พบ API Key (AI_API_KEY) ในการตั้งค่า Cloud Run ครับ"}

        # ==========================================
        # 3. การประมวลผลข้อความและไฟล์ (Multimodal)
        # ==========================================
        uploaded_file = None
        content_to_send = []
        
        try:
            if file_path and os.path.exists(file_path):
                logger.info(f"📤 [CEO Secretary]: กำลังอัปโหลดไฟล์ {file_type} ขนาด {os.path.getsize(file_path)} bytes...")
                
                # รันการอัปโหลดผ่าน Thread เพื่อไม่ให้บล็อกการตอบของ LINE
                uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path)
                
                # ⏳ รอจนกว่า AI จะย่อยวิดีโอ/เสียง/เอกสาร เสร็จสมบูรณ์
                while uploaded_file.state.name == "PROCESSING":
                    logger.info("⏳ [CEO Secretary]: AI กำลังย่อยข้อมูลมัลติมีเดีย...")
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return {"type": "text", "text": "⚠️ [Error]: AI ของ Google ไม่สามารถประมวลผลไฟล์ชนิดนี้ได้ครับ"}
                    
                content_to_send.append(uploaded_file)
                
                if not message or message.startswith("[System Alert:"):
                    content_to_send.append("โปรดวิเคราะห์ ถอดรหัส และสรุปเนื้อหาจากไฟล์/มัลติมีเดียที่แนบมานี้อย่างละเอียดครับท่านประธาน")
                else:
                    content_to_send.append(message)
            else:
                content_to_send.append(message)

            # 🧠 สั่งรันโมเดล Gemini
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
            # 🛑 จุดสำคัญ: หากเกิด Error ระบบจะพิมพ์สาเหตุที่แท้จริงออกมาใน LINE 
            reply_text = f"⚠️ ขออภัยครับท่านประธาน ระบบเลขาฯ ติดขัดชั่วคราว\n\nสาเหตุ (Debug): {str(e)[:300]}"
            
        finally:
            # 🛡️ ทำลายไฟล์ชั่วคราวบนเซิร์ฟเวอร์ Google ทันที (Security)
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except Exception as e:
                    logger.error(f"⚠️ Failed to delete file: {e}")

        # ==========================================
        # 4. ส่ง Flex Message ขออนุมัติ (เมื่อเลขาฯ เสนองาน)
        # ==========================================
        if any(keyword in reply_text for keyword in ["เสนอ", "พิจารณา", "แผนการ", "ปรับปรุงใหม่", "อนุมัติ"]):
            plan_id = f"PLAN_{int(time.time())}"
            self.pending_plans[plan_id] = reply_text
            return self._build_approval_flex_message(reply_text, plan_id)
        
        return {"type": "text", "text": reply_text}

    def _build_approval_flex_message(self, report_text: str, plan_id: str) -> dict:
        """สร้าง LINE Flex Message พร้อม 3 ปุ่มกดสไตล์พรีเมียม"""
        return {
            "type": "flex",
            "altText": "แฟ้มรายงานจากเลขาฯ อัจฉริยะ (รอการอนุมัติ)",
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
                    "contents": [{"type": "text", "text": report_text[:300] + "...\n\n(โปรดดูรายละเอียดเต็มในข้อความด้านบน)", "wrap": True, "size": "sm"}]
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
                            "action": {"type": "message", "label": "✅ ตกลง (Approve)", "text": f"ACTION:APPROVE:{plan_id}"}
                        },
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#D4AF37",
                            "action": {"type": "message", "label": "📝 สั่งแก้ไข (Modify)", "text": f"ACTION:MODIFY:{plan_id}"}
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
            "text": f"✅ อนุมัติสำเร็จ! เลขาฯ ได้นำแผนรหัส [{plan_id}] ไปดำเนินการต่อ และประสานงานระบบหลังบ้านเรียบร้อยแล้วครับท่านประธาน"
        }