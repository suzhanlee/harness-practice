#!/bin/bash
# harness-lib.sh — 공통 헬퍼 함수 (mini-harness hook 스크립트에서 source)

# resolve_run_state CWD SESSION_ID
# → 해당 세션의 STATE_FILE 절대 경로를 stdout에 출력
# → 포인터가 없으면 빈 문자열 출력
resolve_run_state() {
  local cwd="$1"
  local session_id="$2"
  local runs_dir="$cwd/.dev/harness/runs"

  for run_dir in "$runs_dir"/run-*/; do
    [[ -f "$run_dir/sessions/$session_id" ]] || continue
    local state_file="$run_dir/state/state.json"
    [[ -f "$state_file" ]] && echo "$state_file" && return 0
  done
  echo ""
}

# generate_run_id
# → yyyymmdd-HHMMSS-{4hex} 형식의 run_id를 stdout에 출력 (Windows 호환)
generate_run_id() {
  local ts
  ts=$(date -u +"%Y%m%d-%H%M%S")
  local rand
  rand=$(printf '%04x' $((RANDOM * RANDOM % 65536)))
  echo "${ts}-${rand}"
}

# ============================================================
# Pipeline stage 헬퍼 (Option A 상태 머신)
# ============================================================

# set_pipeline_stage SPEC_PATH TASK_ID STAGE
# → spec.json의 해당 task에 pipeline_stage 설정
set_pipeline_stage() {
  local spec="$1"
  local tid="$2"
  local stage="$3"
  [[ -f "$spec" ]] || return 1
  jq --arg tid "$tid" --arg s "$stage" \
    '.tasks |= map(if .task_id == $tid then .pipeline_stage = $s else . end)' \
    "$spec" > "${spec}.tmp" && mv "${spec}.tmp" "$spec"
}

# increment_attempt STATE_FILE TASK_ID STAGE_KEY
# → state.json.pipeline_attempts["task_id"]["stage_key"] += 1
# → 현재 카운트를 stdout에 출력
increment_attempt() {
  local state="$1"
  local tid="$2"
  local key="$3"
  [[ -f "$state" ]] || { echo 0; return 1; }
  jq --arg tid "$tid" --arg k "$key" \
    '(.pipeline_attempts[$tid][$k] // 0) as $n
     | .pipeline_attempts[$tid][$k] = ($n + 1)' \
    "$state" > "${state}.tmp" && mv "${state}.tmp" "$state"
  jq -r --arg tid "$tid" --arg k "$key" \
    '.pipeline_attempts[$tid][$k] // 0' "$state"
}

# attempt_exceeded STATE_FILE TASK_ID STAGE_KEY LIMIT
# → exit 0 if count > LIMIT, else exit 1
attempt_exceeded() {
  local state="$1"
  local tid="$2"
  local key="$3"
  local limit="$4"
  local n
  n=$(jq -r --arg tid "$tid" --arg k "$key" \
    '.pipeline_attempts[$tid][$k] // 0' "$state" 2>/dev/null || echo 0)
  [[ "$n" -gt "$limit" ]]
}

# reset_attempt STATE_FILE TASK_ID STAGE_KEY
# → 카운터 리셋 (단계 성공 시 호출)
reset_attempt() {
  local state="$1"
  local tid="$2"
  local key="$3"
  [[ -f "$state" ]] || return 0
  jq --arg tid "$tid" --arg k "$key" \
    'if .pipeline_attempts[$tid] then .pipeline_attempts[$tid] |= (del(.[$k])) else . end' \
    "$state" > "${state}.tmp" && mv "${state}.tmp" "$state"
}

# emit_escalation TASK_ID REASON
# → Stop hook이 사용할 block-reason JSON을 stdout에 출력 후 exit 0
emit_escalation() {
  local tid="$1"
  local reason="$2"
  local msg="⛔ ${tid}: ${reason}. 수동 개입 필요 — spec.json의 pipeline_stage를 수정하거나 state.json.pipeline_attempts.${tid} 를 삭제 후 재개하세요."
  echo "{\"decision\":\"block\",\"reason\":\"$msg\"}"
}
