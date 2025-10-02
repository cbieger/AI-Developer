import argparse
from utils import load_tasks, save_tasks

def main():
    parser = argparse.ArgumentParser(description="Reset all tasks to 'pending'")
    parser.add_argument(
        "--tasks",
        required=True,
        help="Path to the tasks file (e.g., ../other_project/tasks.json)"
    )
    args = parser.parse_args()

    tasks = load_tasks(args.tasks)
    for task in tasks:
        task["status"] = "pending"
    save_tasks(tasks, args.tasks)

    print(f"✅ All tasks in {args.tasks} have been reset to 'pending'")

if __name__ == "__main__":
    main()

