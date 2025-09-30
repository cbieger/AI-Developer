#!/usr/bin/env python3
import argparse, os, sys
from typing import Dict, Any

from task_runner import run_task
from git_utils import (
    create_or_checkout_branch_for_task,
    commit_all_for_task,
    merge_branch_to_default,
)
from utils import (
    ensure_log_dirs,
    log_info,
    log_error,
    log_feedback,
    load_tasks,
    save_tasks,
    is_automation_locked_by_task,
    load_tasks_from_path,
)

def main():
    # Keep logs in the orchestrator's starting folder
    ensure_log_dirs()

    parser = argparse.ArgumentParser(description="AI Developer Orchestrator")
    parser.add_argument("--provider", choices=["llm"], required=True,
                        help="Provider must be 'llm' for this workflow.")
    parser.add_argument("--auto", action="store_true", help="Run all tasks automatically")
    parser.add_argument("--git", action="store_true", help="Commit & merge changes per task")
    parser.add_argument("--project", dest="project_path", default=".",
                        help="Path to the target project/repo to edit (default: current dir)")
    parser.add_argument("--tasks", dest="tasks_path", default="tasks.json",
                        help="Path to tasks file (default: tasks.json in working dir)")
    args = parser.parse_args()

    # Calculate project path (allow env override ORCH_PROJECT)
    env_project = os.getenv("ORCH_PROJECT")
    proj = env_project if env_project else args.project_path
    project_abs = os.path.abspath(proj)

    if not os.path.exists(project_abs):
        log_error(f"Project path does not exist: {project_abs}")
        sys.exit(1)
    if not os.path.isdir(project_abs):
        log_error(f"Project path is not a directory: {project_abs}")
        sys.exit(1)

    if args.git and not os.path.exists(os.path.join(project_abs, ".git")):
        log_error(f"--git specified but target is not a git repo: {project_abs}")
        sys.exit(1)

    original_cwd = os.getcwd()
    os.chdir(project_abs)
    log_info(f"📂 Working directory set to: {project_abs}")

    try:
        tasks = load_tasks_from_path(args.tasks_path)
        tasks_iter = tasks if isinstance(tasks, list) else [tasks]

        for task in tasks_iter:
            status = task.get("status", "pending")
            if status not in ("pending", "error"):
                continue

            task_id = task.get("id", "unknown-task")
            title = task.get("title") or task.get("description", "Untitled Task")

            log_info(f"🔧 Running {task_id}: {title}")

            if is_automation_locked_by_task(task):
                msg = "❌ Automation core files are locked and cannot be modified by tasks."
                log_error(f"{task_id}: {msg}")
                log_feedback(task_id, msg)
                task["status"] = "error"
                continue

            result: Dict[str, Any] = run_task(task, provider="llm")
            feedback = (result or {}).get("feedback", "").strip()
            error_flag = bool((result or {}).get("error", False))

            if feedback:
                log_feedback(task_id, feedback)

            if error_flag or ("error" in feedback.lower()):
                log_error(f"❌ {task_id}: LLM reported errors. Skipping git.")
                task["status"] = "error"
                continue

            if args.git:
                try:
                    branch = create_or_checkout_branch_for_task(task_id, cwd=project_abs)
                    commit_all_for_task(task_id, title or task_id, cwd=project_abs)
                    merge_branch_to_default(branch, cwd=project_abs)
                except Exception as e:
                    log_error(f"{task_id}: Git failure: {e}")
                    task["status"] = "error"
                    continue

            task["status"] = "done"
            log_info(f"✅ {task_id}: completed.")
    finally:
        # Persist task state back to the provided tasks path (if it lives in project)
        try:
            # Only save if tasks_path is within project folder to avoid overwriting external files unintentionally
            t_abs = os.path.abspath(args.tasks_path)
            if t_abs.startswith(project_abs):
                with open(t_abs, "w", encoding="utf-8") as f:
                    import json
                    json.dump(tasks, f, indent=2)
        except Exception as e:
            log_error(f"Failed to save tasks: {e}")
        os.chdir(original_cwd)

    log_info("✅ All tasks processed.")

if __name__ == "__main__":
    main()
