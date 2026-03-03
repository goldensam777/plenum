from agents.claude import ClaudeAgent
from test_agent import run_sync

if __name__ == "__main__":
    run_sync(ClaudeAgent, "Claude")