#!/bin/bash
# mini-stop.sh — Stop hook for mini-harness orchestration + compound guard
# Orchestrates skill chain via run-scoped state; fallback to original compound guard

INPUT=$(cat)
CWD=$(echo "$INPUT" | jq -r '.cwd')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
SESSION_FILE="$CWD/.mini-harness/session/learnings.json"

RUNS_DIR="$CWD/.dev/harness/runs"

source "$CWD/scripts/harness-lib.sh"

# ── run state 파일 resolve ──
STATE_FILE=$(resolve_run_state "$CWD" "$SESSION_ID")

# ── 오케스트레이션 체인 ──
if [[ -n "$STATE_FILE" && -f "$STATE_FILE" ]]; then
  SKILL_NAME=$(jq -r '.skill_name' "$STATE_FILE")
  GOAL=$(jq -r '.goal // empty' "$STATE_FILE")
  RUN_ID=$(jq -r '.run_id' "$STATE_FILE")
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  case "$SKILL_NAME" in
    mini-harness)
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "{\"decision\":\"block\",\"reason\":\"interview 스킬을 실행하세요. args: \\\"run_id:$RUN_ID\\\"\"}"
      exit 0
      ;;
    interview)
      INTERVIEW_FILE=$(jq -r '.paths.interview // empty' "$STATE_FILE")
      INTERVIEW_ARG=""
      REFINED_GOAL="$GOAL"
      if [[ -n "$INTERVIEW_FILE" && -f "$CWD/$INTERVIEW_FILE" ]]; then
        INTERVIEW_ARG=" interview:$INTERVIEW_FILE"
        REFINED_GOAL=$(jq -r '.refined_goal // .original_goal' "$CWD/$INTERVIEW_FILE" 2>/dev/null || echo "$GOAL")
      fi
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "{\"decision\":\"block\",\"reason\":\"council 스킬을 실행하세요. goal: \\\"$REFINED_GOAL\\\"$INTERVIEW_ARG run_id:$RUN_ID\"}"
      exit 0
      ;;
    council)
      ADR_DIR=$(jq -r '.paths.adr_dir // empty' "$STATE_FILE")
      ADR_FILE=""
      [[ -n "$ADR_DIR" ]] && ADR_FILE=$(ls -t "$CWD/$ADR_DIR/"*.md 2>/dev/null | head -1)
      ADR_ARG=""
      [[ -n "$ADR_FILE" ]] && ADR_ARG=" adr:$ADR_FILE"
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "{\"decision\":\"block\",\"reason\":\"design-review 스킬을 실행하세요. args: \\\"run_id:$RUN_ID$ADR_ARG\\\"\"}"
      exit 0
      ;;
    design-review)
      ADR_DIR=$(jq -r '.paths.adr_dir // empty' "$STATE_FILE")
      REVIEW_DIR=$(jq -r '.paths.review_dir // empty' "$STATE_FILE")
      ADR_FILE=""
      REVIEW_FILE=""
      [[ -n "$ADR_DIR" ]] && ADR_FILE=$(ls -t "$CWD/$ADR_DIR/"*.md 2>/dev/null | head -1)
      [[ -n "$REVIEW_DIR" ]] && REVIEW_FILE=$(ls -t "$CWD/$REVIEW_DIR/"*.md 2>/dev/null | head -1)
      ADR_ARG=""
      REVIEW_ARG=""
      [[ -n "$ADR_FILE" ]] && ADR_ARG=" adr:$ADR_FILE"
      [[ -n "$REVIEW_FILE" ]] && REVIEW_ARG=" review:$REVIEW_FILE"
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "{\"decision\":\"block\",\"reason\":\"mini-specify 스킬을 실행하세요. args: \\\"$GOAL$ADR_ARG$REVIEW_ARG run_id:$RUN_ID\\\"\"}"
      exit 0
      ;;
    mini-specify)
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "{\"decision\":\"block\",\"reason\":\"taskify 스킬을 실행하세요. args: \\\"run_id:$RUN_ID\\\"\"}"
      exit 0
      ;;
    taskify)
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "{\"decision\":\"block\",\"reason\":\"dependency-resolve 스킬을 실행하세요. args: \\\"run_id:$RUN_ID\\\"\"}"
      exit 0
      ;;
    dependency-resolve)
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "{\"decision\":\"block\",\"reason\":\"mini-execute 스킬을 실행하세요. args: \\\"run_id:$RUN_ID\\\"\"}"
      exit 0
      ;;
    mini-execute)
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "{\"decision\":\"block\",\"reason\":\"mini-compound 스킬을 실행하세요. args: \\\"run_id:$RUN_ID\\\"\"}"
      exit 0
      ;;
    mini-compound)
      # 체인 완료: run state 파일 및 세션 포인터 삭제
      RUN_DIR_ABS=$(dirname "$(dirname "$STATE_FILE")")
      rm -f "$STATE_FILE"
      [[ -n "$SESSION_ID" ]] && rm -f "$RUN_DIR_ABS/sessions/${SESSION_ID}"
      echo '{"decision":"approve"}'
      exit 0
      ;;
  esac
fi

# ── 기존 compound guard (run state 없을 때) ──
if [[ -f "$SESSION_FILE" ]]; then
  COUNT=$(jq 'length' "$SESSION_FILE" 2>/dev/null || echo 0)
  echo "{\"decision\":\"block\",\"reason\":\"⚠️  $COUNT 개의 learning이 session에 기록되어 있습니다. /mini-compound 를 실행하여 영구 저장하세요.\"}"
else
  echo '{"decision":"approve"}'
fi
