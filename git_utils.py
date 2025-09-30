import os, subprocess
from utils import log_info, log_error

def _run(cmd, cwd=None):
    res = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{res.stdout}\n{res.stderr}")
    return res.stdout.strip()

def _default_branch(cwd=None):
    # Try to detect default branch
    for cand in ("main", "master"):
        try:
            _run(["git", "rev-parse", "--verify", cand], cwd=cwd)
            return cand
        except Exception:
            continue
    # Fallback to current branch
    return _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)

def create_or_checkout_branch_for_task(task_id: str, cwd=None) -> str:
    branch = f"task/{task_id}"
    try:
        _run(["git", "rev-parse", "--verify", branch], cwd=cwd)
        log_info(f"Checking out existing branch {branch}")
        _run(["git", "checkout", branch], cwd=cwd)
    except Exception:
        log_info(f"Creating branch {branch}")
        _run(["git", "checkout", "-b", branch], cwd=cwd)
    return branch

def commit_all_for_task(task_id: str, title: str, cwd=None):
    _run(["git", "add", "-A"], cwd=cwd)
    msg = f"{task_id}: {title}"
    _run(["git", "commit", "-m", msg], cwd=cwd)
    log_info(f"Committed changes: {msg}")

def merge_branch_to_default(branch: str, cwd=None):
    default = _default_branch(cwd=cwd)
    # Checkout default and merge
    _run(["git", "checkout", default], cwd=cwd)
    _run(["git", "merge", "--no-ff", branch, "-m", f"Merge {branch}"], cwd=cwd)
    log_info(f"Merged {branch} into {default}")
