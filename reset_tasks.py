import argparse
from utils import load_tasks, save_tasks

def main():
    parser = argparse.ArgumentParser(description="Reset task statuses to 'pending'")
    parser.add_argument(
        "--tasks",
        required=True,
        help="Path to the tasks file (e.g., ../other_project/tasks.json)"
    )
    parser.add_argument(
        "--filter",
        choices=["all", "error", "done"],
        default="all",
        help="Only reset tasks with this status (default: all)"
    )
    args = parser.parse_args()

    tasks = load_tasks(args.tasks)
    count = 0

    for task in tasks:
        if args.filter == "all" or task.get("status") == args.filter:
            task["status"] = "pending"
            count += 1

    save_tasks(tasks, args.tasks)
    print(f"✅ {count} task(s) in '{args.tasks}' reset to 'pending' (filter: {args.filter})")

if __name__ == "__main__":
    main()

