import os, tempfile
from typing import List, Dict
from utils import log_info, log_error

VALID_ACTIONS = {"write", "append", "patch"}

def _atomic_write(path: str, content: str):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    dir_ = os.path.dirname(path) or "."
    with tempfile.NamedTemporaryFile("w", delete=False, dir=dir_, encoding="utf-8") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    os.replace(tmp_path, path)

def apply_operations(operations: List[Dict], dry_run: bool = False) -> List[str]:
    results = []
    for op in operations:
        action = op.get("action")
        path = op.get("path")
        content = op.get("content")

        if action not in VALID_ACTIONS:
            log_error(f"❌ Invalid action: {action}")
            continue
        if not path or not isinstance(content, str):
            log_error(f"❌ Invalid operation format: {op}")
            continue

        if dry_run:
            log_info(f"[Dry Run] Would perform: {action.upper()} -> {path}")
            results.append(f"{action.upper()} {path}")
            continue

        try:
            if action == "write":
                _atomic_write(path, content)
            elif action == "append":
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "a", encoding="utf-8") as f:
                    f.write(content)
            elif action == "patch":
                os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
                with open(path, "a", encoding="utf-8") as f:
                    f.write("\n# PATCH APPLIED:\n" + content)
            results.append(f"{action.upper()} {path}")
            log_info(f"✅ {action.upper()} applied to {path}")
        except Exception as e:
            log_error(f"❌ Failed to apply operation {action} on {path}: {e}")
    return results
