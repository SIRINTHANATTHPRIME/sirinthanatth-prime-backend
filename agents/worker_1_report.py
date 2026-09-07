import os
import time
import logging
import asyncio
import mimetypes
import re
from datetime import datetime
from google import genai
from google.genai import types

# =========================================================
# 🌐 นำเข้าศูนย์บัญชาการ AI และระบบ Swarm
# =========================================================
from core_services.swarm_dispatcher import swarm_hub

try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.1-pro-preview" # 🚀 อัปเกรดเป็นรุ่นเรือธง 3.1 Pro
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

logger = logging.getLogger("Worker1-Report")

class ReportWorker:
    """
    📊 Worker 1: Chief Data Officer (CDO) & Executive Report Specialist
    อัปเกรด: Gemini 3.1 Pro, Report Generation Engine, Swarm Delegation, และ Real-time Research
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.1-pro-preview")
        self.base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
        
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        self.topup_link = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")

    async def _deduct_token(self, user_id: str, tokens_needed: int) -> dict:
        """💳 ตรวจสอบแพ็กเกจและหัก PRIME CREDITS อัจฉริยะ"""
        if not self.db:
            return {"authorized": True, "tier": "ESSENTIAL"}
        
        try:
            def _check_and_deduct():
                user_data = self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
                
                if not user_data.data:
                    return {"authorized": False, "msg": "⚠️ ไม่พบข้อมูลบัญชี กรุณาลงทะเบียนผ่านเมนูเพื่อรับสิทธิ์ใช้งานระบบวิเคราะห์ข้อมูลขั้นสูงครับ"}
                    
                balance = float(user_data.data[0].get("token_balance", 0.0))
                tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
                
                if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]:
                    return {"authorized": True, "tier": tier}
                    
                if balance >= tokens_needed:
                    new_balance = balance - tokens_needed
                    self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                    logger.info(f"🪙 [Token Engine]: หัก {tokens_needed} Credits จาก {user_id} (บริการ Data & Report)")
                    return {"authorized": True, "tier": tier}
                else:
                    return {"authorized": False, "msg": f"⚠️ PRIME CREDITS ของท่านไม่เพียงพอสำหรับการวิเคราะห์และสร้างเอกสาร (ต้องการ {tokens_needed} Credits)\n👉 เติมเครดิตได้ที่: {self.topup_link}"}

            return await asyncio.to_thread(_check_and_deduct)
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return {"authorized": True, "tier": "ESSENTIAL"}

    async def process_command(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """รองรับการเรียกใช้งานผ่าน Swarm Dispatcher"""
        return await self.process_task(user_id, message, file_path)

    async def process(self, user_id: str, message: str, file_path: str = None) -> str:
        return await self.process_task(user_id, message, file_path)

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """ทำงานเบื้องหลัง: วิเคราะห์ข้อมูล สร้างโครงสร้างเอกสาร และงานวิจัย"""
        if not self.client:
            return "⚠️ [Worker 1]: ระบบวิเคราะห์ข้อมูลออฟไลน์ (ไม่พบ API Key ในระบบส่วนกลาง)"

        tokens_needed = 100 if file_path else 10
        auth_status = await self._deduct_token(user_id, tokens_needed)
        
        if not auth_status["authorized"]:
            return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "ESSENTIAL")
        logger.info(f"📊 [Document Engineering]: สร้างรายงานให้ User {user_id} (Tier: {package_tier})")

        system_instruction = f"""
        คุณคือ 'Chief Data Officer (CDO)' และ 'Executive Administrator' ของ SIRINTHANATTH PRIME
        ลูกค้ารายนี้อยู่ในแพ็กเกจระดับ: {package_tier}
        
        หน้าที่และแนวทางการทำงาน:
        1. 📊 ตารางและการคำนวณ: ร่างโครงสร้าง Excel, สร้างสูตร (Formulas), หรือเขียนโครงสร้างจัดการ Big Data 
        2. 📑 การจัดการเอกสาร (Filing) & งานวิจัย: ร่างหนังสือราชการ, โครงสร้างงานวิจัย, แผนงานการศึกษา, หรือ Presentation (PowerPoint)
        3. 🔍 การย่อยข้อมูล (Data Extraction): สกัดข้อมูลสำคัญจากข้อความหรือไฟล์ นำเสนอแบบ Executive Summary
        
        การยกระดับตามแพ็กเกจ:
        - {package_tier} (SMEs/บุคคล): เน้นความถูกต้อง เข้าใจง่าย ช่วยลดเวลาทำงาน Office รายวัน
        - หากเป็น ENTERPRISE / VIP: เน้นระบบ Database Architecture, การวิเคราะห์สถิติขั้นสูง
        
        🚨 กฎการสร้างไฟล์รายงาน (Document Generation): 
        - หากลูกค้าสั่ง "ทำรายงาน", "สร้างตาราง", "สรุปเป็นเอกสาร" ให้คุณสร้างหน้ารายงานผ่านแท็กนี้เสมอ:
          [FILE_OUTPUT: ชื่อไฟล์.html] <h1>หัวข้อรายงาน</h1>ตารางหรือเนื้อหา... [/FILE_OUTPUT]
          
        🚨 กฎการส่งต่องาน (Swarm Delegation):
        - หากงานนั้นหลุดจากขอบเขตข้อมูล ไปสู่เรื่องเฉพาะทาง (เช่น ตรวจสอบกฎหมายภาษี, ทำคลิปวิดีโอ) ให้โยนงานให้แผนกอื่นโดยพิมพ์:
          [DELEGATE: WORKER_X_NAME] ข้อความที่ต้องการส่งต่อ
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 📂 1. จัดการระบบวิเคราะห์ไฟล์
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"📊 [Worker 1]: กำลังอัปโหลด Data File สู่ระบบ AI เพื่อวิเคราะห์เชิงลึก...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith(('.xlsx', '.xls')): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif file_path.lower().endswith('.csv'): mime_type = "text/csv"
                elif file_path.lower().endswith('.pdf'): mime_type = "application/pdf"
                if not mime_type: mime_type = "application/octet-stream"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    logger.error(f"⚠️ [File Upload Error]: {e}")
                    return f"⚠️ [Worker 1]: ไม่สามารถประมวลผลไฟล์นี้ได้ รบกวนแปลงเป็น PDF หรือ CSV เพื่อประสิทธิภาพสูงสุดครับ"

                timeout = 60
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        raise TimeoutError("หมดเวลาการสแกนและประมวลผลไฟล์เอกสาร")
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 1]: เกิดข้อผิดพลาดในกระบวนการถอดรหัสเอกสารบนเซิร์ฟเวอร์ครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดวิเคราะห์ข้อมูล สกัดตัวเลขสำคัญ และจัดทำรายงานสรุปตามคำสั่งนี้:\n{message}")
            else:
                content_to_send.append(f"โปรดออกแบบโครงสร้างเอกสาร ตารางคำนวณ หรืองานวิจัย ตามคำสั่งนี้:\n{message}")

            # ==========================================
            # 🧠 2. สั่งรัน Gemini 3.1 Pro (พร้อม Research Tools)
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2, 
                    tools=[{"google_search": {}}] # เปิดระบบให้ CDO ค้นหาข้อมูลอ้างอิงสถิติโลกได้
                )
            )
            
            reply_text = response.text.strip() if response.text else "✅ วิเคราะห์และจัดทำโครงร่างเอกสารเสร็จสิ้นครับ"

            # ==========================================
            # 📄 3. ระบบสร้างรายงานอัตโนมัติ (Document Engine)
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
                
                # CSS ออกแบบให้เป็นแนว Corporate Data Dashboard
                html_template = f"""
                <!DOCTYPE html>
                <html lang="th">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>{safe_filename} - Data Report</title>
                    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap" rel="stylesheet">
                    <style>
                        body {{ font-family: 'Sarabun', sans-serif; background-color: #F4F7F6; color: #333; line-height: 1.6; padding: 20px; }}
                        .container {{ max-width: 1100px; margin: 0 auto; background: #FFFFFF; padding: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); border-radius: 12px; border-top: 6px solid #0052CC; }}
                        .header {{ text-align: center; margin-bottom: 30px; border-bottom: 2px solid #E1E4E8; padding-bottom: 20px; }}
                        .header h1 {{ color: #0052CC; margin: 0; font-size: 28px; font-weight: 700; }}
                        .header p {{ color: #666; font-size: 14px; margin-top: 5px; text-transform: uppercase; letter-spacing: 1px; }}
                        h2, h3 {{ color: #003E99; margin-top: 25px; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; margin-bottom: 20px; font-size: 15px; }}
                        th, td {{ border: 1px solid #E1E4E8; padding: 12px 15px; text-align: left; }}
                        th {{ background-color: #F8FAFC; color: #0052CC; font-weight: 600; }}
                        tr:nth-child(even) {{ background-color: #F8FAFC; }}
                        pre {{ background: #1E1E1E; padding: 20px; border-radius: 8px; overflow-x: auto; color: #D4D4D4; font-family: 'Consolas', monospace; }}
                        .timestamp {{ text-align: right; font-size: 12px; color: #999; margin-top: 40px; border-top: 1px solid #E1E4E8; padding-top: 15px; }}
                        @media print {{ body {{ background: #fff; padding: 0; }} .container {{ box-shadow: none; border: none; padding: 0; }} }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>DATA & EXECUTIVE REPORT</h1>
                            <p>PRODUCED BY SIRINTHANATTH PRIME CDO ENGINE</p>
                        </div>
                        <div class="content">
                            {file_content}
                        </div>
                        <div class="timestamp">Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                    </div>
                </body>
                </html>
                """
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(html_template)
                    
                generated_file_url = f"{self.base_url}/{reports_dir}/{safe_filename}"
                reply_text += f"\n\n📊 **แฟ้มรายงานวิเคราะห์ข้อมูลและตาราง เสร็จสมบูรณ์ครับ**\nคลิกเปิดเพื่อดูรายละเอียด (รองรับการสั่งพิมพ์เป็น PDF ทันที):\n👉 {generated_file_url}"

            # ==========================================
            # 🔄 4. ตรวจจับการส่งต่องาน (Swarm Delegation Logic)
            # ==========================================
            delegate_match = re.search(r'\[DELEGATE:\s*(.+?)\](.*)', reply_text, re.DOTALL | re.IGNORECASE)
            if delegate_match:
                target_worker = delegate_match.group(1).strip()
                handoff_message = delegate_match.group(2).strip()
                
                clean_reply = re.sub(r'\[DELEGATE:\s*(.+?)\](.*)', '', reply_text, flags=re.DOTALL | re.IGNORECASE).strip()
                
                worker_response = await swarm_hub.delegate_task(
                    from_worker="WORKER_1_REPORT", 
                    to_worker=target_worker, 
                    user_id=user_id, 
                    message=handoff_message, 
                    file_path=file_path, 
                    file_type=None
                )
                
                return f"{clean_reply}\n\n🔄 [ส่งข้อมูลต่อให้ผู้เชี่ยวชาญ {target_worker}]:\n{worker_response}"

            return reply_text

        except TimeoutError:
            logger.error("❌ [Worker 1 Timeout]: ไฟล์ Data มีขนาดใหญ่หรือซับซ้อนเกินไป")
            return "ขออภัยครับ ไฟล์ข้อมูลหรือเอกสารมีความซับซ้อนเกินไป รบกวนแยกไฟล์เพื่อการประมวลผลที่รวดเร็วขึ้นครับ"
        except Exception as e:
            logger.error(f"❌ [Worker 1 Error]: {e}")
            return f"⚠️ [Worker 1]: ระบบจัดการเอกสารขัดข้องชั่วคราว ทีมวิศวกรกำลังเข้าตรวจสอบครับ"

        finally:
            # ==========================================
            # 🧹 5. Zero-Data Retention Policy (PDPA Shield)
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🗑️ [Worker 1]: ทำลายไฟล์ Data ของลูกค้าออกจากระบบคลาวด์เรียบร้อย (Data Privacy Shield)")
                except Exception as e:
                    logger.error(f"⚠️ [File Deletion Failed]: {e}")