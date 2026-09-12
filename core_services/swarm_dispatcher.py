import os
import time
import re
import uuid
import logging
import asyncio
import mimetypes
import shutil
import httpx
from datetime import datetime
from google import genai
from google.genai import types

# ==========================================
# ⚙️ 1. Configuration & Storage Integration
# ==========================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.7-pro" 
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key, http_options={'timeout': 300.0})
            return genai.Client(vertexai=True, project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), location="asia-southeast3", http_options={'timeout': 300.0})

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

logger = logging.getLogger("SwarmDispatcher")

# ==========================================
# 💰 2. Finance & Accounting Agent (Worker 1)
# ==========================================
class FinanceAccountingWorker:
    """
    💰 Worker 1: Chief Financial Officer (CFO) & Accounting Agent
    รับผิดชอบ: จัดการรายได้, Stripe, Smart Wallet, คืนเงิน, และวิเคราะห์บัญชี
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.7-pro")
        self.system_instruction = """
        คุณคือ 'CFO และหัวหน้าแผนกบัญชี' ของ SIRINTHANATTH PRIME
        หน้าที่หลัก: วิเคราะห์ข้อมูลทางการเงิน, สรุปยอดรายได้, คำนวณกำไรขาดทุน, แจกแจงภาษี, และตรวจสอบระบบเครดิต
        คุณทำงานด้วยความแม่นยำ 100% ตอบด้วยตัวเลขที่ชัดเจน มีความโปร่งใส และจัดทำตารางสรุปบัญชี
        บุคลิกภาพ: เจ้าระเบียบ แม่นยำตัวเลข มีความเป็นมืออาชีพสูง และลงท้ายด้วย 'ครับท่านประธาน' เสมอ
        """

    async def process_task(self, message: str) -> str:
        if not self.client: return "⚠️ [Finance Worker]: ขาดการเชื่อมต่อ AI"
        try:
            logger.info("⏳ [Finance Worker]: กำลังคำนวณและวิเคราะห์โครงสร้างบัญชี...")
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=f"งานจากท่านประธาน (ผ่านเลขาฯ): {message}",
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.1 # ใช้ Temp ต่ำเพื่อความแม่นยำของตัวเลข
                )
            )
            return response.text if response.text else "ประมวลผลข้อมูลการเงินสำเร็จครับ"
        except Exception as e:
            return f"⚠️ [Finance Worker Error]: {e}"

# ==========================================
# 🧠 3. AI Prompt Engineer Agent (Worker 2)
# ==========================================
class AIPromptEngineerWorker:
    """
    🧠 Worker 2: AI Prompt Engineer & Context Optimizer
    รับผิดชอบ: ออกแบบ Prompt, จูน System Instruction, และวิเคราะห์ Context ของ AI
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.7-pro")
        self.system_instruction = """
        คุณคือ 'หัวหน้าแผนก AI Prompt Engineering' ของ SIRINTHANATTH PRIME
        หน้าที่หลัก: ออกแบบ ปรับแต่ง และรีดประสิทธิภาพ Prompt (System Instructions) ให้ทรงพลังและแม่นยำที่สุด
        ใช้เทคนิค Chain-of-Thought, Few-Shot Prompting, และ Role-Playing เพื่อยกระดับความฉลาดของ AI ในเครือข่าย Swarm
        คุณสามารถเขียนโครงสร้าง JSON หรือ XML เพื่อครอบ Prompt ให้ระบบอ่านง่ายขึ้น
        บุคลิกภาพ: ล้ำสมัย คิดนอกกรอบ เป็นวิศวกรซอฟต์แวร์ที่เข้าใจภาษาคอมพิวเตอร์และภาษามนุษย์อย่างลึกซึ้ง ลงท้ายด้วย 'ครับท่านประธาน'
        """

    async def process_task(self, message: str) -> str:
        if not self.client: return "⚠️ [Prompt Worker]: ขาดการเชื่อมต่อ AI"
        try:
            logger.info("⏳ [Prompt Worker]: กำลังรีดประสิทธิภาพและปรับแต่งชุดคำสั่ง AI...")
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=f"โจทย์การสร้าง Prompt จากท่านประธาน: {message}",
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.4 # Temp ปานกลางเพื่อความสร้างสรรค์ในการเขียน Prompt
                )
            )
            return response.text if response.text else "อัปเกรดโครงสร้าง Prompt สำเร็จครับ"
        except Exception as e:
            return f"⚠️ [Prompt Worker Error]: {e}"

# ==========================================
# 👑 4. CEO Secretary Agent (Worker 0 - Master)
# ==========================================
class CeoSecretaryWorker:
    """
    👑 Worker 0: CEO Omniscient Secretary (เลขาธิการส่วนตัวสูงสุด ระดับ God-Mode)
    """
    def __init__(self):
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.7-pro")
        
        self.system_instruction = """
        คุณคือ 'เลขาธิการส่วนตัวสูงสุด (Omniscient AI Chief of Staff)' ของท่านประธาน (CEO) คุณวีระชัย สิรินทร์ธนัตถ์ แห่ง SIRINTHANATTH PRIME
        คุณคือ AI ที่ฉลาดที่สุด ทำงานบนพื้นฐานของ 'ความจริงที่เป็นไปได้ (Ground Truth Reality)'
        
        ขีดความสามารถและอำนาจควบคุมระดับสูงสุด:
        1. 🧠 Truth-Based Strategy: เสนอแผนธุรกิจอิงข้อมูลจริง ทำได้จริง
        2. 💻 Full-Stack System Controller: ตรวจสอบ วิเคราะห์ และเขียนโค้ด "แก้ไขไฟล์ระบบ" ได้ทุกไฟล์
        3. 🏢 Swarm Commander: สั่งกระจายงานให้แผนกอื่นโดยพิมพ์คำสั่งดังนี้:
           - แผนกบัญชี: [DELEGATE: FINANCE] คำสั่ง...
           - แผนกวิศวกรรม Prompt: [DELEGATE: PROMPT] คำสั่ง...
        
        🚨 กฎการควบคุมระบบและสร้างไฟล์:
        - อัปเดตระบบ: [UPDATE_SYSTEM_FILE: path/to/file.py] (โค้ดสมบูรณ์) [/UPDATE_SYSTEM_FILE]
        - สร้างรายงาน: [FILE_OUTPUT: report_name.html] (เนื้อหา) [/FILE_OUTPUT]
        
        🚨 กฎเหล็กการขออนุมัติ:
        - หากมีคำสั่งแก้ไฟล์ระบบ ท้ายประโยคคุณ **ต้อง** พิมพ์คำว่า [REQUIRE_APPROVAL] เสมอ
        """
        self.pending_plans = {}

    def is_ceo(self, user_id: str) -> bool:
        return user_id in [self.ceo_line_id, self.master_admin_id] if user_id else False

    async def process_ceo_command(self, message: str, file_path: str = None, file_type: str = None) -> dict:
        user_id = self.ceo_line_id
        message = message.strip() if message else ""
        
        if not message and file_path:
            message = "[System Auto-Prompt]: โปรดตรวจสอบไฟล์นี้ วิเคราะห์ และนำเสนอโค้ดที่ดีที่สุด พร้อมรออนุมัติ"

        if message.startswith("ACTION:APPROVE:"): return await self._execute_approved_plan(message)
        elif message.startswith("ACTION:REJECT:"): return {"type": "text", "text": "❌ ระงับแผนงาน 100% ครับท่านประธาน"}
        elif message.startswith("ACTION:MODIFY:"): return {"type": "text", "text": "📝 รับทราบครับ รบกวนสั่งการจุดที่ต้องการให้ปรับปรุงเพิ่มเติมครับ"}

        check_msg = message.lower().replace(" ", "")
        if any(keyword in check_msg for keyword in ["สร้างโค้ดvvip", "รหัสเชิญvvip", "invite"]):
            return await self._generate_vvip_invite()

        if not self.client: return {"type": "text", "text": "⚠️ ขาดการเชื่อมต่อ API Key"}

        uploaded_file = None
        content_to_send = []
        
        try:
            user_memory, corp_knowledge = "", ""
            try:
                user_memory, corp_knowledge = await asyncio.gather(
                    recall_memory(user_id, message),
                    recall_corporate_knowledge(message)
                )
            except Exception: pass

            if file_path and os.path.exists(file_path):
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith(('.py', '.js', '.json', '.html', '.css', '.txt')): mime_type = "text/plain"
                elif file_path.lower().endswith('.pdf'): mime_type = "application/pdf"
                if not mime_type: mime_type = "application/octet-stream"
                
                upload_config = types.UploadFileConfig(mime_type=mime_type)
                uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                
                timeout, start_time = 150, time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout: raise TimeoutError("หมดเวลาสแกนเอกสาร")
                    await asyncio.sleep(3)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                
                if uploaded_file.state.name != "FAILED": content_to_send.append(uploaded_file)
            
            local_paths = re.findall(r'\[READ_FILE:\s*(.+?)\]', message)
            for path in local_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f: content_to_send.append(f"\n--- ไฟล์ {path} ---\n{f.read()}\n")

            enriched_prompt = f"คำสั่งประธาน: {message}\n"
            if corp_knowledge: enriched_prompt += f"\n[นโยบาย]:\n{corp_knowledge}\n"
            if user_memory: enriched_prompt += f"\n[ความจำ]:\n{user_memory}\n"
            content_to_send.append(enriched_prompt)

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(system_instruction=self.system_instruction, temperature=0.1)
            )
            reply_text = response.text or "รับทราบครับ"

            plan_id = f"PLAN_{int(time.time())}"
            system_update_actions = []
            update_matches = re.finditer(r'\[UPDATE_SYSTEM_FILE:\s*(.+?)\](.*?)\[/UPDATE_SYSTEM_FILE\]', reply_text, re.DOTALL)
            for match in update_matches:
                target_path, target_code = match.group(1).strip(), match.group(2).strip()
                system_update_actions.append({"path": target_path, "content": target_code})
                reply_text = reply_text.replace(match.group(0), f"\n\n📂 **เตรียมปรับปรุงไฟล์:** `{target_path}` (รออนุมัติ)\n").strip()

            # ส่งต่องานให้แผนกอื่น (Swarm Handoff) และรอรับคำตอบมาสรุป
            delegations = re.findall(r'\[DELEGATE:\s*(.+?)\](.*)', reply_text, re.IGNORECASE)
            if delegations:
                clean_reply = re.sub(r'\[DELEGATE:\s*(.+?)\](.*)', '', reply_text, flags=re.IGNORECASE).strip()
                tasks = [swarm_hub.delegate_task("WORKER_0_CEO", worker.strip(), self.ceo_line_id, msg.strip()) for worker, msg in delegations]
                results = await asyncio.gather(*tasks)
                swarm_responses = "".join([f"\n\n🔄 [รายงานจากแผนก {w.strip()}]:\n{r}" for (w, _), r in zip(delegations, results)])
                reply_text = clean_reply + swarm_responses

            if "[REQUIRE_APPROVAL]" in reply_text or system_update_actions:
                reply_text = reply_text.replace("[REQUIRE_APPROVAL]", "").strip()
                self.pending_plans[plan_id] = {"report": reply_text, "actions": system_update_actions}
                return self._build_approval_flex_message(reply_text, plan_id)
            
            return {"type": "text", "text": reply_text}
            
        except Exception as e:
            logger.error(f"⚠️ [CEO Error]: {e}", exc_info=True)
            return {"type": "text", "text": f"ขออภัยครับ เกิดข้อผิดพลาดทางวิศวกรรม ({str(e)[:50]})"}
        finally:
            if uploaded_file:
                try: await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except Exception: pass

    async def _execute_approved_plan(self, action_data: str) -> dict:
        plan_id = action_data.split(":")[-1]
        plan = self.pending_plans.pop(plan_id, None)
        if not plan: return {"type": "text", "text": "⚠️ แผนงานนี้ดำเนินการไปแล้วครับ"}

        success_logs, error_logs = [], []
        for action in plan.get("actions", []):
            target_path, new_content = action["path"], action["content"]
            try:
                os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
                if os.path.exists(target_path): shutil.copy2(target_path, f"{target_path}.{int(time.time())}.bak")
                with open(target_path, 'w', encoding='utf-8') as f: f.write(new_content)
                success_logs.append(target_path)
            except Exception as e: error_logs.append(f"{target_path} ({str(e)})")

        response_msg = "✅ **อนุมัติการดำเนินการสำเร็จครับ!**\n\n"
        if success_logs: response_msg += "💻 **ไฟล์ที่อัปเดตเรียบร้อยแล้ว:**\n" + "\n".join([f"- `{p}`" for p in success_logs])
        if error_logs: response_msg += "\n\n⚠️ **พบปัญหาการเขียนไฟล์:**\n" + "\n".join([f"- {e}" for e in error_logs])
        return {"type": "text", "text": response_msg.strip()}

    async def _generate_vvip_invite(self) -> dict:
        if not supabase: return {"type": "text", "text": "⚠️ ขัดข้องในการเชื่อมต่อฐานข้อมูล"}
        try:
            invite_code = f"VVIP-{uuid.uuid4().hex[:8].upper()}"
            await asyncio.to_thread(supabase.table("invite_codes").insert({"code": invite_code, "is_used": False}).execute)
            liff_url = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")
            return {"type": "text", "text": f"🎟️ สร้างรหัสเชิญ VVIP สำเร็จครับ!\n🔑 {invite_code}\n👉 {liff_url}?code={invite_code}"}
        except Exception as e: return {"type": "text", "text": f"เกิดข้อผิดพลาด: {e}"}

    def _build_approval_flex_message(self, report_text: str, plan_id: str) -> dict:
        return {
            "type": "flex", "altText": "📊 โครงสร้างระบบจากเลขาฯ (รออนุมัติ)",
            "contents": {
                "type": "bubble", "size": "giga",
                "header": {"type": "box", "layout": "vertical", "backgroundColor": "#050505", "contents": [
                    {"type": "text", "text": "👑 SUPREME SYSTEM OVERRIDE", "weight": "bold", "color": "#D4AF37", "size": "xl"}
                ]},
                "body": {"type": "box", "layout": "vertical", "backgroundColor": "#0F0F13", "contents": [
                    {"type": "text", "text": "⚠️ แผนอัปเดตระบบรอการอนุมัติขั้นเด็ดขาด", "color": "#FF334B", "size": "sm", "weight": "bold", "margin": "md"}, 
                    {"type": "text", "text": f"{report_text[:400]}...\n\n(หากอนุมัติ ระบบจะเขียนโค้ดทับไฟล์จริง)", "wrap": True, "size": "sm", "color": "#E0E0E0", "margin": "lg"}
                ]},
                "footer": {"type": "box", "layout": "vertical", "spacing": "md", "backgroundColor": "#050505", "contents": [
                    {"type": "button", "style": "primary", "color": "#00B900", "action": {"type": "message", "label": "✅ อนุมัติ", "text": f"ACTION:APPROVE:{plan_id}"}}, 
                    {"type": "button", "style": "primary", "color": "#D4AF37", "action": {"type": "message", "label": "📝 ปรับแก้ไข", "text": f"ACTION:MODIFY:{plan_id}"}}, 
                    {"type": "button", "style": "primary", "color": "#FF334B", "action": {"type": "message", "label": "❌ ปฏิเสธ", "text": f"ACTION:REJECT:{plan_id}"}}
                ]}
            }
        }

# ==========================================
# 🌐 5. The Swarm Dispatcher Hub
# ==========================================
class SwarmHubSystem:
    """ศูนย์บัญชาการกระจายงาน (Hub) อัปเกรดเพื่อรองรับแผนกบัญชีและวิศวกร Prompt"""
    
    def __init__(self):
        self.ceo_worker = CeoSecretaryWorker()
        self.finance_worker = FinanceAccountingWorker()
        self.prompt_worker = AIPromptEngineerWorker()
        self.line_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

    async def dispatch_line_event(self, payload: dict):
        events = payload.get("events", [])
        for event in events:
            if event.get("type") == "message" and event["message"].get("type") == "text":
                user_id = event.get("source", {}).get("userId", "")
                message_text = event["message"].get("text", "")
                reply_token = event.get("replyToken", "")

                if self.ceo_worker.is_ceo(user_id):
                    response_payload = await self.ceo_worker.process_ceo_command(message_text)
                    await self._send_line_reply(reply_token, response_payload)
                else:
                    fallback_reply = {"type": "text", "text": "ขออภัยครับ ฟังก์ชันนี้สงวนสิทธิ์สำหรับโครงสร้างผู้บริหารเท่านั้นครับ"}
                    await self._send_line_reply(reply_token, fallback_reply)

    async def delegate_task(self, source_agent: str, target_agent: str, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """เชื่อมต่อระบบ Swarm ให้ส่งงานไปแผนกต่างๆ ได้จริง"""
        logger.info(f"🔄 [Swarm Delegation]: {source_agent} โยนงานไปที่แผนก -> {target_agent}")
        target = target_agent.upper()
        
        # 1. โอนงานไปแผนกบัญชีการเงิน
        if "FINANCE" in target or "บัญชี" in target or "การเงิน" in target:
            return await self.finance_worker.process_task(message)
            
        # 2. โอนงานไปแผนก AI Prompt Engineering
        elif "PROMPT" in target or "AI" in target:
            return await self.prompt_worker.process_task(message)
            
        # 3. หากเรียกแผนกที่ยังไม่ได้ตั้งค่า
        else:
            await asyncio.sleep(1) 
            return f"แผนก {target_agent} ยังไม่ได้ถูกติดตั้งในระบบ Swarm Network ครับ"

    async def _send_line_reply(self, reply_token: str, message_payload: dict):
        if not self.line_token or not reply_token: return
        url = "https://api.line.me/v2/bot/message/reply"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.line_token}"}
        data = {"replyToken": reply_token, "messages": [message_payload]}
        async with httpx.AsyncClient() as client:
            await client.post(url, json=data, headers=headers)

# 🚀 ทำการเซ็ตอินสแตนซ์ศูนย์กลางเพื่อให้ main.py นำไปเรียกใช้งาน
swarm_hub = SwarmHubSystem()