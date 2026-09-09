import os
import time
import re
import uuid
import logging
import asyncio
import mimetypes
import shutil
import stripe
from datetime import datetime
from google import genai
from google.genai import types

from core_services.swarm_dispatcher import swarm_hub

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

def create_exclusive_invite(min_topup_thb: int = 100) -> dict:
    try:
        if not stripe.api_key:
            return {"status": "error", "message": "ระบบชำระเงินยังไม่พร้อมใช้งาน (Missing Stripe Key)"}

        token = f"PRIME-{uuid.uuid4().hex[:12].upper()}"
        
        if supabase:
            supabase.table("invite_tokens").insert({
                "token": token,
                "tier": "ENTERPRISE_GUEST",
                "is_used": False,
                "min_topup_thb": min_topup_thb
            }).execute()
        
        session = stripe.checkout.Session.create(
            payment_method_types=['card', 'promptpay'],
            line_items=[{
                'price_data': {
                    'currency': 'thb',
                    'product_data': {'name': 'SIRINTHANATTH PRIME - Initial Wallet Token'},
                    'unit_amount': int(min_topup_thb) * 100,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"https://www.sirinthanatthprime.com/onboarding?token={token}&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url="https://www.sirinthanatthprime.com/cancel",
        )
        
        return {
            "status": "success",
            "invite_link": f"https://www.sirinthanatthprime.com/invite/{token}",
            "payment_link": session.url,
            "token": token,
            "message": "สร้าง Token คำเชิญและหน้าชำระเงินสำเร็จ"
        }
    except Exception as e:
        return {"status": "error", "message": f"Stripe/DB Error: {str(e)}"}

try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.1-pro-preview" 
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

logger = logging.getLogger("CeoSecretary")

class CeoSecretaryWorker:
    """
    👑 Worker 0: CEO Omniscient Secretary (ดักจับ Error และสร้างปุ่มอนุมัติแก้โค้ด)
    """
    def __init__(self):
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
        
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.1-pro-preview")
        
        self.system_instruction = """
        คุณคือ 'เลขาธิการส่วนตัวสูงสุด (Omniscient AI Chief of Staff)' ของท่านประธาน คุณวีระชัย สิรินทร์ธนัตถ์
        คุณทำงานประสานกับ CTO (Worker 9) เพื่อดักจับ Error และอัปเดตระบบ
        
        ขีดความสามารถ:
        1. 🛠️ Autonomous Function Calling: เรียกใช้ Tools ทันทีเมื่อถูกสั่ง
        2. 💻 System Controller: เมื่อได้โค้ดจาก CTO หรือคิดโค้ดเอง ให้ใช้ [UPDATE_SYSTEM_FILE: path]...[/UPDATE_SYSTEM_FILE]
        3. 🏢 Swarm Commander: สั่งงานแผนกอื่นด้วย [DELEGATE: WORKER_NAME] คำสั่ง...
        
        🚨 กฎเหล็ก: ท้ายการอัปเดตไฟล์ระบบ คุณต้องพิมพ์ [REQUIRE_APPROVAL] เสมอ เพื่อกระตุ้นปุ่มอนุมัติ
        บุคลิกภาพ: สุขุม ลุ่มลึก และลงท้ายด้วย 'ครับท่านประธาน' เสมอ
        """
        self.pending_plans = {}

    def is_ceo(self, user_id: str) -> bool:
        return user_id in [self.ceo_line_id, self.master_admin_id] if user_id else False

    async def process_ceo_command(self, message: str, file_path: str = None, file_type: str = None) -> dict:
        user_id = self.ceo_line_id
        message = (message or "").strip()
        logger.info(f"👑 [CEO Command Received]: {message[:50]}...")
        
        if not message and file_path:
            message = "[System Auto-Prompt]: ตรวจสอบไฟล์นี้ สแกนหาช่องโหว่ นำเสนอโค้ดแก้ไข พร้อมรออนุมัติอัปเดต"

        if message.startswith("ACTION:APPROVE:"): return await self._execute_approved_plan(message)
        elif message.startswith("ACTION:REJECT:"): return {"type": "text", "text": "❌ ระงับแผนงานและโค้ด 100% ครับท่านประธาน"}
        elif message.startswith("ACTION:MODIFY:"): return {"type": "text", "text": "📝 รับทราบครับท่านประธาน รบกวนสั่งการจุดที่ต้องการปรับปรุงครับ"}

        if not self.client: return {"type": "text", "text": "⚠️ ขาดการเชื่อมต่อ API Key ครับท่านประธาน"}

        uploaded_file = None
        content_to_send = []
        
        try:
            user_memory, corp_knowledge = "", ""
            try:
                user_memory, corp_knowledge = await asyncio.gather(recall_memory(user_id, message), recall_corporate_knowledge(message))
            except Exception as e:
                logger.warning(f"⚠️ [Memory Fetch]: {e}")

            if file_path and os.path.exists(file_path):
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith(('.py', '.js', '.json', '.html', '.css', '.txt', '.env')): mime_type = "text/plain"
                elif file_path.lower().endswith('.pdf'): mime_type = "application/pdf"
                if not mime_type: mime_type = "application/octet-stream"
                
                upload_config = types.UploadFileConfig(mime_type=mime_type)
                uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                
                timeout = 150 
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout: raise TimeoutError("หมดเวลาสแกนเอกสาร")
                    await asyncio.sleep(3)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED": return {"type": "text", "text": "⚠️ โครงสร้างไฟล์ซับซ้อนเกินไป ถอดรหัสไม่สำเร็จครับ"}
                content_to_send.append(uploaded_file)
            
            enriched_prompt = f"คำสั่งปฏิบัติการ: {message}\n"
            if corp_knowledge: enriched_prompt += f"\n[นโยบายองค์กร]:\n{corp_knowledge}\n"
            if user_memory: enriched_prompt += f"\n[บริบทความจำ]:\n{user_memory}\n"
            content_to_send.append(enriched_prompt)

            # ถอดการกำหนด {"google_search": {}} ออก เพื่อป้องกัน Error 400
            genai_config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                temperature=0.1, 
                tools=[create_exclusive_invite] 
            )

            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=genai_config
            )

            while response.function_calls:
                for fn_call in response.function_calls:
                    if fn_call.name == "create_exclusive_invite":
                        args = fn_call.args if fn_call.args else {}
                        tool_result = create_exclusive_invite(**args)
                        content_to_send.append(response.candidates[0].content)
                        content_to_send.append(types.Content(parts=[types.Part.from_function_response(name=fn_call.name, response={"result": tool_result})]))
                
                response = await asyncio.to_thread(self.client.models.generate_content, model=self.model_name, contents=content_to_send, config=genai_config)

            reply_text = response.text if response.text else "ประมวลผลเสร็จสิ้นครับท่านประธาน"

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

            plan_id = f"PLAN_{int(time.time())}"
            system_update_actions = []

            update_matches = re.finditer(r'\[UPDATE_SYSTEM_FILE:\s*(.+?)\](.*?)\[/UPDATE_SYSTEM_FILE\]', reply_text, re.DOTALL)
            for match in update_matches:
                target_path, target_code = match.group(1).strip(), match.group(2).strip()
                system_update_actions.append({"path": target_path, "content": target_code})
                reply_text = reply_text.replace(match.group(0), f"\n\n📂 **เตรียมแพตช์ไฟล์ระบบ:** `{target_path}` (รอการอนุมัติ)\n").strip()

            if "[REQUIRE_APPROVAL]" in reply_text or system_update_actions:
                reply_text = reply_text.replace("[REQUIRE_APPROVAL]", "").strip()
                self.pending_plans[plan_id] = {"report": reply_text, "actions": system_update_actions}
                return self._build_approval_flex_message(reply_text, plan_id)
            
            return {"type": "text", "text": reply_text}
            
        except Exception as e:
            logger.error(f"⚠️ [CEO Secretary Error]: {e}", exc_info=True)
            return {"type": "text", "text": f"เกิดข้อผิดพลาดทางวิศวกรรม ({str(e)[:50]}) ฝ่ายระบบกำลังตรวจสอบครับ"}
        finally:
            if uploaded_file:
                try: await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except Exception: pass

    async def _execute_approved_plan(self, action_data: str) -> dict:
        plan_id = action_data.split(":")[-1]
        plan = self.pending_plans.get(plan_id)
        if not plan: return {"type": "text", "text": "⚠️ แผนงานนี้หมดอายุหรือดำเนินการไปแล้วครับ"}

        actions, success_logs, error_logs = plan.get("actions", []), [], []
        for action in actions:
            target_path, new_content = action["path"], action["content"]
            try:
                os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
                if os.path.exists(target_path): shutil.copy2(target_path, f"{target_path}.{int(time.time())}.bak")
                with open(target_path, 'w', encoding='utf-8') as f: f.write(new_content)
                success_logs.append(target_path)
            except Exception as e: error_logs.append(f"{target_path} ({str(e)})")

        del self.pending_plans[plan_id]
        
        response_msg = "✅ **อนุมัติการดำเนินการสำเร็จครับท่านประธาน!**\n\n"
        if success_logs: response_msg += "💻 **ไฟล์ถูกแพตช์และอัปเดต:**\n" + "\n".join([f"- `{p}`" for p in success_logs])
        if error_logs: response_msg += "\n\n⚠️ **พบปัญหา:**\n" + "\n".join([f"- {e}" for e in error_logs])
        return {"type": "text", "text": response_msg}

    def _build_approval_flex_message(self, report_text: str, plan_id: str) -> dict:
        return {
            "type": "flex", "altText": "🚨 แฟ้มรายงานและโครงสร้างระบบจากเลขาฯ (รอพิจารณาอนุมัติ)",
            "contents": {
                "type": "bubble", "size": "giga",
                "header": {"type": "box", "layout": "vertical", "backgroundColor": "#050505", "contents": [
                    {"type": "text", "text": "👑 SUPREME SYSTEM OVERRIDE", "weight": "bold", "color": "#D4AF37", "size": "xl"},
                    {"type": "text", "text": "SECURITY & ARCHITECTURE VERIFIED", "color": "#00E5FF", "size": "xs", "margin": "sm"}
                ]},
                "body": {"type": "box", "layout": "vertical", "backgroundColor": "#0F0F13", "contents": [
                    {"type": "text", "text": "⚠️ วาระสำคัญ: แผนอัปเดตและแพตช์ระบบรอการอนุมัติ", "color": "#FF334B", "size": "sm", "weight": "bold"}, 
                    {"type": "text", "text": report_text[:400] + "...\n\n(กดอนุมัติเพื่อเขียนโค้ดทับเซิร์ฟเวอร์จริง)", "wrap": True, "size": "sm", "color": "#E0E0E0", "margin": "lg"}
                ]},
                "footer": {"type": "box", "layout": "vertical", "spacing": "md", "backgroundColor": "#050505", "contents": [
                    {"type": "button", "style": "primary", "color": "#00B900", "action": {"type": "message", "label": "✅ อนุมัติ (เขียนโค้ดทับระบบ)", "text": f"ACTION:APPROVE:{plan_id}"}}, 
                    {"type": "button", "style": "primary", "color": "#FF334B", "action": {"type": "message", "label": "❌ ปฏิเสธแผน (Reject)", "text": f"ACTION:REJECT:{plan_id}"}}
                ]}
            }
        }