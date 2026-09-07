import os
import time
import re
import logging
import asyncio
import mimetypes
from datetime import datetime
from google import genai
from google.genai import types

# =========================================================
# 🌐 นำเข้าศูนย์บัญชาการ AI ส่วนกลางและระบบ Swarm
# =========================================================
from core_services.swarm_dispatcher import swarm_hub

try:
    from core_services.ai_config import PrimeAIConfig
except ImportError:
    class PrimeAIConfig:
        EXECUTIVE_MODEL = "gemini-3.1-pro-preview" 
        @staticmethod
        def get_client():
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key: return genai.Client(api_key=api_key)
            return genai.Client(
                vertexai=True, 
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                location="asia-southeast3"
            )

# =========================================================
# 🧠 นำเข้าระบบความจำองค์กรและประวัติลูกค้า (Graph RAG & Vector Memory)
# =========================================================
try:
    from agents.memory_engine import recall_corporate_knowledge, recall_memory, save_memory, save_corporate_knowledge
except ImportError:
    def recall_corporate_knowledge(q): return ""
    def recall_memory(uid, msg): return ""
    def save_memory(uid, summary): pass
    def save_corporate_knowledge(title, content): return False

logger = logging.getLogger("PrimeBrain")

# 1. 🔑 ตั้งค่าการเชื่อมต่อ AI จากส่วนกลาง
client = PrimeAIConfig.get_client()
MODEL_NAME = getattr(PrimeAIConfig, "EXECUTIVE_MODEL", "gemini-3.1-pro-preview")

# =========================================================
# 👑 2. SYSTEM PROMPT: กฎเหล็กของสมองกลระดับโลก (Global Intelligence)
# =========================================================
SYSTEM_PROMPT = """คุณคือ "SIRINTHANATTH PRIME" สุดยอด AI สมองกลศูนย์กลางและที่ปรึกษาธุรกิจระดับสากล

หน้าที่ของคุณคือคิดวิเคราะห์เชิงลึก (Deep Reasoning) วางแผนกลยุทธ์ และบริหารจัดการครอบคลุมทุกอุตสาหกรรมบนโลกอย่างแม่นยำ 100%

ขีดความสามารถและกฎเหล็กการประมวลผล (World-Class Standard):
1. 🌐 Real-time Fact-Checking: 
   - ใช้เครื่องมือ Google Search เสมอเมื่อต้องการยืนยัน กฎหมาย, แนวโน้มตลาด, หรือข้อมูลที่ต้องการความอัปเดตล่าสุด ห้ามคาดเดาข้อมูลทางธุรกิจหรือการเงินเด็ดขาด
2. 🧠 Predictive Empathy & Graph RAG: 
   - วิเคราะห์จิตวิทยาและอารมณ์ของลูกค้า (Sentiment Analysis) เพื่อนำเสนอทางแก้ปัญหาแบบรู้ใจ (Proactive) ก่อนที่ลูกค้าจะร้องขอ
3. 👁️ Omni-Modal Mastery (การจัดการไฟล์):
   - สกัดเนื้อหาจาก PDF, Excel, หรือรูปภาพอย่างแม่นยำระดับ 100% เพื่อใช้วิเคราะห์งบการเงิน แผนการตลาด หรือโครงสร้างองค์กร
4. 📚 ระบบเรียนรู้ด้วยตนเอง (Self-Learning Ingestion):
   - หากผู้ใช้สั่ง "บันทึกความรู้" ให้คุณสกัดแก่นความรู้ (Core Knowledge) จัดโครงสร้างเป็น Bullet Points ให้อ่านง่าย เพื่อนำไปเซฟลงฐานข้อมูล
5. 🛡️ Absolute Legal & Cybersecurity Shield: 
   - ห้ามให้คำแนะนำการลงทุนแบบฟันธง (Buy/Sell/Hold) ห้ามการันตีผลตอบแทน เพื่อป้องกันการผิดกฎหมาย ก.ล.ต. / สคบ. / อย.
   
🚨 กฎการทำงานร่วมกับ Swarm Network:
- หากคำถามต้องการผู้เชี่ยวชาญเฉพาะทาง (เช่น เลขาฯ, CTO, ทนายความ) ให้คุณโยนงานทันทีโดยพิมพ์:
  [DELEGATE: WORKER_X_NAME] คำสั่งที่ต้องการส่งต่อ

📄 กฎการสร้างไฟล์รายงาน:
- หากถูกสั่งให้ "ทำรายงาน", "สร้าง PDF" หรือ "เขียนโค้ด" ให้พิมพ์แท็กนี้เสมอ:
  [FILE_OUTPUT: ชื่อไฟล์.html] <h1>เนื้อหา</h1> [/FILE_OUTPUT]
"""

# =========================================================
# ⚙️ 3. แกนประมวลผลเชิงลึก (Deep Reasoning Logic)
# =========================================================
async def generate_intelligent_response(user_id: str, incoming_message: str, file_path: str = None, file_type: str = None) -> str:
    """ฟังก์ชันสมองกลประมวลผลเชิงลึก ดึงความจำ ดึงไฟล์ ค้นหาเว็บ สร้างรายงาน และผสาน Graph RAG"""
    
    if not client:
        return "⚠️ System Offline: ไม่พบการเชื่อมต่อ API Key ในระบบส่วนกลางครับ"

    uploaded_file = None
    content_to_send = []
    
    # 🚩 ตรวจสอบโหมด "เรียนรู้ด้วยตนเอง" (Self-Learning Mode)
    is_learning_mode = False
    if incoming_message and any(k in incoming_message.lower() for k in ["บันทึกความรู้", "จงเรียนรู้", "learn this", "บันทึกลงฐานข้อมูล"]):
        is_learning_mode = True

    try:
        # ==========================================
        # 1. ดึงความรู้จาก Corporate DB และประวัติลูกค้า (Graph RAG Engine)
        # ==========================================
        corporate_context = ""
        user_history = ""
        
        if incoming_message and not is_learning_mode:
            try:
                corporate_context = await asyncio.to_thread(recall_corporate_knowledge, incoming_message)
                user_history = await asyncio.to_thread(recall_memory, user_id, incoming_message)
            except Exception as rag_err:
                logger.warning(f"⚠️ [RAG Fetch Warning]: {rag_err}")

        # ==========================================
        # 2. ระบบจัดการไฟล์และมัลติมีเดียขั้นสูง
        # ==========================================
        if file_path and os.path.exists(file_path):
            logger.info(f"🧠 [Prime Brain]: กำลังสกัดข้อมูลจากไฟล์ {file_type}...")
            
            mime_type, _ = mimetypes.guess_type(file_path)
            if file_path.lower().endswith(('.xlsx', '.xls')): mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            elif file_path.lower().endswith('.csv'): mime_type = "text/csv"
            elif file_path.lower().endswith('.pdf'): mime_type = "application/pdf"
            if not mime_type: mime_type = "application/octet-stream"

            try:
                upload_config = types.UploadFileConfig(mime_type=mime_type)
                uploaded_file = await asyncio.to_thread(client.files.upload, file=file_path, config=upload_config)
            except Exception as e:
                logger.warning(f"⚠️ File upload rejected by AI: {e}")
                return "⚠️ ระบบความปลอดภัยปฏิเสธไฟล์ชนิดนี้ครับ รบกวนบันทึกเป็น PDF, รูปภาพ หรือไฟล์เสียง แล้วส่งมาใหม่อีกครั้งนะครับ"

            timeout = 60
            start_time = time.time()
            while uploaded_file.state.name == "PROCESSING":
                if time.time() - start_time > timeout:
                    raise TimeoutError("การประมวลผลไฟล์ใช้เวลานานเกินกำหนดระบบรักษาความปลอดภัย")
                await asyncio.sleep(2)
                uploaded_file = await asyncio.to_thread(client.files.get, name=uploaded_file.name)
                
            if uploaded_file.state.name == "FAILED":
                return "⚠️ ขออภัยครับ โครงสร้างไฟล์มีความซับซ้อนหรือติดรหัสผ่าน ระบบ AI ไม่สามารถถอดรหัสไฟล์นี้ได้ครับ"
                
            content_to_send.append(uploaded_file)
            
            if is_learning_mode:
                content_to_send.append("โปรดสกัดองค์ความรู้สำคัญจากไฟล์นี้ และจัดโครงสร้างเป็นหมวดหมู่ เพื่อให้ระบบนำไปบันทึกลงฐานข้อมูลส่วนกลางอย่างมีประสิทธิภาพ")
            elif not incoming_message or incoming_message.startswith("[System Alert:"):
                content_to_send.append("โปรดวิเคราะห์ สกัดข้อมูลสำคัญ และอธิบายรายละเอียดเชิงลึกจากไฟล์นี้อย่างมืออาชีพครับ")
            else:
                content_to_send.append(incoming_message)
        else:
            content_to_send.append(incoming_message)

        # ==========================================
        # 3. ประกอบร่าง Graph RAG Context
        # ==========================================
        final_prompt = ""
        if corporate_context or user_history:
            final_prompt += "\n\n--- [ข้อมูลสนับสนุนจากระบบความจำ Graph RAG] ---\n"
            if corporate_context:
                final_prompt += f"🏢 [ฐานความรู้องค์กร/กฎหมาย]:\n{corporate_context}\n"
            if user_history:
                final_prompt += f"👤 [ประวัติและพฤติกรรมลูกค้ารายนี้]:\n{user_history}\n"
            final_prompt += "--------------------------------------------------\nโปรดใช้ข้อมูลข้างต้นประกอบการวิเคราะห์อย่างเหนือชั้น"
            
            content_to_send.append(final_prompt)

        # ==========================================
        # 4. สั่งรันโมเดลเรือธง (Gemini 3.1 Pro + Search)
        # ==========================================
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=MODEL_NAME,
            contents=content_to_send,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2, 
                tools=[{"google_search": {}}] 
            )
        )
        
        reply_text = response.text if response.text else "รับทราบข้อมูลเรียบร้อยครับ มีส่วนไหนให้ผมช่วยเหลือเพิ่มเติม แจ้งได้เลยครับ"
        
        # ==========================================
        # 5. ระบบสร้างเอกสารรายงานอัตโนมัติ (Document Engine)
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
            
            base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
            
            html_template = f"""
            <!DOCTYPE html>
            <html lang="th">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{safe_filename} - SIRINTHANATTH PRIME</title>
                <link href="https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;600;700&display=swap" rel="stylesheet">
                <style>
                    body {{ font-family: 'Sarabun', sans-serif; background-color: #050505; color: #E0E0E0; line-height: 1.7; padding: 20px; }}
                    .container {{ max-width: 1000px; margin: 0 auto; background: #0F0F13; padding: 50px; box-shadow: 0 15px 40px rgba(0, 229, 255, 0.08); border-radius: 16px; border-top: 6px solid #D4AF37; }}
                    .header {{ text-align: center; margin-bottom: 40px; border-bottom: 1px solid #222; padding-bottom: 25px; }}
                    .header h1 {{ color: #D4AF37; margin: 0; font-size: 32px; text-transform: uppercase; letter-spacing: 3px; font-weight: 700; }}
                    .header p {{ color: #888; font-weight: 400; margin-top: 10px; font-size: 14px; letter-spacing: 1px; }}
                    h2, h3 {{ color: #00E5FF; margin-top: 30px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 25px; margin-bottom: 25px; color: #fff; background: #15151A; }}
                    th, td {{ border: 1px solid #333; padding: 15px; text-align: left; }}
                    th {{ background-color: #1A1A24; color: #D4AF37; font-weight: 600; text-transform: uppercase; font-size: 14px; }}
                    pre {{ background: #0A0A0C; padding: 20px; border-radius: 10px; overflow-x: auto; color: #00E5FF; border: 1px solid #2A2A35; box-shadow: inset 0 0 10px rgba(0,0,0,0.5); }}
                    code {{ font-family: 'Consolas', 'Courier New', monospace; font-size: 14.5px; }}
                    .timestamp {{ text-align: right; font-size: 12px; color: #555; margin-top: 40px; border-top: 1px solid #222; padding-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>SIRINTHANATTH PRIME</h1>
                        <p>STRICTLY CONFIDENTIAL • PRIME BRAIN ANALYTICS</p>
                    </div>
                    <div class="content">
                        {file_content}
                    </div>
                    <div class="timestamp">Generated by Prime Omniscient Core | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                </div>
            </body>
            </html>
            """
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html_template)
                
            generated_file_url = f"{base_url}/{reports_dir}/{safe_filename}"
            reply_text += f"\n\n📄 **แฟ้มเอกสารรายงานการวิเคราะห์ พร้อมแล้วครับ**\nคลิกเพื่อตรวจสอบรายละเอียด และสามารถกด (Ctrl+P) เพื่อบันทึกเป็น PDF เก็บไว้ได้ทันทีครับ:\n👉 {generated_file_url}"

        # ==========================================
        # 6. ตรวจจับการส่งต่องาน (Swarm Delegation)
        # ==========================================
        delegate_match = re.search(r'\[DELEGATE:\s*(.+?)\](.*)', reply_text, re.DOTALL | re.IGNORECASE)
        if delegate_match:
            target_worker = delegate_match.group(1).strip()
            handoff_message = delegate_match.group(2).strip()
            
            reply_text = re.sub(r'\[DELEGATE:\s*(.+?)\](.*)', '', reply_text, flags=re.DOTALL | re.IGNORECASE).strip()
            
            worker_response = await swarm_hub.delegate_task(
                from_worker="PRIME_BRAIN", 
                to_worker=target_worker, 
                user_id=user_id, 
                message=handoff_message, 
                file_path=file_path, 
                file_type=file_type
            )
            return f"{reply_text}\n\n🔄 [สมองกลส่งต่อให้ผู้เชี่ยวชาญ {target_worker}]:\n{worker_response}"

        # ==========================================
        # 7. การบันทึกความรู้ (Self-Learning) และความจำ
        # ==========================================
        if is_learning_mode and uploaded_file:
            title = f"Knowledge_Extract_{int(time.time())}"
            success = await asyncio.to_thread(save_corporate_knowledge, title, reply_text)
            if success:
                reply_text = f"✅ [Knowledge Ingestion]: สกัดความรู้และบันทึกลงฐานข้อมูลสมองกลของ SIRINTHANATTH PRIME สำเร็จเรียบร้อยแล้วครับ\n\nสรุปเนื้อหา:\n{reply_text}"
            else:
                reply_text = "⚠️ สกัดความรู้สำเร็จ แต่เกิดข้อผิดพลาดในการเชื่อมต่อ Vector Database เพื่อบันทึกข้อมูลครับ"

        elif incoming_message and not incoming_message.startswith("[System Alert:"):
            # กรองข้อความสั้นๆ ทิ้ง ประหยัดพื้นที่
            if len(incoming_message) > 10 or len(reply_text) > 20:
                compact_memory = f"Q: {incoming_message[:150]} | A: {reply_text[:150]}"
                asyncio.create_task(asyncio.to_thread(save_memory, user_id, compact_memory))
            
        return reply_text
        
    except TimeoutError:
        logger.error("❌ [Prime Brain Timeout]: ไฟล์มีขนาดใหญ่หรือซับซ้อนเกินไป")
        return "ขออภัยครับคุณลูกค้า ไฟล์มีขนาดใหญ่เกินไป ทำให้ระบบประมวลผลนานกว่าปกติ รบกวนย่อขนาดไฟล์ลงนิดนึงนะครับ"
    except Exception as e:
        logger.error(f"❌ [Prime Brain Error]: {e}")
        return "ขออภัยครับ ขณะนี้ระบบประมวลผลหลักอัจฉริยะกำลังปรับปรุงฐานข้อมูล กรุณาลองส่งข้อความใหม่อีกครั้งในสักครู่ครับ"
        
    finally:
        # ==========================================
        # 🧹 8. Zero-Data Retention (ทำลายไฟล์ทิ้งเพื่อความปลอดภัยขั้นสูงสุด)
        # ==========================================
        if uploaded_file:
            try:
                await asyncio.to_thread(client.files.delete, name=uploaded_file.name)
                logger.info(f"🛡️ [Zero-Data Security]: ทำลายไฟล์ {uploaded_file.name} ออกจากระบบ AI Cloud ทิ้งถาวรเรียบร้อยแล้ว")
            except Exception as e:
                logger.error(f"⚠️ [File Deletion Error]: ไม่สามารถลบไฟล์จาก AI Cloud ได้ -> {e}")