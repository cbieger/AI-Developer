# AI Developer Orchestrator

A clean, commented scaffold for automating coding workflows with an LLM. It handles task execution, parallel workers, archiving outputs, and safe preflight checks so you do not accidentally call the API without a key.

This repo intentionally avoids product-specific prompts and personal references. It is safe to make public.

---

## Features

- Parallel task execution (`--workers N`)
- Clean exits via preflight check (prevents calls without `OPENAI_API_KEY`)
- Archiving of outputs to `archive/run_<timestamp>/`
- Thin provider wrapper with defensive error handling
- Hygiene included: `.gitignore`, `.editorconfig`, `pyproject.toml`, neutral prompt

---

## Quick Start


## 1) Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

## 2) Install dependencies
pip install -r requirements.txt

## 3) Configure environment (do not commit secrets)
source envStartUp.sh
# Set OPENAI_API_KEY in your shell

## 4) See options
python orchestrator_ai_parallel_with_archive.py --help


Run the example tasks:

python orchestrator_ai_parallel_with_archive.py \
  --project .. \
  --tasks tasks.json \
  --workers 2 \
  --git
  
Outputs are written to ai_out/ and archived to archive/run_<UTC-timestamp>/.

Project Structure

.
├─ orchestrator_ai_parallel_with_archive.py   # Main runner (parallel + archive), fully commented
├─ providers/
│  └─ llm_openai.py                           # Provider wrapper: preflight + chat call + error handling
├─ scripts/
│  ├─ scrub_terms.sh                          # Repo-wide term scrubber (dry-run by default)
│  └─ annotate_repo.py                        # Adds header comments/docstrings to files
├─ prompts/
│  └─ engine_guru_v2.txt                      # Neutral “engine guru” system prompt
├─ tasks.json                                 # Example tasks
├─ envStartUp.sh                              # Local env variable template (do not commit secrets)
├─ requirements.txt
├─ .editorconfig
├─ .gitignore
├─ pyproject.toml                             # Ruff/Black settings
└─ LICENSE

Configuration
Export environment variables in your shell; do not commit values.
OPENAI_API_KEY (required) — API key for the model provider
OPENAI_BASE_URL (optional) — custom API base URL
OPENAI_MODEL (optional) — default model name (for example, gpt-5)
ORCH_PROJECT (optional) — project root that tasks operate on (default: ..)
Template (envStartUp.sh):
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
export OPENAI_BASE_URL="${OPENAI_BASE_URL:-}"
export OPENAI_MODEL="${OPENAI_MODEL:-gpt-5}"
export ORCH_PROJECT="${ORCH_PROJECT:-../MyProject}"

How It Works
Preflight: the orchestrator asks the provider whether it can safely call the API. If the key is missing, it exits cleanly with code 2.
Tasks: reads tasks.json (either a list or an object with a tasks array).
Execution: runs sequentially or with a thread pool (--workers N).
Persistence: writes each task’s result into ai_out/<task-id>.txt.
Archiving: copies ai_out/ into archive/run_<timestamp>/.
Optional Git: stages and commits changes with a generic message.

Example tasks.json
[
  {
    "id": "llm-hello",
    "title": "LLM Hello",
    "description": "Say hello and list three bullet points about this orchestrator.",
    "status": "pending"
  }
]


Useful Commands
Term scrubber (dry-run by default):
./scripts/scrub_terms.sh
./scripts/scrub_terms.sh --apply --replace "the application"
Annotate files with headers/docstrings (backs up to .annotate_backup/):
python scripts/annotate_repo.py
Secret and key scans:
# names of sensitive things (references are OK; look for actual values)
rg -n --hidden --glob '!.git' '(?i)(api[_-]?key|secret|token|authorization|password|private[_-]?key)'

# private key blocks (must return nothing)
rg -n --hidden --glob '!.git' -- '-----BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY-----'


Troubleshooting
Preflight failed: OPENAI_API_KEY is missing. Export the key and re-run:

export OPENAI_API_KEY="<YOUR_OPENAI_API_KEY>"

No outputs in ai_out/: ensure tasks.json exists and has tasks; check provider errors.
Git commit does nothing: if there are no file changes, the commit is a no-op.

Design Notes
ChatGPT played a pivotal role in creating this application / workflow.  Hate if you want, or just use it. 
Provider wrapper is intentionally thin to keep it swappable.
The orchestrator favors predictable behavior:
Exit codes: 0 success, 1 partial/total task failure, 2 configuration error.
Files are written plainly for easy diffing and archiving.
Prompts are neutral and portable; avoid naming specific engines or tools in system prompts.
Contributing


Pull requests are welcome. Keep prompts neutral and portable. Avoid committing secrets, logs, or archives. Favor small, well-commented changes.

ruff check .


MIT. See LICENSE.
