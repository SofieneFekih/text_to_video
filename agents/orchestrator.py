# agents/orchestrator.py
from agents.speech_agent import SpeechAgent
from agents.emotion_agent import EmotionAgent
from agents.video_agent import VideoAgent
from agents.coach_agent import CoachAgent

class Orchestrator:
    def __init__(self):
        self.speech_agent = SpeechAgent()
        self.emotion_agent = EmotionAgent()
        self.video_agent = VideoAgent()
        self.coach = CoachAgent()

    def run(self):
        print("🎤 Welcome to TheraVision — your AI Exposure Coach!")
        print("🧠 Preparing system...")
        text = self.speech_agent.listen()

        if not text:
            print("⚠️ No speech detected. Exiting.")
            return

        emotion = self.emotion_agent.detect_emotion(text)
        print(f"🎭 Emotion detected: {emotion}")

        self.coach.respond_to_emotion(emotion, text)

        video_path = self.video_agent.generate(
            f"A realistic VR scene where the user practices {text}, with emotional tone {emotion}"
        )
        if video_path:
            print(f"🎥 Session video ready at: {video_path}")
