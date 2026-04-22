#!/bin/bash
# mini-start-session.sh — SessionStart hook for state recovery after compact
# Detects interrupted work and reconnects to the correct run after compact

INPUT=$(cat)
_RAW_CWD=$(echo "$INPUT" | jq -r '.cwd')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')
IS_COMPACT=$(echo "$INPUT" | jq -r '.is_compact // false')

# harness-lib.sh source 전에 normalize_cwd 인라인 처리
if [[ "${_RAW_CWD:1:1}" == ":" ]]; then
  _drive="${_RAW_CWD:0:1}"; _rest="${_RAW_CWD:2}"; _rest="${_rest//\\/\/}"
  CWD="/${_drive,,}${_rest}"
else
  CWD="$_RAW_CWD"
fi

LOG_FILE="$CWD/.dev/harness/session-recovery.log"

RUNS_DIR="$CWD/.dev/harness/runs"

mkdir -p "$CWD/.dev/harness"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo "[$TIMESTAMP] SessionStart fired. session_id=$SESSION_ID is_compact=$IS_COMPACT" >> "$LOG_FILE"

source "$CWD/scripts/harness-lib.sh"

# ── 내부 헬퍼: 활성 state 파일에 대해 block/approve 결정 ──
handle_active_state() {
  local state_file="$1"
  local is_compact="$2"
  local cwd="$3"

  local skill_name run_id spec_path goal remaining
  skill_name=$(jq -r '.skill_name' "$state_file")
  run_id=$(jq -r '.run_id' "$state_file")
  spec_path=$(jq -r '.paths.spec // empty' "$state_file")
  goal=$(jq -r '.goal // ""' "$state_file")
  remaining=0

  if [[ -n "$spec_path" && -f "$cwd/$spec_path" ]]; then
    remaining=$(jq '[.tasks[] | select(.status != "end")] | length' "$cwd/$spec_path")
  fi

  if [[ "$remaining" -gt 0 ]]; then
    local msg="${skill_name} 재개 필요. run_id:${run_id} goal:\"${goal}\" (미완료 task: ${remaining}개)"
    [[ "$is_compact" == "true" ]] && msg="$msg (compact 후 복구됨)"
    printf '{"decision":"block","reason":"%s"}' "$msg"
  else
    printf '{"decision":"approve"}'
  fi
}

# ── Step 1: 현재 session_id로 포인터 확인 ──
STATE_FILE=$(resolve_run_state "$CWD" "$SESSION_ID")

if [[ -n "$STATE_FILE" && -f "$STATE_FILE" ]]; then
  echo "[$TIMESTAMP] Pointer found for session $SESSION_ID" >> "$LOG_FILE"
  handle_active_state "$STATE_FILE" "$IS_COMPACT" "$CWD"
  exit $?
fi

# ── Step 2: 포인터 없음 → runs/ 스캔 (compact 후 새 session_id 상황) ──
echo "[$TIMESTAMP] No pointer for session_id=$SESSION_ID. Scanning runs/..." >> "$LOG_FILE"

if [[ ! -d "$RUNS_DIR" ]]; then
  echo '{"decision":"approve"}'; exit 0
fi

ACTIVE_RUNS=()
for run_dir in "$RUNS_DIR"/run-*/; do
  run_file="$run_dir/state/state.json"
  [[ -f "$run_file" ]] || continue
  run_status=$(jq -r '.status // empty' "$run_file" 2>/dev/null)
  [[ "$run_status" == "processing" ]] || continue
  ACTIVE_RUNS+=("$run_file")
done

ACTIVE_COUNT=${#ACTIVE_RUNS[@]}
echo "[$TIMESTAMP] Active runs found: $ACTIVE_COUNT" >> "$LOG_FILE"

if [[ "$ACTIVE_COUNT" -eq 0 ]]; then
  echo '{"decision":"approve"}'; exit 0
fi

if [[ "$ACTIVE_COUNT" -eq 1 ]]; then
  # 단일 활성 run: 자동으로 새 세션에 연결
  STATE_FILE="${ACTIVE_RUNS[0]}"
  RUN_DIR_ABS=$(dirname "$(dirname "$STATE_FILE")")
  RUN_ID=$(jq -r '.run_id' "$STATE_FILE")
  touch "$RUN_DIR_ABS/sessions/${SESSION_ID}"
  echo "[$TIMESTAMP] Auto-recovered: run_id=$RUN_ID → session $SESSION_ID" >> "$LOG_FILE"
  handle_active_state "$STATE_FILE" "$IS_COMPACT" "$CWD"
  exit $?
fi

# ── Step 3: 활성 run 2개 이상 → 수동 선택 필요 ──
echo "[$TIMESTAMP] AMBIGUOUS: $ACTIVE_COUNT active runs" >> "$LOG_FILE"
RUNS_LIST=""
for run_file in "${ACTIVE_RUNS[@]}"; do
  RUN_ID=$(jq -r '.run_id' "$run_file")
  SKILL=$(jq -r '.skill_name' "$run_file")
  GOAL=$(jq -r '.goal // ""' "$run_file")
  RUNS_LIST="${RUNS_LIST}  run_id:${RUN_ID} (${SKILL}) goal:\"${GOAL}\" | "
done

MSG="compact 후 복구 불가: 활성 run이 ${ACTIVE_COUNT}개입니다. 수동으로 run_id를 확인 후 재개하세요. ${RUNS_LIST}"
printf '{"decision":"block","reason":"%s"}' "$MSG"
exit 0
