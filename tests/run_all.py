from tests.test_agent import run_sync
from agents.claude import ClaudeAgent
from agents.gemini import GeminiAgent
from agents.deepseek import DeepSeekAgent
from agents.chatgpt import ChatGPTAgent
from agents.kimi import KimiAgent

agents = [
    (ClaudeAgent, "Claude"),
    (GeminiAgent, "Gemini"),
    (DeepSeekAgent, "DeepSeek"),
    (ChatGPTAgent, "ChatGPT"),
    (KimiAgent, "Kimi")
]

for agent_class, name in agents:
    run_sync(agent_class, name)