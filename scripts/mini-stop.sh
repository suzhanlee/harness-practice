#!/bin/bash
# mini-stop.sh — Stop hook for mini-harness orchestration + compound guard
# Orchestrates skill chain via state.json; fallback to original compound guard

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd')
STATE_FILE="$CWD/.claude/state/state.json"
SESSION_FILE="$CWD/.mini-harness/session/learnings.json"

# ── 오케스트레이션 체인 ──
if [[ -f "$STATE_FILE" ]]; then
  SKILL_NAME=$(jq -r '.skill_name' "$STATE_FILE")
  GOAL=$(jq -r '.goal // empty' "$STATE_FILE")
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  case "$SKILL_NAME" in
    mini-harness)
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "{\"decision\":\"block\",\"reason\":\"council 스킬을 실행하세요. goal: \\\"$GOAL\\\"\"}"
      exit 0
      ;;
    council)
      ADR_FILE=$(ls -t "$CWD/.dev/adr/"*.md 2>/dev/null | head -1)
      ADR_ARG=""
      [[ -n "$ADR_FILE" ]] && ADR_ARG=" adr:$ADR_FILE"
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "{\"decision\":\"block\",\"reason\":\"mini-specify 스킬을 실행하세요. args: \\\"$GOAL$ADR_ARG\\\"\"}"
      exit 0
      ;;
    mini-specify)
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "{\"decision\":\"block\",\"reason\":\"taskify 스킬을 실행하세요.\"}"
      exit 0
      ;;
    taskify)
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "{\"decision\":\"block\",\"reason\":\"dependency-resolve 스킬을 실행하세요.\"}"
      exit 0
      ;;
    dependency-resolve)
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "{\"decision\":\"block\",\"reason\":\"mini-execute 스킬을 실행하세요.\"}"
      exit 0
      ;;
    mini-execute)
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "{\"decision\":\"block\",\"reason\":\"mini-compound 스킬을 실행하세요.\"}"
      exit 0
      ;;
    mini-compound)
      # 체인 완료: state.json 삭제
      rm -f "$STATE_FILE"
      echo '{"decision":"approve"}'
      exit 0
      ;;
  esac
fi

# ── 기존 compound guard (state.json 없을 때) ──
if [[ -f "$SESSION_FILE" ]]; then
  COUNT=$(jq 'length' "$SESSION_FILE" 2>/dev/null || echo 0)
  echo "{\"decision\":\"block\",\"reason\":\"⚠️  $COUNT 개의 learning이 session에 기록되어 있습니다. /mini-compound 를 실행하여 영구 저장하세요.\"}"
else
  echo '{"decision":"approve"}'
fi
