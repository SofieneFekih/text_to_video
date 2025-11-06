import speech_recognition as sr

class SpeechAgent:
    def __init__(self):
        self.recognizer = sr.Recognizer()

        # 🎙️ Use your Realtek microphone (device index 9)
        self.mic = sr.Microphone(device_index=14)

        # Optional: set a fixed threshold to avoid silent detection
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = False

    def listen(self):
        import io
        import wave

        with self.mic as source:
            print("🎧 Listening (speak now)...")
            audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)

        # Save the raw audio for debugging
        with open("debug_audio.wav", "wb") as f:
            f.write(audio.get_wav_data())
        print("💾 Saved what I heard as debug_audio.wav")

        try:
            text = self.recognizer.recognize_google(audio, language="en-US")
            print(f"🗣️ You said: {text}")
            return text
        except sr.UnknownValueError:
            print("⚠️ Could not understand speech.")
            return None
        except sr.WaitTimeoutError:
            print("⚠️ No speech detected (timeout).")
            return None
