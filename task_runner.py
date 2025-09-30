from typing import Dict, Any
from providers.llm_openai import call_openai_chat

def run_task(task: Dict[str, Any], provider: str = "llm") -> Dict[str, Any]:
    if provider != "llm":
        return {"feedback": "❌ Only 'llm' provider is supported in this workflow.", "error": True}
    return call_openai_chat(task)
