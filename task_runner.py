from typing import Dict, Any
from providers.llm_openai import call_openai_chat

def run_task(task: Dict[str, Any], provider: str = "llm", dry_run: bool = False, context: Dict[str, Any] = {}) -> Dict[str, Any]:
    if provider != "llm":
        return {"feedback": "❌ Unsupported provider.", "error": True}
    return call_openai_chat(task, dry_run=dry_run, context=context)
