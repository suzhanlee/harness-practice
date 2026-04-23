#!/bin/bash
# mini-post-tool-use.sh — PostToolUse hook for mini-harness orchestration
# After mini-harness Skill completes, ensure run state status is processing

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')
_RAW_CWD=$(echo "$INPUT" | jq -r '.cwd')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')

if [[ "${_RAW_CWD:1:1}" == ":" ]]; then
  _drive="${_RAW_CWD:0:1}"; _rest="${_RAW_CWD:2}"; _rest="${_rest//\\/\/}"
  CWD="/${_drive,,}${_rest}"
else
  CWD="$_RAW_CWD"
fi

source "$CWD/scripts/harness-lib.sh"

if [[ "$TOOL_NAME" == "Skill" ]]; then
  STATE_FILE=$(resolve_active_state "$CWD" "$SESSION_ID")

  if [[ -n "$STATE_FILE" && -f "$STATE_FILE" ]]; then
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    SKILL_NAME=$(jq -r '.skill_name' "$STATE_FILE")

    if [[ "$SKILL_NAME" == "mini-harness" ]]; then
      jq --arg ts "$TIMESTAMP" '.status = "processing" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
    fi
  fi
fi
