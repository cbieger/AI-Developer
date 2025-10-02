#!/usr/bin/env python3
import argparse, os, sys, json
from typing import Dict, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from task_runner import run_task
from git_utils import create_or_checkout_branch_for_task, commit_all_for_task, merge_branch_to_default
from utils import ensure_log_dirs, log_info, log_error, log_feedback, load_tasks_from_path

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

VALID_STATUSES = {"pending", "error"}
REQUIRED_TASK_KEYS = {"id", "title", "description"}

def validate_task(task: Dict[str, Any]) -> bool:
    missing = [k for k in REQUIRED_TASK_KEYS if k not in task]
    if missing:
        log_error(f"❌ Task missing keys: {', '.join(missing)}")
        return False
    return True

def process_task(task, args, project_abs):
    task_id = task["id"]
    title = task["title"]
    log_info(f"🔧 Running {task_id}: {title}")

    result: Dict[str, Any] = run_task(task, provider=args.provider, dry_run=args.dry_run, context={"cwd": project_abs})
    feedback = (result or {}).get("feedback", "").strip()
    error_flag = bool(result.get("error", False))

    if feedback:
        log_feedback(task_id, feedback)

    if error_flag:
        log_error(f"❌ {task_id}: Task failed. Skipping git.")
        task["status"] = "error"
        if args.archive:
            archive_append({**task, "failed_at": datetime.utcnow().isoformat() + "Z"}, "archive/failed_tasks.json")
        return task

    if args.git and not args.dry_run:
        try:
            branch = create_or_checkout_branch_for_task(task_id, cwd=project_abs)
            commit_all_for_task(task_id, title, cwd=project_abs)
            merge_branch_to_default(branch, cwd=project_abs)
        except Exception as e:
            log_error(f"{task_id}: Git error: {e}")
            task["status"] = "error"
            if args.archive:
                archive_append({**task, "error": str(e)}, "archive/failed_tasks.json")
            return task

    task["status"] = "done"
    log_info(f"✅ {task_id}: completed.")
    if args.archive:
        archive_append({**task, "completed_at": datetime.utcnow().isoformat() + "Z"}, "archive/completed_tasks.json")

    return task

def main():
    ensure_log_dirs()

    parser = argparse.ArgumentParser(description="AI Developer Orchestrator")
    parser.add_argument("--provider", choices=["llm"], required=True)
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--git", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--archive", action="store_true")
    parser.add_argument("--parallel", type=int, default=1, help="Number of tasks to run in parallel (default 1 = sequential)")
    parser.add_argument("--project", dest="project_path", default=".")
    parser.add_argument("--tasks", dest="tasks_path", default="tasks.json")
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

    original_cwd = os.getcwd()
    os.chdir(project_abs)
    log_info(f"📂 Working directory set to: {project_abs}")

    try:
        tasks = load_tasks_from_path(args.tasks_path)
        runnable = []

        for task in tasks:
            status = task.get("status", "pending")
            if status not in VALID_STATUSES:
                continue
            if not validate_task(task):
                task["status"] = "error"
                if args.archive:
                    archive_append({
                        "id": task.get("id"),
                        "title": task.get("title"),
                        "error": "validation failed",
                        "failed_at": datetime.utcnow().isoformat() + "Z"
                    }, "archive/failed_tasks.json")
                continue
            runnable.append(task)

        if args.parallel <= 1:
            for task in runnable:
                process_task(task, args, project_abs)
        else:
            with ThreadPoolExecutor(max_workers=args.parallel) as executor:
                futures = {executor.submit(process_task, task, args, project_abs): task for task in runnable}
                for future in as_completed(futures):
                    future.result()

    finally:
        try:
            t_abs = os.path.abspath(args.tasks_path)
            if t_abs.startswith(project_abs) and not args.dry_run:
                with open(t_abs, "w", encoding="utf-8") as f:
                    json.dump(tasks, f, indent=2)
        except Exception as e:
            log_error(f"Failed to save tasks: {e}")
        os.chdir(original_cwd)

    log_info("✅ All tasks processed.")

if __name__ == "__main__":
    main()

