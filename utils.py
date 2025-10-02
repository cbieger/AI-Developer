import json
import os
from datetime import datetime

# Ensure log and archive directories exist
def ensure_log_dirs():
    os.makedirs("logs", exist_ok=True)
    os.makedirs("archive", exist_ok=True)

# Info logger
def log_info(msg):
    print(msg)
    with open("logs/workflow.log", "a", encoding="utf-8") as f:
        f.write(f"[INFO] {msg}\n")

# Error logger
def log_error(msg):
    print(msg)
    with open("logs/errors.log", "a", encoding="utf-8") as f:
        f.write(f"[ERROR] {msg}\n")

# Feedback logger
def log_feedback(task_id, msg):
    print(f"💬 Feedback from {task_id}:\n{msg}")
    with open("logs/ai_feedback.log", "a", encoding="utf-8") as f:
        f.write(f"\n==== {task_id} - {datetime.utcnow().isoformat()} ====\n{msg}\n")

# Append a task to a JSON archive file
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

# Load tasks from JSON file
def load_tasks(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# Save tasks to JSON file
def save_tasks(tasks, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)

# Higher-level loader with path validation and logging
def load_tasks_from_path(path):
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        log_error(f"❌ Task file does not exist: {abs_path}")
        raise FileNotFoundError(f"Task file not found: {abs_path}")
    return load_tasks(abs_path)

