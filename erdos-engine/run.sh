#!/usr/bin/env zsh
set -euo pipefail

source "$HOME/.elan/env"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "OPENROUTER_API_KEY is not set."
  echo "Export it first, then re-run this script."
  exit 1
fi

OPENAI_COMPATIBLE_API_KEY="${OPENROUTER_API_KEY}" \
OPENAI_COMPATIBLE_BASE_URL="https://openrouter.ai/api" \
OPENAI_COMPATIBLE_MODEL="deepseek/deepseek-v4-flash" \
OPENAI_COMPATIBLE_CRITIC_API_KEY="${OPENROUTER_API_KEY}" \
OPENAI_COMPATIBLE_CRITIC_BASE_URL="https://openrouter.ai/api" \
OPENAI_COMPATIBLE_CRITIC_MODEL="google/gemini-3.1-flash-lite-preview" \
python -m erdos_engine.cli run erdos_004 \
  --use-rlm \
  --run-label solve4_retry_with_fallback_logging \
  --max-depth 2 \
  --beam-width 2 \
  --moves-per-state 2 \
  --llm-timeout-seconds 120 \
  --llm-max-tokens 2200 \
  "$@"
