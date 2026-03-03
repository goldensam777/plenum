from agents.chatgpt import ChatGPTAgent
from test_agent import run_sync

if __name__ == "__main__":
    run_sync(ChatGPTAgent, "ChatGPT")