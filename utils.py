import json
import os
from datetime import datetime

def ensure_log_dirs():
    os.makedirs("logs", exist_ok=True)
    os.makedirs("archive", exist_ok=True)

def log_info(msg):
    print(msg)
    with open("logs/workflow.log", "a", encoding="utf-8") as f:
        f.write(f"[INFO] {msg}\n")

def log_error(msg):
    print(msg)
    with open("logs/errors.log", "a", encoding="utf-8") as f:
        f.write(f"[ERROR] {msg}\n")

def log_feedback(task_id, msg):
    print(f"💬 Feedback from {task_id}:\n{msg}")
    with open("logs/ai_feedback.log", "a", encoding="utf-8") as f:
        f.write(f"\n==== {task_id} - {datetime.utcnow().isoformat()} ====\n{msg}\n")

def archive_append(task_data, filename):
    path = os.path.join("archive", filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    data.append(task_data)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_tasks(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_tasks(tasks, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)

