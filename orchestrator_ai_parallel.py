
#!/usr/bin/env python3
import argparse, os, sys, json
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from task_runner import run_task
from git_utils import create_or_checkout_branch_for_task, commit_all_for_task, merge_branch_to_default
from utils import ensure_log_dirs, log_info, log_error, log_feedback, load_tasks_from_path

VALID_STATUSES = {"pending", "error"}
REQUIRED_TASK_KEYS = {"id", "title", "description"}

def validate_task(task: Dict[str, Any]) -> bool:
    missing = [k for k in REQUIRED_TASK_KEYS if k not in task]
    if missing:
        log_error(f"❌ Task missing keys: {', '.join(missing)}")
        return False
    return True

def execute_task(task: Dict[str, Any], args: argparse.Namespace, project_abs: str) -> Dict[str, Any]:
    task_id = task["id"]
    title = task["title"]

    if not validate_task(task):
        task["status"] = "error"
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
        return task

    if args.git and not args.dry_run:
        try:
            branch = create_or_checkout_branch_for_task(task_id, cwd=project_abs)
            commit_all_for_task(task_id, title, cwd=project_abs)
            merge_branch_to_default(branch, cwd=project_abs)
        except Exception as e:
            log_error(f"{task_id}: Git error: {e}")
            task["status"] = "error"
            return task

    task["status"] = "done"
    log_info(f"✅ {task_id}: completed.")
    return task

def main():
    ensure_log_dirs()

    parser = argparse.ArgumentParser(description="AI Developer Orchestrator")
    parser.add_argument("--provider", choices=["llm"], required=True)
    parser.add_argument("--auto", action="store_true")
    parser.add_argument("--git", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--project", dest="project_path", default=".")
    parser.add_argument("--tasks", dest="tasks_path", default="tasks.json")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
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

    try:
        tasks = load_tasks_from_path(args.tasks_path)
        tasks_to_run = [t for t in tasks if t.get("status", "pending") in VALID_STATUSES]

        updated_tasks = []
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_task = {executor.submit(execute_task, task, args, project_abs): task for task in tasks_to_run}
            for future in as_completed(future_to_task):
                updated_task = future.result()
                updated_tasks.append(updated_task)

        task_dict = {t["id"]: t for t in tasks}
        for ut in updated_tasks:
            task_dict[ut["id"]] = ut

        if not args.dry_run:
            with open(os.path.abspath(args.tasks_path), "w", encoding="utf-8") as f:
                json.dump(list(task_dict.values()), f, indent=2)

    finally:
        os.chdir("..")

    log_info("✅ All tasks processed.")

if __name__ == "__main__":
    main()
