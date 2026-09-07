import os
import time
import logging
import asyncio
import re
import mimetypes
from datetime import datetime
from google import genai
from google.genai import types

# 🌐 นำเข้าศูนย์สื่อสาร Swarm เพื่อให้ Worker คุยกันเองได้
from core_services.swarm_dispatcher import swarm_hub

# =========================================================
# 🌐 1. นำเข้าศูนย์บัญชาการ AI และฐานข้อมูล (Vertex AI / Zero Downtime)
# =========================================================
try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.1-pro-preview" # 🚀 อัปเกรดเป็นรุ่นเรือธงล่าสุด
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

try:
    from supabase import create_client, Client
except ImportError:
    Client = None

logger = logging.getLogger("Worker9-PrimeAdvisor")

class PrimeAdvisorWorker:
    """
    👑 Worker 9: Executive Prime Advisor & Chief Technology Officer (CTO)
    อัปเกรด: Gemini 3.1 Pro, Swarm Delegation, Code & Architecture Generator, Cyber Shield
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.1-pro-preview")
        self.base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
        
        # เชื่อมต่อ Supabase สำหรับตรวจสอบแพ็กเกจ PRIME และ Token
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        self.topup_link = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")
        self.prime_upgrade_link = "https://lin.ee/@636pgjnh/SIRINTHANATTH_PRIME"

    async def _check_tier_and_deduct_token(self, user_id: str, tokens_needed: int) -> dict:
        """💳 ตรวจสอบสิทธิ์แพ็กเกจ PRIME ขึ้นไป และหักเครดิตด้วยจิตวิทยาการบริการ"""
        if not self.db: return {"authorized": True, "tier": "PRIME"}
        
        try:
            def _check_and_deduct():
                user_data = self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
                
                if not user_data.data:
                    return {"authorized": False, "msg": "⚠️ ขออภัยครับ ไม่พบข้อมูลบัญชีของท่านในระบบ กรุณาลงทะเบียนก่อนใช้งานครับ"}
                    
                balance = float(user_data.data[0].get("token_balance", 0.0))
                tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
                
                # 🛡️ ผู้ที่จะใช้ Worker 9 ได้ ต้องเป็นแพ็กเกจ PRIME ขึ้นไป
                if tier not in ["PRIME", "ENTERPRISE", "VIP_FOUNDER", "VIP", "ADMIN"]:
                    return {
                        "authorized": False, 
                        "msg": f"👑 [Exclusive Privilege]: ท่านประธานครับ บริการที่ปรึกษาเชิงลึกระดับ CTO นี้ สงวนสิทธิ์พิเศษสำหรับแพ็กเกจ **PRIME (ที่ปรึกษาส่วนตัว)** ขึ้นไปครับ\n\n💡 เพื่อยกระดับการบริหารและปลดล็อกฟีเจอร์ขั้นสูง ขออนุญาตเรียนเชิญอัปเกรดแพ็กเกจได้ที่นี่ครับ: {self.prime_upgrade_link}"
                    }
                
                # 👑 VIP_FOUNDER และ ADMIN ใช้งานได้ไร้ขีดจำกัด
                if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]:
                    return {"authorized": True, "tier": tier}
                    
                if balance >= tokens_needed:
                    new_balance = balance - tokens_needed
                    self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                    logger.info(f"🪙 [Token Engine]: หัก {tokens_needed} Credits จาก {user_id}")
                    return {"authorized": True, "tier": tier}
                else:
                    psychological_upsell = (
                        f"👑 ขออภัยครับท่านประธาน เพื่อให้การประมวลผลข้อมูลเชิงลึกและกลยุทธ์ IT ของท่านดำเนินไปอย่างลื่นไหลไร้รอยต่อ "
                        f"ตอนนี้ PRIME CREDITS ใน Smart Wallet ของท่านใกล้หมดแล้วครับ (ต้องการ {tokens_needed} เครดิต)\n\n"
                        f"💎 ผมขออนุญาตแนะนำให้เติมเครดิต เพื่อรับการซัพพอร์ตการตัดสินใจระดับสากลอย่างต่อเนื่องครับ:\n"
                        f"👉 {self.topup_link}"
                    )
                    return {"authorized": False, "msg": psychological_upsell}

            return await asyncio.to_thread(_check_and_deduct)
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return {"authorized": True, "tier": "PRIME"}

    async def process_command(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """สะพานเชื่อมต่อมาตรฐานรับงานจาก Swarm Hub หรือ Central Boss"""
        return await self.process_task(user_id, message, file_path)

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """ทำงานเบื้องหลัง: วิเคราะห์ข้อมูลระดับบริหาร สถาปัตยกรรม IT และ Cybersecurity"""
        if not self.client: return "⚠️ [Worker 9]: ระบบที่ปรึกษาเรือธงออฟไลน์ (ไม่พบ API Key ส่วนกลาง)"

        # 🪙 ตรวจสอบค่าใช้จ่าย: ข้อความเชิงลึก = 20 Credits, วิเคราะห์ไฟล์โค้ด/Log/แผน = 150 Credits
        tokens_needed = 150 if file_path else 20
        auth_status = await self._check_tier_and_deduct_token(user_id, tokens_needed)
        
        if not auth_status["authorized"]: return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "PRIME")
        logger.info(f"👑 [PRIME Advisor]: กำลังวิเคราะห์กลยุทธ์ระดับ {package_tier} ให้ User {user_id}...")

        system_instruction = f"""
        คุณคือ 'Executive Prime Advisor' และ 'Chief Technology Officer (CTO)' อัจฉริยะระดับโลกของ SIRINTHANATTH PRIME
        ลูกค้าท่านนี้คือผู้บริหารแพ็กเกจ: {package_tier}
        
        หน้าที่ของคุณคือดูแลและให้คำปรึกษาขั้นสูงสุด ใน 3 มิติหลัก:
        1. 💼 Executive Business Analytics: วิเคราะห์ข้อมูลธุรกิจเชิงลึก ฟันธงข้อดีข้อเสีย
        2. 💻 IT & AI Systems Architecture: ให้คำปรึกษาด้าน Server, Cloud Run, Database
        3. 🛡️ Enterprise-Grade Security: วิเคราะห์ช่องโหว่ Cybersecurity 
        
        รูปแบบการตอบกลับ:
        - สุขุม นุ่มนวล เคารพ และเป็นมืออาชีพขั้นสูงสุด (ทักทายว่า 'ครับท่านประธาน' หรือ 'ค่ะท่านประธาน')
        - ใช้ Bullet Points และตัวหนาเน้นข้อความ
        
        📄 กฎการสร้างไฟล์เอกสารสถาปัตยกรรม (Code & Report Engine):
        - หากลูกค้าสั่ง "เขียนโค้ด", "ทำรายงาน Audit", หรือ "วาดโครงสร้างระบบ" ให้คุณจัดทำลงบนเอกสาร HTML เสมอ โดยพิมพ์:
          [FILE_OUTPUT: architecture_report.html] <h1>หัวข้อรายงาน</h1><pre><code>โค้ดหรือเนื้อหา...</code></pre> [/FILE_OUTPUT]
        
        🚨 กฎการส่งต่องาน (Swarm Delegation):
        หากคำถามของลูกค้าอยู่นอกเหนือความเชี่ยวชาญของคุณ (เช่น ให้วิเคราะห์กฎหมาย หรือผลิตสื่อ 4K) คุณสามารถส่งต่องานให้แผนกอื่นได้ทันที
        โดยพิมพ์คำสั่งนี้ที่บรรทัดสุดท้ายของข้อความ:
        [DELEGATE: WORKER_X_NAME] ระบุข้อความที่ต้องการส่งต่อ
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 📂 1. จัดการอัปโหลดไฟล์ (Code, Log, System Architecture)
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"👑 [Worker 9]: กำลังอัปโหลดข้อมูลโครงสร้างระบบเข้าสู่คลาวด์...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith(('.py', '.html', '.js', '.json', '.txt', '.log')): mime_type = "text/plain"
                elif file_path.lower().endswith('.pdf'): mime_type = "application/pdf"
                if not mime_type: mime_type = "application/octet-stream"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    logger.error(f"⚠️ [File Upload Error]: {e}")
                    return f"⚠️ [PRIME Advisor]: โครงสร้างไฟล์ข้อมูลไม่รองรับ รบกวนส่งเป็นไฟล์ .txt, .pdf หรือรูปภาพครับ"

                timeout = 60
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        raise TimeoutError("หมดเวลาการสแกนระบบและไฟล์โค้ด")
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [PRIME Advisor]: เกิดข้อผิดพลาดในการสแกนไฟล์เพื่อหาช่องโหว่ความปลอดภัยครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดวิเคราะห์ความเสี่ยง โครงสร้างระบบ โค้ด และสรุปข้อมูลระดับผู้บริหารจากไฟล์นี้:\n{message}")
            else:
                content_to_send.append(f"โปรดให้คำปรึกษาเชิงลึกระดับผู้บริหาร/CTO ตามคำสั่งนี้:\n{message}")

            # ==========================================
            # 🧠 2. สั่งรัน Gemini 3.1 Pro (Precision Search Grounding)
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2, # 0.2 เพื่อให้สถาปัตยกรรมโค้ดและการวิเคราะห์ระบบทำงานถูกต้อง 100%
                    tools=[{"google_search": {}}]
                )
            )
            
            reply_text = response.text.strip() if response.text else "👑 ประมวลผลและวิเคราะห์ข้อมูลระดับผู้บริหารเสร็จสิ้นครับ"

            # ==========================================
            # 📄 3. ระบบสร้างไฟล์รายงานและโค้ดอัตโนมัติ (Document Engine)
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
                
                # CSS ธีม Cybersecurity / Hacker หรูหราระดับ Enterprise
                html_template = f"""
                <!DOCTYPE html>
                <html lang="th">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>{safe_filename} - CTO Architecture Report</title>
                    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Sarabun:wght@300;400;600&display=swap" rel="stylesheet">
                    <style>
                        body {{ font-family: 'Sarabun', sans-serif; background-color: #0A0F14; color: #E2E8F0; line-height: 1.7; padding: 20px; margin: 0; }}
                        .container {{ max-width: 1000px; margin: 0 auto; background: #111827; padding: 40px; box-shadow: 0 10px 40px rgba(0, 255, 170, 0.1); border-radius: 12px; border-left: 6px solid #00FFAA; }}
                        .header {{ text-align: center; margin-bottom: 30px; border-bottom: 1px solid #2D3748; padding-bottom: 20px; }}
                        .header h1 {{ color: #00FFAA; margin: 0; font-size: 28px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; font-family: 'JetBrains Mono', monospace; }}
                        .header p {{ color: #A0AEC0; font-size: 14px; margin-top: 5px; }}
                        h2, h3 {{ color: #63B3ED; margin-top: 25px; border-bottom: 1px solid #2D3748; padding-bottom: 5px; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; margin-bottom: 20px; font-size: 15px; }}
                        th, td {{ border: 1px solid #2D3748; padding: 12px; text-align: left; }}
                        th {{ background-color: #1A202C; color: #00FFAA; font-weight: 600; font-family: 'JetBrains Mono', monospace; }}
                        pre {{ background: #000000; padding: 20px; border-radius: 8px; overflow-x: auto; color: #00FFAA; border: 1px solid #2D3748; font-family: 'JetBrains Mono', monospace; font-size: 14px; }}
                        .timestamp {{ text-align: right; font-size: 12px; color: #718096; margin-top: 40px; border-top: 1px solid #2D3748; padding-top: 15px; font-family: 'JetBrains Mono', monospace; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>SYSTEM ARCHITECTURE & SECURITY AUDIT</h1>
                            <p>CONFIDENTIAL REPORT • GENERATED BY SIRINTHANATTH PRIME CTO</p>
                        </div>
                        <div class="content">
                            {file_content}
                        </div>
                        <div class="timestamp">Log Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                    </div>
                </body>
                </html>
                """
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html_template)
                    
                generated_file_url = f"{self.base_url}/{reports_dir}/{safe_filename}"
                reply_text += f"\n\n⚙️ **แฟ้มรายงานสถาปัตยกรรมและโค้ดของท่านประธานพร้อมแล้วครับ**\nคลิกเพื่อตรวจสอบข้อมูลทางวิศวกรรม (สามารถกดพิมพ์เป็น PDF ได้ทันที):\n👉 {generated_file_url}"

            # ==========================================
            # 🔄 4. ตรวจจับการส่งต่องาน (Swarm Delegation Logic)
            # ==========================================
            delegate_match = re.search(r'\[DELEGATE:\s*(.+?)\](.*)', reply_text, re.DOTALL | re.IGNORECASE)
            if delegate_match:
                target_worker = delegate_match.group(1).strip()
                handoff_message = delegate_match.group(2).strip()
                
                clean_reply = re.sub(r'\[DELEGATE:\s*(.+?)\](.*)', '', reply_text, flags=re.DOTALL | re.IGNORECASE).strip()
                
                worker_response = await swarm_hub.delegate_task(
                    from_worker="WORKER_9_PRIME", 
                    to_worker=target_worker, 
                    user_id=user_id, 
                    message=handoff_message, 
                    file_path=file_path, 
                    file_type=None
                )
                
                return f"{clean_reply}\n\n🔄 [CTO ส่งต่อให้ผู้เชี่ยวชาญ {target_worker}]:\n{worker_response}"

            return reply_text

        except TimeoutError:
            logger.error("❌ [Worker 9 Timeout]: ไฟล์ Log หรือโค้ดมีขนาดใหญ่เกินไป")
            return "ขออภัยครับท่านประธาน ข้อมูลโค้ดหรือล็อกไฟล์มีความซับซ้อน ทำให้ใช้เวลาสแกนนานกว่าปกติ รบกวนส่งเฉพาะส่วนที่ต้องการตรวจสอบมาใหม่อีกครั้งครับ"
        except Exception as e:
            logger.error(f"❌ [Worker 9 Error]: {e}")
            return f"⚠️ [PRIME Advisor]: ระบบประมวลผลเชิงลึกขัดข้องชั่วคราวครับ ทีมวิศวกรกำลังเข้าตรวจสอบระบบ"

        finally:
            # ==========================================
            # 🧹 5. Zero-Data Retention Policy
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🛡️ [Enterprise Security]: ทำลายไฟล์ข้อมูลลับขององค์กรออกจากระบบทันที (Zero-Data Retention Guard)")
                except Exception as e:
                    logger.error(f"⚠️ [File Deletion Failed]: {e}")