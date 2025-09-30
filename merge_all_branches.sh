#!/bin/bash
# Automatically merge all local branches into master
# Usage: ./merge_all_branches.sh

LOG_FILE="merge_log.txt"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "===== Merge Run at $DATE =====" >> "$LOG_FILE"

# Ensure we’re on master
echo "[INFO] Switching to master..." | tee -a "$LOG_FILE"
git checkout master >>"$LOG_FILE" 2>&1
git pull origin master >>"$LOG_FILE" 2>&1

# List all branches except master
branches=$(git branch --list | grep -v "master" | sed 's/*//' | awk '{$1=$1};1')

# Merge each branch into master
for branch in $branches; do
    echo "[INFO] Merging branch: $branch" | tee -a "$LOG_FILE"
    git merge --no-edit "$branch" >>"$LOG_FILE" 2>&1

    if [ $? -eq 0 ]; then
        echo "[SUCCESS] Merged $branch into master" | tee -a "$LOG_FILE"
    else
        echo "[WARNING] Merge conflict in $branch. Skipping. Resolve manually." | tee -a "$LOG_FILE"
        git merge --abort >>"$LOG_FILE" 2>&1
    fi
done

# Push master
echo "[INFO] Pushing master to origin..." | tee -a "$LOG_FILE"
git push origin master >>"$LOG_FILE" 2>&1

echo "[DONE] All merges attempted. Check $LOG_FILE for details." | tee -a "$LOG_FILE"

