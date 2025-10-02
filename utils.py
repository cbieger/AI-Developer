import os
import json
from datetime import datetime, timezone

LOG_DIR = "logs"

def ensure_log_dirs():
    os.makedirs(LOG_DIR, exist_ok=True)

def log_info(msg: str):
    print(msg)
    with open(os.path.join(LOG_DIR, "workflow.log"), "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} INFO: {msg}\n")

def log_error(msg: str):
    print(msg)
    with open(os.path.join(LOG_DIR, "errors.log"), "a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} ERROR: {msg}\n")

def log_feedback(task_id: str, feedback: str):
    with open(os.path.join(LOG_DIR, "ai_feedback.log"), "a", encoding="utf-8") as f:
        f.write(f"=== {task_id} ===\n{feedback}\n\n")

def archive_append(data: dict, filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    archive = []
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            archive = json.load(f)
    archive.append(data)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(archive, f, indent=2)

def load_tasks_from_path(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_tasks(tasks: list, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)
