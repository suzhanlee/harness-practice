#!/bin/bash
# mini-pre-tool-use.sh — PreToolUse hook for mini-harness orchestration
# Before any Skill tool call, update run state with current skill and processing status

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name')
SKILL_NAME=$(echo "$INPUT" | jq -r '.tool_input.skill // empty')
ARGS=$(echo "$INPUT" | jq -r '.tool_input.args // empty')
_RAW_CWD=$(echo "$INPUT" | jq -r '.cwd')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')

# harness-lib.sh source 전에 normalize_cwd 인라인 처리
if [[ "${_RAW_CWD:1:1}" == ":" ]]; then
  _drive="${_RAW_CWD:0:1}"; _rest="${_RAW_CWD:2}"; _rest="${_rest//\\/\/}"
  CWD="/${_drive,,}${_rest}"
else
  CWD="$_RAW_CWD"
fi

source "$CWD/scripts/harness-lib.sh"

if [[ "$TOOL_NAME" == "Skill" && -n "$SKILL_NAME" ]]; then
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  if [[ "$SKILL_NAME" == "mini-harness" ]]; then
    # 최초 진입: run_id 생성, run state 파일 신규 생성, 세션 포인터 등록
    RUN_ID=$(generate_run_id)
    RUN_DIR=".dev/harness/runs/run-${RUN_ID}"
    mkdir -p "$CWD/$RUN_DIR/state" \
             "$CWD/$RUN_DIR/sessions" \
             "$CWD/$RUN_DIR/interview" \
             "$CWD/$RUN_DIR/requirement" \
             "$CWD/$RUN_DIR/spec" \
             "$CWD/$RUN_DIR/adr" \
             "$CWD/$RUN_DIR/review"

    STATE_FILE="$CWD/$RUN_DIR/state/state.json"

    jq -n \
      --arg run_id   "$RUN_ID" \
      --arg name     "mini-harness" \
      --arg goal     "$ARGS" \
      --arg ts       "$TIMESTAMP" \
      --arg run_dir  "$RUN_DIR" \
      --arg state    "$RUN_DIR/state/state.json" \
      --arg interview "$RUN_DIR/interview/interview.json" \
      --arg req_path  "$RUN_DIR/requirement/requirements.json" \
      --arg spec_path "$RUN_DIR/spec/spec.json" \
      --arg adr_dir   "$RUN_DIR/adr" \
      --arg review_dir "$RUN_DIR/review" \
      --arg sess_dir  "$RUN_DIR/sessions" \
      '{
        "run_id":     $run_id,
        "skill_name": $name,
        "status":     "processing",
        "goal":       $goal,
        "timestamp":  $ts,
        "paths": {
          "run_dir":      $run_dir,
          "state":        $state,
          "interview":    $interview,
          "requirements": $req_path,
          "spec":         $spec_path,
          "adr_dir":      $adr_dir,
          "review_dir":   $review_dir,
          "sessions_dir": $sess_dir
        }
      }' > "$STATE_FILE"

    # 세션 포인터 등록 (빈 마커 파일)
    [[ -n "$SESSION_ID" ]] && touch "$CWD/$RUN_DIR/sessions/${SESSION_ID}"

  else
    # 체인 중 다음 스킬: 세션 포인터 → 폴백 스캔 순으로 STATE_FILE resolve
    STATE_FILE=$(resolve_active_state "$CWD" "$SESSION_ID")

    if [[ -n "$STATE_FILE" && -f "$STATE_FILE" ]]; then
      # 세션 포인터 갱신 (compact 후 새 session_id로 들어왔을 경우 대비)
      if [[ -n "$SESSION_ID" ]]; then
        RUN_DIR_ABS=$(dirname "$(dirname "$STATE_FILE")")
        touch "$RUN_DIR_ABS/sessions/${SESSION_ID}"
      fi

      if [[ "$SKILL_NAME" == "mini-execute" ]]; then
        jq \
          --arg name "$SKILL_NAME" \
          --arg ts "$TIMESTAMP" \
          '.skill_name = $name | .status = "processing" | .last_action = "execute" | .timestamp = $ts' \
          "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      else
        jq \
          --arg name "$SKILL_NAME" \
          --arg ts "$TIMESTAMP" \
          '.skill_name = $name | .status = "processing" | .timestamp = $ts' \
          "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      fi
    fi
    # STATE_FILE이 없으면 (수동 호출 + 활성 run 없음) hook은 아무것도 하지 않음
  fi
fi

echo '{"decision":"approve"}'
