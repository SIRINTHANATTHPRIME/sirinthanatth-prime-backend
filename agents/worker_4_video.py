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

logger = logging.getLogger("Worker4-VideoDirector")

class VideoProductionWorker:
    """
    🎬 Worker 4: Executive Video Director & Analyst
    อัปเกรด: Gemini 3.1 Pro, Swarm Delegation, 4K Storyboard Generator และ Zero-Data Shield
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
        """💳 ตรวจสอบแพ็กเกจและหัก PRIME CREDITS อัจฉริยะ สำหรับงานวิดีโอ"""
        if not self.db: return {"authorized": True, "tier": "ESSENTIAL"}
        
        try:
            def _check_and_deduct():
                user_data = self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
                if not user_data.data:
                    return {"authorized": False, "msg": "⚠️ ไม่พบข้อมูลบัญชี กรุณาลงทะเบียนเพื่อเปิดใช้งานระบบ Video Production ครับ"}
                    
                balance = float(user_data.data[0].get("token_balance", 0.0))
                tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
                
                if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]: return {"authorized": True, "tier": tier}
                    
                if balance >= tokens_needed:
                    new_balance = balance - tokens_needed
                    self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                    logger.info(f"🪙 [Token Engine]: หัก {tokens_needed} Credits จาก {user_id} (บริการ Video Production)")
                    return {"authorized": True, "tier": tier}
                else:
                    return {"authorized": False, "msg": f"⚠️ PRIME CREDITS ของท่านไม่เพียงพอสำหรับการวิเคราะห์หรือสร้างสคริปต์วิดีโอ (ต้องการ {tokens_needed} Credits)\n👉 เติมเครดิตได้ที่: {self.topup_link}"}

            return await asyncio.to_thread(_check_and_deduct)
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return {"authorized": True, "tier": "ESSENTIAL"}

    async def process_command(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """สะพานเชื่อมต่อรับงานจาก Swarm Hub หรือ Central Boss"""
        return await self.process_task(user_id, message, file_path)

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """ทำงานเบื้องหลัง: วิเคราะห์วิดีโอ สร้าง Storyboard และส่งต่อให้แผนกเรนเดอร์ 4K"""
        if not self.client: return "⚠️ [Worker 4]: ระบบ Video Director ออฟไลน์"

        # 🪙 ตรวจสอบค่าใช้จ่าย: อัปโหลดวิดีโอ = 100 Credits, คิดบทโฆษณา = 20 Credits
        tokens_needed = 100 if file_path else 20
        auth_status = await self._deduct_token(user_id, tokens_needed)
        if not auth_status["authorized"]: return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "ESSENTIAL")
        logger.info(f"🎬 [Video Production]: เริ่มโปรดักชันให้ User {user_id} (Tier: {package_tier})")

        system_instruction = f"""
        คุณคือ 'Executive Video Director' ระดับฮอลลีวูด ประจำสตูดิโอ SIRINTHANATTH PRIME
        ลูกค้ารายนี้อยู่ในแพ็กเกจระดับ: {package_tier}
        
        หน้าที่ของคุณ:
        1. 🎞️ การวิเคราะห์วิดีโอ (Deep Video Parsing): ถอดรหัสองค์ประกอบภาพ เสียง อารมณ์ และชี้จุดปรับปรุงเพื่อเพิ่ม Conversion Rate โฆษณา
        2. 📝 การออกแบบ Storyboard (Scene-by-Scene): หากลูกค้าให้คิดคอนเซปต์ ให้แบ่งฉากอย่างเป็นระบบ: [Hook 3วิ], [Pain Point], [Solution], [Call-to-Action]
        3. 🗣️ บทพากย์ (Voiceover Script): เขียนสคริปต์คำพูดแยกไว้ให้ชัดเจน เพื่อส่งให้ระบบ AI พากย์เสียง
        
        📄 กฎการสร้างไฟล์สคริปต์อัตโนมัติ (Document Engine):
        - หากลูกค้าสั่ง "ออกแบบสคริปต์", "เขียนสตอรี่บอร์ด" หรือ "คิดคอนเทนต์วิดีโอ" ให้คุณจัดทำแผนงานลงบนหน้ากระดาน HTML เสมอ โดยใช้แท็ก:
          [FILE_OUTPUT: storyboard.html] <h1>หัวข้อโฆษณา</h1>ตารางช็อตวิดีโอ... [/FILE_OUTPUT]
          
        🚨 กฎการส่งต่องาน (Swarm Delegation):
        - หากลูกค้าต้องการให้ 'พากย์เสียงจากสคริปต์' ให้โยนงานให้สตูดิโอเสียง โดยพิมพ์:
          [DELEGATE: WORKER_3_AUDIO] ช่วยพากย์เสียงสคริปต์นี้หน่อยครับ: (ใส่เนื้อหาสคริปต์)
        - หากลูกค้าต้องการให้ 'เรนเดอร์ภาพเคลื่อนไหว/สร้างวิดีโอ 4K' ให้โยนงานไปให้มีเดียเอนจิน โดยพิมพ์:
          [DELEGATE: WORKER_11_MEDIA] ช่วยนำ Prompt และสคริปต์วิดีโอนี้ไปเรนเดอร์เป็นภาพ 4K ครับ: (ใส่ข้อมูล)
        
        ⚠️ หากไม่ได้ส่งต่องาน ให้ตบท้ายข้อความเพื่อเข้าสู่ระบบ Approval Workflow:
        "📝 [ระบบผู้กำกับ]: หากพึงพอใจกับสคริปต์โครงสร้างนี้ โปรดพิมพ์คำว่า 'ยืนยันการสร้างคลิป' เพื่อให้ระบบส่งต่อคิวเข้าสตูดิโอเรนเดอร์ 4K ทันทีครับ"
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 📂 1. จัดการอัปโหลดไฟล์วิดีโอ 
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"🎞️ [Worker 4]: กำลังอัปโหลดวิดีโอขึ้น Cloud เพื่อวิเคราะห์เฟรมต่อเฟรม...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type: mime_type = "video/mp4"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    logger.error(f"⚠️ [File Upload Error]: {e}")
                    return f"⚠️ [Worker 4]: โครงสร้างไฟล์วิดีโอไม่รองรับหรือใหญ่เกินไปครับ รบกวนส่งเป็นไฟล์ .mp4 ขนาดไม่เกิน 50MB ครับ"

                timeout = 120
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        raise TimeoutError("หมดเวลาการสแกนและแยกเฟรมวิดีโอ")
                    logger.info("⏳ [Worker 4]: AI กำลังแยกเฟรมภาพและเสียงในวิดีโอ (Processing)...")
                    await asyncio.sleep(4) 
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Worker 4]: ขออภัยครับ AI ไม่สามารถถอดรหัสวิดีโอนี้ได้ ไฟล์อาจเสียหรือติดการเข้ารหัส"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดวิเคราะห์วิดีโอนี้อย่างละเอียด และให้คำแนะนำตามคำสั่ง:\n{message}")
            else:
                content_to_send.append(f"โปรดออกแบบและวางแผนสคริปต์วิดีโอโฆษณา (Storyboard) สำหรับหัวข้อนี้:\n{message}")

            # ==========================================
            # 🧠 2. ประมวลผลขั้นสูงด้วย Gemini 3.1 Pro 
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7 
                )
            )
            
            reply_text = response.text.strip() if response.text else "✅ ออกแบบสคริปต์และวางแผนวิดีโอเสร็จสิ้นครับ"

            # ==========================================
            # 📄 3. ระบบสร้างสคริปต์บอร์ดอัตโนมัติ (Document Engine)
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
                    <title>{safe_filename} - Storyboard</title>
                    <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;600;700&display=swap" rel="stylesheet">
                    <style>
                        body {{ font-family: 'Prompt', sans-serif; background-color: #121212; color: #E0E0E0; line-height: 1.6; padding: 20px; }}
                        .container {{ max-width: 1000px; margin: 0 auto; background: #1E1E1E; padding: 40px; box-shadow: 0 15px 40px rgba(0, 0, 0, 0.5); border-radius: 12px; border-left: 6px solid #FF3366; }}
                        .header {{ text-align: center; margin-bottom: 30px; border-bottom: 1px solid #333; padding-bottom: 20px; }}
                        .header h1 {{ color: #FF3366; margin: 0; font-size: 28px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; }}
                        .header p {{ color: #888; font-size: 14px; margin-top: 5px; }}
                        h2, h3 {{ color: #FF99AA; margin-top: 25px; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; margin-bottom: 20px; font-size: 15px; }}
                        th, td {{ border: 1px solid #333; padding: 15px; text-align: left; vertical-align: top; }}
                        th {{ background-color: #2A2A2A; color: #FF3366; font-weight: 600; }}
                        tr:nth-child(even) {{ background-color: #252525; }}
                        .timestamp {{ text-align: right; font-size: 12px; color: #666; margin-top: 40px; border-top: 1px solid #333; padding-top: 15px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>CINEMATIC STORYBOARD & SCRIPT</h1>
                            <p>DIRECTED BY SIRINTHANATTH PRIME VIDEO ENGINE</p>
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
                reply_text += f"\n\n🎬 **สคริปต์และบอร์ดไดเรกเตอร์ของคุณเสร็จสมบูรณ์ครับ**\nคลิกเพื่อตรวจสอบฉากต่อฉาก (รองรับการเซฟเป็น PDF ทันที):\n👉 {generated_file_url}"

            # ==========================================
            # 🔄 4. ตรวจจับการส่งต่องาน (Swarm Delegation Logic)
            # ==========================================
            delegate_match = re.search(r'\[DELEGATE:\s*(.+?)\](.*)', reply_text, re.DOTALL | re.IGNORECASE)
            if delegate_match:
                target_worker = delegate_match.group(1).strip()
                handoff_message = delegate_match.group(2).strip()
                
                clean_reply = re.sub(r'\[DELEGATE:\s*(.+?)\](.*)', '', reply_text, flags=re.DOTALL | re.IGNORECASE).strip()
                
                worker_response = await swarm_hub.delegate_task(
                    from_worker="WORKER_4_VIDEO", 
                    to_worker=target_worker, 
                    user_id=user_id, 
                    message=handoff_message, 
                    file_path=file_path, 
                    file_type=None
                )
                return f"{clean_reply}\n\n🔄 [ผู้กำกับส่งต่องานให้แผนก {target_worker}]:\n{worker_response}"

            return reply_text

        except TimeoutError:
            logger.error("❌ [Worker 4 Timeout]: ไฟล์วิดีโอมีความยาวเกินไป")
            return "ขออภัยครับ ไฟล์วิดีโอมีความยาวหรือความละเอียดสูงเกินไป รบกวนตัดคลิปให้สั้นลงแล้วส่งมาใหม่อีกครั้งนะครับ"
        except Exception as e:
            logger.error(f"❌ [Worker 4 Error]: {e}")
            return f"⚠️ [Worker 4]: สตูดิโอวิดีโอขัดข้องชั่วคราว ทีมวิศวกรกำลังตรวจสอบครับ"

        finally:
            # ==========================================
            # 🧹 5. Zero-Data Retention Policy
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🗑️ [Worker 4]: ลบไฟล์วิดีโอ Footage ลับของลูกค้าออกจากคลาวด์เรียบร้อย (Data Privacy Shield)")
                except Exception as e:
                    logger.error(f"⚠️ [File Deletion Failed]: {e}")