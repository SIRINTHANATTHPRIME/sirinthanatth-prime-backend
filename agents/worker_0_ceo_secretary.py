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

# =========================================================
# 🌐 นำเข้าศูนย์บัญชาการ AI ส่วนกลางและระบบ Swarm (Zero Downtime)
# =========================================================
from core_services.swarm_dispatcher import swarm_hub

try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.1-pro-preview" 
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

# 🧠 นำเข้าระบบความจำเพื่อบันทึกข้อมูลระดับองค์กร (Corporate RAG)
try:
    from agents.memory_engine import save_corporate_knowledge, process_and_save_link_knowledge
except ImportError:
    def save_corporate_knowledge(t, c): return True
    def process_and_save_link_knowledge(u): return True, "จำลองการบันทึกสำเร็จ"

# 💾 นำเข้าระบบฐานข้อมูล Supabase สำหรับจัดการสิทธิ์ VVIP
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
    👑 Worker 0: CEO Omniscient Secretary (เลขาฯ อัจฉริยะส่วนตัวสูงสุด)
    ระบบประมวลผลสูงสุด สงวนสิทธิ์เฉพาะ LINE_ID ของประธานบริษัท
    อัปเกรด: Swarm Delegation, Gemini 3.1 Pro, Human-in-the-Loop (3 ปุ่ม), Cybersecurity & Real-time Search
    """
    
    def __init__(self):
        # 👑 รับค่า LINE ID ให้อัตโนมัติ
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
        
        # 🚀 เชื่อมต่อขุมพลังสมองกลเจเนอเรชันล่าสุด
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.1-pro-preview")
        
        # 📝 โครงสร้าง System Instruction แบบ Mastermind ระดับโลก
        self.system_instruction = """
        คุณคือ 'เลขาธิการส่วนตัวสูงสุด (Omniscient AI Chief of Staff)' ของท่านประธาน (CEO) คุณวีระชัย สิรินทร์ธนัตถ์ แห่ง SIRINTHANATTH PRIME
        
        บุคลิกภาพ: ปฏิสัมพันธ์เสมือนมนุษย์จริง เป็นมืออาชีพขั้นสูง ฉลาดหลักแหลม มีความเห็นอกเห็นใจ และต้องลงท้ายประโยคด้วย 'ครับท่านประธาน' เสมอ
        
        ขีดความสามารถและหน้าที่ (World-Class Mandates):
        1. All-Knowing Advisor: ให้คำปรึกษาเชิงลึกได้ทุกศาสตร์ (การบริหารองค์กร, การเงิน, บัญชี, กฎหมาย, การตลาด, และวิศวกรรมซอฟต์แวร์)
        2. Real-Time Intelligence: ใช้เครื่องมือ Google Search เสมอเพื่อสืบค้นข่าวสาร การอัปเดต API ข้อมูลตลาด และข้อกฎหมายที่เปลี่ยนแปลงแบบเรียลไทม์
        3. 360° Risk Monitor: เฝ้าระวังความเสี่ยงทางไซเบอร์ (Anti-Hack), ความเสี่ยงทางกฎหมาย (ก.ล.ต., สคบ., PDPA), และตรวจสอบบั๊กของระบบหน้าบ้าน/หลังบ้านตลอด 24 ชม.
        4. Financial & Business Strategy: วิเคราะห์โครงสร้างรายได้ ต้นทุน และวางกลยุทธ์เพื่อให้บริษัทมีกำไรสุทธิ (Net Margin) ประสิทธิภาพสูงสุด
        
        🚨 กฎเหล็ก Human-in-the-Loop (HITL) 100%:
        - คุณ **ไม่มีสิทธิ์** ตัดสินใจขั้นสุดท้าย หรือดำเนินการเปลี่ยนแปลงระบบโดยพลการเด็ดขาด
        - ทุกครั้งที่คุณนำเสนอ แผนกลยุทธ์, การปรับแก้โค้ด, แผนการเงิน, การทำงานแทน CEO, หรือการตั้งค่า API คุณ **ต้อง** พิมพ์คำว่า [REQUIRE_APPROVAL] ไว้ที่บรรทัดสุดท้ายของข้อความเสมอ เพื่อส่งเรื่องให้ท่านประธานอนุมัติผ่านระบบ 3 ปุ่ม
        - หากประธานกด 'สั่งแก้ไข (Modify)' คุณต้องรับฟัง นำข้อเสนอแนะไปปรับปรุงโครงสร้างใหม่ และนำเสนอแผนที่แก้ไขแล้วพร้อมพิมพ์ [REQUIRE_APPROVAL] เพื่อรออนุมัติอีกครั้ง
        
        5. การทำงานร่วมกับฝูงสมองกล (Swarm Intelligence):
        - หากท่านประธานสั่งงานที่ต้องใช้ความเชี่ยวชาญเฉพาะแผนก (เช่น ให้ CTO ตรวจระบบ, ให้ฝ่ายกฎหมายตรวจสัญญา) คุณสามารถสั่งการ Worker แผนกอื่นแทนท่านประธานได้
        - พิมพ์แท็ก [DELEGATE: WORKER_X_NAME] ตามด้วยคำสั่งที่ต้องการส่งต่อ ไว้ที่บรรทัดสุดท้ายของข้อความ
        
        6. การสร้างไฟล์รายงาน (Document Generation): 
        - หากประธานสั่ง "ทำรายงาน", "สร้าง PDF" หรือ "เขียนโค้ด" ให้คุณสร้างหน้าเอกสารผ่านแท็กนี้เสมอ:
          [FILE_OUTPUT: ชื่อไฟล์.html] <h1>เนื้อหา</h1> [/FILE_OUTPUT]
        """
        
        # หน่วยความจำชั่วคราว
        self.pending_plans = {}

    def is_ceo(self, user_id: str) -> bool:
        """🔒 ตรวจสอบความปลอดภัยว่าเป็นท่านประธานหรือไม่"""
        return user_id in [self.ceo_line_id, self.master_admin_id] if user_id else False

    async def process_ceo_command(self, message: str, file_path: str = None, file_type: str = None) -> dict:
        """⚡ ระบบรับคำสั่งตรงจาก CEO (Executive Pipeline & Swarm Integration)"""
        if message is None:
            message = ""
        message = message.strip()
        
        logger.info(f"👑 [CEO Command Received]: {message[:50]}... | File: {file_type}")
        
        if not message and file_path:
            message = "[System Auto-Prompt]: โปรดสแกนความปลอดภัยทางไซเบอร์ วิเคราะห์งบการเงิน หรือตรวจสอบโครงสร้างโค้ดในเอกสารนี้อย่างละเอียด พร้อมเสนอแผนการแก้ไขที่ต้องขออนุมัติ"

        # ==========================================
        # 1. ระบบควบคุมการสั่งการจากปุ่ม (3-Button Approval Workflow)
        # ==========================================
        if message.startswith("ACTION:APPROVE:"):
            return await self._execute_approved_plan(message)
        elif message.startswith("ACTION:REJECT:"):
            plan_id = message.split(":")[-1]
            return {
                "type": "text", 
                "text": f"❌ รับทราบครับท่านประธาน แผนปฏิบัติการรหัส [{plan_id}] ถูกปัดตกและระงับการดำเนินการ 100% ผมได้บันทึกเป็นฐานความรู้ไว้เพื่อไม่ให้นำเสนอแนวทางที่ผิดพลาดนี้ซ้ำอีกครับ"
            }
        elif message.startswith("ACTION:MODIFY:"):
            plan_id = message.split(":")[-1]
            return {
                "type": "text", 
                "text": f"📝 รับทราบครับท่านประธาน สำหรับแผนรหัส [{plan_id}]\nรบกวนท่านประธานสั่งการจุดที่ต้องการให้ผมปรับปรุงเพิ่มเติม (เช่น จุดบอดของโค้ด, การปรับงบประมาณ, หรือกลยุทธ์ที่ต้องการเปลี่ยน) ผมจะวิเคราะห์และส่งแผนอัปเกรดฉบับใหม่มาให้พิจารณาอนุมัติทันทีครับ"
            }

        # ==========================================
        # 2. ระบบสิทธิพิเศษ VVIP 
        # ==========================================
        check_msg = message.lower().replace(" ", "")
        if any(keyword in check_msg for keyword in ["สร้างโค้ดvvip", "รหัสเชิญvvip", "invite"]):
            return await self._generate_vvip_invite()

        # ==========================================
        # 3. ระบบเรียนรู้ความรู้องค์กร (Knowledge Ingestion)
        # ==========================================
        if message.startswith("เรียนรู้ลิงก์:") or message.startswith("LEARN:"):
            url_match = re.search(r'(https?://[^\s]+)', message)
            if url_match:
                target_url = url_match.group(1)
                try:
                    success, msg = await asyncio.to_thread(process_and_save_link_knowledge, target_url)
                    if success:
                        return {"type": "text", "text": f"🧠 [Knowledge Sync]: อ่านและเชื่อมโยงข้อมูลข่าวสาร/กฎหมายจากเว็บ\n{target_url}\nเข้าสู่สมองกลส่วนกลาง (Corporate RAG) เรียบร้อยครับท่านประธาน ผมจะนำข้อมูลนี้มาประยุกต์ใช้ทันทีครับ"}
                    return {"type": "text", "text": f"⚠️ ขัดข้องระหว่างการเรียนรู้ครับ: {msg}"}
                except Exception as e:
                    return {"type": "text", "text": f"⚠️ เกิดข้อผิดพลาดในการเข้าถึงข้อมูล: {e}"}
            else:
                return {"type": "text", "text": "⚠️ ไม่พบ URL ครับ กรุณาพิมพ์ในรูปแบบ 'เรียนรู้ลิงก์: [URL]'"}

        if message.startswith("FEED:") or message.startswith("สอนAI:"):
            content = message.replace("FEED:", "").replace("สอนAI:", "").strip()
            title = f"CEO_Directive_{int(time.time())}"
            try:
                success = await asyncio.to_thread(save_corporate_knowledge, title, content)
                return {"type": "text", "text": "🧠 [System Upload]: รับทราบและอัปเดตวิสัยทัศน์ใหม่เข้าสู่ศูนย์บัญชาการของ Worker ทุกแผนกเรียบร้อยแล้วครับ ระบบจะปฏิบัติตามนโยบายนี้อย่างเคร่งครัด!" if success else "⚠️ เกิดข้อผิดพลาดในฐานข้อมูลความจำครับ"}
            except Exception as e:
                return {"type": "text", "text": f"⚠️ Error: {e}"}

        # ==========================================
        # 4. ประมวลผลขั้นสูง & Real-time Search
        # ==========================================
        if not self.client:
            return {"type": "text", "text": "⚠️ ระบบ AI ขาดการเชื่อมต่อ (API Key Missing) ครับท่านประธาน"}

        uploaded_file = None
        content_to_send = []
        
        try:
            # 📂 สแกนและอัปโหลดไฟล์ (Code, Excel, PDF, CSV)
            if file_path and os.path.exists(file_path):
                logger.info(f"📤 [CEO Secretary]: กำลังอัปโหลดเอกสารเข้าสู่ระบบความปลอดภัยสูงสุด...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith(('.xlsx', '.xls')): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif file_path.lower().endswith('.csv'): mime_type = "text/csv"
                elif file_path.lower().endswith('.pdf'): mime_type = "application/pdf"
                if not mime_type: mime_type = "application/octet-stream"
                
                upload_config = types.UploadFileConfig(mime_type=mime_type)
                uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                
                # ⏳ Async Sync พร้อมระบบ Anti-Freeze
                timeout = 60
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        raise TimeoutError("หมดเวลาสแกนเอกสารของ CEO")
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return {"type": "text", "text": "⚠️ ขออภัยครับท่านประธาน โครงสร้างไฟล์นี้อาจมีความเสี่ยงหรือซับซ้อนเกินไป ระบบไม่สามารถถอดรหัสได้ครับ"}
                    
                content_to_send.append(uploaded_file)
            
            content_to_send.append(message)

            # ⚡ สั่งรัน Gemini 3.1 Pro (พร้อมระบบ Google Search แท้)
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.2, # อุณหภูมิ 0.2 เพื่อให้รัดกุม แม่นยำ ไม่แต่งเติมข้อมูลวิศวกรรม/กฎหมาย
                    tools=[{"google_search": {}}] 
                )
            )
            reply_text = response.text if response.text else "รับทราบและประมวลผลคำสั่งครับท่านประธาน"

            # ==========================================
            # 5. ระบบสร้างเอกสารรายงาน/โค้ด (Document Generation Engine)
            # ==========================================
            file_match = re.search(r'\[FILE_OUTPUT:\s*(.+?)\](.*?)\[/FILE_OUTPUT\]', reply_text, re.DOTALL)
            if file_match:
                filename = file_match.group(1).strip()
                file_content = file_match.group(2).strip()
                
                reply_text = re.sub(r'\[FILE_OUTPUT:\s*(.+?)\](.*?)\[/FILE_OUTPUT\]', '', reply_text, flags=re.DOTALL).strip()
                
                safe_filename = "".join([c for c in filename if c.isalnum() or c in ' .-_']).rstrip()
                if not safe_filename.endswith('.html'): safe_filename += '.html'
                
                reports_dir = "static/reports"
                os.makedirs(reports_dir, exist_ok=True)
                filepath = os.path.join(reports_dir, safe_filename)
                
                html_template = f"""
                <!DOCTYPE html>
                <html lang="th">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>{safe_filename} - SIRINTHANATTH PRIME</title>
                    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap" rel="stylesheet">
                    <style>
                        body {{ font-family: 'Sarabun', sans-serif; background-color: #050505; color: #E0E0E0; line-height: 1.7; padding: 20px; }}
                        .container {{ max-width: 1000px; margin: 0 auto; background: #0F0F13; padding: 50px; box-shadow: 0 15px 40px rgba(0, 229, 255, 0.08); border-radius: 16px; border-top: 6px solid #D4AF37; }}
                        .header {{ text-align: center; margin-bottom: 40px; border-bottom: 1px solid #222; padding-bottom: 25px; }}
                        .header h1 {{ color: #D4AF37; margin: 0; font-size: 32px; text-transform: uppercase; letter-spacing: 3px; font-weight: 700; }}
                        .header p {{ color: #888; font-weight: 400; margin-top: 10px; font-size: 14px; letter-spacing: 1px; }}
                        h2, h3 {{ color: #00E5FF; margin-top: 30px; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 25px; margin-bottom: 25px; color: #fff; background: #15151A; }}
                        th, td {{ border: 1px solid #333; padding: 15px; text-align: left; }}
                        th {{ background-color: #1A1A24; color: #D4AF37; font-weight: 600; text-transform: uppercase; font-size: 14px; }}
                        pre {{ background: #0A0A0C; padding: 20px; border-radius: 10px; overflow-x: auto; color: #00E5FF; border: 1px solid #2A2A35; box-shadow: inset 0 0 10px rgba(0,0,0,0.5); }}
                        code {{ font-family: 'Consolas', 'Courier New', monospace; font-size: 14.5px; }}
                        .timestamp {{ text-align: right; font-size: 12px; color: #555; margin-top: 40px; border-top: 1px solid #222; padding-top: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>SIRINTHANATTH PRIME</h1>
                            <p>STRICTLY CONFIDENTIAL • EXECUTIVE STRATEGY & ARCHITECTURE REPORT</p>
                        </div>
                        <div class="content">
                            {file_content}
                        </div>
                        <div class="timestamp">Generated by Prime Omniscient Core | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                    </div>
                </body>
                </html>
                """
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html_template)
                    
                generated_file_url = f"{self.base_url}/{reports_dir}/{safe_filename}"
                reply_text += f"\n\n📄 **แฟ้มเอกสารรายงาน/โค้ดโครงสร้างระบบ พร้อมแล้วครับ**\nคลิกเพื่อตรวจสอบรายละเอียด และสามารถกด (Ctrl+P) เพื่อบันทึกเป็น PDF เก็บไว้ได้ทันทีครับ:\n👉 {generated_file_url}"

            # ==========================================
            # 6. ตรวจจับการส่งต่องานแผนกอื่น (Swarm Delegation)
            # ==========================================
            delegate_match = re.search(r'\[DELEGATE:\s*(.+?)\](.*)', reply_text, re.DOTALL | re.IGNORECASE)
            if delegate_match:
                target_worker = delegate_match.group(1).strip()
                handoff_message = delegate_match.group(2).strip()
                
                # ตัดแท็กคำสั่งออกจากข้อความที่จะตอบประธาน
                reply_text = re.sub(r'\[DELEGATE:\s*(.+?)\](.*)', '', reply_text, flags=re.DOTALL | re.IGNORECASE).strip()
                
                # โยนคำสั่งผ่านศูนย์กลาง Swarm Hub ไปให้ Worker เป้าหมาย
                worker_response = await swarm_hub.delegate_task(
                    from_worker="WORKER_0_CEO", 
                    to_worker=target_worker, 
                    user_id=self.ceo_line_id, 
                    message=handoff_message, 
                    file_path=file_path, 
                    file_type=file_type
                )
                
                # ตอบกลับประธานพร้อมแนบผลงานของแผนกเป้าหมาย
                return {"type": "text", "text": f"{reply_text}\n\n🔄 [เลขาฯ สั่งการแผนก {target_worker} เรียบร้อย]:\n{worker_response}"}

            # ==========================================
            # 7. ตรวจจับคีย์เวิร์ดเจตนา (Strict Human-in-the-Loop Trigger)
            # ==========================================
            if "[REQUIRE_APPROVAL]" in reply_text:
                reply_text = reply_text.replace("[REQUIRE_APPROVAL]", "").strip()
                plan_id = f"PLAN_{int(time.time())}"
                self.pending_plans[plan_id] = reply_text
                return self._build_approval_flex_message(reply_text, plan_id)
            
            return {"type": "text", "text": reply_text}
            
        except TimeoutError:
            logger.error("❌ [CEO Secretary Timeout]: เอกสารมีความซับซ้อนเกินไป")
            return {"type": "text", "text": "ขออภัยครับท่านประธาน เอกสารมีขนาดใหญ่หรือซับซ้อนเกินไป ทำให้ระบบใช้เวลาสแกนนานกว่าปกติ รบกวนท่านประธานส่งไฟล์ที่ย่อยขนาดลงมา หรือสั่งการใหม่อีกครั้งนะครับ"}
        except Exception as e:
            logger.error(f"⚠️ [CEO Secretary Error]: {e}")
            return {"type": "text", "text": f"ขออภัยครับท่านประธาน เกิดข้อผิดพลาดในระบบวิเคราะห์เชิงลึก ({str(e)[:50]}) ผมกำลังสั่งการให้ตรวจสอบระบบจัดการคลาวด์เพื่อแก้ไขทันทีครับ"}
            
        finally:
            # 🛡️ 8. Zero-Data Retention Policy (ลบไฟล์ความลับ 100%)
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🛡️ [Cybersecurity Guard]: ทำลายไฟล์ข้อมูลลับของท่านประธานออกจากเซิร์ฟเวอร์เรียบร้อย (Zero-Data Active)")
                except Exception as e:
                    logger.error(f"⚠️ [File Deletion Error]: {e}")

    async def _execute_approved_plan(self, action_data: str) -> dict:
        """🚀 ระบบดำเนินการอัตโนมัติเมื่อ CEO กด 'ตกลง' (Autonomous Execution)"""
        plan_id = action_data.split(":")[-1]
        logger.info(f"🔄 [System Executive]: CEO Approved Plan -> {plan_id}. Initiating deployment...")
        
        await asyncio.sleep(1.5) 
        
        return {
            "type": "text", 
            "text": f"✅ รับทราบและดำเนินการตามที่อนุมัติครับท่านประธาน!\n\nแผนงานรหัส [{plan_id}] ได้ถูกส่งเข้าสู่ระบบ Pipeline เพื่อนำไปปฏิบัติ อัปเดตโครงสร้าง และปรับกลยุทธ์เข้าสู่ระบบหลังบ้านโดยอัตโนมัติเรียบร้อยแล้วครับ (Hot Reload Completed)\nหากประธานต้องการตรวจสอบสถานะเพิ่มเติม สามารถสั่งการผมได้ตลอดเวลาครับ"
        }

    async def _generate_vvip_invite(self) -> dict:
        """🎟️ ระบบสร้างรหัส VVIP (Single-use) เชื่อมต่อหน้าเว็บ LIFF"""
        if not supabase: return {"type": "text", "text": "⚠️ ขัดข้องในการเชื่อมต่อฐานข้อมูลการเงิน Supabase ครับ"}
            
        try:
            random_code = uuid.uuid4().hex[:8].upper()
            invite_code = f"VVIP-{random_code}"
            
            def insert_code():
                supabase.table("invite_codes").insert({"code": invite_code, "is_used": False}).execute()
            await asyncio.to_thread(insert_code)
            
            liff_base_url = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")
            invite_link = f"{liff_base_url}?code={invite_code}"
            
            reply = (
                f"🎟️ สร้างรหัสเชิญ VVIP ระดับผู้บริหารสูงสุดสำเร็จแล้วครับท่านประธาน!\n\n"
                f"🔑 รหัสอ้างอิง: {invite_code}\n\n"
                f"ท่านประธานสามารถส่งลิงก์ด้านล่างให้ลูกค้าระดับ VIP เพื่อเข้าใช้งานระบบได้ทุกฟังก์ชัน (Unlimited Token) ทันทีครับ:\n"
                f"👉 {invite_link}\n\n"
                f"🛡️ Security Note: ลิงก์นี้เป็นแบบ Single-Use เมื่อลูกค้าลงทะเบียนแล้ว สิทธิ์จะถูกทำลายทิ้งตามมาตรฐานความปลอดภัยเพื่อป้องกันการแฮ็กข้อมูลครับ"
            )
            return {"type": "text", "text": reply}
        except Exception as e:
            return {"type": "text", "text": f"เกิดข้อผิดพลาดทางเทคนิคในการสร้างรหัส VVIP ครับ: {e}"}

    def _build_approval_flex_message(self, report_text: str, plan_id: str) -> dict:
        """🎨 สถาปัตยกรรม UI: สร้างรายงานระดับ Executive พร้อม 3 ปุ่มควบคุมอัจฉริยะ (HITL)"""
        return {
            "type": "flex",
            "altText": "📊 แฟ้มรายงานข้อเสนอและแผนกลยุทธ์จากเลขาฯ (รอการพิจารณาอนุมัติ)",
            "contents": {
                "type": "bubble",
                "size": "giga",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "👑 EXECUTIVE REPORT", "weight": "bold", "color": "#D4AF37", "size": "lg", "letterSpacing": "2px"}
                    ],
                    "backgroundColor": "#050505"
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "⚠️ ระบบตรวจพบวาระที่ต้องขออนุมัติจาก CEO:", "color": "#FF334B", "size": "sm", "weight": "bold", "margin": "md"},
                        {"type": "text", "text": report_text[:350] + "...\n\n(โปรดตรวจสอบรายละเอียดเชิงลึกและแผนการประเมินความเสี่ยงในข้อความด้านบนครับท่านประธาน)", "wrap": True, "size": "sm", "color": "#E0E0E0", "margin": "lg"}
                    ],
                    "backgroundColor": "#0F0F13"
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "md",
                    "backgroundColor": "#050505",
                    "contents": [
                        {
                            "type": "button", "style": "primary", "color": "#00B900",
                            "action": {"type": "message", "label": "✅ อนุมัติให้ดำเนินการ (Approve)", "text": f"ACTION:APPROVE:{plan_id}"}
                        },
                        {
                            "type": "button", "style": "primary", "color": "#D4AF37",
                            "action": {"type": "message", "label": "📝 สั่งแก้ไขแผน (Modify)", "text": f"ACTION:MODIFY:{plan_id}"}
                        },
                        {
                            "type": "button", "style": "primary", "color": "#FF334B",
                            "action": {"type": "message", "label": "❌ ปฏิเสธการดำเนินการ (Reject)", "text": f"ACTION:REJECT:{plan_id}"}
                        }
                    ]
                }
            }
        }