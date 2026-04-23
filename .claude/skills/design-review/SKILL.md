---
name: design-review
description: |
  Use when the user says "/design-review [run_id:xxx adr:<path>]".
  Council이 만든 ADR을 입력으로, 계약면(테이블·애그리게이트·인터페이스·모듈 경계·이벤트 스키마)을
  고정 3명 패널(+필요 시 1~2명 추가, 최대 5명)이 단일 라운드로 리뷰한다.
  design-review.md 를 .dev/harness/runs/run-{run_id}/review/ 에 저장하고
  AskUserQuestion으로 승인을 받은 뒤 mini-specify로 넘긴다.
allowed-tools:
  - Agent
  - TeamCreate
  - TeamDelete
  - SendMessage
  - AskUserQuestion
  - Read
  - Grep
  - Glob
  - Write
  - Bash
---

# design-review — 계약면(Contract Surface) 리뷰

## Purpose

`/design-review` 한 번으로 ADR 기반 계약면 리뷰를 구동한다:

1. ADR + 현재 코드베이스 대조면 수집
2. team-lead가 `draft-template.md`로 계약면 초안 작성
3. 고정 3명 패널(+필요 시 추가, 최대 5명)이 **단일 라운드 병렬 리뷰**
4. team-lead가 의견을 수렴해 `design-review-template.md` 포맷으로 최종 md 작성
5. AskUserQuestion 2지선다로 사용자 승인 → mini-specify로 전달

포맷 상세는 reference 파일을 참조한다:
- `.claude/skills/design-review/reference/design-review-template.md` — 최종 산출물
- `.claude/skills/design-review/reference/draft-template.md` — 패널 리뷰 대상 초안
- `.claude/skills/design-review/reference/opinion-template.md` — 패널리스트 의견 회신
- `.claude/skills/design-review/reference/personas.md` — 고정 3명 + 예비 2명 역할 정의

---

## Workflow

### Pre-phase: Args 파싱 및 경로 해석

```bash
RUN_ID=$(echo "$ARGS" | grep -o 'run_id:[^ ]*' | cut -d: -f2)
ADR_FILE=$(echo "$ARGS" | grep -o 'adr:[^ ]*' | cut -d: -f2)
```

**run_id가 있는 경우** (mini-harness 체인):
```bash
STATE_FILE=".dev/harness/runs/run-${RUN_ID}/state/state.json"
REVIEW_DIR=$(jq -r '.paths.review_dir' "$STATE_FILE")
ADR_DIR=$(jq -r '.paths.adr_dir' "$STATE_FILE")
# ADR_FILE이 없으면 ADR_DIR에서 가장 최근 md 선택
```

**run_id가 없는 경우** (수동 호출):
```bash
REVIEW_DIR=".dev/review"
```

이후 모든 단계에서 `$REVIEW_DIR`을 출력 경로로 사용한다.

---

### Step 1: ADR + 코드베이스 대조면 수집

단일 메시지에서 병렬로 수집한다.

**ADR 로드**: `$ADR_FILE`을 Read해 아래 섹션을 추출한다:
- `## 결정` / `## 채택된 아키텍처`
- `## YAGNI 경계`
- `## 거부된 대안`

**코드베이스 대조면** (Glob/Grep 병렬):
| 항목 | 수집 방법 |
|------|----------|
| 기존 애그리게이트 루트 | `Glob` 도메인 모델 경로 (예: `kiosk/domain/models/*.py`) + `Grep` 주요 클래스·불변식 |
| 기존 리포지토리 인터페이스 | `Glob` repositories 경로 + 주요 시그니처 수집 |
| 기존 이벤트 스키마 | `Grep` `DomainEvent|Event` 패턴으로 탐지 (없으면 "없음") |
| 모듈 import 방향 샘플 | `Grep -r "from <module>"` 으로 샘플 수집 |
| 네이밍 컨벤션 샘플 | 기존 엔티티/이벤트/리포 이름 3~5개 |

수집 결과를 다음 형태로 정리해 team-lead(= 본 skill) 내부 컨텍스트로 보유한다:

```
📋 대조면 수집
- aggregates: [Order, MenuItem, Payment]
- repositories: [OrderRepository, MenuItemRepository, PaymentRepository]
- existing events: (없음)
- naming: snake_case 파일, PascalCase 클래스
```

---

### Step 2: 계약면 초안 작성

team-lead가 ADR + 대조면을 바탕으로 `.claude/skills/design-review/reference/draft-template.md` 포맷에 맞춰 **초안**을 만든다. 이 초안은 패널 리뷰의 **대상**이며, 파일로 저장하지 않고 다음 Step의 Agent 프롬프트 본문으로 전달한다.

초안은 아래 5개 섹션을 순서대로 포함해야 한다:

1. 테이블 변경 (DB 변경 없으면 "해당 없음" 한 줄)
2. 애그리게이트 / VO / 바운디드 컨텍스트
3. 인터페이스 스키마 (시그니처·예외·반환 타입)
4. 모듈 경계 / 의존성 방향 (mermaid 다이어그램 필수)
5. 이벤트 스키마 (없으면 "해당 없음")

---

### Step 3: 패널 구성

```
TeamCreate(team_name: "design-review", description: "<ADR 제목>")
```

**고정 3명 (필수)** — `reference/personas.md` 정의:
- `api-shape-reviewer`
- `integration-reviewer`
- `test-surface-reviewer`

**선택 추가 (최대 2명, 총 5명 상한)** — ADR 주제에 따라 team-lead가 판단해 포함:
- 이벤트가 3개 이상 등장 → `event-schema-reviewer`
- 테이블 변경 섹션이 비어있지 않음 → `persistence-reviewer`

---

### Step 4: Phase 1 — 단일 라운드 병렬 의견 수집

**단일 메시지에서 모든 패널리스트를 `Agent`로 병렬 spawn** (`run_in_background=True`).

각 Agent prompt에 반드시 포함할 항목:

| 항목 | 내용 |
|------|------|
| 역할 선언 | "당신은 [리뷰어명] 입니다. 아래 역할 정의를 따릅니다." (personas.md에서 해당 부분 복사) |
| ADR 요약 | ADR의 `## 결정` 섹션 전체 |
| 초안 | Step 2에서 만든 draft 전체 |
| 대조면 | Step 1에서 수집한 aggregates/repositories/events/naming 요약 |
| 출력 포맷 | `.claude/skills/design-review/reference/opinion-template.md` 포맷 그대로 작성 |
| 행동 지시 | 의견 작성 후 `SendMessage(to: "team-lead", message: <의견 전문>)` 실행 후 대기 |

team-lead는 모든 패널리스트의 SendMessage를 수신한 후 Step 5로 진행한다.

**Rebuttal/shift 루프는 없다.** council과 달리 design-review는 단일 라운드다.

---

### Step 5: Phase 2 — 수렴 및 최종 md 작성

team-lead가 모든 의견을 받아 `.claude/skills/design-review/reference/design-review-template.md` 포맷으로 최종 문서를 작성한다.

파일명: `$REVIEW_DIR/YYYY-MM-DD-{slug}.md`
- `slug`: ADR 파일명에서 날짜 앞부분을 제외하고 따옴. 예: `2026-04-21-kds-domain-event-architecture.md` → `kds-domain-event-architecture`
- 날짜: 실행 당일

```bash
mkdir -p "$REVIEW_DIR"
```

Write로 저장한다.

**패널 요약 섹션**에는 각 리뷰어의 의견에서 "승인/반대" + "핵심 지적 1개"를 간결히 요약해 넣는다.

---

### Step 6: TeamDelete

모든 teammates에게 shutdown 신호 병렬 전송:
```
SendMessage(to: "<api-shape-reviewer>", message: {"type": "shutdown_request"})
SendMessage(to: "<integration-reviewer>", message: {"type": "shutdown_request"})
SendMessage(to: "<test-surface-reviewer>", message: {"type": "shutdown_request"})
# (추가 패널리스트가 있으면 동일하게)
```

모든 `teammate_terminated` 이벤트 수신 후 `TeamDelete()` 실행.

---

### Step 7: 승인 게이트 — AskUserQuestion

저장한 design-review.md 의 경로와 요지를 텍스트로 출력한 뒤 AskUserQuestion을 호출한다.

```
📋 design-review 완료
───────────────────────────────────────
파일: {REVIEW_DIR}/{filename}.md
섹션 요약:
  1. 테이블 변경: {N건 / 해당 없음}
  2. 애그리게이트/VO: {N개}
  3. 인터페이스: {N개}
  4. 모듈 경계: {다이어그램 포함}
  5. 이벤트: {N개 / 해당 없음}
패널 결과: 승인 {X}/{총} · 수정 필요 {Y}/{총}
───────────────────────────────────────
```

AskUserQuestion 호출:
- 질문: `"이 design-review 대로 mini-specify 진행할까요?"`
- header: `"Proceed?"`
- 옵션:
  - **"이대로 진행"** — description: `"현재 design-review.md 를 최종으로 확정하고 mini-specify 단계로 넘어갑니다."`
  - **"수정 필요"** — description: `"design-review.md 를 수정/보완합니다. 피드백을 반영해 재작성 후 다시 승인을 받습니다."`

사용자가 **"이대로 진행"** 을 선택하면 Step 8로 진행한다.
**"수정 필요"** (또는 Other)를 선택한 경우, 피드백을 반영해 design-review.md 를 재작성하고 Step 7을 반복한다.

---

### Step 8: 완료 보고

```
✓ design-review 완료
  - 파일: {REVIEW_DIR}/{filename}.md
  - 패널: {리뷰어 목록}
  - 다음: /mini-specify (stop hook이 자동 라우팅)
```

Stop 훅이 `state.json`을 읽어 다음 스킬(`mini-specify`)을 `review:<path>` 인자와 함께 트리거한다.

---

## Rules

- **단일 라운드만 수행한다.** rebuttal-response-template 루프를 쓰지 않는다. 더 깊은 토론이 필요하면 council을 다시 돌리는 것이 맞다.
- **패널은 최소 3명, 최대 5명.** 고정 3명(api-shape, integration, test-surface)은 주제와 무관하게 항상 포함한다.
- **Write는 Step 5 이후에만 실행**. 초안은 파일로 저장하지 않는다.
- **AskUserQuestion에서 "이대로 진행" 선택 전에는 state.json을 end로 바꾸지 않는다.** 승인 게이트가 실질적 완료선이다.
- **TeamDelete 필수.** Step 6 완료 없이 workflow 종료 금지.
- 산출물은 반드시 `$REVIEW_DIR`에 저장한다 (run_id 있으면 `.dev/harness/runs/run-{id}/review/`, 없으면 `.dev/review/`).
- mermaid 다이어그램은 섹션 4(모듈 경계)와 섹션 5(이벤트)에 **반드시** 포함한다. 테이블만으로는 통과하지 않는다.
- ADR 파일은 Read만 하며 수정하지 않는다. design-review가 ADR 결정을 뒤집는 경우는 없다 — 계약 "면"만 확정한다.
