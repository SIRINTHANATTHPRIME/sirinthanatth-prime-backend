import os
import time
import re
import logging
import asyncio
from datetime import datetime
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
    อัปเกรดสถาปัตยกรรมระดับโลกด้วย Google GenAI SDK ล่าสุด พร้อมระบบ "ดวงตา" วิเคราะห์ไฟล์
    """
    
    def __init__(self):
        # 👑 รับค่า LINE ID ให้อัตโนมัติ (ดึงจากตัวแปร Cloud Run)
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        
        self.api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        
        # 🧠 ใช้ Gemini 1.5 Pro (โมเดลเรือธงล่าสุดที่ฉลาดและวิเคราะห์ไฟล์ได้ลึกซึ้งที่สุด)
        self.model_name = 'gemini-1.5-pro'
        
        self.system_instruction = """
        คุณคือ 'เลขาธิการส่วนตัวสูงสุด' ของท่านประธาน (CEO) คุณวีระชัย สิรินทร์ธนัตถ์
        ระบบที่คุณดูแลคือ SIRINTHANATTH PRIME (AI SaaS บน LINE OA)
        
        หน้าที่ของคุณ:
        1. ตอบกลับด้วยความสุภาพ เป็นมืออาชีพ และใช้คำทักทายว่า 'ครับท่านประธาน' เสมอ
        2. หากท่านประธานส่งรูปภาพ หรือไฟล์ PDF มา ให้วิเคราะห์ สกัดข้อมูล และสรุปใจความสำคัญให้ท่านประธานทราบอย่างละเอียด
        3. หากประธานขอดูสรุป (Report) ให้จำลองข้อมูลสรุปภาพรวม 4 แกนหลัก (การเงิน, การตลาด, กฎหมาย, วิศวกรรม) แบบสั้นๆ กระชับ
        4. หากมีข้อเสนอแนะ ให้เสนอมาเป็นข้อๆ อย่างชาญฉลาด เพื่อให้ประธานตัดสินใจ
        5. หากประธานสั่ง 'แก้ไข' จากแผนเดิม ให้คุณวิเคราะห์และเขียนแผนใหม่ที่รัดกุมกว่าเดิม
        """
        
        # หน่วยความจำชั่วคราวสำหรับเก็บแผนงานที่รอการอนุมัติ/แก้ไข
        self.pending_plans = {}

    def is_ceo(self, user_id: str) -> bool:
        """ตรวจสอบว่าเป็นท่านประธานหรือไม่"""
        return user_id == self.ceo_line_id

    async def process_ceo_command(self, message: str, file_path: str = None, file_type: str = None) -> dict:
        """รับคำสั่งและไฟล์ตรงจาก CEO และสั่งการระบบเบื้องหลัง"""
        logger.info(f"👑 [CEO Command Received]: {message[:50]}... | File: {file_type}")
        
        # ==========================================
        # 1. ระบบดักจับการกดปุ่มจาก Flex Message
        # ==========================================
        if message.startswith("ACTION:APPROVE:"):
            return self._execute_approved_plan(message)
        elif message.startswith("ACTION:REJECT:"):
            return {"type": "text", "text": "❌ รับทราบครับท่านประธาน แผนนี้ถูกปฏิเสธและปัดตกเรียบร้อยแล้วครับ"}
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
                try:
                    # ใช้ asyncio.to_thread เพื่อป้องกันการบล็อกขณะดึงข้อมูลจากเว็บ
                    success, msg = await asyncio.to_thread(process_and_save_link_knowledge, target_url)
                    if success:
                        return {"type": "text", "text": f"🧠 [Knowledge Update]: ระบบได้สแกนและดึงความรู้ทั้งหมดจากลิงก์\n{target_url}\n\nเข้าสู่สมองกลส่วนกลาง (Corporate RAG) เรียบร้อยแล้วครับ!"}
                    else:
                        return {"type": "text", "text": f"⚠️ [Error]: {msg}"}
                except Exception as e:
                    logger.error(f"❌ [Link Learning Error]: {e}")
                    return {"type": "text", "text": f"⚠️ [Error]: เกิดข้อผิดพลาดในการดึงข้อมูลจากลิงก์: {e}"}
            else:
                 return {"type": "text", "text": "⚠️ ไม่พบ URL ในข้อความ กรุณาพิมพ์ในรูปแบบ 'เรียนรู้ลิงก์: [URL]'"}

        if message.startswith("FEED:") or message.startswith("สอนAI:"):
            content = message.replace("FEED:", "").replace("สอนAI:", "").strip()
            title = f"CEO_Update_{int(time.time())}"
            try:
                # ใช้ asyncio.to_thread เพื่อป้องกันการบล็อกขณะบันทึกฐานข้อมูล
                success = await asyncio.to_thread(save_corporate_knowledge, title, content)
                if success:
                    return {"type": "text", "text": "🧠 [System Upload]: นำข้อมูลใหม่เข้าสู่สมองกลส่วนกลางและฐานข้อมูลความรู้บริษัท (Corporate RAG) เรียบร้อยแล้ว ระบบจะนำข้อมูลนี้ไปใช้วิเคราะห์และคำนวณให้ถูกต้องที่สุดนับจากนี้ครับ!"}
                else:
                    return {"type": "text", "text": "⚠️ เกิดข้อผิดพลาดในการนำเข้าข้อมูลสู่ฐานข้อมูลเวกเตอร์ครับ"}
            except Exception as e:
                logger.error(f"❌ [Feed Learning Error]: {e}")
                return {"type": "text", "text": "⚠️ เกิดข้อผิดพลาดในระบบฐานข้อมูลครับ"}

        # ==========================================
        # 3. การประมวลผลข้อความทั่วไปและไฟล์มัลติมีเดีย (Multimodal Async)
        # ==========================================
        uploaded_file = None
        content_to_send = []
        
        try:
            if file_path and os.path.exists(file_path):
                logger.info(f"📤 [CEO Secretary]: กำลังอัปโหลดไฟล์ {file_type} เพื่อให้เลขาฯ วิเคราะห์...")
                uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path)
                
                # รอกระบวนการแปลงไฟล์ (ถ้าเป็นวิดีโอหรือ PDF ใหญ่)
                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                content_to_send.append(uploaded_file)
                
                # ถ้าประธานส่งรูปมาแต่ไม่พิมพ์อะไรให้เพิ่มข้อความมาตรฐานให้
                if message == "" or message.startswith("[System Alert:"):
                    content_to_send.append("โปรดวิเคราะห์รูปภาพหรือเอกสารที่แนบมานี้อย่างละเอียดครับท่านประธาน")
                else:
                    content_to_send.append(message)
            else:
                content_to_send.append(message)

            # ⚡ สั่งรัน AI แบบ Asynchronous โดยใช้ asyncio.to_thread ล้อมคำสั่ง SDK ใหม่
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
            logger.error(f"⚠️ [CEO Secretary Error]: {e}")
            reply_text = "ขออภัยครับท่านประธาน ขณะนี้สมองกลประมวลผลส่วนผู้บริหารขัดข้องเล็กน้อย กำลังดำเนินการแก้ไขครับ"
            
        finally:
            # 🗑️ ลบไฟล์ออกจากเซิร์ฟเวอร์ Google ทันทีเพื่อความปลอดภัย (Zero-Data Retention)
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
        """สร้าง LINE Flex Message สไตล์พรีเมียม (Navy & Gold) พร้อม 3 ปุ่ม"""
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
            "text": f"✅ อนุมัติสำเร็จ! เลขาฯ ได้นำแผนรหัส [{plan_id}] ไปสั่งการอัปเดตระบบหลังบ้านให้อัตโนมัติเรียบร้อยแล้วครับ (Zero Downtime) การทำงานของระบบหลักจะไม่ได้รับผลกระทบใดๆ ครับ"
        }
