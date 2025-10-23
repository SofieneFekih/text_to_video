import speech_recognition as sr
from moviepy.editor import TextClip, CompositeVideoClip


def text_to_video(text, output="output.mp4"):
    # Create a text clip
    txt_clip = TextClip(
        text,
        fontsize=70,
        color='white',
        bg_color='black',
        size=(1280, 720),
        method='caption'
    ).set_duration(5)  # Duration in seconds

    # Write to a video file
    txt_clip.write_videofile(output, fps=24)
    print(f"🎬 Video saved as {output}")

def recognize_speech(lang="en-US"):
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    print("🎤 Calibrating microphone for ambient noise...")
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
        print("✅ Microphone ready! Start speaking (Ctrl+C to stop).")

        while True:
            print("\nListening...")
            audio = recognizer.listen(source)

            try:
                text = recognizer.recognize_google(audio, language=lang)
                print("🗣 You said:", text)
            except sr.UnknownValueError:
                print("❌ Couldn't understand what you said.")
            except sr.RequestError as e:
                print(f"⚠️ API unavailable or network issue: {e}")
            except KeyboardInterrupt:
                print("\n🛑 Stopped by user.")
                break

if __name__ == "__main__":
    # You can change the language code (e.g. 'fr-FR', 'ar-TN', 'en-US')
    recognize_speech(lang="en-US")
