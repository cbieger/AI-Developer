#!/usr/bin/env python3
import argparse, os, sys, json, threading
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from task_runner import run_task
from git_utils import create_or_checkout_branch_for_task, commit_all_for_task, merge_branch_to_default
from utils import ensure_log_dirs, log_info, log_error, log_feedback, load_tasks_from_path, save_tasks

from providers.llm_openai import preflight_openai

VALID_STATUSES = {"pending", "error"}
REQUIRED_TASK_KEYS = {"id", "title", "description"}

ARCHIVE_DONE = "archive/completed_tasks.json"
ARCHIVE_FAILED = "archive/failed_tasks.json"

_GIT_LOCK = threading.Lock()

def validate_task(task: Dict[str, Any]) -> bool:
    missing = [k for k in REQUIRED_TASK_KEYS if k not in task]
    if missing:
        log_error(f"❌ Task missing keys: {', '.join(missing)}")
        return False
    return True

def archive_append(obj: dict, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    blob = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                blob = json.load(f)
        except Exception:
            blob = []
    blob.append(obj)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(blob, f, indent=2)

def execute_task(task: Dict[str, Any], args: argparse.Namespace, project_abs: str) -> Dict[str, Any]:
    task_id = task["id"]
    title = task.get("title", task_id)
    branch = None

    if not validate_task(task):
        task["status"] = "error"
        archive_append({
            "id": task_id, "title": title, "error": "validation failed",
            "failed_at": datetime.utcnow().isoformat() + "Z"
        }, ARCHIVE_FAILED)
        return task

    log_info(f"🔧 Running {task_id}: {title}")
    result: Dict[str, Any] = run_task(task, provider=args.provider, dry_run=args.dry_run, context={"cwd": project_abs})

    feedback = result.get("feedback", "").strip()
    error_flag = result.get("error", False)

    if feedback:
        log_feedback(task_id, feedback)

    if error_flag:
        log_error(f"❌ {task_id}: Task failed.")
        task["status"] = "error"
        archive_append({
            "id": task_id,
            "title": title,
            "description": task.get("description"),
            "error": feedback,
            "failed_at": datetime.utcnow().isoformat() + "Z"
        }, ARCHIVE_FAILED)
        return task

    if args.git and not args.dry_run:
        try:
            with _GIT_LOCK:
                branch = create_or_checkout_branch_for_task(task_id, cwd=project_abs)
                commit_all_for_task(task_id, title, cwd=project_abs)
                merge_branch_to_default(branch, cwd=project_abs)
        except Exception as e:
            log_error(f"{task_id}: Git error: {e}")
            task["status"] = "error"
            archive_append({
                "id": task_id, "title": title, "description": task.get("description"),
                "error": f"Git error: {e}",
                "failed_at": datetime.utcnow().isoformat() + "Z"
            }, ARCHIVE_FAILED)
            return task

    task["status"] = "done"
    task["completed_at"] = datetime.utcnow().isoformat() + "Z"
    task["branch"] = branch or f"task-{task_id}"
    log_info(f"✅ {task_id}: completed.")

    archive_append({
        "id": task_id,
        "title": title,
        "branch": task.get("branch"),
        "completed_at": task.get("completed_at"),
        "description": task.get("description"),
        "notes": task.get("notes", "")
    }, ARCHIVE_DONE)
    return task

def main():
    ensure_log_dirs()

    parser = argparse.ArgumentParser(description="AI Developer Orchestrator (parallel + archive)")
    parser.add_argument("--provider", choices=["llm"], required=True)
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--git", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--project", dest="project_path", default=".")
    parser.add_argument("--tasks", dest="tasks_path", default="tasks.json")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("--skip-preflight", action="store_true", help="Skip API connectivity preflight")
    parser.add_argument("--preflight-chat-fallback", action="store_true", help="Allow 1-token chat ping if models.list() unsupported")
    parser.add_argument("--preflight-timeout", type=float, default=8.0, help="Timeout (s) for preflight checks")
    parser.add_argument("--prune-done", action="store_true", help="Remove done/error tasks from tasks.json after run")
    args = parser.parse_args()

    env_project = os.getenv("ORCH_PROJECT")
    proj = env_project if env_project else args.project_path
    project_abs = os.path.abspath(proj)

    if not os.path.exists(project_abs) or not os.path.isdir(project_abs):
        log_error(f"Invalid project path: {project_abs}")
        sys.exit(1)

    if args.git and not os.path.exists(os.path.join(project_abs, ".git")):
        log_error(f"--git specified but not a git repo: {project_abs}")
        sys.exit(1)

    os.chdir(project_abs)
    log_info(f"📂 Working directory set to: {project_abs}")

    # Env echo for clarity
    api_key_present = bool(os.getenv("OPENAI_API_KEY"))
    base_url = os.getenv("OPENAI_BASE_URL") or "default"
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    log_info(f"[Env] OPENAI_API_KEY present={api_key_present} OPENAI_BASE_URL={base_url} OPENAI_MODEL={model}")

    if not args.skip_preflight:
        ok, msg = preflight_openai(model=model,
                                   timeout=args.preflight_timeout,
                                   chat_fallback=args.preflight_chat_fallback)
        if ok:
            log_info("✅ Preflight success: " + msg)
        else:
            log_error("❌ Preflight failed: " + msg)
            log_error("Aborting before task execution.")
            sys.exit(2)
    else:
        log_info("⚠️  Preflight skipped by flag.")

    try:
        tasks = load_tasks_from_path(args.tasks_path)
        tasks_to_run = [t for t in tasks if t.get("status", "pending") in VALID_STATUSES]

        updated_tasks = []
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_task = {executor.submit(execute_task, task, args, project_abs): task for task in tasks_to_run}
            for future in as_completed(future_to_task):
                updated_task = future.result()
                updated_tasks.append(updated_task)

        # Merge updates
        task_dict = {t["id"]: t for t in tasks}
        for ut in updated_tasks:
            task_dict[ut["id"]] = ut

        # Optionally prune processed tasks
        final_tasks = list(task_dict.values())
        if args.prune_done:
            final_tasks = [t for t in final_tasks if t.get("status") == "pending"]

        if not args.dry_run:
            save_tasks(final_tasks, os.path.abspath(args.tasks_path))

    finally:
        os.chdir("..")

    log_info("✅ All tasks processed.")

if __name__ == "__main__":
    main()
