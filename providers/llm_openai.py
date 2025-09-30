import os, json
from typing import Dict, Any, List, Tuple
from openai import OpenAI
from utils import log_info, log_error
from file_ops import apply_operations

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

SYSTEM_PROMPT = """You are an autonomous Godot/GDScript engineer.
You receive a single task (JSON with id/title/description/type).
- Output two top-level keys: "operations" and "notes".
- "operations" MUST be a JSON array of file-edit ops: {action, path, content}.
  Actions: "write" (full file), "append" (add to end), or "patch" (unified/restore text).
  Only create/modify files necessary for the task. Keep changes minimal but working.
  NEVER modify automation core files: orchestrator_ai.py, task_runner.py, utils.py, git_utils.py, reset_tasks.py
- Prefer Godot 4.x conventions. Use GDScript unless task says otherwise.
- Keep content self-contained and compilable.
- If creating scenes, include minimal .tscn structure.
- Use forward slashes in paths. Project root is current working directory.
"""

def _build_input(task: Dict[str, Any]) -> str:
    payload = {
        "task": {
            "id": task.get("id"),
            "title": task.get("title"),
            "description": task.get("description"),
            "type": task.get("type", "code"),
        },
        "format": {
            "operations": [
                {"action": "write|append|patch", "path": "relative/file.ext", "content": "<text or unified diff>"}
            ],
            "notes": "short human-readable summary of what changed"
        }
    }
    return (
        "Follow the system instructions exactly and return STRICT JSON.\n"
        "Do not wrap in markdown code fences. Do not include extra text.\n"
        f"Task JSON:\n{json.dumps(payload, indent=2)}\n"
    )

def _parse_model_json(text: str):
    data = json.loads(text)
    ops = data.get("operations", [])
    notes = data.get("notes", "")
    if not isinstance(ops, list):
        raise ValueError("`operations` must be an array.")
    return ops, notes

def call_openai_chat(task: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"feedback": "❌ OPENAI_API_KEY is not set.", "error": True}

    client = OpenAI(api_key=api_key, base_url=OPENAI_BASE_URL or None)
    model = os.getenv("OPENAI_MODEL", OPENAI_MODEL)
    log_info(f"[OPENAI] model={model}")

    inp = _build_input(task)
    try:
        resp = client.responses.create(
            model=model,
            input=inp,
            temperature=0.2,
            max_output_tokens=3000,
            system=SYSTEM_PROMPT
        )
        try:
            text = resp.output_text
        except AttributeError:
            if getattr(resp, "content", None):
                text = "".join([p.get("text", "") for p in resp.content if p.get("type") == "output_text"])
            else:
                text = str(resp)
    except Exception as e:
        return {"feedback": f"❌ OpenAI call failed: {e}", "error": True}

    try:
        operations, notes = _parse_model_json(text)
    except Exception as e:
        return {"feedback": f"❌ Invalid model JSON: {e}", "error": True}

    try:
        results = apply_operations(operations)
    except Exception as e:
        return {"feedback": f"❌ Failed applying operations: {e}", "error": True}

    summary = "✅ Edits applied:\n" + "\n".join(f" - {r}" for r in results)
    if notes:
        summary += f"\n\nNotes:\n{notes}"
    return {"feedback": summary, "error": False}
