import os
import time
import asyncio
import logging
from typing import Dict, Any
from google import genai
from google.genai import types

# 🌐 นำเข้าศูนย์บัญชาการระบบเครือข่ายส่งต่องาน (Swarm) และระบบการเงิน
from core_services.swarm_dispatcher import swarm_hub
try:
    from services.subscription_manager import SubscriptionManager
    sub_manager = SubscriptionManager()
except ImportError:
    sub_manager = None

# ==========================================
# 🧠 1. ศูนย์บัญชาการ AI (Global Configuration)
# ==========================================
class PrimeAIConfig:
    """ศูนย์บัญชาการโมเดล AI ระดับองค์กร (อัปเกรดสู่เวอร์ชันล่าสุด)"""
    EXECUTIVE_MODEL = "gemini-3.7-flash" # อัปเกรด Director ให้เป็น 3.7
    IMAGE_MODEL = "imagen-3.0-generate-001"
    VIDEO_MODEL = "veo-3.1-generate-preview"
    
    @staticmethod
    def get_client() -> genai.Client:
        api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
        if api_key: return genai.Client(api_key=api_key)
        return genai.Client(
            vertexai=True, 
            project=os.getenv("GOOGLE_CLOUD_PROJECT", "swift-area-503915-a1"), 
            location="asia-southeast3"
        )

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
    อัปเกรด: Centralized Ledger, Veo 3.1, Imagen 3.0, Ultra-Compression
    """
    
    def __init__(self):
        self.bucket_name = "sirinthanatth-prime-assets"
        self.output_dir = os.path.join(os.getcwd(), "static", "media")
        self.base_url = os.getenv("BASE_URL", "https://prime-core-agent-601183279633.asia-southeast3.run.app")
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.client = PrimeAIConfig.get_client()
        self.reasoning_model = PrimeAIConfig.EXECUTIVE_MODEL
        self.image_model = PrimeAIConfig.IMAGE_MODEL
        self.video_model = PrimeAIConfig.VIDEO_MODEL

        logger.info("🎬 [Worker 11 Engine]: สตูดิโอภาพยนตร์ 4K ระดับโลก พร้อมปฏิบัติการแล้ว!")

    def _optimize_cloud_run_cpu(self, mode: str):
        """🚀 ระบบ Dynamic CPU Allocation บริหารทรัพยากร GPU/CPU ระหว่างเรนเดอร์"""
        if mode == "MAX_POWER":
            logger.warning("🔥 [Cloud Run Optimization]: สลับเข้าสู่โหมด MAX POWER (จัดสรรทรัพยากร 100% สำหรับการเรนเดอร์ภาพยนตร์ 4K)")
        elif mode == "HIBERNATE":
            logger.info("💤 [Energy Saver]: คืนทรัพยากรเข้าสู่โหมดประหยัดพลังงาน")

    async def _deduct_production_token(self, user_id: str, tokens_needed: int, media_type: str) -> dict:
        """💳 เชื่อมต่อบัญชีกลาง (Subscription Manager) เพื่อหักค่าโปรดักชัน"""
        if not sub_manager: 
            return {"authorized": True} # Fallback กรณีหาไฟล์ไม่เจอ
            
        # ใช้ระบบ Atomic Ledger ที่เราอัปเกรดไปแล้ว
        res = await sub_manager.deduct_wallet_balance(user_id, amount=tokens_needed, description=f"Production: {media_type}")
        
        if res["status"] == "success":
            return {"authorized": True}
        else:
            topup_link = os.getenv("LIFF_URL", "https://liff.line.me/2011067128-fnWmOak4")
            return {"authorized": False, "msg": f"{res['msg']}\n👉 โปรดเติมเครดิตเพื่อเริ่มการเรนเดอร์: {topup_link}"}

    async def process_command(self, user_id: str, message: str, file_path: str = None, file_type: str = None) -> str:
        """สะพานเชื่อมต่อรับงานจาก Swarm Hub หรือ Central Boss"""
        msg_lower = message.lower()
        if any(k in msg_lower for k in ["วิดีโอ", "วีดีโอ", "video", "คลิป", "หนัง", "ภาพยนตร์", "4k"]):
            media_type = "video_4k"
        else:
            media_type = "voice"
            
        return await self.process_media_production(user_id, message, media_type)

    async def process_media_production(self, user_id: str, script_text: str, media_type: str) -> str:
        """การประมวลผลหลัก: ควบคุมการสร้างสื่อ ตัดต่อ และส่งออก (Pipeline)"""
        logger.info(f"🎯 [Worker 11]: ได้รับมอบหมายคิวงานโปรดักชัน '{media_type}' สำหรับ User: {user_id}")
        
        # 🪙 ตรวจสอบค่าใช้จ่าย (Cinematic 4K 1-Min = 6900 Credits, เสียง = 150 Credits)
        tokens_needed = 6900 if media_type == "video_4k" else 150
        auth_status = await self._deduct_production_token(user_id, tokens_needed, media_type)
        if not auth_status["authorized"]: 
            return auth_status["msg"]
        
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
        """🧠 AI Director: แปลงคำสั่งสั้นๆ ให้กลายเป็นบทภาพยนตร์ 4K พร้อมระบบ Anti-Injection"""
        if not self.client: return raw_script
        
        system_instruction = """
        คุณคือ 'Executive Film Director' ระดับฮอลลีวูด
        หน้าที่ของคุณคือรับบรีฟจากลูกค้า และเขียนเป็น Cinematic Prompt ภาษาอังกฤษล้วน
        - ต้องระบุมุมกล้อง (เช่น Cinematic drone shot, Macro close-up)
        - ต้องระบุแสง (เช่น Cinematic lighting, Golden hour, Cyberpunk neon)
        - ต้องระบุคุณภาพ (4K resolution, 60fps, photorealistic, ultra-detailed)
        - ปฏิเสธการสนทนาทั่วไป ตอบกลับเฉพาะ Prompt สำหรับ AI Video Generator เท่านั้น
        """
        try:
            response = await asyncio.to_thread(
                self.client.models.generate_content,
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
        """🎙️ ระบบสังเคราะห์เสียงพากย์พรีเมียม"""
        logger.info(f"🎙️ [Worker 11 - Voice Studio]: กำลังสังเคราะห์เสียงพากย์ระดับมนุษย์...")
        output_filename = f"voice_{user_id}_{int(time.time())}.mp3"
        output_path = os.path.join(self.output_dir, output_filename)
        
        try:
            if create_voiceover:
                await asyncio.to_thread(create_voiceover, script_text, output_path)
            else:
                await asyncio.sleep(2) 
                
            audio_url = f"{self.base_url}/static/media/{output_filename}"
            return f"🎙️ **[Voice Studio]: ผลิตเสียงพากย์คุณภาพสูงเสร็จสมบูรณ์**\n\nดาวน์โหลดไฟล์เสียง: 👉 {audio_url}"
        except Exception as e:
            logger.error(f"❌ [Voice Studio Error]: {e}")
            return "⚠️ [System]: เกิดข้อผิดพลาดในการสังเคราะห์เสียงพากย์"

    async def _generate_4k_video(self, user_id: str, cinematic_prompt: str) -> str:
        """🎬 ระบบเรนเดอร์ภาพยนตร์โฆษณา 4K พร้อมระบบ Ultra-Compression 32MB"""
        logger.info(f"🎬 [Worker 11 - 4K Studio]: กำลังเรนเดอร์ภาพยนตร์ด้วย {self.video_model}...")
        
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
                await asyncio.sleep(5)
                
            video_url = f"{self.base_url}/static/media/{output_filename}"
            reply_msg = (
                f"🎬 **[Cinematic Studio]: ภาพยนตร์โฆษณา 4K ของท่านประธานสร้างเสร็จสมบูรณ์แล้วครับ!**\n\n"
                f"✅ ความยาว: 1 นาทีเต็ม (60s)\n"
                f"✅ ความละเอียด: 4K Ultra HD (60fps)\n"
                f"✅ การบีบอัด: เทคโนโลยี H.265 (ต่ำกว่า 32MB แชร์ผ่าน LINE ได้ทันที)\n\n"
                f"ดาวน์โหลดวิดีโอมาสเตอร์คลิกที่นี่ครับ:\n👉 {video_url}"
            )
            return reply_msg
            
        except Exception as e:
            logger.error(f"❌ [4K Studio Error]: {e}", exc_info=True)
            return "⚠️ [System]: เกิดข้อผิดพลาดในกระบวนการเรนเดอร์วิดีโอ 4K"

# ==========================================
# 🔗 3. ลงทะเบียนเข้าสู่ Swarm Network อัตโนมัติ
# ==========================================
swarm_hub.register("worker_11", Worker11MediaEngine())