# agents/coach_agent.py
class CoachAgent:
    def respond_to_emotion(self, emotion, context):
        if emotion in ["fear", "sadness", "nervousness"]:
            print("🧘 I can tell this feels tough. Let’s take a deep breath.")
            print("✨ Remember: each exposure builds confidence.")
        elif emotion == "joy":
            print("💪 You sound confident! Let’s build on that energy.")
        else:
            print("🫶 Let’s explore this step together — you’re doing great.")
