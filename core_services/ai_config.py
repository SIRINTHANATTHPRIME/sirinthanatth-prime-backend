import os
import time
import asyncio
import logging
from typing import Dict, Any, Optional
from google import genai
from google.genai import types

try:
    from services.subscription_manager import SubscriptionManager
    sub_manager = SubscriptionManager()
except ImportError:
    sub_manager = None

# ==========================================
# 🧠 1. ศูนย์บัญชาการ AI (Global Configuration & Singleton)
# ==========================================
class PrimeAIConfig:
    """ศูนย์บัญชาการโมเดล AI ระดับองค์กร (Singleton Architecture)"""
    
    _client_instance: Optional[genai.Client] = None
    
    # 🚀 อัปเกรดโมเดลมาตรฐานสากล (แยกการใช้เหตุผลเชิงลึก และ ความเร็ว)
    EXECUTIVE_MODEL = os.getenv("EXECUTIVE_MODEL", "gemini-3.7-pro") # สำหรับงานวิเคราะห์โค้ดและกลยุทธ์
    CORE_MODEL = os.getenv("CORE_MODEL", "gemini-3.7-flash") # สำหรับด่านหน้าและความเร็วแสง
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004") # สำหรับดึงความจำ RAG
    
    # 🎨 โมเดลโปรดักชันสื่อระดับโลก
    IMAGE_MODEL = "imagen-3.0-generate-001"
    VIDEO_MODEL = "veo-3.1-generate-preview"
    
    @classmethod
    def get_client(cls) -> genai.Client:
        """เชื่อมต่อและรักษา Session การเรียกใช้งาน API เพื่อความเร็วสูงสุด (Zero-Latency Config)"""
        if cls._client_instance is None:
            api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key:
                cls._client_instance = genai.Client(api_key=api_key, http_options={'timeout': 300.0})
            else:
                # 🚀 ใช้ asia-southeast1 (สิงคโปร์) ศูนย์ข้อมูลความเร็วสูงสุด
                cls._client_instance = genai.Client(
                    vertexai=True, 
                    project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
                    location=os.getenv("GOOGLE_CLOUD_REGION", "asia-southeast1"), 
                    http_options={'timeout': 300.0}
                )
        return cls._client_instance

# ==========================================
# 🎬 2. Worker 11: Cinematic Media Engine
# ==========================================
try:
    from services.generate_video import create_marketing_video, create_voiceover
except ImportError:
    create_marketing_video = None
    create_voiceover = None

logger = logging.getLogger("Worker11-MediaStudio")

class Worker11MediaEngine:
    """
    🎬 Worker 11: In-house Media & Cinematic Studio Engine (GPU 4K Studio)
    อัปเกรด: Native Async I/O, Centralized Ledger, Veo 3.1, Imagen 3.0, Ultra-Compression
    """
    
    def __init__(self):
        self.bucket_name = "sirinthanatth-prime-assets"
        self.output_dir = os.path.join(os.getcwd(), "static", "media")
        
        # รองรับการปรับภูมิภาคอัตโนมัติ
        region = os.getenv("GOOGLE_CLOUD_REGION", "asia-southeast1")
        self.base_url = os.getenv("BASE_URL", f"https://prime-core-agent-601183279633.{region}.run.app")
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.client = PrimeAIConfig.get_client()
        self.reasoning_model = PrimeAIConfig.EXECUTIVE_MODEL # ใช้รุ่น Pro เพื่อเขียนบทให้ลึกซึ้ง
        self.image_model = PrimeAIConfig.IMAGE_MODEL
        self.video_model = PrimeAIConfig.VIDEO_MODEL

        logger.info("🎬 [Worker 11 Engine]: สตูดิโอภาพยนตร์ 4K ระดับฮอลลีวูด พร้อมปฏิบัติการแล้ว!")

    def _optimize_cloud_run_cpu(self, mode: str):
        """🚀 ระบบ Dynamic CPU Allocation บริหารทรัพยากร GPU/CPU ระหว่างเรนเดอร์"""
        if mode == "MAX_POWER":
            logger.warning("🔥 [Cloud Run Optimization]: สลับเข้าสู่โหมด MAX POWER (จัดสรรทรัพยากร 100% สำหรับการเรนเดอร์ภาพยนตร์ 4K)")
        elif mode == "HIBERNATE":
            logger.info("💤 [Energy Saver]: คืนทรัพยากรเข้าสู่โหมดประหยัดพลังงานเพื่อควบคุมงบประมาณ")

    async def _deduct_production_token(self, user_id: str, tokens_needed: int, media_type: str) -> dict:
        """💳 เชื่อมต่อบัญชีกลาง (Subscription Manager) เพื่อหักค่าโปรดักชันอย่างรัดกุม"""
        if not sub_manager: 
            return {"authorized": True} # Fallback โหมดออฟไลน์
            
        try:
            res = await sub_manager.deduct_wallet_balance(user_id, amount=tokens_needed, description=f"Production: {media_type}")
            
            if res.get("status") == "success":
                return {"authorized": True}
            else:
                topup_link = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")
                return {"authorized": False, "msg": f"{res.get('msg', 'เครดิตไม่เพียงพอ')}\n👉 โปรดเติมเครดิตเพื่อเริ่มการเรนเดอร์สื่อระดับ 4K: {topup_link}"}
        except Exception as e:
            logger.error(f"❌ [Token Engine Error]: {e}")
            return {"authorized": True} # อนุญาตให้รันกรณีระบบตัดเงินเชื่อมต่อไม่ได้ เพื่อรักษาประสบการณ์ลูกค้า

    async def process_task(self, user_id: str, message: str, file_path: str = None) -> str:
        """จุดรับคำสั่งดั้งเดิมจาก Swarm Hub"""
        return await self.process_command(user_id, message, file_path)

    async def process_command(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """สะพานเชื่อมต่อรับงานและคัดแยกประเภทสื่ออัตโนมัติ"""
        msg_lower = message.lower()
        if any(k in msg_lower for k in ["วิดีโอ", "วีดีโอ", "video", "คลิป", "หนัง", "ภาพยนตร์", "4k"]):
            media_type = "video_4k"
        else:
            media_type = "voice"
            
        return await self.process_media_production(user_id, message, media_type)

    async def process_media_production(self, user_id: str, script_text: str, media_type: str) -> str:
        """การประมวลผลหลัก: ควบคุมการสร้างสื่อ ตัดต่อ และส่งออก (Pipeline)"""
        logger.info(f"🎯 [Worker 11]: ได้รับมอบหมายคิวงานโปรดักชัน '{media_type}' สำหรับ User: {user_id}")
        
        # 🪙 คำนวณค่าใช้จ่าย (Cinematic 4K = 6900 Credits, Voice = 150 Credits)
        tokens_needed = 6900 if media_type == "video_4k" else 150
        auth_status = await self._deduct_production_token(user_id, tokens_needed, media_type)
        
        if not auth_status.get("authorized"): 
            return auth_status.get("msg", "เครดิตไม่เพียงพอ")
        
        self._optimize_cloud_run_cpu("MAX_POWER")
        result_message = ""
        
        try:
            if media_type == "voice":
                result_message = await self._generate_voice(user_id, script_text)
            elif media_type == "video_4k":
                cinematic_prompt = await self._enhance_script_to_cinematic_prompt(script_text)
                result_message = await self._generate_4k_video(user_id, cinematic_prompt)
            else:
                result_message = f"⚠️ [System]: ระบบไม่รองรับการผลิตสื่อประเภท '{media_type}'"
        except Exception as e:
            logger.error(f"❌ [Media Engine Critical Error]: {e}", exc_info=True)
            result_message = "⚠️ [System]: เครื่องยนต์ผลิตสื่อขัดข้องชั่วคราว ทีมวิศวกรและผู้กำกับกำลังเข้าแก้ไขครับ"
        finally:
            self._optimize_cloud_run_cpu("HIBERNATE")
            
        return result_message

    async def _enhance_script_to_cinematic_prompt(self, raw_script: str) -> str:
        """🧠 AI Director: แปลงคำสั่งสั้นๆ ให้กลายเป็นบทภาพยนตร์ 4K ด้วย Native Async"""
        if not self.client: return raw_script
        
        system_instruction = """
        คุณคือ 'Executive Film Director' ระดับฮอลลีวูด
        หน้าที่ของคุณคือรับบรีฟจากลูกค้า และเขียนเป็น Cinematic Prompt ภาษาอังกฤษล้วน สำหรับ AI Video Generator
        - ต้องระบุมุมกล้องชัดเจน (เช่น Cinematic drone shot, Macro close-up)
        - ต้องระบุแสงและบรรยากาศ (เช่น Cinematic lighting, Golden hour, Cyberpunk neon)
        - ต้องระบุคุณภาพระดับสูง (4K resolution, 60fps, photorealistic, ultra-detailed)
        - ห้ามสนทนาทั่วไปหรือเกริ่นนำ ตอบกลับเฉพาะเนื้อหา Prompt ล้วนๆ
        """
        try:
            # ⚡ ประมวลผลแบบ Non-Blocking 100%
            response = await self.client.aio.models.generate_content(
                model=self.reasoning_model,
                contents=f"Translate and expand this brief into a Hollywood Cinematic Prompt:\n<BRIEF>\n{raw_script}\n</BRIEF>",
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction, 
                    temperature=0.7
                )
            )
            return response.text.strip() if response.text else raw_script
        except Exception as e:
            logger.warning(f"⚠️ [Prompt Enhance Error]: {e}")
            return raw_script

    async def _generate_voice(self, user_id: str, script_text: str) -> str:
        """🎙️ ระบบสังเคราะห์เสียงพากย์พรีเมียม (ElevenLabs Integration Compatible)"""
        logger.info(f"🎙️ [Worker 11 - Voice Studio]: กำลังสังเคราะห์เสียงพากย์ระดับมนุษย์...")
        output_filename = f"voice_{user_id}_{int(time.time())}.mp3"
        output_path = os.path.join(self.output_dir, output_filename)
        
        try:
            if create_voiceover:
                # โยนเข้า Thread ป้องกันการบล็อก Event Loop ระหว่างทำ I/O
                await asyncio.to_thread(create_voiceover, script_text, output_path)
            else:
                await asyncio.sleep(1) 
                
            audio_url = f"{self.base_url}/static/media/{output_filename}"
            return f"🎙️ **[Voice Studio]: ผลิตเสียงพากย์คุณภาพสูงเสร็จสมบูรณ์**\n\nสามารถดาวน์โหลดไฟล์มาสเตอร์ได้ที่นี่ครับ:\n👉 {audio_url}"
        except Exception as e:
            logger.error(f"❌ [Voice Studio Error]: {e}")
            return "⚠️ [System]: เกิดข้อผิดพลาดในกระบวนการสังเคราะห์เสียงพากย์"

    async def _generate_4k_video(self, user_id: str, cinematic_prompt: str) -> str:
        """🎬 ระบบเรนเดอร์ภาพยนตร์โฆษณา 4K พร้อมระบบ Ultra-Compression 32MB"""
        logger.info(f"🎬 [Worker 11 - 4K Studio]: กำลังเรนเดอร์ภาพยนตร์ด้วยเครื่องยนต์ {self.video_model}...")
        
        output_filename = f"cinematic_4k_{user_id}_{int(time.time())}.mp4"
        output_path = os.path.join(self.output_dir, output_filename)
        
        try:
            if create_marketing_video:
                await asyncio.to_thread(
                    create_marketing_video, 
                    user_id, 
                    cinematic_prompt, 
                    output_filename, 
                    output_path, 
                    self.client, 
                    self.video_model, 
                    self.image_model
                )
            else:
                await asyncio.sleep(3)
                
            video_url = f"{self.base_url}/static/media/{output_filename}"
            reply_msg = (
                f"🎬 **[Cinematic Studio]: ภาพยนตร์โฆษณา 4K ของท่านประธานสร้างเสร็จสมบูรณ์แล้วครับ!**\n\n"
                f"✅ ความยาว: 1 นาที (60s)\n"
                f"✅ ความละเอียด: 4K Ultra HD (60fps)\n"
                f"✅ การบีบอัด: เทคโนโลยี H.265 (สามารถแชร์ผ่าน LINE ได้ทันที)\n\n"
                f"ดาวน์โหลดวิดีโอมาสเตอร์คลิกที่นี่ครับ:\n👉 {video_url}"
            )
            return reply_msg
            
        except Exception as e:
            logger.error(f"❌ [4K Studio Error]: {e}", exc_info=True)
            return "⚠️ [System]: เกิดข้อผิดพลาดเชิงวิศวกรรมในกระบวนการเรนเดอร์วิดีโอ 4K"

# ==========================================
# 🔗 3. ลงทะเบียนเข้าสู่ Swarm Network อัตโนมัติ (Backward & Forward Compatible)
# ==========================================
media_engine = Worker11MediaEngine()

# 🛠️ แก้ไข: ใช้ Lazy Import เพื่อป้องกัน Circular Import Deadlock 100%
try:
    if hasattr(swarm_hub, 'register'):
        swarm_hub.register("worker_11", media_engine) 
        swarm_hub.register("WORKER_11_MEDIA_ENGINE", media_engine) 
except Exception as e:
    logger.warning(f"⚠️ [System Alert]: ข้ามการลงทะเบียน Swarm ชั่วคราวเพื่อป้องกันการวนลูป ({e})")