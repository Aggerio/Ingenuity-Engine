#!/usr/bin/env zsh
set -euo pipefail

source "$HOME/.elan/env"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
# Prefer in-repo sources over any older site-packages `erdos_engine` install.
export PYTHONPATH="${SCRIPT_DIR}/src:${PYTHONPATH:-}"

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "OPENROUTER_API_KEY is not set."
  echo "Export it first, then re-run this script."
  exit 1
fi

OPENAI_COMPATIBLE_API_KEY="${OPENROUTER_API_KEY}" \
OPENAI_COMPATIBLE_BASE_URL="https://openrouter.ai/api" \
OPENAI_COMPATIBLE_MODEL="x-ai/grok-4.1-fast" \
OPENAI_COMPATIBLE_CRITIC_API_KEY="${OPENROUTER_API_KEY}" \
OPENAI_COMPATIBLE_CRITIC_BASE_URL="https://openrouter.ai/api" \
OPENAI_COMPATIBLE_CRITIC_MODEL="google/gemini-3.1-flash-lite-preview" \
exec python -m erdos_engine.cli run erdos_004 "$@"
