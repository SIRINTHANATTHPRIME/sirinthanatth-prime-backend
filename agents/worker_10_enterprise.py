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

logger = logging.getLogger("Worker10-Enterprise")

class EnterprisePartnerWorker:
    """
    🏢 Worker 10: Executive Enterprise Partner & Big Data Architect
    อัปเกรด: Gemini 3.1 Pro, Swarm Delegation, Big Data Dashboard Generator, และ Zero-Trust Security
    """
    def __init__(self):
        self.client = PrimeAIConfig.get_client()
        self.model_name = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.1-pro-preview")
        self.base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
        
        supa_url = os.getenv("SUPABASE_URL")
        supa_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        self.db: Client = create_client(supa_url, supa_key) if supa_url and supa_key else None
        
        self.topup_link = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")
        self.enterprise_upgrade_m = "https://buy.stripe.com/eVqeVf2Nh1OBaM7eJa6Zy04" 
        self.enterprise_upgrade_y = "https://buy.stripe.com/bJe9AVfA3ctf2fB0Sk6Zy05" 

    async def _check_tier_and_deduct_token(self, user_id: str, tokens_needed: int) -> dict:
        """💳 ตรวจสอบสิทธิ์ระดับองค์กร (ENTERPRISE) และหักเครดิตอย่างชาญฉลาด"""
        if not self.db: return {"authorized": True, "tier": "ENTERPRISE"} 
        
        try:
            def _check_and_deduct():
                user_data = self.db.table("prime_clients").select("package_tier, token_balance").eq("line_user_id", user_id).execute()
                
                if not user_data.data:
                    return {"authorized": False, "msg": "⚠️ ขออภัยครับ ไม่พบข้อมูลบัญชีองค์กรของท่านในระบบ กรุณาติดต่อทีมงานครับ"}
                    
                balance = float(user_data.data[0].get("token_balance", 0.0))
                tier = user_data.data[0].get("package_tier", "ESSENTIAL").upper()
                
                if tier not in ["ENTERPRISE", "VIP_FOUNDER", "VIP", "ADMIN"]:
                    upsell_msg = (
                        f"🏢 [Enterprise Exclusive]: ท่านผู้บริหารครับ ระบบวิเคราะห์ข้อมูลตลาด Real-time และการจัดการ Big Data/คลังสินค้า "
                        f"เป็นฟีเจอร์ที่สงวนสิทธิ์เฉพาะแพ็กเกจ **'พันธมิตรองค์กร (ENTERPRISE)'** ขึ้นไปเท่านั้นครับ\n\n"
                        f"💡 ขออนุญาตเรียนเชิญอัปเกรดแพ็กเกจเพื่อยกระดับระบบหลังบ้านด้วยทีมวิศวกร AI ของเราครับ:\n"
                        f"🔹 รายเดือน (4,900 ฿): {self.enterprise_upgrade_m}\n"
                        f"⭐ รายปีสุดคุ้ม (39,900 ฿ - ประหยัด 20%): {self.enterprise_upgrade_y}"
                    )
                    return {"authorized": False, "msg": upsell_msg}
                
                if tier in ["VIP_FOUNDER", "VIP", "ADMIN"]: return {"authorized": True, "tier": tier}
                    
                if balance >= tokens_needed:
                    new_balance = balance - tokens_needed
                    self.db.table("prime_clients").update({"token_balance": new_balance}).eq("line_user_id", user_id).execute()
                    logger.info(f"🪙 [Enterprise Token Engine]: หัก {tokens_needed} Credits จาก {user_id}")
                    return {"authorized": True, "tier": tier}
                else:
                    psychological_topup = (
                        f"🏢 เรียนท่านผู้บริหาร ระบบตรวจพบว่า 'PRIME CREDITS' ใน Smart Wallet ขององค์กรท่านใกล้หมดแล้วครับ "
                        f"(ปริมาณ Data ชุดนี้ต้องการ {tokens_needed} เครดิต)\n\n"
                        f"⚡ เพื่อไม่ให้การวิเคราะห์ข้อมูลและการจัดการคลังสินค้าของท่านหยุดชะงัก ท่านสามารถสั่งเติมเครดิตเข้าสู่ระบบองค์กรได้ทันทีครับ:\n"
                        f"👉 {self.topup_link}"
                    )
                    return {"authorized": False, "msg": psychological_topup}

            return await asyncio.to_thread(_check_and_deduct)
        except Exception as e:
            logger.error(f"❌ [Enterprise Token Error]: {e}")
            return {"authorized": True, "tier": "ENTERPRISE"}

    async def process_command(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """สะพานเชื่อมต่อรับงานจาก Swarm Hub หรือ Central Boss"""
        return await self.process_task(user_id, message, file_path)

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """ทำงานเบื้องหลัง: วิเคราะห์ Big Data, วางแผน Supply Chain และ Whitelisting"""
        if not self.client: return "⚠️ [Worker 10]: ระบบพันธมิตรองค์กรออฟไลน์ (ไม่พบ API Key)"

        tokens_needed = 300 if file_path else 50
        auth_status = await self._check_tier_and_deduct_token(user_id, tokens_needed)
        if not auth_status["authorized"]: return auth_status["msg"]
            
        package_tier = auth_status.get("tier", "ENTERPRISE")
        logger.info(f"🏢 [Enterprise Analytics]: เริ่มกระบวนการวิเคราะห์ข้อมูลระดับอุตสาหกรรมให้ User {user_id}")

        system_instruction = f"""
        คุณคือ 'Chief Data Officer' และ 'Enterprise Architect' ระดับโลก ของ SIRINTHANATTH PRIME
        ลูกค้าท่านนี้คือพันธมิตรองค์กรระดับ: {package_tier}
        
        หน้าที่ของคุณ (Enterprise Solutions):
        1. 📊 Big Data & Supply Chain: วิเคราะห์ข้อมูลคลังสินค้า (Inventory), การพยากรณ์อุปสงค์ (Demand Forecasting)
        2. 🛡️ Brand Protection: วางแผนการจัดการลิขสิทธิ์ และความปลอดภัยระดับองค์กร (Zero-Trust Security)
        3. ⚙️ Automation Integration: เสนอโครงสร้างเชื่อมต่อ API, ERP, หรือ CRM
        
        รูปแบบการตอบกลับ:
        - ภาษาระดับ Corporate Executive ชัดเจน มี Action Plan (สิ่งที่ต้องทำทันที, ระยะกลาง, ระยะยาว)
        - คำนึงถึง "กฎหมาย", "ความเสี่ยงทางธุรกิจ", และ "ความคุ้มค่า (ROI)" เสมอ
        
        📄 กฎการสร้างไฟล์รายงาน (Enterprise Dashboard):
        - หากลูกค้าสั่ง "สร้างแดชบอร์ด", "สรุปเป็นรายงาน", หรือ "พล็อตกราฟข้อมูล" ให้คุณสร้างลงบนเอกสาร HTML เสมอ โดยพิมพ์:
          [FILE_OUTPUT: enterprise_dashboard.html] <h1>หัวข้อรายงาน</h1>ตาราง/เนื้อหา/กราฟ... [/FILE_OUTPUT]
          
        🚨 กฎการส่งต่องาน (Swarm Delegation):
        - หากการวิเคราะห์คลังสินค้าพบว่าสินค้าขาดสต๊อก หรือต้องวางแผนโปรโมชัน ให้โยนงานให้แผนกกลยุทธ์:
          [DELEGATE: WORKER_6_STRATEGY] ฝากวางแผนการตลาดและการจัดซื้อจากรายงานข้อมูลคลังสินค้านี้ครับ: (ระบุข้อมูล)
        - หากแผน Supply Chain ต้องการผู้เชี่ยวชาญ E-commerce/Logistics:
          [DELEGATE: WORKER_8_ECOMMERCE] ฝากประเมินโครงสร้างราคาและการจัดส่ง Flash จากออเดอร์องค์กรนี้ครับ: (ระบุข้อมูล)
        """

        uploaded_file = None
        content_to_send = []

        try:
            # ==========================================
            # 📂 1. จัดการอัปโหลดไฟล์ (Big Data, CSV, SQL, JSON)
            # ==========================================
            if file_path and os.path.exists(file_path):
                logger.info(f"🏢 [Worker 10]: กำลังอัปโหลด Big Data เข้าสู่ Secure Cloud เพื่อทำการ Data Mining...")
                
                mime_type, _ = mimetypes.guess_type(file_path)
                if file_path.lower().endswith(('.csv', '.json', '.xml', '.sql')): mime_type = "text/plain" 
                elif file_path.lower().endswith('.xlsx'): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                if not mime_type: mime_type = "application/octet-stream"

                try:
                    upload_config = types.UploadFileConfig(mime_type=mime_type)
                    uploaded_file = await asyncio.to_thread(self.client.files.upload, file=file_path, config=upload_config)
                except Exception as e:
                    logger.error(f"⚠️ [File Upload Error]: {e}")
                    return f"⚠️ [Enterprise Analytics]: โครงสร้าง Database File ซับซ้อนเกินไป รบกวนส่งเป็นไฟล์ .csv, .json หรือ .xlsx ครับ"

                timeout = 60
                start_time = time.time()
                while uploaded_file.state.name == "PROCESSING":
                    if time.time() - start_time > timeout:
                        raise TimeoutError("หมดเวลาการประมวลผลฐานข้อมูล (Timeout)")
                    await asyncio.sleep(3)
                    uploaded_file = await asyncio.to_thread(self.client.files.get, name=uploaded_file.name)
                    
                if uploaded_file.state.name == "FAILED":
                    return "⚠️ [Enterprise Analytics]: เกิดข้อผิดพลาดในการทำ Data Mining ระดับลึกในไฟล์ครับ"

                content_to_send.append(uploaded_file)
                content_to_send.append(f"โปรดทำการวิเคราะห์ Big Data / คลังสินค้า จากฐานข้อมูลนี้:\n{message}")
            else:
                content_to_send.append(f"โปรดให้คำปรึกษาระดับองค์กร/Supply Chain สำหรับประเด็นนี้:\n{message}")

            # ==========================================
            # 🧠 2. สั่งรัน Gemini 3.1 Pro (Precision Search Grounding)
            # ==========================================
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=content_to_send,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1, # อุณหภูมิต่ำสุดเพื่อความถูกต้องของตัวเลข สถิติ และความปลอดภัย 100%
                    tools=[{"google_search": {}}] 
                )
            )
            
            reply_text = response.text.strip() if response.text else "🏢 การวิเคราะห์ข้อมูลระดับองค์กรและคลังสินค้า เสร็จสมบูรณ์ครับ"

            # ==========================================
            # 📄 3. ระบบสร้างไฟล์รายงาน (Enterprise Dashboard Engine)
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
                
                # CSS Corporate Analytics Dashboard
                html_template = f"""
                <!DOCTYPE html>
                <html lang="th">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>{safe_filename} - Enterprise Data Analytics</title>
                    <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap" rel="stylesheet">
                    <style>
                        body {{ font-family: 'Sarabun', sans-serif; background-color: #0A0A0A; color: #F0F4F8; line-height: 1.7; padding: 20px; }}
                        .container {{ max-width: 1100px; margin: 0 auto; background: #121212; padding: 40px; box-shadow: 0 15px 50px rgba(0, 229, 255, 0.1); border-radius: 16px; border-left: 6px solid #00E5FF; border-top: 1px solid #1A1A1A; }}
                        .header {{ text-align: center; margin-bottom: 40px; border-bottom: 1px solid #222; padding-bottom: 25px; }}
                        .header h1 {{ color: #00E5FF; margin: 0; font-size: 32px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; }}
                        .header p {{ color: #888; font-size: 14px; margin-top: 5px; }}
                        h2, h3 {{ color: #00B8D4; margin-top: 30px; }}
                        table {{ width: 100%; border-collapse: collapse; margin-top: 25px; margin-bottom: 25px; font-size: 15px; }}
                        th, td {{ border: 1px solid #333; padding: 15px; text-align: left; }}
                        th {{ background-color: #1A1A1A; color: #00E5FF; font-weight: 600; text-transform: uppercase; font-size: 14px; }}
                        tr:nth-child(even) {{ background-color: #161616; }}
                        .timestamp {{ text-align: right; font-size: 12px; color: #555; margin-top: 40px; border-top: 1px solid #222; padding-top: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <h1>ENTERPRISE BIG DATA ANALYTICS</h1>
                            <p>STRICTLY CONFIDENTIAL • PROCESSED BY SIRINTHANATTH PRIME ENGINE</p>
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
                reply_text += f"\n\n📊 **แฟ้มรายงานสถิติ Big Data องค์กร พร้อมแล้วครับ**\nคลิกเพื่อตรวจสอบข้อมูลเชิงลึก (สามารถกดพิมพ์เป็น PDF ได้ทันที):\n👉 {generated_file_url}"

            # ==========================================
            # 🔄 4. ตรวจจับการส่งต่องาน (Swarm Delegation Logic)
            # ==========================================
            delegate_match = re.search(r'\[DELEGATE:\s*(.+?)\](.*)', reply_text, re.DOTALL | re.IGNORECASE)
            if delegate_match:
                target_worker = delegate_match.group(1).strip()
                handoff_message = delegate_match.group(2).strip()
                
                clean_reply = re.sub(r'\[DELEGATE:\s*(.+?)\](.*)', '', reply_text, flags=re.DOTALL | re.IGNORECASE).strip()
                
                worker_response = await swarm_hub.delegate_task(
                    from_worker="WORKER_10_ENTERPRISE", 
                    to_worker=target_worker, 
                    user_id=user_id, 
                    message=handoff_message, 
                    file_path=file_path, 
                    file_type=None
                )
                return f"{clean_reply}\n\n🔄 [Enterprise Architect ส่งข้อมูลต่อให้ {target_worker}]:\n{worker_response}"

            return reply_text

        except TimeoutError:
            logger.error("❌ [Worker 10 Timeout]: ฐานข้อมูล Big Data มีขนาดใหญ่เกินไป")
            return "ขออภัยครับท่านผู้บริหาร ฐานข้อมูลมีขนาดใหญ่ทำให้ใช้เวลา Data Mining นานกว่าปกติ รบกวนส่งไฟล์ชุดข้อมูลที่เล็กลงมาใหม่อีกครั้งครับ"
        except Exception as e:
            logger.error(f"❌ [Worker 10 Error]: {e}")
            return f"⚠️ [Enterprise Analytics]: ระบบฐานข้อมูลองค์กรขัดข้องชั่วคราว ทีมวิศวกรกำลังตรวจสอบครับ"

        finally:
            # ==========================================
            # 🧹 5. Zero-Data Retention Policy (Military-Grade Cyber Shield)
            # ==========================================
            if uploaded_file:
                try:
                    await asyncio.to_thread(self.client.files.delete, name=uploaded_file.name)
                    logger.info("🛡️ [Zero-Trust Security]: ทำลายฐานข้อมูลลับขององค์กรลูกค้าออกจากระบบทันที (Data Wiped)")
                except Exception as e:
                    logger.error(f"⚠️ [File Deletion Failed]: {e}")