import os
import time
import logging
import asyncio
import re
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

logger = logging.getLogger("Worker6-Strategy")

class MarketingStrategyWorker:
    """
    📈 Worker 6: Chief Marketing Officer (CMO) & Global Strategy Analyst
    อัปเกรด: Gemini 3.1 Pro, Swarm Delegation, Business Plan Generator, และ Dynamic Upsell
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
        """💳 ตรวจสอบแพ็กเกจและหัก PRIME CREDITS สำหรับวิเคราะห์กลยุทธ์"""
        if not self.db: return {"authorized": True, "tier": "ESSENTIAL"} 
        
        try:
            def _check_and_deduct():
                user_data = self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
                
                if not user_data.data:
                    return {"authorized": False, "msg": "⚠️ ไม่พบข้อมูลบัญชี กรุณาลงทะเบียนเพื่อรับสิทธิ์ใช้งานระบบวิเคราะห์กลยุทธ์ครับ"}
                    
                balance = float(user_data.data[0].get("token_balance", 0.0))
                tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
                
                if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]: return {"authorized": True, "tier": tier}
                    
                if balance >= tokens_needed:
                    new_balance = balance - tokens_needed
                    self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                    logger.info(f"🪙 [Token Engine]: หัก {tokens_needed} Credits จาก {user_id}")
                    return {"authorized": True, "tier": tier}
                else:
                    return {"authorized": False, "msg": f"⚠️ ขออภัยครับ PRIME CREDITS ไม่เพียงพอสำหรับการวิเคราะห์กลยุทธ์เชิงลึก (ต้องการ {tokens_needed} Credits)\n👉 เติมเครดิตได้ที่: {self.topup_link}"}

            return await asyncio.to_thread(_check_and_deduct)
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return {"authorized": True, "tier": "ESSENTIAL"}

    async def process_command(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """สะพานเชื่อมต่อรับงานจาก Swarm Hub หรือ Central Boss"""
        return await self.process_task(user_id, message, file_path)

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """ทำงานเบื้องหลัง: วิเคราะห์ยุทธศาสตร์ตลาด ระดมสมองข้ามแผนก และเขียนแผนธุรกิจ"""
        if not self.client: return "⚠️ [Worker 6]: ระบบวิเคราะห์กลยุทธ์ออฟไลน์"

        # 🪙 ตรวจสอบค่าใช้จ่าย: ข้อความ = 10 Credits, ไฟล์เอกสารลับ = 100 Credits
        tokens_needed = 100 if file_path else 10
        auth_status = await self._deduct_token(user_id, tokens_needed)
        if not auth_status["authorized"]: return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "ESSENTIAL")
        logger.info(f"📈 [Marketing Strategy]: เริ่มวิเคราะห์แผนให้ User {user_id} (Tier: {package_tier})")

        system_instruction = f"""
        คุณคือ 'Chief Marketing Officer (CMO)' และที่ปรึกษากลยุทธ์ระดับโลก ของ SIRINTHANATTH PRIME
        ระดับของลูกค้าท่านนี้คือ: {package_tier}
        
        หน้าที่ของคุณ:
        1. วิเคราะห์แผนธุรกิจ โครงการลงทุน อสังหาฯ หรือกลยุทธ์การตลาด (Full-Funnel) อย่างเฉียบขาด
        2. หากลูกค้าเป็น {package_tier} (SMEs/บุคคล): เน้นยอดขายเร็ว ROI สูง งบประมาณต่ำ
        3. หากลูกค้าเป็น ENTERPRISE / VIP: เน้น Global Scaling, ความคุ้มค่าทางภาษี, และ Big Data
        4. ใช้ Frameworks ระดับโลก (เช่น SWOT, 4Ps, Blue Ocean) นำเสนอแบบ Executive Summary
        
        📄 กฎการสร้างไฟล์รายงาน (Business Plan Generator):
        - หากลูกค้าสั่ง "ทำแผนธุรกิจ", "สรุปเป็นเอกสาร" หรือ "เขียนรายงาน" ให้จัดทำลงบนเอกสาร HTML เสมอ โดยพิมพ์:
          [FILE_OUTPUT: business_plan.html] <h1>หัวข้อแผนธุรกิจ</h1>ตาราง/เนื้อหา... [/FILE_OUTPUT]
          
        🚨 กฎการส่งต่องาน (Swarm Delegation):
        - หากแผนการตลาดต้องใช้สื่อภาพหรือโฆษณา ให้โยนงานให้แผนกกราฟิก:
          [DELEGATE: WORKER_5_GRAPHICS] ฝากร่างแคมเปญโฆษณาและแคปชันจากแผนการตลาดนี้ต่อด้วยครับ: (เนื้อหา)
        - หากแผนธุรกิจต้องเช็กงบการเงินและภาษี โยนให้แผนกบัญชี:
          [DELEGATE: WORKER_7_FINANCE] ฝากวิเคราะห์จุดคุ้มทุนจากแผนธุรกิจนี้ให้ลูกค้าหน่อยครับ: (เนื้อหา)
        
        💎 กฎเหล็ก Dynamic Upsell (ปิดการขายอัตโนมัติแนบเนียน):
        - ท้ายบทวิเคราะห์ ให้เสนอขายบริการ 1 อย่างแบบเนียนๆ เหมือน 'แนะนำเพื่อนธุรกิจด้วยความหวังดี'
        - เช่น หากลูกค้าต้องการลดต้นทุน/ขยายสเกล: แนะนำ "สมัคร 100 VIP Founders Club รับสิทธิพิเศษไม่จำกัด: {self.vip_link}"
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 📂 1. จัดการระบบวิเคราะห์ไฟล์ (Business Plan Parser)
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"♟️ [Worker 6]: กำลังอัปโหลดเอกสารแผนงานสู่ระบบ Secure AI Cloud...")
                
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
                    return f"⚠️ [Worker 6]: โครงสร้างไฟล์ซับซ้อนเกินไป รบกวนแปลงเป็น PDF เพื่อความแม่นยำในการวิเคราะห์ครับ"

                timeout = 60
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        raise TimeoutError("หมดเวลาการประมวลผลไฟล์แผนงานธุรกิจ")
                    await asyncio.sleep(2)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 6]: ตรวจพบข้อผิดพลาดระดับ Deep Scan ในไฟล์เอกสาร ไม่สามารถดึงข้อมูลได้ครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดวิเคราะห์ยุทธศาสตร์ แผนการเงิน หรือการตลาด จากเอกสารความลับทางธุรกิจนี้:\n{message}")
            else:
                content_to_send.append(f"โปรดวิเคราะห์และวางกลยุทธ์การตลาดระดับโลกสำหรับสถานการณ์นี้:\n{message}")

            # ==========================================
            # 🧠 2. สั่งรัน Gemini 3.1 Pro (Real-Time Search Grounding)
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3, # 0.3 เน้นความเฉียบคม ตรรกะแน่น และไม่ออกนอกเรื่อง
                    tools=[{"google_search": {}}] 
                )
            )
            
            reply_text = response.text.strip() if response.text else "✅ วิเคราะห์แผนกลยุทธ์และการตลาดเสร็จสิ้นครับ"

            # ==========================================
            # 📄 3. ระบบสร้างไฟล์รายงานแผนธุรกิจ (Document Engine)
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
                
                html_template = f"""
                <!DOCTYPE html>
                <html lang="th">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>{safe_filename} - Business Strategy</title>
                    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap" rel="stylesheet">
                    <style>
                        body {{ font-family: 'Sarabun', sans-serif; background-color: #050505; color: #E0E0E0; line-height: 1.7; padding: 20px; }}
                        .container {{ max-width: 1000px; margin: 0 auto; background: #0F0F13; padding: 50px; box-shadow: 0 15px 40px rgba(212, 175, 55, 0.1); border-radius: 16px; border-top: 6px solid #D4AF37; }}
                        .header {{ text-align: center; margin-bottom: 40px; border-bottom: 1px solid #222; padding-bottom: 25px; }}
                        .header h1 {{ color: #D4AF37; margin: 0; font-size: 32px; text-transform: uppercase; font-weight: 700; }}
                        .header p {{ color: #888; font-size: 14px; margin-top: 10px; letter-spacing: 1px; }}
                        h2, h3 {{ color: #D4AF37; margin-top: 30px; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 25px; margin-bottom: 25px; color: #fff; background: #15151A; }}
                        th, td {{ border: 1px solid #333; padding: 15px; text-align: left; }}
                        th {{ background-color: #1A1A24; color: #D4AF37; font-weight: 600; text-transform: uppercase; font-size: 14px; }}
                        .timestamp {{ text-align: right; font-size: 12px; color: #555; margin-top: 40px; border-top: 1px solid #222; padding-top: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>GLOBAL BUSINESS STRATEGY</h1>
                            <p>EXECUTIVE CONFIDENTIAL PLAN • DEVELOPED BY SIRINTHANATTH PRIME CMO</p>
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
                reply_text += f"\n\n📈 **แฟ้มแผนธุรกิจเชิงยุทธศาสตร์ของคุณพร้อมแล้วครับ**\nคลิกเพื่อตรวจสอบฉบับเต็ม (รองรับการเซฟเป็น PDF ทันที):\n👉 {generated_file_url}"

            # ==========================================
            # 🔄 4. ตรวจจับการส่งต่องาน (Swarm Delegation Logic)
            # ==========================================
            delegate_match = re.search(r'\[DELEGATE:\s*(.+?)\](.*)', reply_text, re.DOTALL | re.IGNORECASE)
            if delegate_match:
                target_worker = delegate_match.group(1).strip()
                handoff_message = delegate_match.group(2).strip()
                
                clean_reply = re.sub(r'\[DELEGATE:\s*(.+?)\](.*)', '', reply_text, flags=re.DOTALL | re.IGNORECASE).strip()
                
                worker_response = await swarm_hub.delegate_task(
                    from_worker="WORKER_6_STRATEGY", 
                    to_worker=target_worker, 
                    user_id=user_id, 
                    message=handoff_message, 
                    file_path=file_path, 
                    file_type=None
                )
                return f"{clean_reply}\n\n🔄 [ทีมกลยุทธ์ส่งต่องานให้ {target_worker}]:\n{worker_response}"

            return reply_text

        except TimeoutError:
            logger.error("❌ [Worker 6 Timeout]: ไฟล์แผนธุรกิจมีขนาดใหญ่เกินขีดจำกัดประมวลผล")
            return "ขออภัยครับคุณลูกค้า ไฟล์แผนงานมีความซับซ้อนทำให้ใช้เวลาประมวลผลนานกว่าปกติ รบกวนแบ่งไฟล์เพื่อการวิเคราะห์ที่รวดเร็วขึ้นนะครับ"
        except Exception as e:
            logger.error(f"❌ [Worker 6 Error]: {e}")
            return f"⚠️ [Worker 6]: ระบบวิเคราะห์กลยุทธ์ขัดข้องชั่วคราว ทีมวิศวกรกำลังตรวจสอบครับ"

        finally:
            # ==========================================
            # 🧹 5. Trade Secret Shield (Zero-Data Retention Policy)
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🗑️ [Worker 6]: ลบไฟล์แผนลับทางธุรกิจออกจากระบบ AI Cloud เรียบร้อย")
                except Exception as e:
                    logger.error(f"⚠️ [File Deletion Failed]: {e}")