#!/bin/bash
# mini-stop.sh — Stop hook for mini harness
# Blocks session exit if session/learnings.json exists (compound not yet run)

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd')
SESSION_FILE="$CWD/.mini-harness/session/learnings.json"

if [[ -f "$SESSION_FILE" ]]; then
  COUNT=$(jq 'length' "$SESSION_FILE" 2>/dev/null || echo 0)
  echo "{\"decision\":\"block\",\"reason\":\"⚠️  $COUNT 개의 learning이 session에 기록되어 있습니다. /mini-compound 를 실행하여 영구 저장하세요.\"}"
else
  echo "{\"decision\":\"allow\"}"
fi
