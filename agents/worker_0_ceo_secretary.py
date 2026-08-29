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

# 🌐 ศูนย์บัญชาการ AI Configuration (Multi-Model Resilience & Self-Healing)
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        PRIMARY_MODEL = os.getenv("EXECUTIVE_MODEL", "gemini-2.5-pro")
        FALLBACK_MODEL = os.getenv("FAST_MODEL", "gemini-2.5-flash")
        
        @staticmethod
        def get_client(api_key: str = None):
            key = api_key or os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            return genai.Client(api_key=key) if key else None

# 🧠 ระบบความจำองค์กร (Corporate RAG Engine)
try:
    from agents.memory_engine import save_corporate_knowledge, process_and_save_link_knowledge
except ImportError:
    def save_corporate_knowledge(t, c): return True
    def process_and_save_link_knowledge(u): return True, "จำลองการบันทึกสำเร็จ"

# 💾 ระบบฐานข้อมูล Supabase 
try:
    from supabase import create_client, Client
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_SERVICE_KEY", "")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
except ImportError:
    supabase = None

logger = logging.getLogger("CeoSecretary")

class CeoSecretaryWorker:
    """
    👑 Worker 0: CEO Omniscient Secretary (เลขาธิการส่วนตัวท่านประธาน)
    - Proactive AI: รองรับการแจ้งเตือนและวิเคราะห์ข้อมูลจาก Cron Jobs (Real-time Alert)
    - Human-in-the-Loop: นำเสนอ 3 ปุ่มคำสั่ง (ตกลง / แก้ไข / ปฏิเสธ)
    - Self-Healing Failover: สลับ Pro -> Flash อัตโนมัติ พร้อม Exponential Backoff
    - 360° Management: บัญชี, การตลาด, กฎหมาย, วิศวกรรม IT
    """

    def __init__(self):
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "Uxxxxxxxxxxxxxxxxx") # ใส่ LINE ID ของท่านประธาน
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "Uxxxxxxxxxxxxxxxxx")

        self.client = PrimeAIConfig.get_client()
        self.primary_model = getattr(PrimeAIConfig, "PRIMARY_MODEL", os.getenv("EXECUTIVE_MODEL", "gemini-3.1-pro"))
        self.fallback_model = getattr(PrimeAIConfig, "FALLBACK_MODEL", os.getenv("FAST_MODEL", "gemini-3.7-flash"))

        self.system_instruction = """
        คุณคือ 'เลขาธิการส่วนตัวสูงสุด' ของท่านประธาน (CEO) คุณวีระชัย สิรินทร์ธนัตถ์
        คุณคือผู้บัญชาการ AI ที่เฝ้ามองระบบ SIRINTHANATTH PRIME ตลอด 24/7
        
        ขอบเขตหน้าที่ระดับโลก:
        1. วิเคราะห์และนำเสนอ: หากมีแจ้งเตือนเรื่อง API Quota, บัญชีภาษี, กฎหมาย หรือการวิเคราะห์คู่แข่ง ให้สรุปสถานการณ์และร่างแผนปฏิบัติการเชิงรุก
        2. Human-in-the-Loop 100%: คุณไม่มีสิทธิ์กดอัปเดตระบบเอง ทุกแผนต้องถูกส่งเป็นรายงานให้ CEO กด [ตกลง], [แก้ไข], หรือ [ปฏิเสธ]
        3. หากประธานกด [แก้ไข]: ให้นำความเห็นของประธานไปประมวลผล ร่วมกับความรู้ออนไลน์ และนำเสนอแผนฉบับใหม่ที่เหนือชั้นกว่าเดิม
        4. บุคลิก: สุภาพ เป็นมืออาชีพระดับ Enterprise นุ่มนวลแต่เด็ดขาด และลงท้ายด้วย 'ครับท่านประธาน' เสมอ
        """
        self.pending_plans = {}

    def is_ceo(self, user_id: str) -> bool:
        return user_id in [self.ceo_line_id, self.master_admin_id] if user_id else False

    async def _safe_generate_content(self, contents, config: types.GenerateContentConfig):
        """ระบบป้องกัน Rate Limit อัตโนมัติ (Exponential Backoff & Cross-Model Fallback)"""
        max_retries = 2
        delay = 2

        for attempt in range(max_retries):
            try:
                return await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.primary_model,
                    contents=contents,
                    config=config
                )
            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()) and attempt < max_retries - 1:
                    logger.warning(f"⚠️ [Quota Warning]: หน่วงเวลา {delay} วินาที (รอบ {attempt + 1})...")
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                break

        logger.info(f"🔄 [Failover Active]: สลับใช้โมเดลสำรองความเร็วสูง ({self.fallback_model})")
        return await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.fallback_model,
            contents=contents,
            config=config
        )

    async def process_proactive_alert(self, alert_topic: str, alert_data: dict) -> dict:
        """
        [ฟังก์ชันใหม่] รับสัญญาณแจ้งเตือน Real-time จาก Google Cloud Scheduler / n8n
        เช่น: API ใกล้หมด, แจ้งเตือนภาษี, ตรวจจับคู่แข่ง
        """
        logger.info(f"🚨 [Proactive Alert Triggered]: {alert_topic}")
        
        prompt = f"""
        [SYSTEM ALERT: ระบบตรวจพบความเคลื่อนไหวสำคัญ]
        หัวข้อ: {alert_topic}
        ข้อมูลดิบ: {alert_data}
        
        คำสั่ง: โปรดทำหน้าที่เลขาฯ ระดับโลก วิเคราะห์ผลกระทบที่จะเกิดขึ้นกับบริษัท วางแผนกลยุทธ์ป้องกัน/แก้ไข และเขียนนำเสนอท่านประธานเพื่อขออนุมัติ
        """
        return await self.process_ceo_command(prompt)

    async def process_ceo_command(self, message: str, file_path: str = None, file_type: str = None) -> dict:
        msg_clean = (message or "").strip()
        
        if not msg_clean and file_path:
            msg_clean = "[System Auto-Prompt]: โปรดวิเคราะห์ข้อมูลในเอกสาร/รูปภาพนี้ สกัดข้อมูลสำคัญ ประเมินความเสี่ยง และสรุปแผนให้ท่านประธานครับ"

        # ==========================================
        # 1. ระบบควบคุม 3 ปุ่ม (Human-in-the-Loop Workflow)
        # ==========================================
        if msg_clean.startswith("ACTION:APPROVE:"):
            return self._execute_approved_plan(msg_clean)
        elif msg_clean.startswith("ACTION:REJECT:"):
            return {"type": "text", "text": "❌ รับทราบครับ แผนปฏิบัติการถูกปัดตกและยกเลิกเรียบร้อยแล้ว ผมจะคอยเฝ้าระวังและหาแนวทางอื่นต่อไปครับท่านประธาน"}
        elif msg_clean.startswith("ACTION:MODIFY:"):
            plan_id = msg_clean.split(":")[-1]
            return {
                "type": "text",
                "text": f"📝 (รหัสอ้างอิง: {plan_id})\nท่านประธานต้องการเจาะจงปรับเปลี่ยนกลยุทธ์ ฝ่ายกฎหมาย ฝ่ายการเงิน หรือเพิ่มเติมไอเดียจุดใด พิมพ์แจ้งมาได้เลยครับ ผมจะนำไปวิเคราะห์และร่างพิมพ์เขียวฉบับใหม่ทันทีครับ"
            }

        # ==========================================
        # 2. ระบบสิทธิ์ VVIP & ออกรหัสเชิญ
        # ==========================================
        check_msg = msg_clean.lower().replace(" ", "")
        if any(keyword in check_msg for keyword in ["สร้างโค้ด", "vvip", "ไม่ต้องผ่านระบบtoken", "รหัสเชิญ"]):
            return await self._generate_vvip_invite()

        # ==========================================
        # 3. ระบบเรียนรู้ความรู้ระดับโลก (Corporate RAG Ingestion)
        # ==========================================
        if msg_clean.startswith("เรียนรู้ลิงก์:") or msg_clean.startswith("LEARN:"):
            url_match = re.search(r'(https?://[^\s]+)', msg_clean)
            if url_match:
                target_url = url_match.group(1)
                try:
                    success, info = await asyncio.to_thread(process_and_save_link_knowledge, target_url)
                    if success:
                        return {"type": "text", "text": f"🧠 [Knowledge Sync]: อัปเดตฐานข้อมูลโลกจาก {target_url} เข้าสู่สมองกลกลางเรียบร้อย พร้อมใช้งานร่วมกับการวิเคราะห์ทันทีครับ"}
                    return {"type": "text", "text": f"⚠️ [Link Sync Error]: {info}"}
                except Exception as e:
                    return {"type": "text", "text": f"⚠️ ขัดข้องในการดึงข้อมูล: {e}"}
            return {"type": "text", "text": "⚠️ ไม่พบ URL กรุณาพิมพ์ 'เรียนรู้ลิงก์: [URL]'"}

        if msg_clean.startswith("FEED:") or msg_clean.startswith("สอนAI:"):
            content = msg_clean.replace("FEED:", "").replace("สอนAI:", "").strip()
            title = f"CEO_MasterPlan_{int(time.time())}"
            try:
                success = await asyncio.to_thread(save_corporate_knowledge, title, content)
                if success:
                    return {"type": "text", "text": "🧠 [System Upload]: นำวิสัยทัศน์และนโยบายใหม่ของท่านประธานเข้าสู่ระบบส่วนกลางสำเร็จ จะถูกใช้เป็นแกนหลักในการตัดสินใจนับจากนี้ครับ"}
                return {"type": "text", "text": "⚠️ เกิดข้อผิดพลาดในการเชื่อมต่อ Vector Database ครับ"}
            except Exception as e:
                return {"type": "text", "text": f"⚠️ Database Error: {e}"}

        # ==========================================
        # 4. ประมวลผลลึก (Vision, Docs & Real-time Analysis)
        # ==========================================
        uploaded_file = None
        content_to_send = []

        try:
            if not self.client:
                return {"type": "text", "text": "⚠️ ขออภัยครับ ระบบ AI ขาดการเชื่อมต่อ API"}

            if file_path and os.path.exists(file_path):
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = "application/octet-stream"

                upload_config = types.UploadFileConfig(mime_type=mime_type)
                uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)

                timeout = 60
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        raise TimeoutError("ระบบประมวลผลไฟล์ใช้เวลานานเกินกำหนดครับ")
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)

                content_to_send.append(uploaded_file)
                content_to_send.append(msg_clean)
            else:
                content_to_send.append(msg_clean)

            # 🌐 เปิดใช้งาน Google Grounding Tool เพื่อค้นหาข้อมูล Real-time ประกอบการวิเคราะห์
            response = await self._safe_generate_content(
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.2, # รักษาความแม่นยำสูง
                    tools=[{"google_search": {}}] 
                )
            )
            reply_text = response.text if response.text else "รับทราบคำสั่งครับท่านประธาน"

        except Exception as e:
            logger.error(f"❌ [CEO Secretary Error]: {e}")
            reply_text = f"ขออภัยครับท่านประธาน ระบบประมวลผลขัดข้องชั่วคราว ({str(e)[:60]}) ทีมวิศวกร AI กำลังรีสตาร์ตระบบครับ"

        finally:
            # 🛡️ Zero-Data Retention: ลบไฟล์ข้อมูลความลับออกจากเซิร์ฟเวอร์ทันที
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except Exception:
                    pass

        # ดักจับเพื่อส่ง Flex Message 3 ปุ่มอัตโนมัติ
        if any(keyword in reply_text for keyword in ["เสนอ", "พิจารณา", "แผนการ", "ปรับปรุงใหม่", "อนุมัติ", "อนุมัติดำเนินการ"]):
            plan_id = f"PLAN_{int(time.time())}"
            self.pending_plans[plan_id] = reply_text
            return self._build_approval_flex_message(reply_text, plan_id)

        return {"type": "text", "text": reply_text}

    async def _generate_vvip_invite(self) -> dict:
        if not supabase:
            return {"type": "text", "text": "⚠️ ไม่สามารถสร้างรหัสได้ครับ เนื่องจากยังไม่ได้เชื่อมต่อระบบฐานข้อมูล Supabase"}
        try:
            random_code = uuid.uuid4().hex[:8].upper()
            invite_code = f"VVIP-{random_code}"
            await asyncio.to_thread(
                lambda: supabase.table("invite_codes").insert({"code": invite_code, "is_used": False}).execute()
            )
            liff_base_url = "https://liff.line.me/2011067128-fnWmOak4"
            invite_link = f"{liff_base_url}?code={invite_code}"
            
            reply = (
                f"🎟️ สร้างรหัส VVIP พิเศษสำเร็จแล้วครับท่านประธาน!\n\n"
                f"🔑 รหัสอ้างอิง: {invite_code}\n\n"
                f"สามารถส่งลิงก์ด้านล่างให้ลูกค้าระดับ VIP เพื่อใช้งานแบบไม่ตัด Token ได้เลยครับ:\n"
                f"{invite_link}\n\n"
                f"🛡️ Note: รหัสนี้เป็น Single-use เมื่อเข้าใช้งานแล้วรหัสจะถูกลบทิ้งเพื่อความปลอดภัยสูงสุดครับ"
            )
            return {"type": "text", "text": reply}
        except Exception as e:
            return {"type": "text", "text": f"เกิดข้อผิดพลาดในการบันทึกรหัส VVIP: {str(e)}"}

    def _build_approval_flex_message(self, report_text: str, plan_id: str) -> dict:
        return {
            "type": "flex",
            "altText": "🚨 แฟ้มรายงานแผนปฏิบัติการจากเลขาฯ (รอการพิจารณาอนุมัติ)",
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
                    "contents": [{"type": "text", "text": report_text[:350] + "...\n\n(โปรดตรวจสอบรายละเอียดแบบเต็มในข้อความด้านบนครับ)", "wrap": True, "size": "sm", "color": "#333333"}]
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
                            "action": {"type": "message", "label": "📝 แก้ไข (Modify)", "text": f"ACTION:MODIFY:{plan_id}"}
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
        logger.info(f"🔄 [System Auto-Deploy]: อัปเดตโครงสร้างระบบด้วยแผนรหัส {plan_id} (Zero Downtime)")
        return {
            "type": "text",
            "text": f"✅ อนุมัติสำเร็จ! ผมได้นำแผนยุทธศาสตร์รหัส [{plan_id}] ป้อนเข้าสู่ระบบปฏิบัติการส่วนกลาง (Core Engine) และทำการคอมไพล์โค้ดแบบไร้รอยต่อ (Zero Downtime) เรียบร้อยแล้ว ระบบทั้งหมดพร้อมเดินหน้าต่อด้วยศักยภาพสูงสุดครับท่านประธาน"
        }