import speech_recognition as sr
import webbrowser
import os
import sys
import time
import subprocess
import threading
from gtts import gTTS
import pygame
from google import genai
from dotenv import load_dotenv

# 1. โหลดกุญแจสมองกลจากไฟล์ .env
load_dotenv()
api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
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

def get_project_root():
    """🔍 ค้นหา Root Directory ของโปรเจกต์อัตโนมัติ เพื่อให้รันคำสั่ง Git ได้แม่นยำ"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # ไต่ระดับขึ้นไป 3 ขั้น (voice_engine -> local_automation -> SIRINTHANATTH_PRIME_BACKEND)
    root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
    return root_dir

def execute_git_deployment():
    """🚀 กระบวนการอัปโหลดโค้ดขึ้น Google Cloud Run (รันใน Background Thread)"""
    def _deploy_process():
        project_root = get_project_root()
        print(f"\n⚙️ [Deployment Engine]: กำลังรันคำสั่ง Git ที่โฟลเดอร์ {project_root}")
        
        try:
            # 1. ตรวจสอบว่ามี Git ในระบบหรือไม่
            subprocess.run(["git", "--version"], cwd=project_root, check=True, capture_output=True)
            
            # 2. เพิ่มไฟล์ทั้งหมด (git add .)
            subprocess.run(["git", "add", "."], cwd=project_root, check=True, capture_output=True)
            
            # 3. ตรวจสอบสถานะว่ามีอะไรให้ Commit ไหม
            status = subprocess.run(["git", "status", "--porcelain"], cwd=project_root, capture_output=True, text=True)
            if not status.stdout.strip():
                speak("ซอร์สโค้ดทุกไฟล์อัปเดตเป็นเวอร์ชันล่าสุดแล้วครับท่านประธาน ไม่มีไฟล์ใหม่ให้ดำเนินการครับ")
                return

            # 4. คอมมิตการเปลี่ยนแปลง (git commit)
            commit_msg = "🚀 Supreme Enterprise Auto-Deployment via Voice Command"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=project_root, check=True, capture_output=True)
            
            # 5. อัปโหลดขึ้น GitHub เพื่อ Trigger Google Cloud Run (git push)
            push_result = subprocess.run(["git", "push", "origin", "main"], cwd=project_root, check=True, capture_output=True, text=True)
            
            print(f"✅ [Git Push Success]: {push_result.stdout or push_result.stderr}")
            speak("ดำเนินการอัปโหลดซอร์สโค้ดสำเร็จแล้วครับท่านประธาน ระบบไปป์ไลน์ CI/CD กำลังนำขึ้นเสิร์ฟเวอร์ Cloud Run ให้อัตโนมัติครับ")
            
        except subprocess.CalledProcessError as e:
            error_output = e.stderr.decode('utf-8', errors='ignore') if e.stderr else str(e)
            print(f"❌ [Git Deployment Error]: {error_output}")
            speak("ขออภัยครับท่านประธาน เกิดข้อขัดข้องในระบบ กิต ไม่สามารถอัปโหลดซอร์สโค้ดได้ครับ กรุณาตรวจสอบสิทธิ์การเข้าถึงครับ")
        except FileNotFoundError:
            print("❌ [System Error]: ไม่พบคำสั่ง Git ในเครื่องคอมพิวเตอร์")
            speak("ระบบตรวจไม่พบโปรแกรม กิต ในเครื่องนี้ครับท่านประธาน กรุณาติดตั้งก่อนสั่งการครับ")
        except Exception as e:
            print(f"❌ [Unknown Error]: {e}")
            speak("เกิดข้อผิดพลาดระดับระบบปฏิบัติการครับ ทีมวิศวกรกำลังตรวจสอบ")

    # สั่งรันใน Thread เพื่อให้เสียงตอบกลับทำงานได้ทันที ไม่กระตุก
    threading.Thread(target=_deploy_process, daemon=True).start()

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
            if ("503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str) and attempt < max_retries - 1:
                print(f"⚠️ [Server Busy]: สัญญาณหนาแน่น กำลังเชื่อมต่อใหม่ใน {delay} วินาที (รอบที่ {attempt + 1})...")
                time.sleep(delay)
                delay *= 2
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

    print("\n" + "="*60)
    print("👑 SIRINTHANATTH PRIME : VOICE & DEPLOYMENT STANDBY MODE")
    print("="*60)

    speak("ระบบปฏิบัติการ สิรินทร์ธนัตถ์ ไพรม์ พร้อมรับคำสั่งจากท่านประธานแล้วครับ")

    while True:
        try:
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=None, phrase_time_limit=10)
            
            command = recognizer.recognize_google(audio, language="th-TH").strip()
            print(f"\n🗣️ ตรวจจับเสียง: '{command}'")
            cmd_lower = command.lower().replace(" ", "")

            # --- โหมดพัก (Standby) ---
            if is_standby:
                if "สิรินทร์ธนัชพรหม" in cmd_lower:
                    is_standby = False
                    speak("ปลดล็อกระบบโครงสร้างหลักครับ ผมพร้อมจัดการแก้ไขไฟล์ อัปเกรดโค้ด และสั่งการทุกแผนกแทนคุณแล้วครับ")
                elif "สิรินทร์ธนัตถ์" in cmd_lower:
                    is_standby = False
                    speak("พร้อมครับท่านประธาน มีวาระเร่งด่วนอะไรให้ผมจัดการ สั่งมาได้เลยครับ")
                continue

            # --- โหมดทำงาน (Active) ---
            if any(word in command for word in ["เท่านี้ก่อน", "พักก่อน", "สแตนด์บาย", "standby"]):
                is_standby = True
                speak("รับทราบครับ พักเข้าสู่โหมดสแตนด์บาย เรียกผมได้ทันทีที่ต้องการครับ")
                continue
                
            # 🚀 ตรวจจับคำสั่งอนุมัติและอัปโหลดขึ้น Cloud Run (Voice Deployment Trigger)
            elif "อนุมัติ" in command and any(w in cmd_lower for w in ["อัพกิต", "อัปgit", "อัพgit", "cloudrun", "คลาวด์รัน"]):
                speak("รับทราบครับท่านประธาน ระบบกำลังประมวลผลผสานโค้ดทั้งหมด และส่งคำสั่ง อัป กิต ขึ้นสู่ กูเกิล คลาวด์ รัน ทันทีครับ")
                execute_git_deployment()
                continue
                
            # คำสั่งเปิดแดชบอร์ดผู้บริหาร
            elif any(word in command for word in ["เปิดแดชบอร์ด", "หน้าจอควบคุม", "ระบบผู้บริหาร"]):
                speak("กำลังเปิดหน้าจอควบคุมระบบผู้บริหารให้เดี๋ยวนี้ครับท่านประธาน")
                trigger_executive_dashboard()
                continue
            
            # การสนทนาทั่วไป
            else:
                ai_answer = ask_prime_brain(command)
                speak(ai_answer)

        except sr.UnknownValueError:
            pass # ตัดเสียงรบกวนที่ฟังไม่ออกทิ้งไป
        except Exception as e:
            print(f"⚠️ [Loop Error]: {e}")

if __name__ == "__main__":
    start_voice_engine()