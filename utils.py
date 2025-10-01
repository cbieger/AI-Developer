import os, json, sys
from datetime import datetime
import logging
import threading

LOG_DIR = os.path.join(os.getcwd(), "logs")
WORKFLOW_LOG = os.path.join(LOG_DIR, "workflow.log")
FEEDBACK_LOG = os.path.join(LOG_DIR, "ai_feedback.log")
ERROR_LOG = os.path.join(LOG_DIR, "errors.log")

AUTOMATION_CORE = {
    "orchestrator_ai_parallel_with_archive.py",
    "task_runner.py",
    "utils.py",
    "git_utils.py",
    "reset_tasks.py",
}

__log_init_lock = threading.Lock()
__initialized = False

def ensure_log_dirs():
    global __initialized
    if __initialized:
        return
    with __log_init_lock:
        if __initialized:
            return
        os.makedirs(LOG_DIR, exist_ok=True)
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        root = logging.getLogger()
        root.setLevel(logging.INFO)

        # Console
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        root.addHandler(ch)

        # Files
        for path, level in [(WORKFLOW_LOG, logging.INFO), (ERROR_LOG, logging.ERROR)]:
            fh = logging.FileHandler(path, encoding="utf-8")
            fh.setLevel(level)
            fh.setFormatter(fmt)
            root.addHandler(fh)

        __initialized = True

def _ts():
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

def log_info(msg: str):
    ensure_log_dirs()
    logging.getLogger().info(msg)

def log_error(msg: str):
    ensure_log_dirs()
    logging.getLogger().error(msg)

def log_feedback(task_id: str, text: str):
    ensure_log_dirs()
    header = f"[{_ts()}] {task_id}"
    with open(FEEDBACK_LOG, "a", encoding="utf-8") as f:
        f.write(header + "\n")
        f.write(text.rstrip() + "\n\n")

def load_tasks_from_path(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Tasks file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_tasks(obj, path="tasks.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def is_automation_locked_by_task(task: dict) -> bool:
    # Hook for future policy (e.g., deny edits to AUTOMATION_CORE).
    return False
