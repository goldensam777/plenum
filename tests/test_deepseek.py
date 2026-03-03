from agents.deepseek import DeepSeekAgent
from test_agent import run_sync

if __name__ == "__main__":
    run_sync(DeepSeekAgent, "DeepSeek")