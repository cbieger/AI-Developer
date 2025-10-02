# AI Developer (the project-focused, ChatGPT API)

Automates “task list → code edits → git” for a the project project using the ChatGPT (OpenAI) API.
You write tasks in `tasks.json`. The orchestrator sends each task to the LLM, applies returned
file operations, and (optionally) commits/merges.

## Features
- **Task-driven workflow**: Each task describes a change; the LLM returns concrete file edits.
- **Safe file ops**: Model outputs a strict JSON list of operations: `write`, `append`, `patch`.
- **Guardrails**: Core workflow files are protected from edits.
- **Git loop**: Optional per-task branch, commit, and merge.
- **Project targeting**: Use `--project` to point at a sibling/other repo.
- **Tasks location**: Default is `tasks.json` in the project; override with `--tasks`.

## Prerequisites
- Python 3.10+
- Git
- OpenAI API key with access to your chosen model
- (Optional) the project 4.x on your PATH for validation hooks later

## Quick Start
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>
export OPENAI_MODEL=gpt-5                   # or gpt-5-thinking if enabled

# Edit a sibling project one directory up, e.g. ../the project
python orchestrator_ai.py --provider llm --auto --git --project ../the project
```

## Repository Layout
```
orchestrator_ai.py      # Main entry; loads tasks, calls runner, handles git
task_runner.py          # Dispatches each task to the LLM provider
providers/llm_openai.py # ChatGPT (OpenAI) provider using the Responses API
file_ops.py             # Applies {write|append|patch} operations safely
git_utils.py            # Branch/commit/merge helpers
utils.py                # Logging, guards, task IO
tasks.json              # Example task list
logs/                   # workflow.log, ai_feedback.log
```

**Locked/guarded files**: `orchestrator_ai.py`, `task_runner.py`, `utils.py`, `git_utils.py`, `reset_tasks.py`

## Writing Tasks
`tasks.json` is an array of task objects:
```json
[
  {
    "id": "task-001",
    "title": "Add Player whip dash",
    "description": "Implement dash in player.gd, bind to 'dash' input, update scene if needed.",
    "type": "code",
    "status": "pending"
  }
]
```

## Running
```bash
# Default: tasks.json in target project
python orchestrator_ai.py --provider llm --auto --git --project ../the project

# Keep tasks in ai-developer repo while editing another repo
python orchestrator_ai.py --provider llm --auto --git --project ../the project --tasks ./tasks.json
```

## Troubleshooting
- Ensure `OPENAI_API_KEY` is exported.
- If parsing errors occur, rerun or move to JSON schema response_format (provider supports easy upgrade).
- If patches fail, the system falls back to replacement.

## License
MIT
