#!/usr/bin/env bash
set -euo pipefail

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

# Fill these locally; do not commit secrets.
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
export OPENAI_MODEL="${OPENAI_MODEL:-gpt-5}"
# Optional proxy/base:
# export OPENAI_BASE_URL="https://api.openai.com/v1"

# Optional project path
# export ORCH_PROJECT="../WyrdRoot"

echo "Environment ready. OPENAI_MODEL=$OPENAI_MODEL"
