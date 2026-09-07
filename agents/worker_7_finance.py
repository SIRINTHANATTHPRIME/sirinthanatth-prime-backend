import os
import time
import re
import logging
import asyncio
import mimetypes
from datetime import datetime
from google import genai
from google.genai import types

# 🌐 นำเข้าศูนย์บัญชาการ AI และระบบเครือข่ายส่งต่องาน (Swarm)
from core_services.swarm_dispatcher import swarm_hub

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

logger = logging.getLogger("Worker7-CFO")

class FinancialAndAccountingWorker:
    """
    💰 Worker 7: Chief Financial Officer (CFO) & Risk Management Expert
    อัปเกรด: Gemini 3.1 Pro, Swarm Delegation, Financial Report Generator, และ Real-time Market Data
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.1-pro-preview")
        self.base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
        
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        self.vip_link = "https://buy.stripe.com/00weVf1JdeBn07t7gI6Zy00"
        self.topup_link = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")

    async def _deduct_token(self, user_id: str, tokens_needed: int) -> dict:
        """💳 ตรวจสอบแพ็กเกจและหัก PRIME CREDITS อัจฉริยะ"""
        if not self.db: return {"authorized": True, "tier": "ESSENTIAL"} 
        
        try:
            def _check_and_deduct():
                user_data = self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
                
                if not user_data.data:
                    return {"authorized": False, "msg": "⚠️ ไม่พบข้อมูลบัญชี กรุณาลงทะเบียนผ่านเมนูเพื่อเปิดใช้งานระบบที่ปรึกษาการเงินครับ"}
                    
                balance = float(user_data.data[0].get("token_balance", 0.0))
                tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
                
                if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]: return {"authorized": True, "tier": tier}
                    
                if balance >= tokens_needed:
                    new_balance = balance - tokens_needed
                    self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                    logger.info(f"🪙 [Token Engine]: หัก {tokens_needed} Credits จาก {user_id} (บริการด้านการเงิน)")
                    return {"authorized": True, "tier": tier}
                else:
                    return {"authorized": False, "msg": f"⚠️ ขออภัยครับ PRIME CREDITS ไม่เพียงพอสำหรับการวิเคราะห์งบการเงิน (ต้องการ {tokens_needed} Credits)\n👉 เติมเครดิตได้ที่: {self.topup_link}"}

            return await asyncio.to_thread(_check_and_deduct)
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return {"authorized": True, "tier": "ESSENTIAL"}

    async def process_command(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """สะพานเชื่อมต่อรับงานจาก Swarm Hub หรือ Central Boss"""
        return await self.process_task(user_id, message, file_path)

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """ทำงานเบื้องหลัง: วิเคราะห์โครงสร้างการเงิน การบัญชี ภาษี และสร้างรายงาน"""
        if not self.client: return "⚠️ [Worker 7]: ระบบวิเคราะห์การเงินออฟไลน์"

        # 🪙 ตรวจสอบค่าใช้จ่าย: ข้อความการเงิน = 10 Credits, ไฟล์งบ/Excel = 100 Credits
        tokens_needed = 100 if file_path else 10
        auth_status = await self._deduct_token(user_id, tokens_needed)
        if not auth_status["authorized"]: return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "ESSENTIAL")
        logger.info(f"💰 [Finance & Accounting]: เริ่มวิเคราะห์งบให้ User {user_id} (Tier: {package_tier})")

        system_instruction = f"""
        คุณคือ 'Chief Financial Officer (CFO)' และผู้เชี่ยวชาญด้านบริหารความเสี่ยงการเงิน ของ SIRINTHANATTH PRIME
        ระดับของลูกค้าท่านนี้คือ: {package_tier}
        
        หน้าที่และกฎเหล็กของคุณ:
        1. วิเคราะห์โครงสร้างรายได้ ต้นทุนแฝง และกระแสเงินสด (Cash Flow) อย่างเฉียบขาด
        2. วางแผนภาษี (Tax Planning) แบบถูกกฎหมาย เพื่อรักษากำไรสุทธิ ให้อยู่ในระดับ 80%+
        3. ชี้จุดเสี่ยงและเสนอวิธีป้องกัน (Hedging/Reserves)
        4. ใช้ข้อมูลแบบ Real-time (อัตราแลกเปลี่ยน, ดอกเบี้ย) เพื่อการตัดสินใจที่แม่นยำ
        
        📄 กฎการสร้างไฟล์รายงานการเงิน (Financial Dashboard):
        - หากลูกค้าสั่ง "สรุปงบ", "ทำรายงาน", "สร้างตารางการเงิน" หรือ "วิเคราะห์จุดคุ้มทุน" ให้พิมพ์แท็กนี้เสมอ:
          [FILE_OUTPUT: financial_report.html] <h1>รายงานการเงิน</h1>ตาราง/เนื้อหา... [/FILE_OUTPUT]
          
        🚨 กฎการส่งต่องาน (Swarm Delegation):
        - หากแผนการเงินต้องตรวจสอบเรื่องกฎหมาย โยนให้ฝ่ายกฎหมาย:
          [DELEGATE: WORKER_2_RISK_QA] ฝากตรวจความเสี่ยงทางกฎหมายของแผนการเงินนี้ครับ: (เนื้อหา)
        - หากต้องนำงบนี้ไปทำแผนการตลาด โยนให้ CMO:
          [DELEGATE: WORKER_6_STRATEGY] ฝากวางแผนการตลาดให้สอดคล้องกับงบประมาณนี้ครับ: (เนื้อหา)
        
        ⚠️ กฎหมายสำคัญ (พิมพ์ท้ายข้อความเสมอ หากไม่มีการ Delegate):
        "หมายเหตุ: ข้อมูลข้างต้นเป็นการวิเคราะห์เชิงกลยุทธ์ ไม่ใช่คำแนะนำการลงทุน (Not Financial Advice) ตามหลักเกณฑ์ ก.ล.ต."
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 📂 1. จัดการระบบวิเคราะห์ไฟล์ (Financial Data Parser)
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"💰 [Worker 7]: กำลังอัปโหลดเอกสารงบการเงินสู่ระบบ Secure AI Cloud...")
                
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
                    return f"⚠️ [Worker 7]: โครงสร้างไฟล์ซับซ้อนเกินไป รบกวนแปลงเป็น PDF หรือ CSV เพื่อความแม่นยำครับ"

                timeout = 60
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        raise TimeoutError("หมดเวลาการประมวลผลไฟล์งบการเงิน")
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 7]: ตรวจพบข้อผิดพลาดระดับ Deep Scan ในไฟล์เอกสารการเงินครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดวิเคราะห์งบการเงิน ประเมินความคุ้มทุน (ROI) และความเสี่ยงทางภาษีจากเอกสารนี้:\n{message}")
            else:
                content_to_send.append(f"โปรดวางแผนและให้คำปรึกษาด้านการเงิน/การบัญชี/ภาษี สำหรับสถานการณ์นี้:\n{message}")

            # ==========================================
            # 🧠 2. สั่งรัน Gemini 3.1 Pro (Precision Asynchronous)
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1, # 0.1 เพื่อให้ตัวเลข การคำนวณ และกฎหมายภาษี แม่นยำ 100%
                    tools=[{"google_search": {}}] # เปิด Search ให้ AI ดึงข้อมูลเศรษฐกิจแบบ Real-time
                )
            )
            
            reply_text = response.text.strip() if response.text else "✅ วิเคราะห์การเงินและบัญชีเสร็จสิ้นครับ"

            # ==========================================
            # 📄 3. ระบบสร้างไฟล์รายงานการเงิน (Document Engine)
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
                
                # CSS ออกแบบแนว Corporate Finance Board
                html_template = f"""
                <!DOCTYPE html>
                <html lang="th">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>{safe_filename} - Financial Report</title>
                    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap" rel="stylesheet">
                    <style>
                        body {{ font-family: 'Sarabun', sans-serif; background-color: #F8FAFC; color: #1A202C; line-height: 1.7; padding: 20px; }}
                        .container {{ max-width: 1000px; margin: 0 auto; background: #FFFFFF; padding: 50px; box-shadow: 0 10px 30px rgba(0, 51, 102, 0.08); border-radius: 12px; border-top: 6px solid #003366; }}
                        .header {{ text-align: center; margin-bottom: 40px; border-bottom: 2px solid #EDF2F7; padding-bottom: 25px; }}
                        .header h1 {{ color: #003366; margin: 0; font-size: 32px; font-weight: 700; letter-spacing: 1px; }}
                        .header p {{ color: #718096; font-size: 14px; margin-top: 10px; text-transform: uppercase; }}
                        h2, h3 {{ color: #2B6CB0; margin-top: 30px; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 25px; margin-bottom: 25px; font-size: 15px; }}
                        th, td {{ border: 1px solid #E2E8F0; padding: 15px; text-align: right; }}
                        th:first-child, td:first-child {{ text-align: left; font-weight: 600; }}
                        th {{ background-color: #F7FAFC; color: #2D3748; font-weight: 700; text-transform: uppercase; }}
                        tr:nth-child(even) {{ background-color: #F7FAFC; }}
                        .timestamp {{ text-align: right; font-size: 12px; color: #A0AEC0; margin-top: 40px; border-top: 1px solid #EDF2F7; padding-top: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>FINANCIAL & ACCOUNTING REPORT</h1>
                            <p>STRICTLY CONFIDENTIAL • PREPARED BY SIRINTHANATTH PRIME CFO</p>
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
                reply_text += f"\n\n📊 **แฟ้มรายงานการเงินและการประเมินภาษี พร้อมแล้วครับ**\nคลิกเพื่อตรวจสอบข้อมูล (สามารถกดพิมพ์เป็น PDF ได้ทันที):\n👉 {generated_file_url}"

            # ==========================================
            # 🔄 4. ตรวจจับการส่งต่องาน (Swarm Delegation Logic)
            # ==========================================
            delegate_match = re.search(r'\[DELEGATE:\s*(.+?)\](.*)', reply_text, re.DOTALL | re.IGNORECASE)
            if delegate_match:
                target_worker = delegate_match.group(1).strip()
                handoff_message = delegate_match.group(2).strip()
                
                clean_reply = re.sub(r'\[DELEGATE:\s*(.+?)\](.*)', '', reply_text, flags=re.DOTALL | re.IGNORECASE).strip()
                
                worker_response = await swarm_hub.delegate_task(
                    from_worker="WORKER_7_FINANCE", 
                    to_worker=target_worker, 
                    user_id=user_id, 
                    message=handoff_message, 
                    file_path=file_path, 
                    file_type=None
                )
                return f"{clean_reply}\n\n🔄 [ทีมการเงินส่งต่องานให้ {target_worker}]:\n{worker_response}"

            return reply_text

        except TimeoutError:
            logger.error("❌ [Worker 7 Timeout]: ไฟล์งบการเงินขนาดใหญ่เกินกำหนด")
            return "ขออภัยครับ ไฟล์งบการเงินมีความซับซ้อนทำให้ใช้เวลาประมวลผลนานกว่าปกติ รบกวนสรุปไฟล์เฉพาะส่วนที่ต้องการวิเคราะห์แล้วส่งมาใหม่อีกครั้งนะครับ"
        except Exception as e:
            logger.error(f"❌ [Worker 7 Error]: {e}")
            return f"⚠️ [Worker 7]: ระบบวิเคราะห์การเงินขัดข้องชั่วคราว ทีมวิศวกรกำลังตรวจสอบครับ"

        finally:
            # ==========================================
            # 🧹 5. Zero-Data Retention Policy (Financial Data Protection)
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🗑️ [Worker 7]: ลบไฟล์งบการเงินลับของลูกค้าออกจากระบบ AI Cloud เรียบร้อย")
                except Exception as e:
                    logger.error(f"⚠️ [File Deletion Failed]: {e}")