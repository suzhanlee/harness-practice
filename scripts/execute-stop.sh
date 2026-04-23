#!/bin/bash
# execute-stop.sh — Stop hook for mini-execute ralph loop orchestration
# Handles validation-execute alternation and prevents infinite loops via last_action field

INPUT=$(cat)
_RAW_CWD=$(echo "$INPUT" | jq -r '.cwd')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')

if [[ "${_RAW_CWD:1:1}" == ":" ]]; then
  _drive="${_RAW_CWD:0:1}"; _rest="${_RAW_CWD:2}"; _rest="${_rest//\\/\/}"
  CWD="/${_drive,,}${_rest}"
else
  CWD="$_RAW_CWD"
fi

source "$CWD/scripts/harness-lib.sh"

# run state resolve
STATE_FILE=$(resolve_active_state "$CWD" "$SESSION_ID")

# Not in execute context → approve (delegate to mini-stop.sh)
if [[ -z "$STATE_FILE" || ! -f "$STATE_FILE" ]]; then
  echo '{"decision":"approve"}'; exit 0
fi

SKILL_NAME=$(jq -r '.skill_name' "$STATE_FILE")
if [[ "$SKILL_NAME" != "mini-execute" ]]; then
  echo '{"decision":"approve"}'; exit 0
fi

# spec 경로 동적 취득
SPEC_PATH=$(jq -r '.paths.spec // empty' "$STATE_FILE")
if [[ -z "$SPEC_PATH" ]]; then
  # fallback: 수동 호출(run_id 없음) 시 레거시 경로
  SPEC_PATH=".dev/harness/spec.json"
fi
SPEC_FILE="$CWD/$SPEC_PATH"

# spec.json missing → approve
if [[ ! -f "$SPEC_FILE" ]]; then
  echo '{"decision":"approve"}'; exit 0
fi

REMAINING=$(jq '[.tasks[] | select(.status != "end")] | length' "$SPEC_FILE")
LAST_ACTION=$(jq -r '.last_action // "execute"' "$STATE_FILE")
RUN_ID=$(jq -r '.run_id' "$STATE_FILE")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [[ "$REMAINING" -gt 0 ]]; then
  if [[ "$LAST_ACTION" == "execute" ]]; then
    # Transition to validate: set last_action to prevent re-entry
    jq --arg ts "$TIMESTAMP" '.last_action = "validate" | .timestamp = $ts' \
      "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
    INCOMPLETE=$(jq -r '[.tasks[] | select(.status != "end") | .action] | join(", ")' "$SPEC_FILE")
    echo "{\"decision\":\"block\",\"reason\":\"미완료 task가 있습니다. validate-tasks agent를 실행하세요. 미완료: $INCOMPLETE run_id:$RUN_ID\"}"
  else
    # Transition to re-execute: set last_action to prevent re-entry
    jq --arg ts "$TIMESTAMP" '.last_action = "execute" | .timestamp = $ts' \
      "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
    echo "{\"decision\":\"block\",\"reason\":\"검증 후 미완료 task가 남아있습니다. mini-execute 스킬을 실행하세요. args: \\\"run_id:$RUN_ID\\\"\"}"
  fi
else
  # All tasks complete → approve → mini-stop.sh handles compound transition
  echo '{"decision":"approve"}'
fi
