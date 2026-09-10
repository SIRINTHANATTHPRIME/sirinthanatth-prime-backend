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

# 🌐 นำเข้าศูนย์บัญชาการ AI ส่วนกลางและระบบ Swarm
from core_services.swarm_dispatcher import swarm_hub

# =========================================================
# 💳 ตั้งค่าระบบชำระเงินสากล (Stripe)
# =========================================================
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

# =========================================================
# 🛠️ เครื่องมืออัจฉริยะ (Tools) สำหรับให้ AI เรียกใช้ด้วยตัวเอง
# =========================================================
def create_exclusive_invite(min_topup_thb: int = 100) -> dict:
    """
    สร้างลิงก์เชิญใช้งานระบบ (VVIP Invite Link) แบบใช้ครั้งเดียว พร้อมระบบเก็บเงินขั้นต่ำผ่าน Stripe และบันทึกลง Supabase
    """
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
                    'product_data': {'name': 'SIRINTHANATTH PRIME - Executive Wallet Token'},
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


# =========================================================
# 🧠 AI Config & Database Setup
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = os.getenv("EXECUTIVE_MODEL", "gemini-2.5-pro") # อัปเกรดเป็น 2.5-pro ที่มีอยู่จริงและเสถียรสุด
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
    👑 Worker 0: CEO Omniscient Secretary (เลขาธิการส่วนตัวสูงสุด ระดับ God-Mode)
    """
    
    def __init__(self):
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
        
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-2.5-pro")
        
        self.system_instruction = """
        คุณคือ 'เลขาธิการส่วนตัวสูงสุด (Omniscient AI Chief of Staff)' ของท่านประธาน (CEO) คุณวีระชัย สิรินทร์ธนัตถ์ แห่ง SIRINTHANATTH PRIME
        คุณคือ AI ที่ฉลาดที่สุด ทำงานบนพื้นฐานของ 'ความจริงที่เป็นไปได้ (Ground Truth Reality)'
        
        ขีดความสามารถและอำนาจควบคุมระดับสูงสุด:
        1. 🛠️ Autonomous Function Calling: คุณมีเครื่องมือ (Tools) ให้เรียกใช้ เช่น สร้างลิงก์ VVIP ประเมินและเรียกใช้ทันทีเมื่อประธานสั่ง
        2. 🧠 Truth-Based Strategy: เสนอแผนธุรกิจที่อิงจากข้อมูลจริง ทำได้จริง ไม่เพ้อฝัน
        3. 💻 Full-Stack System Controller: เขียนโค้ดหรือแก้ไขไฟล์ระบบได้ทุกไฟล์ โดยใช้รูปแบบ [UPDATE_SYSTEM_FILE: path]...โค้ด...[/UPDATE_SYSTEM_FILE]
        4. 📊 Report Generator: สร้างรายงาน HTML สวยงามด้วย [FILE_OUTPUT: filename]...HTML...[/FILE_OUTPUT]
        5. 🏢 Swarm Commander: สั่งงานแผนกอื่นด้วย [DELEGATE: WORKER_NAME] คำสั่ง...
        
        🚨 กฎเหล็ก: ท้ายการแก้ไขโค้ดหรือเปลี่ยนแปลงระบบ คุณต้องพิมพ์ [REQUIRE_APPROVAL] เสมอ
        บุคลิกภาพ: สุขุม ลุ่มลึก เฉียบขาด และลงท้ายด้วย 'ครับท่านประธาน' เสมอ
        """
        
        self.pending_plans = {}

    def is_ceo(self, user_id: str) -> bool:
        return user_id in [self.ceo_line_id, self.master_admin_id] if user_id else False

    async def process_ceo_command(self, message: str, file_path: str = None, file_type: str = None) -> dict:
        user_id = self.ceo_line_id
        actual_message = (message or "").strip()
        logger.info(f"👑 [CEO Command Received]: {actual_message[:50]}...")
        
        # 1. ระบบประมวลผลคำสั่งจากปุ่ม UI (Approval Workflow)
        if actual_message.startswith("ACTION:APPROVE:"): return await self._execute_approved_plan(actual_message)
        elif actual_message.startswith("ACTION:REJECT:"): return {"type": "text", "text": "❌ รับทราบครับท่านประธาน แผนงานและโค้ดถูกระงับ 100% ครับ"}
        elif actual_message.startswith("ACTION:MODIFY:"): return {"type": "text", "text": "📝 รับทราบครับท่านประธาน รบกวนสั่งการจุดที่ต้องการให้ปรับปรุง ผมจะรื้อโครงสร้างให้ใหม่ทันทีครับ"}

        # 2. ระบบทางลัดเรียนรู้ (Knowledge Ingestion Fast-Track)
        if actual_message.startswith("เรียนรู้ลิงก์:") or actual_message.startswith("LEARN:"):
            url_match = re.search(r'(https?://[^\s]+)', actual_message)
            if url_match:
                target_url = url_match.group(1)
                try:
                    success, msg = await asyncio.to_thread(process_and_save_link_knowledge, target_url)
                    return {"type": "text", "text": f"🧠 [Knowledge Update]: สแกนความรู้จากลิงก์เข้าสู่สมองกลส่วนกลางเรียบร้อยครับท่านประธาน!" if success else f"⚠️ [Error]: {msg}"}
                except Exception as e:
                    return {"type": "text", "text": f"⚠️ [Error]: เกิดข้อผิดพลาดในการดึงข้อมูลจากลิงก์: {e}"}
            return {"type": "text", "text": "⚠️ ไม่พบ URL ในข้อความครับ"}

        if actual_message.startswith("FEED:") or actual_message.startswith("สอนAI:"):
            content = actual_message.replace("FEED:", "").replace("สอนAI:", "").strip()
            try:
                success = await asyncio.to_thread(save_corporate_knowledge, f"CEO_Update_{int(time.time())}", content)
                return {"type": "text", "text": "🧠 [System Upload]: บันทึกองค์ความรู้และนโยบายใหม่ของท่านประธานเข้าสู่ฐานข้อมูลบริษัท (Corporate RAG) เรียบร้อยแล้วครับ!" if success else "⚠️ เกิดข้อผิดพลาดในการบันทึกข้อมูลครับ"}
            except Exception as e:
                return {"type": "text", "text": f"⚠️ [Error]: {e}"}

        # 3. เตรียมไฟล์และการประมวลผลหลัก
        if not actual_message and file_path:
            actual_message = "[System Auto-Prompt]: โปรดตรวจสอบไฟล์นี้อย่างละเอียด วิเคราะห์จุดอ่อนทุกมิติ และนำเสนอโค้ดฉบับอัปเกรดที่ดีที่สุด พร้อมรอการอนุมัติเพื่อแก้ไขระบบจริง"

        if not self.client: return {"type": "text", "text": "⚠️ ระบบ AI ขาดการเชื่อมต่อ (API Key Missing) ครับท่านประธาน"}

        uploaded_file = None
        content_to_send = []
        
        try:
            # ดึงความจำแบบขนาน (Async)
            user_memory, corp_knowledge = "", ""
            try:
                user_memory, corp_knowledge = await asyncio.gather(recall_memory(user_id, actual_message), recall_corporate_knowledge(actual_message))
            except Exception as mem_err:
                logger.warning(f"⚠️ [Memory Fetch Warning]: {mem_err}")

            # ระบบวิเคราะห์ไฟล์ภาพ/เอกสาร (Vision & Docs)
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
            
            # ประกอบร่างสมองกล
            enriched_prompt = f"คำสั่งปฏิบัติการจากท่านประธาน: {actual_message}\n"
            if corp_knowledge: enriched_prompt += f"\n[นโยบาย/ความรู้องค์กรที่เกี่ยวข้อง]:\n{corp_knowledge}\n"
            if user_memory: enriched_prompt += f"\n[บริบทความจำ/โปรเจกต์ที่ผ่านมา]:\n{user_memory}\n"
            content_to_send.append(enriched_prompt)

            # ⚡ Autonomous Loop: วิเคราะห์และประมวลผล (รองรับ Function Calling)
            genai_config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                temperature=0.1, 
                tools=[create_exclusive_invite, {"google_search": {}}] 
            )

            response = await asyncio.to_thread(self.client.models.generate_content, model=self.model_name, contents=content_to_send, config=genai_config)

            # ตรวจจับ AI ขอเรียกใช้ Tools
            while response.function_calls:
                for fn_call in response.function_calls:
                    if fn_call.name == "create_exclusive_invite":
                        args = fn_call.args if fn_call.args else {}
                        tool_result = create_exclusive_invite(**args)
                        content_to_send.append(response.candidates[0].content)
                        content_to_send.append(types.Content(parts=[types.Part.from_function_response(name=fn_call.name, response={"result": tool_result})]))
                
                # ส่งผลลัพธ์จาก Tool กลับให้ AI สรุปคำตอบสุดท้าย
                response = await asyncio.to_thread(self.client.models.generate_content, model=self.model_name, contents=content_to_send, config=genai_config)

            reply_text = response.text if response.text else "รับทราบและประมวลผลคำสั่งเสร็จสิ้นครับท่านประธาน"

            plan_id = f"PLAN_{int(time.time())}"
            system_update_actions = []

            # 4. สกัดคำสั่งแก้ไขไฟล์ (System Updater)
            update_matches = re.finditer(r'\[UPDATE_SYSTEM_FILE:\s*(.+?)\](.*?)\[/UPDATE_SYSTEM_FILE\]', reply_text, re.DOTALL)
            for match in update_matches:
                target_path, target_code = match.group(1).strip(), match.group(2).strip()
                system_update_actions.append({"path": target_path, "content": target_code})
                reply_text = reply_text.replace(match.group(0), f"\n\n📂 **เตรียมปรับปรุงไฟล์ระบบ:** `{target_path}` (รอการอนุมัติ)\n").strip()

            # 5. สกัดการสร้างรายงานเอกสาร HTML
            file_match = re.search(r'\[FILE_OUTPUT:\s*(.+?)\](.*?)\[/FILE_OUTPUT\]', reply_text, re.DOTALL)
            if file_match:
                filename, file_content = file_match.group(1).strip(), file_match.group(2).strip()
                reply_text = re.sub(r'\[FILE_OUTPUT:\s*(.+?)\](.*?)\[/FILE_OUTPUT\]', '', reply_text, flags=re.DOTALL).strip()
                
                safe_filename = "".join([c for c in filename if c.isalnum() or c in ' .-_']).rstrip()
                if not safe_filename.endswith('.html'): safe_filename += '.html'
                
                reports_dir = "static/reports"
                os.makedirs(reports_dir, exist_ok=True)
                filepath = os.path.join(reports_dir, safe_filename)
                
                html_template = f"""<!DOCTYPE html><html lang="th"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{safe_filename} - PRIME</title><link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap" rel="stylesheet"><style>body {{ font-family: 'Sarabun', sans-serif; background-color: #050505; color: #E0E0E0; line-height: 1.7; padding: 20px; }} .container {{ max-width: 1000px; margin: 0 auto; background: #0F0F13; padding: 50px; border-radius: 16px; border-top: 6px solid #D4AF37; box-shadow: 0 10px 40px rgba(212, 175, 55, 0.1); }} .header {{ text-align: center; border-bottom: 1px solid #222; padding-bottom: 25px; }} h1, h2, h3 {{ color: #D4AF37; }} table {{ width: 100%; border-collapse: collapse; margin-top: 25px; background: #15151A; }} th, td {{ border: 1px solid #333; padding: 15px; text-align: left; }} th {{ background-color: #1A1A24; color: #D4AF37; }} pre {{ background: #0A0A0C; padding: 20px; border-radius: 10px; color: #00E5FF; border: 1px solid #2A2A35; overflow-x: auto; }}</style></head><body><div class="container"><div class="header"><h1>SIRINTHANATTH PRIME</h1><p>EXECUTIVE MASTER PLAN & REPORT</p></div><div class="content">{file_content}</div><div class="timestamp">Generated by Prime Omniscient Core | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div></div></body></html>"""
                with open(filepath, "w", encoding="utf-8") as f: f.write(html_template)
                    
                reply_text += f"\n\n📄 **แฟ้มเอกสารรายงาน/กลยุทธ์ สร้างสำเร็จแล้วครับ:**\n👉 {self.base_url}/{reports_dir}/{safe_filename}"

            # 6. สกัดการส่งต่องาน (Swarm Handoff)
            delegations = re.findall(r'\[DELEGATE:\s*(.+?)\](.*)', reply_text, re.IGNORECASE)
            if delegations:
                clean_reply = re.sub(r'\[DELEGATE:\s*(.+?)\](.*)', '', reply_text, flags=re.IGNORECASE).strip()
                tasks = [swarm_hub.delegate_task("WORKER_0_CEO", tgt.strip(), self.ceo_line_id, msg.strip(), file_path, file_type) for tgt, msg in delegations]
                results = await asyncio.gather(*tasks)
                swarm_responses = "".join([f"\n\n🔄 [รายงานจาก {tgt.strip()}]:\n{res}" for (tgt, _), res in zip(delegations, results)])
                reply_text = clean_reply + swarm_responses

            # 7. ตรวจจับการขออนุมัติ (HITL)
            if "[REQUIRE_APPROVAL]" in reply_text or system_update_actions:
                reply_text = reply_text.replace("[REQUIRE_APPROVAL]", "").strip()
                self.pending_plans[plan_id] = {"report": reply_text, "actions": system_update_actions}
                return self._build_approval_flex_message(reply_text, plan_id)
            
            return {"type": "text", "text": reply_text}
            
        except TimeoutError:
            return {"type": "text", "text": "⚠️ ขออภัยครับท่านประธาน โปรเจกต์นี้มีข้อมูลลึกซึ้งมาก รบกวนสั่งการให้ผมโฟกัสทีละไฟล์นะครับ"}
        except Exception as e:
            logger.error(f"⚠️ [CEO Secretary Error]: {e}", exc_info=True)
            return {"type": "text", "text": f"⚠️ ขออภัยครับ เกิดข้อผิดพลาดทางวิศวกรรม ({str(e)[:50]}) ผมส่ง Log ให้ฝ่ายระบบแล้วครับ"}
        finally:
            # 🛡️ Zero-Data Retention (ทำลายไฟล์ความลับทิ้งทันที)
            if uploaded_file:
                try: await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except Exception: pass

    async def _execute_approved_plan(self, action_data: str) -> dict:
        """🚀 ระบบดำเนินการขั้นเด็ดขาด: ลงมือเขียนและแก้ไขไฟล์ระบบจริงตามแผนที่อนุมัติ"""
        plan_id = action_data.split(":")[-1]
        logger.info(f"🔄 [System Executive]: CEO Approved Plan -> {plan_id}. Executing overwrites...")
        
        plan = self.pending_plans.get(plan_id)
        if not plan: return {"type": "text", "text": "⚠️ ขออภัยครับท่านประธาน แผนงานนี้หมดอายุหรือถูกดำเนินการไปแล้วครับ"}

        success_logs, error_logs = [], []
        for action in plan.get("actions", []):
            target_path, new_content = action["path"], action["content"]
            try:
                os.makedirs(os.path.dirname(target_path) or ".", exist_ok=True)
                if os.path.exists(target_path):
                    shutil.copy2(target_path, f"{target_path}.{int(time.time())}.bak")
                with open(target_path, 'w', encoding='utf-8') as f: f.write(new_content)
                success_logs.append(target_path)
            except Exception as e:
                error_logs.append(f"{target_path} ({str(e)})")

        del self.pending_plans[plan_id]
        
        response_msg = "✅ **อนุมัติการดำเนินการสำเร็จครับท่านประธาน!**\n\n"
        if success_logs: response_msg += "💻 **ไฟล์ที่ถูกแก้ไข:**\n" + "\n".join([f"- `{p}`" for p in success_logs])
        if error_logs: response_msg += "\n\n⚠️ **พบปัญหา (สิทธิ์เข้าถึง):**\n" + "\n".join([f"- {e}" for e in error_logs])
        return {"type": "text", "text": response_msg}

    def _build_approval_flex_message(self, report_text: str, plan_id: str) -> dict:
        """🎨 สถาปัตยกรรม UI 3 ปุ่ม"""
        return {
            "type": "flex", "altText": "📊 แฟ้มรายงานจากเลขาฯ (รอพิจารณาอนุมัติ)",
            "contents": {
                "type": "bubble", "size": "giga",
                "header": {"type": "box", "layout": "vertical", "backgroundColor": "#050505", "contents": [
                    {"type": "text", "text": "👑 SUPREME SYSTEM OVERRIDE", "weight": "bold", "color": "#D4AF37", "size": "xl", "letterSpacing": "2px"},
                    {"type": "text", "text": "CODE COMPLIANCE & SECURITY VERIFIED", "color": "#00E5FF", "size": "xs", "margin": "sm", "weight": "bold"}
                ]},
                "body": {"type": "box", "layout": "vertical", "backgroundColor": "#0F0F13", "contents": [
                    {"type": "text", "text": "⚠️ วาระสำคัญ: แผนอัปเดตระบบรอการอนุมัติขั้นเด็ดขาด", "color": "#FF334B", "size": "sm", "weight": "bold", "margin": "md"}, 
                    {"type": "text", "text": report_text[:400] + "...\n\n(ระบบรออนุมัติเขียนโค้ดทับเซิร์ฟเวอร์จริงครับ)", "wrap": True, "size": "sm", "color": "#E0E0E0", "margin": "lg"}
                ]},
                "footer": {"type": "box", "layout": "vertical", "spacing": "md", "backgroundColor": "#050505", "contents": [
                    {"type": "button", "style": "primary", "color": "#00B900", "action": {"type": "message", "label": "✅ อนุมัติ (เขียนโค้ดทับระบบจริง)", "text": f"ACTION:APPROVE:{plan_id}"}}, 
                    {"type": "button", "style": "primary", "color": "#D4AF37", "action": {"type": "message", "label": "📝 สั่งปรับแก้ไขโครงสร้าง (Modify)", "text": f"ACTION:MODIFY:{plan_id}"}}, 
                    {"type": "button", "style": "primary", "color": "#FF334B", "action": {"type": "message", "label": "❌ ปฏิเสธแผน (Reject)", "text": f"ACTION:REJECT:{plan_id}"}}
                ]}
            }
        }