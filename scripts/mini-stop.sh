#!/bin/bash
# mini-stop.sh — Stop hook for mini-harness orchestration + compound guard
# Orchestrates skill chain via run-scoped state; fallback to original compound guard

INPUT=$(cat)
_RAW_CWD=$(echo "$INPUT" | jq -r '.cwd')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // empty')

# harness-lib.sh source 전에 normalize_cwd 인라인 처리
if [[ "${_RAW_CWD:1:1}" == ":" ]]; then
  _drive="${_RAW_CWD:0:1}"; _rest="${_RAW_CWD:2}"; _rest="${_rest//\\/\/}"
  CWD="/${_drive,,}${_rest}"
else
  CWD="$_RAW_CWD"
fi

SESSION_FILE="$CWD/.mini-harness/session/learnings.json"

source "$CWD/scripts/harness-lib.sh"

# ── run state 파일 resolve ──
STATE_FILE=$(resolve_active_state "$CWD" "$SESSION_ID")

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
      echo "{\"decision\":\"block\",\"reason\":\"gh-issue-sync 스킬을 실행하세요. args: \\\"run_id:$RUN_ID\\\"\"}"
      exit 0
      ;;
    gh-issue-sync)
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "{\"decision\":\"block\",\"reason\":\"mini-execute 스킬을 실행하세요. args: \\\"run_id:$RUN_ID\\\"\"}"
      exit 0
      ;;
    mini-execute)
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"

      # ── 상태 스캐너: spec.json을 보고 다음 강제 액션 결정 (Option A 파이프라인) ──
      SPEC_REL=$(jq -r '.paths.spec // empty' "$STATE_FILE")
      SPEC="$CWD/$SPEC_REL"
      if [[ -z "$SPEC_REL" || ! -f "$SPEC" ]]; then
        # spec 없음 → 바로 compound
        echo "{\"decision\":\"block\",\"reason\":\"mini-compound 스킬을 실행하세요. args: \\\"run_id:$RUN_ID\\\"\"}"
        exit 0
      fi

      ATTEMPT_LIMIT=3

      # 우선순위 1: validated → gh-pr-open 강제
      TID=$(jq -r '[.tasks[] | select(.pipeline_stage == "validated")] | .[0].task_id // empty' "$SPEC")
      if [[ -n "$TID" ]]; then
        COUNT=$(increment_attempt "$STATE_FILE" "$TID" "pr_open")
        if attempt_exceeded "$STATE_FILE" "$TID" "pr_open" "$ATTEMPT_LIMIT"; then
          emit_escalation "$TID" "gh-pr-open ${ATTEMPT_LIMIT}회 초과"
          exit 0
        fi
        echo "{\"decision\":\"block\",\"reason\":\"gh-pr-open 스킬을 실행하세요. args: \\\"run_id:$RUN_ID task_id:$TID\\\" (시도 $COUNT/$ATTEMPT_LIMIT)\"}"
        exit 0
      fi

      # 우선순위 2: pr_opened → gh-pr-review 강제
      TID=$(jq -r '[.tasks[] | select(.pipeline_stage == "pr_opened")] | .[0].task_id // empty' "$SPEC")
      if [[ -n "$TID" ]]; then
        COUNT=$(increment_attempt "$STATE_FILE" "$TID" "review")
        if attempt_exceeded "$STATE_FILE" "$TID" "review" "$ATTEMPT_LIMIT"; then
          emit_escalation "$TID" "gh-pr-review ${ATTEMPT_LIMIT}회 초과"
          exit 0
        fi
        echo "{\"decision\":\"block\",\"reason\":\"gh-pr-review 스킬을 실행하세요. args: \\\"run_id:$RUN_ID task_id:$TID\\\" (시도 $COUNT/$ATTEMPT_LIMIT)\"}"
        exit 0
      fi

      # 우선순위 3: failed 또는 미완료(not_started/implementing) → mini-execute 재진입
      PENDING=$(jq '[.tasks[] | select(
          .pipeline_stage == "failed"
          or (.pipeline_stage // "not_started") == "not_started"
          or .pipeline_stage == "implementing"
        )] | length' "$SPEC")
      if [[ "${PENDING:-0}" -gt 0 ]]; then
        echo "{\"decision\":\"block\",\"reason\":\"mini-execute 스킬을 계속 실행하세요 (${PENDING}개 미완료). args: \\\"run_id:$RUN_ID\\\"\"}"
        exit 0
      fi

      # 우선순위 4: 전부 reviewed이지만 open PR 존재 → 사람 머지 대기
      OPEN_PRS=$(jq '[.tasks[] | select(.pr_state == "open")] | length' "$SPEC" 2>/dev/null || echo 0)
      if [[ "${OPEN_PRS:-0}" -gt 0 ]]; then
        MSG="⏸ ${OPEN_PRS}개 PR 머지 대기 중. 머지 후 'bash scripts/sync-pr-state.sh $RUN_ID' → '/mini-compound run_id:$RUN_ID' 순으로 실행하세요."
        echo "{\"decision\":\"block\",\"reason\":\"$MSG\"}"
        exit 0
      fi

      # 우선순위 5: 전부 merged → mini-compound
      echo "{\"decision\":\"block\",\"reason\":\"mini-compound 스킬을 실행하세요. args: \\\"run_id:$RUN_ID\\\"\"}"
      exit 0
      ;;
    gh-pr-open)
      # gh-pr-open 성공 시 (pipeline_stage=pr_opened 기록됨) → pr_open 카운터 리셋, mini-execute case로 재진입
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts | .skill_name = "mini-execute"' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      # 직전 태스크의 카운터 리셋은 gh-pr-open 내부에서 수행 권장 (여기선 스킵)
      echo "{\"decision\":\"block\",\"reason\":\"mini-execute 상태 스캔 재개. args: \\\"run_id:$RUN_ID\\\"\"}"
      exit 0
      ;;
    gh-pr-review)
      jq --arg ts "$TIMESTAMP" '.status = "end" | .timestamp = $ts | .skill_name = "mini-execute"' \
        "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
      echo "{\"decision\":\"block\",\"reason\":\"mini-execute 상태 스캔 재개. args: \\\"run_id:$RUN_ID\\\"\"}"
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
