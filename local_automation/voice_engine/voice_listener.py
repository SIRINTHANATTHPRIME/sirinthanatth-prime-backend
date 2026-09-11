import speech_recognition as sr
import webbrowser
import os
import time
from gtts import gTTS
import pygame
from google import genai
from dotenv import load_dotenv

# 1. โหลดกุญแจสมองกลจากไฟล์ .env
load_dotenv()
api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None
is_standby = False

# 🚀 อัปเกรดใช้ SDK มาตรฐานใหม่ล่าสุดของ Google GenAI
if api_key:
    client = genai.Client(api_key=api_key)
else:
    client = None
    print("⚠️ [Warning]: ไม่พบ AI_API_KEY ในไฟล์ .env ระบบอาจไม่สามารถคิดคำตอบเองได้")

def speak(text):
    """ฟังก์ชันแปลงข้อความให้เปล่งเสียงออกลำโพงคอมพิวเตอร์"""
    print(f"🤖 [PRIME พูด]: {text}")
    try:
        tts = gTTS(text=text, lang='th')
        filename = "prime_voice_temp.mp3"
        tts.save(filename)
        
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
            
        pygame.mixer.quit()
        if os.path.exists(filename):
            os.remove(filename)
    except Exception as e:
        print(f"⚠️ [System Error]: ระบบลำโพงขัดข้อง - {e}")

def ask_prime_brain(prompt):
    """ส่งคำสั่งเสียงไปให้ Gemini พร้อมระบบ Exponential Backoff ป้องกันคอขวด 503/429"""
    if not client:
        return "ขออภัยครับท่านประธาน ผมไม่สามารถเชื่อมต่อสมองกลส่วนกลางได้ กรุณาตรวจสอบไฟล์ดอทอีเอ็นวีครับ"
    
    system_instruction = "คุณคือ SIRINTHANATTH PRIME เลขา AI ระดับสากลของคุณวีระชัย ตอบกลับแบบรวดเร็ว ฉะฉาน ฉลาด กระตือรือร้นระดับ CEO ไม่เยิ่นเย้อ ลงท้ายด้วยครับท่านประธาน เสมอ"
    
    max_retries = 3
    delay = 2

    for attempt in range(max_retries):
        try:
            # 🚀 ใช้ขุมพลัง Flash มาตรฐานเดียวกับระบบ Central Boss
            response = client.models.generate_content(
                model='gemini-3.7-flash',
                contents=f"{system_instruction}\nคำสั่งจากท่านประธาน: {prompt}"
            )
            return response.text.replace("*", "").strip()
            
        except Exception as e:
            err_str = str(e).upper()
            # ตรวจจับ Error 503 (เซิร์ฟเวอร์ล่ม/หนาแน่น) หรือ 429 (โควตาเต็ม)
            if ("503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str) and attempt < max_retries - 1:
                print(f"⚠️ [Server Busy]: สัญญาณหนาแน่น กำลังเชื่อมต่อใหม่ใน {delay} วินาที (รอบที่ {attempt + 1})...")
                time.sleep(delay)
                delay *= 2 # ทวีคูณเวลารอ (2s -> 4s)
                continue
            
            return f"ขออภัยครับท่านประธาน ตอนนี้เครือข่ายสมองกลปลายทางติดขัดชั่วคราวครับ"

def trigger_executive_dashboard():
    """เปิดหน้าจออนุมัติ 3 ปุ่ม"""
    current_dir = os.getcwd()
    if "voice_engine" in current_dir:
        base_dir = os.path.dirname(os.path.dirname(current_dir))
    else:
        base_dir = current_dir
        
    html_path = os.path.join(base_dir, "fronted_web", "executive_control.html")
    
    if os.path.exists(html_path):
        url = 'file://' + html_path.replace('\\', '/')
        webbrowser.open(url)
    else:
        print(f"❌ [Error]: ไม่พบไฟล์ที่ {html_path}")

def start_voice_engine():
    global is_standby
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()

    print("\n" + "="*50)
    print("👑 SIRINTHANATTH PRIME : VOICE STANDBY MODE")
    print("="*50)

    speak("ระบบปฏิบัติการ สิรินทร์ธนัตถ์ ไพรม์ พร้อมรับคำสั่งจากท่านประธานแล้วครับ")

    while True:
        try:
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=8)
            
            command = recognizer.recognize_google(audio, language="th-TH").strip()
            print(f"\n🗣️ ตรวจจับเสียง: '{command}'")

            # --- โหมดพัก (Standby) ---
            if is_standby:
                if "สิรินทร์ธนัชพรหม" in command.replace(" ", ""):
                    is_standby = False
                    speak("ปลดล็อกระบบโครงสร้างหลักครับ ผมพร้อมจัดการแก้ไขไฟล์ อัปเกรดโค้ด และสั่งการทุกแผนกแทนคุณแล้วครับ")
                elif "สิรินทร์ธนัตถ์" in command.replace(" ", ""):
                    is_standby = False
                    speak("พร้อมครับท่านประธาน มีวาระเร่งด่วนอะไรให้ผมจัดการ สั่งมาได้เลยครับ")
                continue

            # --- โหมดทำงาน (Active) ---
            if any(word in command for word in ["เท่านี้ก่อน", "พักก่อน", "สแตนด์บาย"]):
                is_standby = True
                speak("รับทราบครับ พักเข้าสู่โหมดสแตนด์บาย เรียกผมได้ทันทีที่ต้องการครับ")
                continue
                
            elif any(word in command for word in ["ตกลง", "อนุมัติ"]):
                speak("ระบบรับคำสั่งอนุมัติ กำลังสั่งการ Worker ดำเนินการผสานโค้ดเข้าสู่ระบบหลักทันทีครับ")
                # (อนาคตเชื่อมฟังก์ชันเขียนไฟล์อัตโนมัติที่นี่)
                continue
            
            else:
                ai_answer = ask_prime_brain(command)
                speak(ai_answer)

        except sr.UnknownValueError:
            pass
        except Exception as e:
            print(f"⚠️ [Loop Error]: {e}")

if __name__ == "__main__":
    start_voice_engine()