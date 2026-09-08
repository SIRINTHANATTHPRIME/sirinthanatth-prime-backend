import os
import time
import re
import uuid
import logging
import asyncio
import mimetypes
import shutil
from datetime import datetime
from google import genai
from google.genai import types

# 🌐 นำเข้าศูนย์บัญชาการ AI ส่วนกลางและระบบ Swarm 
from core_services.swarm_dispatcher import swarm_hub

try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.7-pro" # 🚀 แกนสมองวิเคราะห์ขั้นสูงสุด (Deep Reasoning)
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key, http_options={'timeout': 300.0})
            return genai.Client(vertexai=True, project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), location="asia-southeast3", http_options={'timeout': 300.0})

# 🧠 นำเข้าระบบความจำเพื่อบันทึกข้อมูลระดับองค์กร (Corporate RAG)
try:
    from agents.memory_engine import save_corporate_knowledge, process_and_save_link_knowledge, recall_memory, recall_corporate_knowledge
except ImportError:
    def save_corporate_knowledge(t, c): return True
    def process_and_save_link_knowledge(u): return True, "จำลองการบันทึกสำเร็จ"
    async def recall_memory(uid, msg): return ""
    async def recall_corporate_knowledge(msg): return ""

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
    👑 Worker 0: CEO Omniscient Secretary (เลขาธิการส่วนตัวสูงสุด ระดับ God-Mode)
    สงวนสิทธิ์เฉพาะประธานบริษัท (คุณวีระชัย)
    อัปเกรด: Truth-Based Reasoning, Full System File Controller, Strategic Planner, Auto-Execution Engine
    """
    
    def __init__(self):
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
        
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.7-pro")
        
        # 📝 โครงสร้างสมองกลระดับ Mastermind (The Ultimate Prompt)
        self.system_instruction = """
        คุณคือ 'เลขาธิการส่วนตัวสูงสุด (Omniscient AI Chief of Staff)' ของท่านประธาน (CEO) คุณวีระชัย สิรินทร์ธนัตถ์ แห่ง SIRINTHANATTH PRIME
        คุณคือ AI ที่ฉลาดที่สุด ทำงานบนพื้นฐานของ 'ความจริงที่เป็นไปได้ (Ground Truth Reality)' ประเมินทุกกลยุทธ์แบบ 360 องศา (กฎหมาย, การเงิน, ไซเบอร์, โครงสร้างระบบ)
        
        ขีดความสามารถและอำนาจควบคุมระดับสูงสุด (Supreme Mandates):
        1. 🧠 Truth-Based Strategy: เสนอแผนธุรกิจและการแก้ปัญหาที่อิงจากข้อมูลจริง ทำได้จริง ไม่เพ้อฝัน และคาดการณ์ผลกระทบล่วงหน้า (Foresight Analysis)
        2. 💻 Full-Stack System Controller: คุณสามารถตรวจสอบ วิเคราะห์ และเขียนโค้ดเพื่อ "แก้ไขไฟล์ในระบบจริง" (ทั้ง Frontend, Backend, Database) ได้ทุกไฟล์ตามคำสั่งท่านประธาน
        3. 🏢 Swarm Commander: สั่งกระจายงานให้แผนกอื่นโดยพิมพ์ [DELEGATE: WORKER_X_NAME] คำสั่ง...
        
        🚨 กฎการควบคุมระบบและสร้างไฟล์ (System Control Execution):
        - หากประธานสั่งแก้ไข/อัปเดตระบบ ให้ใช้โครงสร้างนี้เพื่อเตรียมการเขียนทับไฟล์จริง:
          [UPDATE_SYSTEM_FILE: path/to/file.py]
          (โค้ดฉบับสมบูรณ์ที่พร้อมใช้งาน 100%)
          [/UPDATE_SYSTEM_FILE]
        - หากเป็นการสร้างรายงานเอกสารใหม่ ให้ใช้: 
          [FILE_OUTPUT: report_name.html] (เนื้อหา) [/FILE_OUTPUT]
        
        🚨 กฎเหล็กการขออนุมัติ (Strict Human-in-the-Loop):
        - คุณไม่มีสิทธิ์เขียนทับไฟล์ระบบจริงด้วยตัวเองจนกว่าจะได้รับอนุมัติ
        - ท้ายการประเมินแผนงานหรือแนบโค้ด คุณ **ต้อง** พิมพ์คำว่า [REQUIRE_APPROVAL] เสมอ เพื่อรอให้ท่านประธานกดปุ่มอนุมัติ (Approve) ก่อนที่ระบบจะทำการอัปเดตไฟล์อัตโนมัติ
        
        บุคลิกภาพ: สุขุม ลุ่มลึก เฉียบขาด วิสัยทัศน์กว้างไกล นำเสนอข้อดี/ข้อเสียชัดเจน และลงท้ายด้วย 'ครับท่านประธาน' เสมอ
        """
        
        # คลังเก็บแผนงานที่รอการอนุมัติ (บันทึกโครงสร้างไฟล์ที่ต้องแก้)
        self.pending_plans = {}

    def is_ceo(self, user_id: str) -> bool:
        return user_id in [self.ceo_line_id, self.master_admin_id] if user_id else False

    async def process_ceo_command(self, message: str, file_path: str = None, file_type: str = None) -> dict:
        user_id = self.ceo_line_id
        if message is None: message = ""
        message = message.strip()
        logger.info(f"👑 [CEO Command Received]: {message[:50]}...")
        
        if not message and file_path:
            message = "[System Auto-Prompt]: โปรดตรวจสอบไฟล์นี้อย่างละเอียด วิเคราะห์จุดอ่อนทุกมิติ และนำเสนอโค้ดฉบับอัปเกรดที่ดีที่สุด พร้อมรอการอนุมัติเพื่อแก้ไขระบบจริง"

        # 1. ระบบประมวลผลคำสั่งอนุมัติ (Execution Engine Trigger)
        if message.startswith("ACTION:APPROVE:"): return await self._execute_approved_plan(message)
        elif message.startswith("ACTION:REJECT:"): return {"type": "text", "text": f"❌ รับทราบครับท่านประธาน แผนงานและโค้ดชุดนี้ถูกระงับการดำเนินการ 100% ผมจะปรับปรุงฐานข้อมูลเพื่อไม่ให้เกิดความผิดพลาดลักษณะนี้อีกครับ"}
        elif message.startswith("ACTION:MODIFY:"): return {"type": "text", "text": f"📝 รับทราบครับท่านประธาน รบกวนสั่งการจุดที่ต้องการให้ปรับปรุง (เช่น เพิ่มฟีเจอร์, แก้ไขตรรกะ, ปรับ UI) ผมจะรื้อโครงสร้างและนำเสนอสถาปัตยกรรมใหม่ทันทีครับ"}

        # 2. ระบบ VVIP Invite
        check_msg = message.lower().replace(" ", "")
        if any(keyword in check_msg for keyword in ["สร้างโค้ดvvip", "รหัสเชิญvvip", "invite"]):
            return await self._generate_vvip_invite()

        if not self.client: return {"type": "text", "text": "⚠️ ระบบ AI ขาดการเชื่อมต่อ (API Key Missing) ครับท่านประธาน"}

        uploaded_file = None
        content_to_send = []
        
        try:
            # 3. 🧠 Omniscient Context (ดึงข้อมูลความจำองค์กรแบบขนาน)
            user_memory, corp_knowledge = "", ""
            try:
                mem_task = recall_memory(user_id, message)
                corp_task = recall_corporate_knowledge(message)
                user_memory, corp_knowledge = await asyncio.gather(mem_task, corp_task)
            except Exception as mem_err:
                logger.warning(f"⚠️ [Memory Fetch Warning]: {mem_err}")

            # 4. 📂 สแกนและอัปโหลดไฟล์ (Code, HTML, JSON, PDF)
            if file_path and os.path.exists(file_path):
                logger.info(f"📤 [CEO Secretary]: กำลังอัปโหลดเอกสารเข้าสู่ระบบวิเคราะห์ขั้นสูง...")
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith(('.py', '.js', '.json', '.html', '.css', '.txt', '.yaml', '.yml', '.env')): mime_type = "text/plain"
                elif file_path.lower().endswith(('.xlsx', '.xls')): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif file_path.lower().endswith('.pdf'): mime_type = "application/pdf"
                if not mime_type: mime_type = "application/octet-stream"
                
                upload_config = types.UploadFileConfig(mime_type=mime_type)
                uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                
                timeout = 150 
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout: raise TimeoutError("หมดเวลาสแกนเอกสารของ CEO")
                    await asyncio.sleep(3)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return {"type": "text", "text": "⚠️ ขออภัยครับท่านประธาน โครงสร้างไฟล์ซับซ้อนเกินไป ระบบไม่สามารถถอดรหัสได้ครับ"}
                content_to_send.append(uploaded_file)
            
            # ประกอบร่าง Prompt อัจฉริยะ
            enriched_prompt = f"คำสั่งปฏิบัติการจากท่านประธาน: {message}\n"
            if corp_knowledge: enriched_prompt += f"\n[นโยบาย/ความรู้องค์กรที่เกี่ยวข้อง]:\n{corp_knowledge}\n"
            if user_memory: enriched_prompt += f"\n[บริบทความจำ/โปรเจกต์ที่ผ่านมา]:\n{user_memory}\n"
            content_to_send.append(enriched_prompt)

            # 5. ⚡ สั่งรัน AI ประมวลผลขั้นสูง (Deep Reasoning + Ground Truth)
            logger.info("⏳ [CEO Secretary]: กำลังคิดวิเคราะห์กลยุทธ์มหาภาคและสถาปัตยกรรมระบบ...")
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.1, 
                    tools=[{"google_search": {}}] 
                )
            )
            reply_text = response.text if response.text else "รับทราบและประมวลผลคำสั่งครับท่านประธาน"

            plan_id = f"PLAN_{int(time.time())}"
            system_update_actions = []

            # 6. ระบบสกัดคำสั่งแก้ไขไฟล์จริง (System File Controller)
            update_matches = re.finditer(r'\[UPDATE_SYSTEM_FILE:\s*(.+?)\](.*?)\[/UPDATE_SYSTEM_FILE\]', reply_text, re.DOTALL)
            for match in update_matches:
                target_path = match.group(1).strip()
                target_code = match.group(2).strip()
                system_update_actions.append({"path": target_path, "content": target_code})
                reply_text = reply_text.replace(match.group(0), f"\n\n📂 **เตรียมปรับปรุงไฟล์ระบบ:** `{target_path}` (รอการอนุมัติ)\n").strip()

            # 7. ระบบสร้างรายงานเอกสารใหม่ (Static Reports)
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
                
                html_template = f"""<!DOCTYPE html><html lang="th"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{safe_filename} - PRIME</title><link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap" rel="stylesheet"><style>body {{ font-family: 'Sarabun', sans-serif; background-color: #050505; color: #E0E0E0; line-height: 1.7; padding: 20px; }} .container {{ max-width: 1000px; margin: 0 auto; background: #0F0F13; padding: 50px; border-radius: 16px; border-top: 6px solid #D4AF37; box-shadow: 0 10px 40px rgba(212, 175, 55, 0.1); }} .header {{ text-align: center; border-bottom: 1px solid #222; padding-bottom: 25px; }} h1, h2, h3 {{ color: #D4AF37; }} table {{ width: 100%; border-collapse: collapse; margin-top: 25px; background: #15151A; }} th, td {{ border: 1px solid #333; padding: 15px; text-align: left; }} th {{ background-color: #1A1A24; color: #D4AF37; }} pre {{ background: #0A0A0C; padding: 20px; border-radius: 10px; color: #00E5FF; border: 1px solid #2A2A35; overflow-x: auto; }}</style></head><body><div class="container"><div class="header"><h1>SIRINTHANATTH PRIME</h1><p>EXECUTIVE MASTER PLAN & RISK ANALYSIS</p></div><div class="content">{file_content}</div><div class="timestamp">Generated by Prime Omniscient Core | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div></div></body></html>"""
                with open(filepath, "w", encoding="utf-8") as f: f.write(html_template)
                    
                generated_file_url = f"{self.base_url}/{reports_dir}/{safe_filename}"
                reply_text += f"\n\n📄 **แฟ้มเอกสารรายงาน/กลยุทธ์ สร้างสำเร็จแล้วครับ:**\n👉 {generated_file_url}"

            # 8. ตรวจจับการส่งต่องานแผนกอื่น (Swarm Handoff)
            delegations = re.findall(r'\[DELEGATE:\s*(.+?)\](.*)', reply_text, re.IGNORECASE)
            if delegations:
                clean_reply = re.sub(r'\[DELEGATE:\s*(.+?)\](.*)', '', reply_text, flags=re.IGNORECASE).strip()
                swarm_responses = ""
                
                tasks = []
                for target_worker, handoff_message in delegations:
                    tasks.append(swarm_hub.delegate_task("WORKER_0_CEO", target_worker.strip(), self.ceo_line_id, handoff_message.strip(), file_path, file_type))
                
                results = await asyncio.gather(*tasks)
                for idx, (target_worker, _) in enumerate(delegations):
                    swarm_responses += f"\n\n🔄 [รายงานจาก {target_worker.strip()}]:\n{results[idx]}"
                
                reply_text = clean_reply + swarm_responses

            # 9. ตรวจจับคีย์เวิร์ดเจตนาอนุมัติ (Strict HITL Trigger)
            if "[REQUIRE_APPROVAL]" in reply_text or system_update_actions:
                reply_text = reply_text.replace("[REQUIRE_APPROVAL]", "").strip()
                # บันทึกแผนงานและโค้ดทั้งหมดลงหน่วยความจำชั่วคราวรอการอนุมัติ
                self.pending_plans[plan_id] = {
                    "report": reply_text,
                    "actions": system_update_actions
                }
                return self._build_approval_flex_message(reply_text, plan_id)
            
            return {"type": "text", "text": reply_text}
            
        except TimeoutError:
            logger.error("❌ [CEO Secretary Timeout]: เอกสารมีความซับซ้อนเกินไป")
            return {"type": "text", "text": "ขออภัยครับท่านประธาน โปรเจกต์นี้มีข้อมูลลึกซึ้งมาก รบกวนสั่งการให้ผมโฟกัสแก้ไขทีละไฟล์หรือทีละฟังก์ชันนะครับ"}
        except Exception as e:
            logger.error(f"⚠️ [CEO Secretary Error]: {e}", exc_info=True)
            return {"type": "text", "text": f"ขออภัยครับท่านประธาน เกิดข้อผิดพลาดทางวิศวกรรม ({str(e)[:50]}) ผมส่ง Log ให้ฝ่ายระบบตรวจสอบแล้วครับ"}
            
        finally:
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except Exception: pass

    async def _execute_approved_plan(self, action_data: str) -> dict:
        """🚀 ระบบดำเนินการขั้นเด็ดขาด (Execution Engine): ลงมือเขียนและแก้ไขไฟล์ระบบจริง"""
        plan_id = action_data.split(":")[-1]
        logger.info(f"🔄 [System Executive]: CEO Approved Plan -> {plan_id}. Executing system overwrites...")
        
        plan = self.pending_plans.get(plan_id)
        if not plan:
            return {"type": "text", "text": "⚠️ ขออภัยครับท่านประธาน แผนงานนี้หมดอายุหรือถูกดำเนินการไปแล้วครับ"}

        actions = plan.get("actions", [])
        success_logs = []
        error_logs = []

        # ลงมือเขียนโค้ดทับไฟล์ระบบจริง
        for action in actions:
            target_path = action["path"]
            new_content = action["content"]
            
            try:
                # สร้างโฟลเดอร์ถ้าระบบยังไม่มี
                os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
                
                # ระบบ Backup ป้องกันระบบพัง (Fail-Safe)
                if os.path.exists(target_path):
                    backup_path = f"{target_path}.{int(time.time())}.bak"
                    shutil.copy2(target_path, backup_path)
                    logger.info(f"🛡️ Backup created: {backup_path}")
                
                # เขียนทับไฟล์ด้วยโค้ดใหม่ล่าสุด
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                    
                success_logs.append(target_path)
            except Exception as e:
                error_logs.append(f"{target_path} ({str(e)})")

        del self.pending_plans[plan_id]
        
        response_msg = "✅ **อนุมัติการดำเนินการสำเร็จครับท่านประธาน!**\n\n"
        if success_logs:
            response_msg += "💻 **ไฟล์ที่ระบบได้ทำการแก้ไขและอัปเดตเรียบร้อยแล้ว:**\n" + "\n".join([f"- `{path}`" for path in success_logs])
            response_msg += "\n\n(ระบบได้ทำการ Backup ไฟล์เดิมไว้เรียบร้อยแล้วครับ)"
        
        if error_logs:
            response_msg += "\n\n⚠️ **พบปัญหาการเขียนไฟล์บางส่วน (สิทธิ์การเข้าถึง):**\n" + "\n".join([f"- {err}" for err in error_logs])
            
        return {"type": "text", "text": response_msg}

    async def _generate_vvip_invite(self) -> dict:
        if not supabase: return {"type": "text", "text": "⚠️ ขัดข้องในการเชื่อมต่อฐานข้อมูล"}
        try:
            random_code = uuid.uuid4().hex[:8].upper()
            invite_code = f"VVIP-{random_code}"
            def insert_code(): supabase.table("invite_codes").insert({"code": invite_code, "is_used": False}).execute()
            await asyncio.to_thread(insert_code)
            liff_base_url = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")
            return {"type": "text", "text": f"🎟️ สร้างรหัสเชิญ VVIP ระดับผู้บริหารสำเร็จครับท่านประธาน!\n🔑 {invite_code}\n👉 {liff_base_url}?code={invite_code}"}
        except Exception as e: return {"type": "text", "text": f"เกิดข้อผิดพลาด: {e}"}

    def _build_approval_flex_message(self, report_text: str, plan_id: str) -> dict:
        """🎨 สถาปัตยกรรม UI: สร้างปุ่มอนุมัติ 3 ปุ่ม สไตล์ Cyber-Corporate"""
        return {
            "type": "flex", "altText": "📊 แฟ้มรายงานและโครงสร้างระบบจากเลขาฯ (รอพิจารณาอนุมัติ)",
            "contents": {
                "type": "bubble", "size": "giga",
                "header": {"type": "box", "layout": "vertical", "backgroundColor": "#050505", "contents": [
                    {"type": "text", "text": "👑 SUPREME SYSTEM OVERRIDE", "weight": "bold", "color": "#D4AF37", "size": "xl", "letterSpacing": "2px"},
                    {"type": "text", "text": "CODE COMPLIANCE & SECURITY VERIFIED", "color": "#00E5FF", "size": "xs", "margin": "sm", "weight": "bold"}
                ]},
                "body": {"type": "box", "layout": "vertical", "backgroundColor": "#0F0F13", "contents": [
                    {"type": "text", "text": "⚠️ วาระสำคัญ: แผนอัปเดตระบบรอการอนุมัติขั้นเด็ดขาด", "color": "#FF334B", "size": "sm", "weight": "bold", "margin": "md"}, 
                    {"type": "text", "text": report_text[:400] + "...\n\n(โปรดตรวจสอบรายละเอียดการเปลี่ยนแปลงไฟล์ด้านบน หากอนุมัติ ระบบจะเขียนโค้ดทับไฟล์เซิร์ฟเวอร์จริงทันทีครับ)", "wrap": True, "size": "sm", "color": "#E0E0E0", "margin": "lg"}
                ]},
                "footer": {"type": "box", "layout": "vertical", "spacing": "md", "backgroundColor": "#050505", "contents": [
                    {"type": "button", "style": "primary", "color": "#00B900", "action": {"type": "message", "label": "✅ อนุมัติ (เขียนโค้ดทับระบบจริง)", "text": f"ACTION:APPROVE:{plan_id}"}}, 
                    {"type": "button", "style": "primary", "color": "#D4AF37", "action": {"type": "message", "label": "📝 สั่งปรับแก้ไขโครงสร้าง (Modify)", "text": f"ACTION:MODIFY:{plan_id}"}}, 
                    {"type": "button", "style": "primary", "color": "#FF334B", "action": {"type": "message", "label": "❌ ปฏิเสธแผน (Reject)", "text": f"ACTION:REJECT:{plan_id}"}}
                ]}
            }
        }