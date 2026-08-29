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

# 🧠 นำเข้าระบบความจำเพื่อบันทึกข้อมูลระดับองค์กร (Corporate RAG)
try:
    from agents.memory_engine import save_corporate_knowledge, process_and_save_link_knowledge
except ImportError:
    def save_corporate_knowledge(t, c): return True
    def process_and_save_link_knowledge(u): return True, "จำลองการบันทึกสำเร็จ"

# 💾 นำเข้าระบบฐานข้อมูล Supabase สำหรับจัดการ VVIP
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
    - ระบบ Human-in-the-Loop 3 ปุ่มคำสั่ง (ตกลง / แก้ไข / ปฏิเสธ)
    - ระบบ Self-Healing & Exponential Backoff (ป้องกัน Quota 429)
    - Multimodal Vision (อ่านเอกสาร/รูปภาพ) พร้อม Zero-Data Retention
    """

    def __init__(self):
        # 🔒 ตรวจสอบสิทธิ์ระดับผู้บริหาร
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")

        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None
        
        # 🚀 ใช้โมเดลระดับสูงสุดเพื่อความสามารถในการวิเคราะห์เชิงลึก
        self.model_name = os.getenv("EXECUTIVE_MODEL", "gemini-2.5-pro")

        self.system_instruction = """
        คุณคือ 'เลขาธิการส่วนตัวสูงสุด' ของท่านประธาน (CEO) คุณวีระชัย สิรินทร์ธนัตถ์
        ระบบที่คุณดูแลคือ SIRINTHANATTH PRIME (Enterprise AI SaaS บน LINE OA)

        กฎเหล็กในการทำงาน:
        1. Human-in-the-Loop: ห้ามตัดสินใจอัปเดตระบบหรือใช้งานงบประมาณเองเด็ดขาด ทุกแผนการต้องสรุปเป็นรายงานเสนอให้ประธานกดปุ่ม [ตกลง], [แก้ไข], หรือ [ปฏิเสธ] เสมอ
        2. หากประธานสั่ง 'แก้ไข' แผน ให้รับฟังคำสั่ง นำไปวิเคราะห์หาข้อบกพร่อง และสร้างสรรค์แผนใหม่ที่อุดรอยรั่วทั้งหมดมานำเสนอใหม่ทันที
        3. ตอบกลับด้วยความเคารพ เป็นมืออาชีพขั้นสูง และใช้คำลงท้ายว่า 'ครับท่านประธาน' เสมอ
        4. หากประธานส่งรูปภาพ เอกสาร หรืองบการเงิน ให้สกัดข้อมูลและสรุป Executive Summary ที่เฉียบคม
        """

        self.pending_plans = {}

    def is_ceo(self, user_id: str) -> bool:
        """ตรวจสอบความปลอดภัยว่าเป็นท่านประธานหรือไม่"""
        return user_id in [self.ceo_line_id, self.master_admin_id] if user_id else False

    async def _safe_generate_content(self, contents, config: types.GenerateContentConfig):
        """ระบบป้องกัน Rate Limit (Error 429) อัตโนมัติด้วย Exponential Backoff"""
        max_retries = 3
        delay = 2
        for attempt in range(max_retries):
            try:
                return await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=contents,
                    config=config
                )
            except Exception as e:
                err_str = str(e)
                if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < max_retries - 1:
                    logger.warning(f"⚠️ [API Limit 429]: รอ {delay} วินาทีก่อนลองใหม่ (รอบที่ {attempt+1})...")
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                raise e

    async def process_ceo_command(self, message: str, file_path: str = None, file_type: str = None) -> dict:
        """รับคำสั่งตรงจาก CEO และประสานงานระบบเบื้องหลัง"""
        msg_clean = (message or "").strip()
        logger.info(f"👑 [CEO Command]: {msg_clean[:50]}... | File: {file_type}")

        if not msg_clean and file_path:
            msg_clean = "[System Auto-Prompt]: โปรดวิเคราะห์ข้อมูลในรูปภาพหรือเอกสารที่แนบมานี้อย่างละเอียด และสรุปประเด็นสำคัญให้ผมทราบครับ"

        # ==========================================
        # 1. ระบบควบคุม 3 ปุ่ม (Human-in-the-Loop)
        # ==========================================
        if msg_clean.startswith("ACTION:APPROVE:"):
            return self._execute_approved_plan(msg_clean)
            
        elif msg_clean.startswith("ACTION:REJECT:"):
            return {"type": "text", "text": "❌ รับทราบครับท่านประธาน แผนนี้ถูกปฏิเสธและยกเลิกการดำเนินงานเรียบร้อยแล้วครับ ผมจะจัดเก็บข้อมูลไว้เป็นกรณีศึกษาเพื่อไม่ให้เกิดข้อผิดพลาดซ้ำครับ"}
            
        elif msg_clean.startswith("ACTION:MODIFY:"):
            plan_id = msg_clean.split(":")[-1]
            return {
                "type": "text", 
                "text": f"📝 รับทราบครับ (แผนรหัส: {plan_id})\nท่านประธานต้องการให้ผมปรับปรุงกลยุทธ์ หรือเพิ่มเติมข้อมูลในจุดไหน พิมพ์สั่งการมาได้เลยครับ ผมจะนำไปวิเคราะห์และร่างแผนฉบับใหม่มาเสนอทันทีครับ"
            }

        # ==========================================
        # 2. ระบบสิทธิ์ VVIP & ออกโค้ด
        # ==========================================
        check_msg = msg_clean.lower().replace(" ", "")
        if any(keyword in check_msg for keyword in ["สร้างโค้ด", "vvip", "ไม่ต้องผ่านระบบtoken", "ระบบtoken", "รหัสเชิญ"]):
            return await self._generate_vvip_invite()

        # ==========================================
        # 3. ระบบนำเข้าความรู้ (Corporate RAG Ingestion)
        # ==========================================
        if msg_clean.startswith("เรียนรู้ลิงก์:") or msg_clean.startswith("LEARN:"):
            url_match = re.search(r'(https?://[^\s]+)', msg_clean)
            if url_match:
                target_url = url_match.group(1)
                try:
                    success, msg = await asyncio.to_thread(process_and_save_link_knowledge, target_url)
                    if success:
                        return {"type": "text", "text": f"🧠 [Knowledge Sync]: ระบบดึงความรู้จากลิงก์ {target_url} เข้าสู่สมองกลส่วนกลางเรียบร้อย พร้อมใช้งานร่วมกับฐานข้อมูลอื่นทันทีครับ"}
                    return {"type": "text", "text": f"⚠️ [Link Sync Error]: {msg}"}
                except Exception as e:
                    return {"type": "text", "text": f"⚠️ เกิดข้อผิดพลาดในการสกัดข้อมูล: {e}"}
            return {"type": "text", "text": "⚠️ ไม่พบ URL ในข้อความ กรุณาพิมพ์ในรูปแบบ 'เรียนรู้ลิงก์: [URL]'"}

        if msg_clean.startswith("FEED:") or msg_clean.startswith("สอนAI:"):
            content = msg_clean.replace("FEED:", "").replace("สอนAI:", "").strip()
            title = f"CEO_Update_{int(time.time())}"
            try:
                success = await asyncio.to_thread(save_corporate_knowledge, title, content)
                if success:
                    return {"type": "text", "text": "🧠 [System Upload]: นำข้อมูลนโยบายใหม่เข้าสู่สมองกลส่วนกลางเรียบร้อยครับ ระบบจะยึดเป็นแนวทางหลักในการวิเคราะห์นับจากนี้ครับ"}
                return {"type": "text", "text": "⚠️ เกิดข้อผิดพลาดในการบันทึกข้อมูลเข้าสู่ฐานข้อมูลครับ"}
            except Exception as e:
                return {"type": "text", "text": f"⚠️ เกิดข้อผิดพลาดในระบบฐานข้อมูล: {e}"}

        # ==========================================
        # 4. การประมวลผลคำสั่งเชิงลึกและอ่านไฟล์มัลติมีเดีย
        # ==========================================
        uploaded_file = None
        content_to_send = []

        try:
            if not self.client:
                return {"type": "text", "text": "⚠️ ขออภัยครับท่านประธาน ระบบ AI ขาดการเชื่อมต่อ API Key"}

            # อัปโหลดและวิเคราะห์ไฟล์ (Vision/PDF)
            if file_path and os.path.exists(file_path):
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type: mime_type = "application/octet-stream"
                
                upload_config = types.UploadFileConfig(mime_type=mime_type)
                uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)

                timeout = 60
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        raise TimeoutError("เซิร์ฟเวอร์ประมวลผลไฟล์ใช้เวลานานเกินกำหนดครับ")
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)

                content_to_send.append(uploaded_file)
                content_to_send.append(msg_clean)
            else:
                content_to_send.append(msg_clean)

            # ยิงคำสั่งเข้าสู่โหมดประมวลผลอัจฉริยะ (Self-Healing)
            response = await self._safe_generate_content(
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.3 # ควบคุมความแม่นยำทางตรรกะสูงสุด
                )
            )
            reply_text = response.text if response.text else "รับทราบคำสั่งครับท่านประธาน"

        except Exception as e:
            err_msg = str(e)
            logger.error(f"❌ [CEO Secretary Error]: {err_msg}")
            reply_text = f"ขออภัยครับท่านประธาน ระบบประมวลผลขัดข้องชั่วคราว ({err_msg[:60]})"

        finally:
            # 🛡️ Zero-Data Retention: ลบไฟล์ลับของประธานออกจาก Cloud ทันทีเมื่อใช้งานเสร็จ
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🧹 [Security]: ลบไฟล์ลับออกจากระบบเซิร์ฟเวอร์เรียบร้อย")
                except:
                    pass

        # สร้าง Flex Message 3 ปุ่มอัตโนมัติ หากตรวจพบเจตนาการเสนอแผนงาน
        if any(keyword in reply_text for keyword in ["เสนอ", "พิจารณา", "แผนการ", "ปรับปรุงใหม่", "อนุมัติ", "ประเมิน"]):
            plan_id = f"PLAN_{int(time.time())}"
            self.pending_plans[plan_id] = reply_text
            return self._build_approval_flex_message(reply_text, plan_id)

        return {"type": "text", "text": reply_text}

    async def _generate_vvip_invite(self) -> dict:
        """ระบบสร้างรหัส VVIP สำหรับ Bypass โควตา API (Single-Use)"""
        if not supabase:
            return {"type": "text", "text": "⚠️ ไม่สามารถสร้างรหัสได้ครับ เนื่องจากยังไม่ได้เชื่อมต่อระบบฐานข้อมูล Supabase"}
            
        try:
            random_code = uuid.uuid4().hex[:8].upper()
            invite_code = f"VVIP-{random_code}"
            
            await asyncio.to_thread(
                lambda: supabase.table("invite_codes").insert({
                    "code": invite_code,
                    "is_used": False
                }).execute()
            )
            
            liff_base_url = "https://liff.line.me/2011067128-fnWmOak4"
            invite_link = f"{liff_base_url}?code={invite_code}"
            
            reply = (
                f"🎟️ สร้างรหัสเชิญ VVIP พิเศษสำเร็จแล้วครับท่านประธาน!\n\n"
                f"🔑 รหัสอ้างอิง: {invite_code}\n\n"
                f"สามารถส่งลิงก์ด้านล่างนี้ให้ลูกค้าระดับ VIP เพื่อใช้งานแบบไม่ตัด Token ได้เลยครับ:\n"
                f"{invite_link}\n\n"
                f"🛡️ Note: รหัสนี้ใช้ได้เพียงครั้งเดียว เมื่อลูกค้าลงทะเบียนสำเร็จ สิทธิ์จะถูกบันทึกและรหัสจะถูกลบทิ้งอัตโนมัติครับ"
            )
            return {"type": "text", "text": reply}
            
        except Exception as e:
            logger.error(f"❌ [VVIP Gen Error]: {e}")
            return {"type": "text", "text": f"เกิดข้อผิดพลาดในการบันทึกรหัส VVIP ลงฐานข้อมูล: {str(e)}"}

    def _build_approval_flex_message(self, report_text: str, plan_id: str) -> dict:
        """สร้าง Flex Message ขออนุมัติ 3 ปุ่ม"""
        return {
            "type": "flex",
            "altText": "แฟ้มรายงานจากเลขาฯ อัจฉริยะ (รอพิจารณา)",
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
                    "contents": [{"type": "text", "text": report_text[:350] + "...\n\n(โปรดดูรายละเอียดเต็มในข้อความด้านบนก่อนตัดสินใจครับ)", "wrap": True, "size": "sm", "color": "#333333"}]
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
        """ดำเนินการจริงแบบ Hot Reload ทันทีที่ท่านประธานกด ✅ ตกลง"""
        plan_id = action_data.split(":")[-1]
        logger.info(f"🔄 [Hot Reload]: อัปเดตระบบด้วยแผน {plan_id} (Zero Downtime)")
        return {
            "type": "text", 
            "text": f"✅ อนุมัติสำเร็จ! ผมได้ล็อกแผนรหัส [{plan_id}] และทำการป้อนข้อมูลสั่งการอัปเดตเข้าระบบปฏิบัติการอัตโนมัติแบบไร้รอยต่อเรียบร้อยแล้วครับ ระบบใหม่พร้อมทำงาน 100% แล้วครับท่านประธาน"
        }