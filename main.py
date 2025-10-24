try:
    
    from moviepy.editor import TextClip, CompositeVideoClip, ColorClip
    import speech_recognition as sr
    MOVIEPY_AVAILABLE = True
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("📦 Please install required packages:")
    print("   pip install moviepy speechrecognition pyaudio pillow")
    MOVIEPY_AVAILABLE = False
import os
from datetime import datetime

def text_to_video(text, output="output.mp4", duration=5):
    """
    Convert text to video with proper error handling
    """
    if not MOVIEPY_AVAILABLE:
        print("❌ MoviePy not available. Cannot create video.")
        # Save text to file as fallback
        with open("recognized_text.txt", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()}: {text}\n")
        print("📝 Text saved to recognized_text.txt")
        return
    
    try:
        # Create text clip
        txt_clip = TextClip(
            text,
            fontsize=50,
            color='white',
            size=(1280, 720),
            method='caption',
            font='Arial-Bold'
        ).set_duration(duration)
        
        # Create background
        background = ColorClip(size=(1280, 720), color=(0, 0, 0), duration=duration)
        
        # Composite video
        video = CompositeVideoClip([background, txt_clip.set_position('center')])
        
        # Write video file
        video.write_videofile(
            output, 
            fps=24,
            verbose=False,
            logger=None
        )
        
        print(f"🎬 Video saved as {output}")
        
        # Clean up
        txt_clip.close()
        video.close()
        background.close()
        
    except Exception as e:
        print(f"❌ Error creating video: {e}")
        # Fallback: save text to file
        with open("recognized_text.txt", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()}: {text}\n")
        print("📝 Text saved to recognized_text.txt as backup")

def recognize_speech(lang="en-US"):
    """
    Speech recognition function
    """
    if not MOVIEPY_AVAILABLE:
        print("⚠️ Running in text-only mode (no video creation)")
    
    recognizer = sr.Recognizer()
    
    try:
        with sr.Microphone() as source:
            print("🎤 Calibrating microphone for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            recognizer.pause_threshold = 1.0
            print("✅ Microphone ready! Start speaking (say 'exit' to stop).")
            
            while True:
                try:
                    print("\n🔴 Listening...")
                    audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
                    print("🟡 Processing...")
                    
                    text = recognizer.recognize_google(audio, language=lang).strip()
                    
                    if text.lower() in ['exit', 'quit', 'stop']:
                        print("👋 Exit command received. Stopping...")
                        break
                    print(f"✅ You said: {text}")
                    
                    # Create video or save text
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_filename = f"speech_video_{timestamp}.mp4"
                    
                    duration = max(3, len(text) * 0.3)
                    text_to_video(text, output_filename, duration=duration)
                    
                except sr.WaitTimeoutError:
                    print("⏰ No speech detected. Still listening...")
                except sr.UnknownValueError:
                    print("❌ Could not understand audio. Please try again.")
                except sr.RequestError as e:
                    print(f"🌐 API Error: {e}")
                    break
                    
    except KeyboardInterrupt:
        print("\n🛑 Program stopped by user.")
    except Exception as e:
        print(f"💥 Error: {e}")

if __name__ == "__main__":
    print("🎤 SPEECH TO VIDEO CONVERTER")
    print("=" * 40)
    
    if not MOVIEPY_AVAILABLE:
        print("⚠️ Running in limited mode - videos won't be created")
        print("💡 Install missing packages to enable full functionality")
    
    recognize_speech(lang="en-US")