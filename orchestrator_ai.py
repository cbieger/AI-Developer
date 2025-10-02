#!/usr/bin/env python3
import argparse, os, sys
from typing import Dict, Any, List
from datetime import datetime, timezone
from task_runner import run_task
from git_utils import (
    start_automation_branch,
    commit_all_for_tasks,
    finalize_automation_branch
)
from utils import (
    ensure_log_dirs,
    log_info,
    log_error,
    log_feedback,
    archive_append,
    load_tasks_from_path
)

VALID_STATUSES = {"pending", "error"}
REQUIRED_TASK_KEYS = {"id", "title", "description"}

def validate_task(task: Dict[str, Any]) -> bool:
    missing = [k for k in REQUIRED_TASK_KEYS if k not in task]
    if missing:
        log_error(f"❌ Task missing keys: {', '.join(missing)}")
        return False
    return True

def main():
    ensure_log_dirs()

    parser = argparse.ArgumentParser(description="AI Developer Orchestrator")
    parser.add_argument("--provider", choices=["llm"], required=True)
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--git", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--archive", action="store_true")
    parser.add_argument("--parallel", type=int, default=1)
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

    completed_tasks: List[Dict[str, Any]] = []

    try:
        tasks = load_tasks_from_path(args.tasks_path)
        branch_name = start_automation_branch(cwd=project_abs) if args.git and not args.dry_run else None

        for task in tasks:
            status = task.get("status", "pending")
            if status not in VALID_STATUSES:
                continue

            if not validate_task(task):
                task["status"] = "error"
                continue

            task_id = task["id"]
            title = task["title"]
            log_info(f"🔧 Running {task_id}: {title}")

            result = run_task(task, provider=args.provider, dry_run=args.dry_run, context={"cwd": project_abs})
            feedback = (result or {}).get("feedback", "").strip()
            error_flag = bool(result.get("error", False))

            if feedback:
                log_feedback(task_id, feedback)

            if error_flag:
                log_error(f"❌ {task_id}: Task failed.")
                task["status"] = "error"
                continue

            task["status"] = "done"
            completed_tasks.append({**task, "feedback": feedback})
            log_info(f"✅ {task_id}: completed.")

        if args.git and not args.dry_run:
            commit_all_for_tasks(branch_name, completed_tasks, cwd=project_abs)
            finalize_automation_branch(branch_name, completed_tasks, cwd=project_abs)

    finally:
        try:
            t_abs = os.path.abspath(args.tasks_path)
            if t_abs.startswith(project_abs) and not args.dry_run:
                import json
                with open(t_abs, "w", encoding="utf-8") as f:
                    json.dump(tasks, f, indent=2)
        except Exception as e:
            log_error(f"Failed to save tasks: {e}")
        os.chdir(original_cwd)

    if args.archive:
        for task in completed_tasks:
            archive_append({**task, "completed_at": datetime.now(timezone.utc).isoformat()}, "archive/completed_tasks.json")

    log_info("✅ All tasks processed.")

if __name__ == "__main__":
    main()
