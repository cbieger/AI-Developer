import os, json, difflib
from typing import List, Dict, Any
from utils import log_info, log_error, AUTOMATION_CORE

REPO_ROOT = os.getcwd()

def _safe_path(path: str) -> str:
    full = os.path.abspath(os.path.join(REPO_ROOT, path))
    if not full.startswith(REPO_ROOT):
        raise ValueError(f"Refusing to write outside repo: {path}")
    return full

def _refuse_if_locked(path: str):
    base = os.path.basename(path)
    if base in AUTOMATION_CORE:
        raise ValueError(f"Refusing to modify locked file: {base}")

def apply_operations(ops: List[Dict[str, Any]]) -> List[str]:
    results = []
    for i, op in enumerate(ops, 1):
        action = (op.get("action") or "").lower()
        path = op.get("path")
        content = op.get("content", "")
        if not action or not path:
            raise ValueError(f"Operation {i} missing action/path.")
        safe = _safe_path(path)
        _refuse_if_locked(safe)
        os.makedirs(os.path.dirname(safe), exist_ok=True)

        if action == "write":
            with open(safe, "w", encoding="utf-8") as f:
                f.write(content)
            results.append(f"[WRITE] {path} ({len(content)} bytes)")
        elif action == "append":
            with open(safe, "a", encoding="utf-8") as f:
                f.write(content)
            results.append(f"[APPEND] {path} (+{len(content)} bytes)")
        elif action == "patch":
            if not os.path.exists(safe):
                raise ValueError(f"Patch target does not exist: {path}")
            with open(safe, "r", encoding="utf-8") as f:
                old = f.read().splitlines(keepends=False)
            try:
                patched = list(difflib.restore(content.splitlines(), 1))
                if not patched:
                    patched = old
            except Exception:
                patched = content.splitlines(keepends=False)

            with open(safe, "w", encoding="utf-8") as f:
                f.write("\n".join(patched) + ("\n" if patched and not patched[-1].endswith("\n") else ""))
            results.append(f"[PATCH] {path} (applied)")
        else:
            raise ValueError(f"Unknown action: {action}")
    return results
