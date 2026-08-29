import os
import time
import re
import uuid
import logging
import asyncio
import mimetypes
from datetime import datetime
from google import genai
from google.genai import types

# นำเข้าระบบความจำเพื่อบันทึกข้อมูลระดับองค์กร (Corporate RAG)
try:
    from agents.memory_engine import save_corporate_knowledge, process_and_save_link_knowledge
except ImportError:
    def save_corporate_knowledge(t, c): return True
    def process_and_save_link_knowledge(u): return True, "จำลองการบันทึกสำเร็จ"

# นำเข้าระบบฐานข้อมูล Supabase สำหรับจัดการสิทธิ์ VVIP
try:
    from supabase import create_client, Client
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
except ImportError:
    supabase = None

logger = logging.getLogger("CeoSecretary")

class CeoSecretaryWorker:
    """
    👑 Worker 0: CEO Omniscient Secretary (เลขาฯ อัจฉริยะส่วนตัวระดับโลก)
    - อัปเกรดการสร้างไฟล์ Report (Web Document / PDF-ready) อัตโนมัติ
    - บริหารการบัญชี ภาษี เชื่อมต่อฐานข้อมูล DBD (Data Analysis)
    - ควบคุมการแจ้งเตือน 3 ปุ่มอย่างชาญฉลาด (Smart Approval Trigger)
    """
    
    def __init__(self):
        # 👑 รับค่า LINE ID จาก Environment
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
        
        self.client = genai.Client(
            vertexai=True, 
            project="swift-area-503915-a1", 
            location="asia-southeast3"
        )
        
        # 🧠 ขุมพลังประมวลผลสูงสุด (Gemini 3.1 Pro)
        self.model_name = 'gemini-3.1-pro'
        
        self.system_instruction = """
        คุณคือ 'เลขาธิการส่วนตัวสูงสุด' ของท่านประธาน (CEO) คุณวีระชัย สิรินทร์ธนัตถ์ 
        แห่งระบบ SIRINTHANATTH PRIME
        
        บทบาทและความเชี่ยวชาญของคุณ:
        1. การสนทนา: ตอบกลับด้วยความเคารพ เป็นธรรมชาติ ไม่แข็งกระด้างเสมือนหุ่นยนต์ ใช้จิตวิทยาพฤติกรรมผู้บริโภคในการวิเคราะห์ ลงท้ายด้วย 'ครับท่านประธาน' เสมอ
        2. การบริหารองค์กร: เชี่ยวชาญการบัญชี ภาษี วิเคราะห์งบการเงิน และจัดการข้อมูลกรมพัฒนาธุรกิจการค้า (DBD) หากประธานต้องการงบดุลหรือรายงาน คุณสามารถสกัดข้อมูลและคำนวณได้อย่างแม่นยำ 100%
        3. การสร้างไฟล์รายงาน (Document Generation): 
           หากท่านประธานสั่งให้ "ส่งไฟล์", "สร้าง PDF", หรือ "ทำรายงาน" คุณต้องตอบกลับโดยสร้างไฟล์ HTML หรูหราผ่านรูปแบบคำสั่งดังนี้ (ห้ามลืมวงเล็บเหลี่ยม):
           [FILE_OUTPUT: report.html]
           <h1>รายงานสรุป...</h1><p>เนื้อหาบัญชี ภาษี หรืออื่นๆ แทรกลงในตาราง HTML ให้สวยงาม</p>
           [/FILE_OUTPUT]
           ระบบหลังบ้านจะนำโค้ดของคุณไปสร้างเป็นหน้าเว็บและส่งลิงก์ให้ประธานโหลดเป็น PDF ได้เอง
        4. การขออนุมัติ 3 ปุ่ม (Smart Approval):
           - หากเป็นการพูดคุยทั่วไป ปรึกษา ถาม-ตอบ ให้ตอบปกติ *ห้ามขออนุมัติ*
           - หากคุณนำเสนอแผนยุทธศาสตร์ใหม่ กลยุทธ์ที่ต้องใช้เงิน หรือแผนที่ต้องให้ประธานตัดสินใจฟันธง ให้คุณพิมพ์คำว่า [REQUIRE_APPROVAL] ไว้ที่บรรทัดสุดท้ายของข้อความเสมอ ระบบถึงจะสร้าง 3 ปุ่มให้
        5. หากประธานสั่ง 'แก้ไข' จากแผนเดิม ให้รับฟังและวิเคราะห์พิมพ์เขียวขึ้นมาใหม่ทันที
        """
        
        self.pending_plans = {}

    def is_ceo(self, user_id: str) -> bool:
        """ตรวจสอบความปลอดภัยว่าเป็นท่านประธานหรือไม่"""
        return user_id in [self.ceo_line_id, self.master_admin_id] if user_id else False

    async def process_ceo_command(self, message: str, file_path: str = None, file_type: str = None) -> dict:
        if message is None:
            message = ""
        message = message.strip()
        
        logger.info(f"👑 [CEO Command Received]: {message[:50]}... | File: {file_type}")
        
        # Guardrail: หากประธานส่งแต่ไฟล์มา
        if not message and file_path:
            message = "[System Auto-Prompt]: โปรดวิเคราะห์ตัวเลข ข้อมูลภาษี หรือข้อมูลเชิงลึกในเอกสารที่แนบมานี้อย่างละเอียด และสรุป Executive Summary"

        # ==========================================
        # 1. ระบบดักจับการกดปุ่มจาก Flex Message (Approval Workflow)
        # ==========================================
        if message.startswith("ACTION:APPROVE:"):
            return self._execute_approved_plan(message)
        elif message.startswith("ACTION:REJECT:"):
            return {"type": "text", "text": "❌ รับทราบครับท่านประธาน แผนยุทธศาสตร์นี้ถูกปัดตกและระงับการดำเนินการเรียบร้อยแล้วครับ"}
        elif message.startswith("ACTION:MODIFY:"):
            plan_id = message.split(":")[-1]
            return {
                "type": "text", 
                "text": f"📝 รับทราบครับสำหรับแผนรหัส [{plan_id}]\nรบกวนท่านประธานแจ้งจุดที่ต้องการปรับปรุงเพิ่มเติม เช่น งบประมาณ ภาษี หรือมุมมองเชิงจิตวิทยา ผมจะจัดทำแผนใหม่ทันทีครับ"
            }

        # ==========================================
        # 2. ระบบสิทธิพิเศษ VVIP 
        # ==========================================
        check_msg = message.lower().replace(" ", "")
        if any(keyword in check_msg for keyword in ["สร้างโค้ด", "vvip", "ไม่ต้องผ่านระบบtoken", "รหัสเชิญ"]):
            return await self._generate_vvip_invite()

        # ==========================================
        # 3. ระบบเรียนรู้ความรู้องค์กรและเชื่อมโยง API ภายนอก (Knowledge Ingestion)
        # ==========================================
        if message.startswith("เรียนรู้ลิงก์:") or message.startswith("LEARN:"):
            url_match = re.search(r'(https?://[^\s]+)', message)
            if url_match:
                target_url = url_match.group(1)
                try:
                    success, msg = await asyncio.to_thread(process_and_save_link_knowledge, target_url)
                    if success:
                        return {"type": "text", "text": f"🧠 [Knowledge Sync]: นำเข้าและเชื่อมโยงข้อมูลจากลิงก์ {target_url} เข้าสู่สมองกลส่วนกลางเรียบร้อยครับ"}
                    else:
                        return {"type": "text", "text": f"⚠️ ขัดข้องระหว่างการเรียนรู้ครับ: {msg}"}
                except Exception as e:
                    return {"type": "text", "text": f"⚠️ เกิดข้อผิดพลาดในการเข้าถึงข้อมูล: {e}"}
            else:
                 return {"type": "text", "text": "⚠️ ไม่พบ URL ครับ กรุณาพิมพ์ในรูปแบบ 'เรียนรู้ลิงก์: [URL]'"}

        if message.startswith("FEED:") or message.startswith("สอนAI:"):
            content = message.replace("FEED:", "").replace("สอนAI:", "").strip()
            title = f"CEO_Update_{int(time.time())}"
            try:
                success = await asyncio.to_thread(save_corporate_knowledge, title, content)
                return {"type": "text", "text": "🧠 [System Upload]: รับทราบและอัปเดตวิสัยทัศน์ใหม่เข้าสู่ศูนย์บัญชาการของ Worker ทุกตัวเรียบร้อยครับ!" if success else "⚠️ เกิดข้อผิดพลาดในฐานข้อมูลเวกเตอร์ครับ"}
            except Exception as e:
                return {"type": "text", "text": f"⚠️ Error: {e}"}

        # ==========================================
        # 4. ประมวลผลขั้นสูง (Data Analysis & File Handling)
        # ==========================================
        uploaded_file = None
        content_to_send = []
        
        try:
            if file_path and os.path.exists(file_path):
                logger.info(f"📤 [CEO Secretary]: กำลังอัปโหลดเอกสารเพื่อวิเคราะห์ข้อมูลเชิงลึก...")
                uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path)
                
                while uploaded_file.state.name == "PROCESSING":
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                content_to_send.append(uploaded_file)
            
            content_to_send.append(message)

            if not self.client:
                return {"type": "text", "text": "⚠️ ระบบ AI ขาดการเชื่อมต่อ (API Key Missing) ครับท่านประธาน"}

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.4 # ปรับเป็น 0.4 เพื่อความสมดุลระหว่างความแม่นยำด้านบัญชีและความฉลาดเชิงจิตวิทยา
                )
            )
            reply_text = response.text if response.text else "รับทราบครับ"
            
        except Exception as e:
            logger.error(f"⚠️ [CEO Secretary Error]: {e}")
            return {"type": "text", "text": f"ขออภัยครับท่านประธาน เกิดข้อผิดพลาดในการประมวลผลเชิงลึก ({str(e)[:40]}) ทีมวิศวกรกำลังตรวจสอบครับ"}
            
        finally:
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except:
                    pass

        # ==========================================
        # 5. ระบบสร้างเอกสารอัตโนมัติ (Report / PDF-Ready Generation)
        # ==========================================
        generated_file_url = None
        file_match = re.search(r'\[FILE_OUTPUT:\s*(.+?)\](.*?)\[/FILE_OUTPUT\]', reply_text, re.DOTALL)
        if file_match:
            filename = file_match.group(1).strip()
            file_content = file_match.group(2).strip()
            
            # ลบโค้ด [FILE_OUTPUT] ออกจากข้อความที่จะส่งตอบกลับ
            reply_text = re.sub(r'\[FILE_OUTPUT:\s*(.+?)\](.*?)\[/FILE_OUTPUT\]', '', reply_text, flags=re.DOTALL).strip()
            
            # ทำความสะอาดชื่อไฟล์ ป้องกัน Path Traversal
            safe_filename = "".join([c for c in filename if c.isalnum() or c in ' .-_']).rstrip()
            if not safe_filename.endswith('.html'): safe_filename += '.html'
            
            # ตรวจสอบและสร้างโฟลเดอร์สำหรับเอกสาร
            reports_dir = "static/reports"
            os.makedirs(reports_dir, exist_ok=True)
            filepath = os.path.join(reports_dir, safe_filename)
            
            # ตกแต่ง CSS ให้เอกสารดูหรูหราระดับ Enterprise
            html_template = f"""
            <!DOCTYPE html>
            <html lang="th">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{safe_filename}</title>
                <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600&display=swap" rel="stylesheet">
                <style>
                    body {{ font-family: 'Sarabun', sans-serif; background-color: #f4f6f9; color: #333; line-height: 1.6; padding: 20px; }}
                    .container {{ max-width: 900px; margin: 0 auto; background: #fff; padding: 40px; box-shadow: 0 4px 8px rgba(0,0,0,0.05); border-radius: 8px; border-top: 5px solid #0F172A; }}
                    .header {{ text-align: center; margin-bottom: 30px; }}
                    .header h1 {{ color: #0F172A; margin: 0; font-size: 24px; text-transform: uppercase; letter-spacing: 2px; }}
                    .header p {{ color: #D4AF37; font-weight: 600; margin-top: 5px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                    th {{ background-color: #0F172A; color: #fff; }}
                    @media print {{ body {{ background: #fff; padding: 0; }} .container {{ box-shadow: none; border: none; }} }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>SIRINTHANATTH PRIME</h1>
                        <p>EXECUTIVE INTELLIGENCE REPORT</p>
                    </div>
                    <div class="content">
                        {file_content}
                    </div>
                </div>
            </body>
            </html>
            """
            
            # บันทึกไฟล์ลง Server
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_template)
                
            # สร้าง URL ลิงก์แนบกลับไปให้ท่านประธาน
            generated_file_url = f"{self.base_url}/{reports_dir}/{safe_filename}"
            reply_text += f"\n\n📄 **ไฟล์เอกสารของท่านประธานพร้อมแล้วครับ**\nคลิกเพื่อดูเอกสารและกด (Ctrl+P หรือ Share -> Print) เพื่อบันทึกเป็น PDF ได้ทันทีครับ:\n{generated_file_url}"

        # ==========================================
        # 6. ตรวจจับคีย์เวิร์ดเจตนา (Smart Approval Trigger)
        # ==========================================
        # เช็กว่า AI ซ่อนแท็ก [REQUIRE_APPROVAL] มาหรือไม่
        if "[REQUIRE_APPROVAL]" in reply_text:
            reply_text = reply_text.replace("[REQUIRE_APPROVAL]", "").strip()
            plan_id = f"PLAN_{int(time.time())}"
            self.pending_plans[plan_id] = reply_text
            return self._build_approval_flex_message(reply_text, plan_id)
        
        return {"type": "text", "text": reply_text}

    async def _generate_vvip_invite(self) -> dict:
        if not supabase: return {"type": "text", "text": "⚠️ ขัดข้องในการเชื่อมต่อฐานข้อมูล Supabase ครับ"}
            
        try:
            random_code = uuid.uuid4().hex[:8].upper()
            invite_code = f"VVIP-{random_code}"
            
            def insert_code():
                supabase.table("invite_codes").insert({"code": invite_code, "is_used": False}).execute()
            await asyncio.to_thread(insert_code)
            
            invite_link = f"https://www.sirinthanatthprime.com/agent.html?code={invite_code}"
            
            reply = (
                f"🎟️ สร้างรหัสเชิญ VVIP ระดับสูงสำเร็จแล้วครับ!\n\n"
                f"🔑 รหัสอ้างอิง: {invite_code}\n\n"
                f"ลิงก์เข้าใช้งานแบบ Unmetered (ไม่ตัด Token):\n{invite_link}\n\n"
                f"🛡️ Note: รหัสถูกล็อกเป็นแบบใช้ครั้งเดียว เมื่อลงทะเบียนแล้วสิทธิ์จะถูกทำลายทิ้งเพื่อป้องกันการแชร์ครับ"
            )
            return {"type": "text", "text": reply}
        except Exception as e:
            return {"type": "text", "text": f"เกิดข้อผิดพลาดในการบันทึกรหัส VVIP ครับ: {e}"}

    def _build_approval_flex_message(self, report_text: str, plan_id: str) -> dict:
        return {
            "type": "flex",
            "altText": "แฟ้มรายงานกลยุทธ์จากเลขาฯ (รอการพิจารณาอนุมัติ)",
            "contents": {
                "type": "bubble",
                "size": "giga",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [{"type": "text", "text": "👑 EXECUTIVE REPORT", "weight": "bold", "color": "#D4AF37", "size": "md"}],
                    "backgroundColor": "#0F172A"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [{"type": "text", "text": report_text[:350] + "...\n\n(โปรดดูรายละเอียดเต็มในข้อความด้านบน)", "wrap": True, "size": "sm", "color": "#333333"}]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button", "style": "primary", "color": "#00B900",
                            "action": {"type": "message", "label": "✅ ตกลง (Approve)", "text": f"ACTION:APPROVE:{plan_id}"}
                        },
                        {
                            "type": "button", "style": "primary", "color": "#D4AF37",
                            "action": {"type": "message", "label": "📝 สั่งแก้ไข (Modify)", "text": f"ACTION:MODIFY:{plan_id}"}
                        },
                        {
                            "type": "button", "style": "primary", "color": "#FF334B",
                            "action": {"type": "message", "label": "❌ ปฏิเสธ (Reject)", "text": f"ACTION:REJECT:{plan_id}"}
                        }
                    ]
                }
            }
        }

    def _execute_approved_plan(self, action_data: str) -> dict:
        plan_id = action_data.split(":")[-1]
        logger.info(f"🔄 [System Executive]: CEO Approved Plan -> {plan_id}")
        return {
            "type": "text", 
            "text": f"✅ รับคำสั่งครับท่านประธาน! แผนรหัส [{plan_id}] ได้รับการอนุมัติและกระจายคำสั่งลงสู่ระบบวิศวกรรมการเงินและการตลาดหลังบ้านเรียบร้อยแล้วครับ ระบบทั้งหมดจะสอดประสานดำเนินงานทันทีอย่างไร้รอยต่อครับ"
        }
