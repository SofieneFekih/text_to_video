import os
import time
from datetime import datetime

# Check for required dependencies
try:
    from moviepy.editor import TextClip, CompositeVideoClip, ColorClip
    import speech_recognition as sr
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
    print("⚠️ MoviePy not available - running in text-only mode")

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ Google GenAI not available - install with: pip install google-genai")
from tenacity import retry, stop_after_attempt, wait_random_exponential
from google.genai import errors

@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def generate_video_with_retry(client, prompt, model):
    operation = client.models.generate_videos(
        model=model,
        prompt=prompt,
    )
    return operation
def initialize_gemini_client():
    """Initialize Gemini client with API key from environment variable"""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY environment variable not set")
        print("💡 Set it with: setx GEMINI_API_KEY \"your_key_here\" (CMD) or $env:GEMINI_API_KEY=\"your_key_here\" (PowerShell)")
        return None
    
    try:
        client = genai.Client(api_key=api_key)
        # Test the client with a simple request
        test_response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents="Hello"
        )
        print("✅ Gemini API connected successfully")
        return client
    except Exception as e:
        print(f"❌ Failed to initialize Gemini client: {e}")
        return None

def generate_video_with_gemini(client, text_prompt, output_path="gemini_generated_video.mp4"):
    """Generate video using Gemini Veo API"""
    if not GEMINI_AVAILABLE or client is None:
        print("❌ Gemini API not available")
        return False
    
    try:
        print(f"🎬 Generating video with prompt: '{text_prompt}'")
        print("⏳ This may take a few minutes...")
        
        # Start the video generation process
        operation = client.models.generate_videos(
            model="veo-3.1-generate-preview",
            prompt=text_prompt,
        )

        # Poll for completion
        while not operation.done:
            print("⏳ Waiting for video generation to complete...")
            time.sleep(15)  # Check every 15 seconds
            operation = client.operations.get(operation.name)

        # Download the result
        if operation.result and operation.result.generated_videos:
            generated_video = operation.result.generated_videos[0]
            client.files.download(file=generated_video.video, path=output_path)
            print(f"✅ Video successfully saved as '{output_path}'")
            return True
        else:
            print("❌ Video generation failed - no video produced")
            return False
            
    except Exception as e:
        print(f"❌ Error generating video with Gemini: {e}")
        return False

def text_to_video(text, output="output.mp4", duration=5):
    """Convert text to simple video using MoviePy (fallback)"""
    if not MOVIEPY_AVAILABLE:
        print("❌ MoviePy not available. Cannot create video.")
        # Save text to file as fallback
        with open("recognized_text.txt", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()}: {text}\n")
        print("📝 Text saved to recognized_text.txt")
        return False
    
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
        
        print(f"🎬 Simple video saved as {output}")
        
        # Clean up
        txt_clip.close()
        video.close()
        background.close()
        return True
        
    except Exception as e:
        print(f"❌ Error creating video: {e}")
        # Fallback: save text to file
        with open("recognized_text.txt", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()}: {text}\n")
        print("📝 Text saved to recognized_text.txt as backup")
        return False

def recognize_speech(lang="en-US", use_gemini=True):
    """Main speech recognition function with video generation options"""
    
    # Initialize Gemini client if requested
    gemini_client = None
    if use_gemini:
        gemini_client = initialize_gemini_client()
        if not gemini_client:
            print("⚠️ Falling back to simple text-to-video")
            use_gemini = False
    
    recognizer = sr.Recognizer()
    
    try:
        with sr.Microphone() as source:
            print("🎤 Calibrating microphone for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            recognizer.pause_threshold = 1.0
            print("✅ Microphone ready!")
            
            if use_gemini:
                print("🚀 Using Gemini AI for advanced video generation")
                print("💡 Speak descriptive scenes (e.g., 'a sunset over mountains')")
            else:
                print("📝 Using simple text-to-video")
            
            print("💬 Start speaking (say 'exit', 'switch mode', or 'simple mode')")

            while True:
                try:
                    print("\n🔴 Listening...", end='\r')
                    audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
                    print("                    ", end='\r')
                    print("🟡 Processing...", end='\r')
                    
                    text = recognizer.recognize_google(audio, language=lang).strip()
                    print("                    ", end='\r')
                    
                    # Command handling
                    if text.lower() in ['exit', 'quit', 'stop']:
                        print("👋 Exit command received. Stopping...")
                        break
                    elif text.lower() in ['switch mode', 'change mode', 'gemini mode']:
                        use_gemini = not use_gemini
                        mode = "Gemini AI" if use_gemini else "simple text-to-video"
                        print(f"🔄 Switched to {mode}")
                        continue
                    elif text.lower() in ['simple mode', 'text mode']:
                        use_gemini = False
                        print("🔄 Switched to simple text-to-video mode")
                        continue
                    
                    print(f"✅ You said: {text}")
                    
                    # Generate video based on mode
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    if use_gemini and gemini_client:
                        output_filename = f"gemini_video_{timestamp}.mp4"
                        success = generate_video_with_gemini(gemini_client, text, output_filename)
                        if not success:
                            print("🔄 Falling back to simple video...")
                            output_filename = f"simple_video_{timestamp}.mp4"
                            duration = max(3, len(text) * 0.3)
                            text_to_video(text, output_filename, duration=duration)
                    else:
                        output_filename = f"simple_video_{timestamp}.mp4"
                        duration = max(3, len(text) * 0.3)
                        text_to_video(text, output_filename, duration=duration)
                    
                    print("-" * 50)
                    
                except sr.WaitTimeoutError:
                    print("⏰ No speech detected. Still listening...")
                except sr.UnknownValueError:
                    print("❌ Could not understand audio. Please try again.")
                except sr.RequestError as e:
                    print(f"🌐 Speech API Error: {e}")
                    break
                    
    except KeyboardInterrupt:
        print("\n🛑 Program stopped by user.")
    except Exception as e:
        print(f"💥 Error: {e}")

def show_menu():
    """Display program options"""
    print("🎤 SPEECH TO VIDEO CONVERTER")
    print("=" * 50)
    print(f"📦 MoviePy Available: {MOVIEPY_AVAILABLE}")
    print(f"🤖 Gemini AI Available: {GEMINI_AVAILABLE}")
    print("\n💡 Available Commands:")
    print("   - 'exit', 'quit', 'stop' - End program")
    print("   - 'switch mode' - Toggle between Gemini AI and simple mode")
    print("   - 'simple mode' - Use simple text-to-video")
    print("\n🎯 Voice Examples:")
    print("   Simple mode: 'Hello world'")
    print("   Gemini mode: 'A beautiful sunset over snowy mountains with aurora borealis'")
    print()

if __name__ == "__main__":
    show_menu()
    
    # Ask for preferred mode
    if GEMINI_AVAILABLE:
        choice = input("Start with Gemini AI video generation? (y/n): ").lower().strip()
        use_gemini = choice in ['y', 'yes', '']
    else:
        use_gemini = False
        print("⚠️ Starting in simple mode (Gemini not available)")
    
    recognize_speech(lang="en-US", use_gemini=use_gemini)