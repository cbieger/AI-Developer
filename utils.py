import os, json, datetime, sys

LOG_DIR = os.path.join(os.getcwd(), "logs")
WORKFLOW_LOG = os.path.join(LOG_DIR, "workflow.log")
FEEDBACK_LOG = os.path.join(LOG_DIR, "ai_feedback.log")
ERROR_LOG = os.path.join(LOG_DIR, "errors.log")

AUTOMATION_CORE = {
    "orchestrator_ai.py",
    "task_runner.py",
    "utils.py",
    "git_utils.py",
    "reset_tasks.py",
}

def ensure_log_dirs():
    os.makedirs(LOG_DIR, exist_ok=True)

def _timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_info(msg: str):
    line = f"[{_timestamp()}] INFO  {msg}"
    print(line)
    try:
        with open(WORKFLOW_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def log_error(msg: str):
    line = f"[{_timestamp()}] ERROR {msg}"
    print(line, file=sys.stderr)
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def log_feedback(task_id: str, text: str):
    header = f"[{_timestamp()}] [{task_id}]"
    try:
        with open(FEEDBACK_LOG, "a", encoding="utf-8") as f:
            f.write(header + "\n")
            f.write(text.rstrip() + "\n\n")
    except Exception:
        pass

def load_tasks():
    """Default tasks.json in the current working directory."""
    path = "tasks.json"
    if not os.path.exists(path):
        raise FileNotFoundError("tasks.json not found in working directory")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_tasks_from_path(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Tasks file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_tasks(obj):
    with open("tasks.json", "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def is_automation_locked_by_task(task: dict) -> bool:
    # Placeholder guard; real policy decisions can go here.
    # We rely primarily on file_ops to block core-file edits.
    return False
