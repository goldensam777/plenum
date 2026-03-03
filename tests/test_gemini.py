from agents.gemini import GeminiAgent
from test_agent import run_sync

if __name__ == "__main__":
    run_sync(GeminiAgent, "Gemini")