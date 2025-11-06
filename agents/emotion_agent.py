# agents/emotion_agent.py
import torch
from transformers import pipeline

class EmotionAgent:
    def __init__(self):
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Device set to use {device.upper()}")
        self.classifier = pipeline(
            "text-classification",
            model="j-hartmann/emotion-english-distilroberta-base",
            return_all_scores=True,
            device=0 if device == "cuda" else -1
        )

    def detect_emotion(self, text: str):
        if not text:
            return "neutral"
        print("🔍 Analyzing emotional tone...")
        results = self.classifier(text)[0]
        # Sort by confidence
        results.sort(key=lambda x: x["score"], reverse=True)
        top_emotion = results[0]["label"].lower()
        print(f"🎭 Detected emotion: {top_emotion}")
        return top_emotion

