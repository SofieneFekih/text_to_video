# agents/video_agent.py
import os, requests, base64
from dotenv import load_dotenv
load_dotenv()

class VideoAgent:
    def __init__(self):
        self.api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.api_base = os.getenv("HUGGINGFACE_API_BASE", "https://router.huggingface.co")
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

        # Preferred VR-like model
        self.model = "ali-vilab/text-to-video-ms-1.7b"  # better for scene generation

    def generate(self, prompt: str):
        print(f"🎬 Generating immersive video for: {prompt}")
        url = f"{self.api_base}/models/{self.model}"

        payload = {"inputs": prompt}
        response = requests.post(url, headers=self.headers, json=payload)

        if response.status_code != 200:
            print(f"❌ Error ({response.status_code}): {response.text}")
            return None

        try:
            data = response.json()
            if "video" in data:
                video_bytes = base64.b64decode(data["video"])
                os.makedirs("generated_videos", exist_ok=True)
                out_path = os.path.join("generated_videos", "session.mp4")
                with open(out_path, "wb") as f:
                    f.write(video_bytes)
                print(f"✅ Video saved to {out_path}")
                return out_path
            else:
                print("⚠️ No video data returned.")
        except Exception as e:
            print(f"⚠️ JSON parse error: {e}")
        return None
