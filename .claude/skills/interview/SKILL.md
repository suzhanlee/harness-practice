---
name: interview
description: |
  Use when the user says "/interview [run_id:xxx]".
  Socratic questioning to clarify requirements before council.
  Asks 6 structured questions across 3 rounds, synthesizes answers into
  interview.json, and confirms with user via AskUserQuestion before saving.
allowed-tools:
  - AskUserQuestion
  - Write
  - Read
  - Bash
---

# interview — 소크라테스 문답 기반 요구사항 구체화

## Purpose

`/interview run_id:xxx` 한 번으로 goal을 소크라테스 문답법으로 구체화한다:
1. 3라운드(6개 질문)로 요구사항을 탐색
2. 답변을 종합해 `refined_goal` 합성
3. AskUserQuestion으로 사용자에게 확인
4. 승인 후 `interview.json` 저장

---

## Args 파싱

```bash
RUN_ID=$(echo "$ARGS" | grep -o 'run_id:[^ ]*' | cut -d: -f2)
STATE_FILE=".dev/harness/runs/run-${RUN_ID}/state/state.json"
GOAL=$(jq -r '.goal' "$STATE_FILE")
INTERVIEW_PATH=$(jq -r '.paths.interview' "$STATE_FILE")
```

State 파일에서 원래 goal을 읽어 문답의 출발점으로 사용한다.

---

## Workflow

### Step 0: 시작 출력

```
🎯 interview 시작
  goal: "{GOAL}"
  소크라테스 문답 3라운드를 통해 요구사항을 구체화합니다.
```

---

### 라운드 1 — 현재 상태 탐색

> 핵심 질문: "지금 어떤 상황인가?" — 가정을 드러내는 Socratic 출발점

AskUserQuestion 호출 (2개 질문):

**Q1**: "지금 이 기능 없이 어떤 상황인가요? 현재 어떻게 해결하고 있나요?"
- 수동으로 처리 중 — 사람이 직접 작업하거나 관리하고 있음
- 다른 기능으로 우회 중 — 원래 목적과 다른 기능을 억지로 사용 중
- 아예 불가능한 상태 — 현재 이 작업 자체를 할 수 없음
- 신규 기능(현재 해결 불필요) — 완전히 새로운 영역으로 현재 해결할 필요 없음

**Q2**: "이 기능이 필요하다고 느끼게 된 가장 직접적인 계기는?"
- 사용자 불만/불편 보고 — 실제 사용자가 문제를 겪고 있다는 피드백 수신
- 비즈니스 기회 발견 — 이 기능이 있으면 새로운 가치를 창출할 수 있음
- 기술적 한계 인식 — 현재 구조가 이 기능을 지원하지 못함을 발견
- 설계 개선 의도 — 기존 코드/구조를 더 나은 방향으로 바꾸고 싶음

---

### 라운드 2 — 원하는 변화 명확화

> 핵심 질문: "이후 어떤 상태가 되어야 하는가?"

AskUserQuestion 호출 (2개 질문):

**Q3**: "이 기능이 완성된 후, 지금과 달라지는 가장 중요한 점은?"
- 사용자가 직접 할 수 있게 됨 — 현재 불가능하거나 어려운 작업을 사용자가 스스로 처리
- 처리 속도/정확도 향상 — 기존보다 빠르거나 더 정확하게 처리됨
- 코드 구조가 단순해짐 — 복잡한 우회로 없이 깔끔한 구조로 개선됨
- 새로운 비즈니스가 가능해짐 — 지금은 불가능한 사용 시나리오가 열림

**Q4**: "성공을 어떻게 측정할 수 있나요?"
- 특정 기능이 동작함 — 명시된 시나리오를 클릭/입력으로 실행 가능
- 테스트 케이스 통과 — 작성된 테스트가 모두 green
- 특정 지표 달성 — 응답 시간, 에러율 등 수치 목표 달성
- 사용자 흐름 전체 완성 — 시작부터 끝까지 전체 사용자 여정이 막힘 없이 동작

---

### 라운드 3 — 경계와 제약 확정

> 핵심 질문: "변하면 안 되는 것은 무엇인가?" — 범위 과잉을 막는 Socratic 제동

AskUserQuestion 호출 (2개 질문):

**Q5**: "이번 구현에서 명시적으로 제외할 것은?"
- UI/프론트엔드 제외 — 백엔드 로직만 구현, 화면 변경 없음
- 외부 API 연동 제외 — 외부 서비스 호출/연결 없이 내부 처리만
- 기존 인터페이스 변경 금지 — 현재 퍼블릭 API/인터페이스는 그대로 유지
- 범위 제한 없음 — 필요한 모든 변경 허용

**Q6**: "반드시 지켜야 할 설계 원칙이나 제약은?"
- DDD 레이어 구조 유지 — domain/application/infrastructure 경계 준수
- 기존 테스트 통과 유지 — 현재 passing 테스트를 깨지 않음
- 성능 제약 있음 — 응답 시간이나 메모리 사용에 제한
- 특별한 제약 없음 — 설계 자유도 있음

---

### Step 4: refined_goal 합성

6개 답변을 종합해 아래 포맷으로 `refined_goal`을 작성한다:

```
[동사] [무엇을] [누구를 위해 / 어떤 문제를 해결하기 위해]
```

**합성 규칙**:
- Q1/Q2 답변 → `problem` 필드 (현재 상태 + 계기)
- Q3 답변 → `refined_goal`의 핵심 동사/목적어
- Q4 답변 → `success_criteria` 필드
- Q5 답변 → `out_of_scope` 필드
- Q6 답변 → `constraints` 필드
- Q2의 "사용자 불만" or Q3의 "사용자가 직접 할 수 있게 됨" → `users`에 "최종 사용자" 포함

**예시**:
- original_goal: "장바구니 기능 추가"
- refined_goal: "주문 전 수량 조정 불가로 불편을 겪는 고객을 위해 PENDING Order에 상품 수량 변경 기능 추가"

---

### Step 5: AskUserQuestion 확인

합성 결과를 아래 형식으로 텍스트 출력 후 AskUserQuestion으로 확인을 받는다:

```
📋 요구사항 합성 결과
───────────────────────────────────────
original_goal: "{GOAL}"
refined_goal:  "{refined_goal}"

problem:          "{Q1+Q2 종합}"
users:            ["{대상}"]
success_criteria: ["{Q4 답변}"]
out_of_scope:     ["{Q5 답변}"]
constraints:      ["{Q6 답변}"]
───────────────────────────────────────
```

AskUserQuestion 호출:
- 질문: "이 요구사항으로 council을 진행할까요?"
- 옵션:
  - "이대로 진행" — refined_goal과 모든 필드가 정확함, interview.json 저장 후 council로 이동
  - "수정 필요" — 일부 내용을 고치고 싶음 (Other로 피드백 입력)

사용자가 "이대로 진행"을 선택하면 Step 6으로 진행한다.
"수정 필요"(또는 Other)를 선택한 경우 피드백을 반영해 refined_goal을 재합성한 뒤 Step 5를 반복한다.

---

### Step 6: interview.json 저장

```bash
mkdir -p "$REQ_DIR"
```

아래 스키마로 `$INTERVIEW_PATH`에 Write한다:

```json
{
  "run_id": "...",
  "original_goal": "...",
  "refined_goal": "...",
  "problem": "...",
  "users": ["..."],
  "success_criteria": ["..."],
  "out_of_scope": ["..."],
  "constraints": ["..."]
}
```

Write 완료 후 출력:

```
✓ interview 완료
  - refined_goal: "{refined_goal}"
  - 저장: {INTERVIEW_PATH}
```

---

## Rules

- 라운드는 반드시 순서대로 진행한다 (1 → 2 → 3). 라운드 간 선행 답변을 다음 질문 컨텍스트에 활용한다.
- AskUserQuestion의 "Other" 옵션을 통해 사용자가 직접 입력한 경우, 그 내용을 JSON에 그대로 반영한다.
- Step 5의 AskUserQuestion 전에 반드시 refined_goal을 합성해야 한다. 미합성 상태로 확인 진입 금지.
- Write는 반드시 Step 5의 AskUserQuestion에서 "이대로 진행" 선택 후에만 실행한다.
- EnterPlanMode/ExitPlanMode는 이 스킬에서 사용하지 않는다. 확인은 AskUserQuestion으로만 처리한다.
- run_id가 없으면(수동 호출) `INTERVIEW_PATH=".dev/harness/interview.json"`을 기본값으로 사용한다.
  (`paths.interview` 반환값: `.dev/harness/runs/run-{id}/interview/interview.json`)
