"""
main.py

Speech -> cinematic scene prompt -> Pika Labs video (optional) -> fallback MoviePy text video.

Usage:
    - Ensure your venv has: speechrecognition, moviepy, pillow, numpy, requests
      pip install speechrecognition moviepy pillow numpy requests

    - If you have a Gemini key: set GEMINI_API_KEY in your environment.
    - If you have a Pika Labs key: set PIKA_API_KEY in your environment.
      (If keys are missing, the script still works and will use the MoviePy fallback.)

Outputs saved to ./videos/
"""

import os
import sys
import time
import json
import requests
from datetime import datetime
from pathlib import Path

# Dependencies (some optional)
try:
    import speech_recognition as sr
except Exception as e:
    print("Missing dependency: speech_recognition. Install with `pip install SpeechRecognition`")
    raise

try:
    import moviepy.editor as mp
    MOVIEPY_AVAILABLE = True
except Exception:
    MOVIEPY_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

import numpy as np

# Optional libs: google.generativeai (Gemini)
try:
    import google.generativeai as genai
    GEMINI_LIB_AVAILABLE = True
except Exception:
    GEMINI_LIB_AVAILABLE = False

# Configuration
OUTPUT_DIR = Path("videos")
OUTPUT_DIR.mkdir(exist_ok=True)
DEFAULT_DURATION = 10  # seconds for generated/fallback videos
FPS = 24

# Load keys from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # optional
PIKA_API_KEY = os.getenv("PIKA_API_KEY")      # optional

# Helper: timestamped filename
def make_filename(prefix="scene", ext="mp4"):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return OUTPUT_DIR / f"{prefix}_{ts}.{ext}"

# -------------------------
# Gemini helper (optional)
# -------------------------
class GeminiHelper:
    def __init__(self, api_key):
        self.client = None
        self.available = False
        if not GEMINI_LIB_AVAILABLE:
            return
        if not api_key:
            return
        try:
            genai.configure(api_key=api_key)
            self.client = genai
            self.available = True
            print("✅ Gemini helper initialized.")
        except Exception as e:
            print(f"⚠️ Gemini init failed: {e}")
            self.available = False

    def build_cinematic_prompt(self, user_text):
        """
        Use Gemini to rewrite user_text into a cinematic, VR-ready scene prompt if possible.
        Otherwise, fall back to our built-in cinematic template.
        """
        if not self.available:
            return cinematic_template(user_text)

        try:
            # Use a simple generative call to rewrite prompt.
            # Note: SDKs change — this is a guarded usage. If your genai client uses different names,
            # you may need to update this call to the version of google-generativeai you use.
            instruction = (
                f"Rewrite the following user issue into a vivid, cinematic VR scene prompt suitable "
                f"for text-to-video generation. Include perspective, environment, mood, lighting, "
                f"and a short action. Keep it concise (one paragraph). User issue: \"{user_text}\""
            )
            resp = self.client.generate_text(instruction) if hasattr(self.client, "generate_text") else None

            # Try a couple of possible response shapes gracefully:
            if resp is None:
                # fallback to simple template
                return cinematic_template(user_text)
            if isinstance(resp, str):
                return resp.strip()
            # some SDKs return an object with 'text' property or 'candidates'
            if hasattr(resp, "text"):
                return resp.text.strip()
            if isinstance(resp, dict):
                # look for common keys
                for k in ("output", "text", "content"):
                    if k in resp and isinstance(resp[k], str):
                        return resp[k].strip()
                # if 'candidates' or 'choices'
                for k in ("candidates", "choices"):
                    if k in resp and isinstance(resp[k], (list, tuple)) and resp[k]:
                        c = resp[k][0]
                        if isinstance(c, str):
                            return c.strip()
                        if isinstance(c, dict) and "text" in c:
                            return c["text"].strip()
            # Last resort
            return cinematic_template(user_text)
        except Exception as e:
            print(f"⚠️ Gemini prompt generation failed: {e}")
            return cinematic_template(user_text)


def cinematic_template(user_text: str) -> str:
    """
    Build a cinematic prompt from the user's text when Gemini is unavailable.
    This is deliberately descriptive and VR-friendly.
    """
    # Example template — cinematic description with perspective, environment, lighting, emotions
    return (
        f"A cinematic VR scene: a single speaker stands at center stage in a large theater, "
        f"spotlight focused on them, rows of shadowed audience facing the stage. "
        f"The speaker appears nervous but determined, hands slightly trembling, "
        f"deep breathing visible. Perspective is third-person slightly behind and to the left of the speaker, "
        f"camera slowly pushes forward. Lighting is warm stage lights with soft backlight and subtle audience movement. "
        f"Environment detail: wooden stage, microphone on stand, theater curtains in the background. "
        f"Emotion to convey: anxious anticipation, hopeful determination. Based on: \"{user_text}\""
    )

# -------------------------
# Pika Labs helper (optional)
# -------------------------
class PikaHelper:
    def __init__(self, api_key):
        self.api_key = api_key
        self.available = bool(api_key)
        if not self.available:
            print("ℹ️ Pika Labs key not provided — Pika generation disabled.")
        else:
            print("ℹ️ Pika Labs helper enabled (API key provided).")

    def generate_video(self, prompt, duration=DEFAULT_DURATION):
        """
        Attempt to generate a video using Pika Labs.
        This function assumes a generic REST endpoint. You may need to adjust URL/fields to Pika's current API.
        It returns the local path to the downloaded mp4 on success, otherwise None.
        """
        if not self.available:
            return None

        # NOTE: Pika Labs API endpoints/parameters may change. Update the endpoint and payload as needed.
        # This is a best-effort template for integration; replace 'https://api.pika.art/v1/generate' with the real endpoint.
        endpoint = "https://api.pika.art/v1/generate"  # <-- update if Pika docs differ
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        payload = {
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": "16:9",
            # additional options could be added here (style, seed, guidance, etc.)
        }

        print("🔁 Sending prompt to Pika Labs (this may take some time)...")
        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=300)
            if resp.status_code not in (200, 201):
                print(f"❌ Pika API responded with status {resp.status_code}: {resp.text[:300]}")
                return None
            data = resp.json()

            # The shape of 'data' depends on the API; many services return a location or job id to poll.
            # We'll attempt both: if there's a direct 'video_url', download; if there's 'job_id', attempt polling.
            if "video_url" in data:
                video_url = data["video_url"]
                return self._download_video(video_url)
            if "result" in data and isinstance(data["result"], dict) and "video_url" in data["result"]:
                return self._download_video(data["result"]["video_url"])

            # If the response contains a job id, we might need to poll a status endpoint
            if "job_id" in data:
                job_id = data["job_id"]
                # Polling template (endpoint depends on actual API)
                status_url = f"https://api.pika.art/v1/jobs/{job_id}"
                for attempt in range(60):  # poll for up to ~5 minutes
                    sresp = requests.get(status_url, headers=headers, timeout=30)
                    if sresp.status_code != 200:
                        time.sleep(3)
                        continue
                    sdata = sresp.json()
                    # Try to find video url in sdata
                    if sdata.get("status") == "succeeded" and "video_url" in sdata:
                        return self._download_video(sdata["video_url"])
                    if sdata.get("status") in ("failed", "error"):
                        print("❌ Pika job failed:", sdata)
                        return None
                    time.sleep(3)
                print("❌ Pika job timed out")
                return None

            # Unknown response shape
            print("⚠️ Pika returned an unexpected response. Inspect the API docs / response:")
            print(json.dumps(data, indent=2)[:1500])
            return None

        except requests.RequestException as e:
            print(f"❌ Request error when calling Pika API: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error when calling Pika API: {e}")
            return None

    def _download_video(self, url):
        """Download a remote video url to the output directory and return local path."""
        try:
            resp = requests.get(url, stream=True, timeout=120)
            if resp.status_code != 200:
                print(f"❌ Failed to download video: {resp.status_code}")
                return None
            out_path = make_filename(prefix="pika_scene")
            with open(out_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)
            print(f"✅ Pika video downloaded to {out_path}")
            return str(out_path)
        except Exception as e:
            print(f"❌ Error downloading Pika video: {e}")
            return None

# -------------------------
# Fallback MoviePy+PIL video creator (guaranteed)
# -------------------------
def render_text_video_with_pil(text, output_path, duration=DEFAULT_DURATION, fps=FPS):
    """
    Create a simple video by rendering text frames with Pillow and converting to video via MoviePy.
    This has no ImageMagick dependency.
    """
    if not MOVIEPY_AVAILABLE:
        print("❌ MoviePy not available; cannot render fallback video.")
        return False
    if not PIL_AVAILABLE:
        print("❌ Pillow not available; cannot render fallback video.")
        return False

    try:
        width, height = 1280, 720
        font_size = max(36, min(80, int(width / (max(1, len(text) / 15)))))
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        num_frames = int(duration * fps)
        frames = []
        for i in range(num_frames):
            # Create image
            img = Image.new("RGB", (width, height), color=(18, 18, 18))
            draw = ImageDraw.Draw(img)

            # Simple outline/wrapping: split into lines of reasonable length
            max_chars_per_line = 40
            words = text.split()
            lines = []
            line = ""
            for w in words:
                if len(line) + len(w) + 1 <= max_chars_per_line:
                    line = (line + " " + w).strip()
                else:
                    lines.append(line)
                    line = w
            if line:
                lines.append(line)

            # Calculate vertical placement
            total_text_height = sum([draw.textsize(ln, font=font)[1] + 6 for ln in lines])
            y = (height - total_text_height) // 2

            # Draw lines centered
            for ln in lines:
                w, h = draw.textsize(ln, font=font)
                x = (width - w) // 2
                draw.text((x, y), ln, fill=(255, 255, 255), font=font)
                y += h + 6

            frames.append(np.array(img))

        clip = mp.ImageSequenceClip(frames, fps=fps)
        # simple fade in/out
        clip = clip.crossfadein(0.6).crossfadeout(0.6)
        clip.write_videofile(str(output_path), fps=fps, verbose=False, logger=None)
        return True
    except Exception as e:
        print(f"❌ Fallback render error: {e}")
        return False

# -------------------------
# Main app: listens and orchestrates
# -------------------------
class SceneGeneratorApp:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.gemini = GeminiHelper(GEMINI_API_KEY) if GEMINI_API_KEY and GEMINI_LIB_AVAILABLE else None
        if GEMINI_API_KEY and not GEMINI_LIB_AVAILABLE:
            print("⚠️ GEMINI_API_KEY present but google.generativeai library not installed; install with `pip install google-generativeai` to enable.")
        self.pika = PikaHelper(PIKA_API_KEY)
        self.default_duration = DEFAULT_DURATION

    def choose_microphone(self):
        names = sr.Microphone.list_microphone_names()
        if not names:
            print("❌ No microphones found. Exiting.")
            sys.exit(1)
        # default to 0; if you want to change, set MIC_INDEX env var
        env_idx = os.getenv("MIC_INDEX")
        idx = 0
        if env_idx and env_idx.isdigit() and 0 <= int(env_idx) < len(names):
            idx = int(env_idx)
        else:
            # prefer devices that contain "Microphone" or "Input" in name
            for i, n in enumerate(names):
                ln = n.lower()
                if "microphone" in ln or "input" in ln:
                    idx = i
                    break
        print(f"ℹ️ Using microphone [{idx}]: {names[idx]}")
        return idx

    def run(self, lang="en-US"):
        mic_index = self.choose_microphone()
        with sr.Microphone(device_index=mic_index) as source:
            print("🎤 Calibrating microphone for ambient noise (short)...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1.0)
            print("✅ Microphone ready!")
            print("💬 Speak a problem (e.g. 'I have stage fright') or say 'exit' to quit.")

            while True:
                try:
                    print("\n🎧 Listening...")
                    audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=20)
                    print("🟡 Recognizing...")
                    text = self.recognizer.recognize_google(audio, language=lang).strip()
                    print(f"✅ You said: {text}")

                    if text.lower() in ("exit", "quit", "stop"):
                        print("👋 Exiting.")
                        break

                    # Convert speech to cinematic prompt
                    if self.gemini and self.gemini.available:
                        print("🧠 Generating cinematic prompt via Gemini...")
                        scene_prompt = self.gemini.build_cinematic_prompt(text)
                    else:
                        print("🧠 Building cinematic prompt (local template)...")
                        scene_prompt = cinematic_template(text)

                    print("🎯 Scene Prompt:\n", scene_prompt)

                    # Attempt Pika Labs generation (if key provided)
                    video_path = None
                    if self.pika and self.pika.available:
                        video_path = self.pika.generate_video(scene_prompt, duration=self.default_duration)

                    # If Pika succeeded, we're done; otherwise fallback to rendering text video
                    if video_path:
                        print(f"🎉 Generated AI video saved to {video_path}")
                    else:
                        print("🔁 Pika not available or failed — rendering fallback text-video.")
                        out = make_filename(prefix="scene")
                        success = render_text_video_with_pil(scene_prompt, out, duration=self.default_duration, fps=FPS)
                        if success:
                            print(f"🎬 Fallback video saved to {out}")
                        else:
                            print("❌ Fallback video rendering failed; saving text to file.")
                            # fallback: save text
                            with open("recognized_text.txt", "a", encoding="utf-8") as fh:
                                fh.write(f"{datetime.now()}: {text}\n")
                    # short pause before next listening
                    time.sleep(0.5)

                except sr.WaitTimeoutError:
                    print("⏳ No speech detected (timeout). Continuing...")
                except sr.UnknownValueError:
                    print("❌ Could not understand audio. Please try again.")
                except sr.RequestError as e:
                    print(f"🌐 Speech API request error: {e}")
                except KeyboardInterrupt:
                    print("\n🛑 User stopped the program.")
                    break
                except Exception as e:
                    print(f"💥 Unexpected error: {e}")

# -------------------------
# Entry point
# -------------------------
def main():
    print("🎤 SPEECH → SCENE → PIKA (optional) → FALLBACK VIDEO")
    print("=" * 60)
    print(f"📦 MoviePy: {MOVIEPY_AVAILABLE}   Pillow: {PIL_AVAILABLE}   Gemini lib: {GEMINI_LIB_AVAILABLE}")
    print(f"🤖 Gemini API key present: {bool(GEMINI_API_KEY)}   🎞️ Pika API key present: {bool(PIKA_API_KEY)}")
    print("Output folder:", OUTPUT_DIR.resolve())
    app = SceneGeneratorApp()
    app.run()

if __name__ == "__main__":
    main()
