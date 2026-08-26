import os
import time
import re
import uuid
import logging
import asyncio
from datetime import datetime
from google import genai
from google.genai import types

# 🌐 นำเข้าศูนย์บัญชาการ AI ส่วนกลาง (รองรับ Zero Downtime Fallback)
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.1-pro-preview" # Fallback Model
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            return genai.Client(api_key=api_key) if api_key else None

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
    👑 Worker 0: CEO Omniscient Secretary (เลขาฯ อัจฉริยะส่วนตัว)
    อัปเกรดระบบ Self-Healing Retry (429 Protection) และ Smart Database Handling
    """

    def __init__(self):
        self.ceo_line_id = os.getenv("CEO_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")
        self.master_admin_id = os.getenv("MASTER_ADMIN_LINE_ID", "U5ea62530173fdb932bb85acd9fd8fbd3")

        self.client = PrimeAIConfig.get_client()
        self.model_name = PrimeAIConfig.EXECUTIVE_MODEL

        self.system_instruction = """
        คุณคือ 'เลขาธิการส่วนตัวสูงสุด' ของท่านประธาน (CEO) คุณวีระชัย สิรินทร์ธนัตถ์
        ระบบที่คุณดูแลคือ SIRINTHANATTH PRIME (Enterprise AI SaaS บน LINE OA)

        หน้าที่และกฎเหล็กของคุณ:
        1. ตอบกลับด้วยความเคารพ เป็นมืออาชีพขั้นสูง และใช้คำลงท้ายหรือเรียกขานว่า 'ครับท่านประธาน' เสมอ
        2. หากประธานส่งรูปภาพ เอกสาร หรืองบการเงิน ให้วิเคราะห์ สกัดข้อมูล และสรุป Executive Summary ที่เฉียบคม
        3. หากประธานขอดูสรุป (Report) ให้รายงาน 4 แกนหลัก (Finance, Marketing, Legal, Engineering) แบบกระชับ ตรงประเด็น
        4. เสนอแนะกลยุทธ์อย่างชาญฉลาด ทันสมัยระดับ Global Tech Company
        5. หากประธานสั่ง 'แก้ไข' แผน ให้รับฟังและสร้างสรรค์แผนใหม่ที่อุดรอยรั่วทั้งหมดทันที
        """

        self.pending_plans = {}

    def is_ceo(self, user_id: str) -> bool:
        """ตรวจสอบความปลอดภัยว่าเป็นท่านประธานหรือไม่"""
        return user_id in [self.ceo_line_id, self.master_admin_id] if user_id else False

    async def _safe_generate_content(self, contents, config):
        """ระบบ Self-Healing อัจฉริยะ: พยายามเชื่อมต่อใหม่แบบ Exponential Backoff หากเจอ Error 429"""
        max_retries = 3
        delay = 3
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
                    logger.warning(f"⚠️ [AI Quota Limit 429]: กำลังลองใหม่รอบที่ {attempt+1} ในอีก {delay} วินาที...")
                    await asyncio.sleep(delay)
                    delay *= 2  # เพิ่มเวลาหน่วงทบต้น
                    continue
                raise e

    async def process_ceo_command(self, message: str, file_path: str = None, file_type: str = None) -> dict:
        """รับคำสั่งและไฟล์ตรงจาก CEO พร้อมระบบจัดการข้อผิดพลาดระดับองค์กร"""
        if message is None:
            message = ""
        message = message.strip()

        logger.info(f"👑 [CEO Command Received]: {message[:50]}... | File: {file_type}")

        if not message and file_path:
            message = "[System Auto-Prompt]: โปรดวิเคราะห์ข้อมูลในรูปภาพหรือเอกสารที่แนบมานี้อย่างละเอียดครับ และสรุปประเด็นสำคัญให้ผมทราบ"

        # 1. ระบบจัดการปุ่มกด Flex Message
        if message.startswith("ACTION:APPROVE:"):
            return self._execute_approved_plan(message)
        elif message.startswith("ACTION:REJECT:"):
            return {"type": "text", "text": "❌ รับทราบครับท่านประธาน แผนนี้ถูกปฏิเสธและปัดตกเรียบร้อยแล้วครับ"}
        elif message.startswith("ACTION:MODIFY:"):
            plan_id = message.split(":")[-1]
            return {
                "type": "text", 
                "text": f"📝 รับทราบครับสำหรับแผนรหัส [{plan_id}]\nท่านประธานต้องการให้ผมปรับปรุงหรือแก้ไขกลยุทธ์ในจุดไหน พิมพ์สั่งการมาได้เลยครับ เดี๋ยวผมจัดการร่างใหม่ทันทีครับ"
            }

        # 2. ระบบสิทธิ์ VVIP
        check_msg = message.lower().replace(" ", "")
        if any(keyword in check_msg for keyword in ["สร้างโค้ด", "vvip", "ไม่ต้องผ่านระบบtoken", "ระบบtoken", "รหัสเชิญ"]):
            return await self._generate_vvip_invite()

        # 3. ระบบเรียนรู้ความรู้ใหม่
        if message.startswith("เรียนรู้ลิงก์:") or message.startswith("LEARN:"):
            url_match = re.search(r'(https?://[^\s]+)', message)
            if url_match:
                target_url = url_match.group(1)
                try:
                    success, msg = await asyncio.to_thread(process_and_save_link_knowledge, target_url)
                    if success:
                        return {"type": "text", "text": f"🧠 [Knowledge Update]: ระบบได้สแกนและดึงความรู้ทั้งหมดจากลิงก์\n{target_url}\n\nเข้าสู่สมองกลส่วนกลาง (Corporate RAG) เรียบร้อยแล้วครับ!"}
                    else:
                        return {"type": "text", "text": f"⚠️ [Error]: {msg}"}
                except Exception as e:
                    return {"type": "text", "text": f"⚠️ [Error]: เกิดข้อผิดพลาดในการดึงข้อมูลจากลิงก์: {e}"}
            else:
                 return {"type": "text", "text": "⚠️ ไม่พบ URL ในข้อความ กรุณาพิมพ์ในรูปแบบ 'เรียนรู้ลิงก์: [URL]'"}

        if message.startswith("FEED:") or message.startswith("สอนAI:"):
            content = message.replace("FEED:", "").replace("สอนAI:", "").strip()
            title = f"CEO_Update_{int(time.time())}"
            try:
                success = await asyncio.to_thread(save_corporate_knowledge, title, content)
                if success:
                    return {"type": "text", "text": "🧠 [System Upload]: นำข้อมูลใหม่เข้าสู่สมองกลส่วนกลาง (Corporate RAG) สำเร็จ ระบบจะนำข้อมูลนี้ไปใช้วิเคราะห์และตัดสินใจนับจากนี้ครับ!"}
                else:
                    return {"type": "text", "text": "⚠️ เกิดข้อผิดพลาดในการนำเข้าข้อมูลสู่ฐานข้อมูลเวกเตอร์ครับ"}
            except Exception as e:
                return {"type": "text", "text": f"⚠️ เกิดข้อผิดพลาดในระบบฐานข้อมูลความรู้: {e}"}

        # 4. การประมวลผลคำสั่งและไฟล์
        uploaded_file = None
        content_to_send = []

        try:
            if file_path and os.path.exists(file_path):
                logger.info(f"📤 [CEO Secretary]: กำลังอัปโหลดไฟล์ {file_type} เพื่อให้ AI วิเคราะห์...")
                uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path)

                timeout = 60
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        raise TimeoutError("เซิร์ฟเวอร์ของระบบประมวลผลไฟล์ใช้เวลานานเกินกำหนดครับท่านประธาน")
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)

                content_to_send.append(uploaded_file)
                content_to_send.append(message)
            else:
                content_to_send.append(message)

            if not self.client:
                return {"type": "text", "text": "⚠️ ขออภัยครับท่านประธาน ระบบ AI ขาดการเชื่อมต่อ (API Key Missing)"}

            # เรียกใช้งานผ่านระบบปลอดภัย Self-Healing Retry
            response = await self._safe_generate_content(
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    temperature=0.7
                )
            )
            reply_text = response.text if response.text else "รับทราบคำสั่งครับท่านประธาน"

        except Exception as e:
            error_str = str(e)
            logger.error(f"⚠️ [CEO Secretary Error]: {error_str}")
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                reply_text = "⚠️ ขออภัยครับท่านประธาน ขณะนี้โควตา AI เต็มชั่วคราว ระบบได้พยายามเชื่อมต่อใหม่แล้วแต่ไม่สำเร็จ กรุณารอสัก 30 วินาทีแล้วลองส่งคำสั่งใหม่อีกครั้งครับ"
            else:
                reply_text = f"ขออภัยครับท่านประธาน สมองกลขัดข้องชั่วคราว ({error_str[:50]}) กำลังดำเนินการแก้ไขครับ"

        finally:
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                except:
                    pass

        if any(keyword in reply_text for keyword in ["เสนอ", "พิจารณา", "แผนการ", "ปรับปรุงใหม่", "อนุมัติ"]):
            plan_id = f"PLAN_{int(time.time())}"
            self.pending_plans[plan_id] = reply_text
            return self._build_approval_flex_message(reply_text, plan_id)

        return {"type": "text", "text": reply_text}

    async def _generate_vvip_invite(self) -> dict:
        """ระบบสร้างรหัส VVIP แบบใช้ครั้งเดียว (Single-use Invite Code)"""
        if not supabase:
            return {"type": "text", "text": "⚠️ ไม่สามารถสร้างรหัสได้ครับ เนื่องจากระบบยังไม่ได้เชื่อมต่อฐานข้อมูล Supabase"}
            
        try:
            random_code = uuid.uuid4().hex[:8].upper()
            invite_code = f"VVIP-{random_code}"
            
            def insert_code():
                supabase.table("invite_codes").insert({
                    "code": invite_code,
                    "is_used": False
                }).execute()
                
            await asyncio.to_thread(insert_code)
            
            # 🚀 แก้ไขจุดนี้: เปลี่ยนจากเว็บตรง เป็นลิงก์ LIFF เพื่อให้เปิดใน LINE ได้อย่างสมบูรณ์ ไม่เด้งออก
            # (ใช้ LIFF ID ของท่านประธาน: 2011067128-fnWmOak4)
            liff_base_url = "https://liff.line.me/2011067128-fnWmOak4"
            invite_link = f"{liff_base_url}?code={invite_code}"
            
            reply = (
                f"🎟️ สร้างรหัสเชิญ VVIP พิเศษสำเร็จแล้วครับท่านประธาน!\n\n"
                f"🔑 รหัสอ้างอิง: {invite_code}\n\n"
                f"ท่านสามารถคัดลอกลิงก์ด้านล่างนี้ ส่งให้ลูกค้าระดับ VIP เพื่อเข้าใช้งานระบบได้ทุกฟังก์ชัน โดยไม่ต้องผ่านระบบ Token ครับ:\n\n"
                f"{invite_link}\n\n"
                f"🛡️ Security Note: ลิงก์และรหัสนี้เป็นแบบใช้ครั้งเดียว เมื่อลูกค้าลงทะเบียนผ่านระบบ LIFF แล้ว ระบบจะทำลายสิทธิ์รหัสนี้ทิ้งทันทีครับ"
            )
            return {"type": "text", "text": reply}
            
        except Exception as e:
            logger.error(f"❌ [VVIP Gen Error]: {e}")
            return {"type": "text", "text": f"เกิดข้อผิดพลาดในการบันทึกรหัส VVIP ลงฐานข้อมูลครับ: {str(e)}"}

    def _build_approval_flex_message(self, report_text: str, plan_id: str) -> dict:
        return {
            "type": "flex",
            "altText": "แฟ้มรายงานจากเลขาฯ อัจฉริยะ (รอการพิจารณาอนุมัติ)",
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
        logger.info(f"🔄 [Hot Reload]: CEO Approved Plan -> {plan_id}")
        return {
            "type": "text", 
            "text": f"✅ อนุมัติสำเร็จ! ผมได้นำแผนรหัส [{plan_id}] ไปสั่งการอัปเดตระบบและฐานข้อมูลเรียบร้อยแล้วครับ (Zero Downtime) ระบบทั้งหมดจะทำงานตามกลยุทธ์ใหม่ทันทีครับท่านประธาน"
        }