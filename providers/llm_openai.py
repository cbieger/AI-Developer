import os, json, time, socket
from typing import Dict, Any, Optional, Tuple
from openai import OpenAI
from utils import log_info, log_error
from file_ops import apply_operations

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

SYSTEM_PROMPT = """You are an autonomous Godot/GDScript engineer.
Your job is to generate only JSON output to accomplish the provided task.
You must not include any Markdown formatting, commentary, or extra text — only valid JSON.
"""
SPATH = os.getenv("OPENAI_SYSTEM_PROMPT_FILE")
if SPATH and os.path.exists(SPATH):
    try:
        with open(SPATH, "r", encoding="utf-8") as f:
            SYSTEM_PROMPT = f.read()
        log_info(f"[Provider] Loaded system prompt from {SPATH}")
    except Exception as e:
        log_error(f"[Provider] Failed to load system prompt file: {e}")

# --- Preflight connectivity checks ---
def _mask(s: Optional[str]) -> str:
    if not s:
        return "None"
    return s[:4] + "..." + s[-4:] if len(s) > 8 else "****"

def preflight_openai(model: Optional[str] = None,
                     timeout: float = 8.0,
                     chat_fallback: bool = True) -> Tuple[bool, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
    cfg_model = os.getenv("OPENAI_MODEL")

    if not api_key:
        return False, "OPENAI_API_KEY is missing."

    if base_url:
        try:
            host = base_url.split("://", 1)[-1].split("/", 1)[0]
            socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
        except Exception as e:
            return False, f"DNS/URL error for OPENAI_BASE_URL={base_url}: {e}"

    try:
        client = OpenAI(api_key=api_key, base_url=base_url or None, timeout=timeout)
    except Exception as e:
        return False, f"Failed to construct OpenAI client: {e}"

    # try token-free list
    try:
        models = list(client.models.list())
        model_ids = {m.id for m in models if getattr(m, 'id', None)}
    except Exception as e:
        if not chat_fallback:
            return False, f"models.list() failed and fallback disabled: {e}"
        # fallback 1-token ping
        try:
            ping_model = model or cfg_model or "gpt-4o-mini"
            resp = client.chat.completions.create(
                model=ping_model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                temperature=0.0,
            )
            usage = getattr(resp, "usage", None)
            used = f" tokens_used={usage.total_tokens}" if usage and getattr(usage, "total_tokens", None) is not None else ""
            return True, f"Preflight OK via chat ping on model={ping_model}.{used}"
        except Exception as e2:
            return False, f"Connectivity failed: models.list() error={e}; chat ping error={e2}"

    if model:
        if model not in model_ids:
            if chat_fallback:
                try:
                    resp = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": "ping"}],
                        max_tokens=1,
                        temperature=0.0,
                    )
                    usage = getattr(resp, "usage", None)
                    used = f" tokens_used={usage.total_tokens}" if usage and getattr(usage, "total_tokens", None) is not None else ""
                    return True, f"Preflight OK (model not in list but chat ping succeeded) model={model}.{used}"
                except Exception as e:
                    return False, f"Model '{model}' not available (list ok, ping failed): {e}"
            return False, f"Model '{model}' not found in models.list()."
    return True, "Preflight OK (models.list() succeeded)."

def _build_input(task: Dict[str, Any]) -> str:
    payload = {
        "task": {
            "id": task.get("id"),
            "title": task.get("title"),
            "description": task.get("description"),
            "type": task.get("type", "code"),
        },
        "format": {
            "operations": [{"action": "write|append|patch", "path": "relative/file.ext", "content": "<text>"}],
            "notes": "short summary"
        }
    }
    return (
        "Strict JSON output only. No markdown or extra text.\n"
        f"Task JSON:\n{json.dumps(payload, indent=2)}\n"
    )

def _parse_model_json(text: str):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")
    ops = data.get("operations", [])
    notes = data.get("notes", "")
    if not isinstance(ops, list):
        raise ValueError("`operations` must be a list.")
    for i, op in enumerate(ops):
        if not isinstance(op, dict):
            raise ValueError(f"operation[{i}] must be an object")
        for key in ("action", "path", "content"):
            if key not in op:
                raise ValueError(f"operation[{i}] missing '{key}'")
    return ops, notes

def call_openai_chat(task: Dict[str, Any], dry_run: bool = False, context: Dict[str, Any] = {}) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"feedback": "❌ Missing OPENAI_API_KEY.", "error": True}

    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("OPENAI_MODEL", OPENAI_MODEL)
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
    max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "3000"))
    log_info(f"[OpenAI] base={base_url or 'default'} model={model} temp={temperature} max_tokens={max_tokens}")

    client = OpenAI(api_key=api_key, base_url=base_url or None)

    user_input = _build_input(task)

    # Simple retries
    last_err = None
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_input}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            break
        except Exception as e:
            last_err = e
            log_error(f"[OpenAI] call error (attempt {attempt+1}/3): {e}")
            time.sleep(1.5 * (attempt + 1))
    else:
        return {"feedback": f"❌ OpenAI call error: {last_err}", "error": True}

    choice = response.choices[0]
    text = choice.message.content.strip()
    fr = getattr(choice, "finish_reason", None)
    usage = getattr(response, "usage", None)
    if usage:
        log_info(f"[OpenAI] usage prompt={usage.prompt_tokens} completion={usage.completion_tokens} total={usage.total_tokens} finish_reason={fr}")
    else:
        log_info(f"[OpenAI] finish_reason={fr} (no usage block returned)")

    try:
        operations, notes = _parse_model_json(text)
    except Exception as e:
        log_error(f"Model output error: {text}")
        return {"feedback": f"❌ JSON parsing failed: {e}", "error": True}

    if dry_run:
        summary = "✅ [Dry Run] Proposed changes:\n" + "\n".join(f" - {op['action']} {op['path']}" for op in operations)
        return {"feedback": summary + (f"\n\nNotes:\n{notes}" if notes else ""), "error": False}

    try:
        results = apply_operations(operations)
    except Exception as e:
        return {"feedback": f"❌ Apply operations failed: {e}", "error": True}

    summary = "✅ Changes applied:\n" + "\n".join(f" - {r}" for r in results)
    if notes:
        summary += f"\n\nNotes:\n{notes}"
    return {"feedback": summary, "error": False}
