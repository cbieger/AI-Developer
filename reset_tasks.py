from utils import load_tasks, save_tasks

tasks = load_tasks()
for task in tasks:
    task["status"] = "pending"
save_tasks(tasks)
print("✅ All tasks have been reset to 'pending'")
