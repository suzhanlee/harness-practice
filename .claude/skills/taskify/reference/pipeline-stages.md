# pipeline_stage — 태스크 파이프라인 상태 머신

`pipeline_stage`는 `status`와 별개로 각 태스크의 **CI 파이프라인 진행 단계**를 기록한다.
Stop hook(`scripts/mini-stop.sh`의 `mini-execute` case)이 이 필드를 스캔해 LLM에게 다음 행동을 강제한다.

## 전이도

```
not_started
    │  task-executor가 브랜치 체크아웃
    ▼
implementing
    │  validate-tasks: verification 통과
    ├────────────→ failed  (verification 실패 — 재시도 경로)
    ▼                │
validated            │  재시도 시 not_started로 복귀
    │  gh-pr-open    │
    ▼                ▼
pr_opened       not_started (재진입)
    │  gh-pr-review
    ▼
reviewed
    │  사람 머지 → sync-pr-state.sh 감지
    ▼
merged (최종)
```

## 각 단계 · 설정 주체

| stage | 의미 | 설정 주체 | 트리거 |
|---|---|---|---|
| `not_started` | 초기 (taskify가 생성) | taskify | 태스크 생성 시점 |
| `implementing` | 구현 중 | task-executor | 브랜치 체크아웃 직후 |
| `validated` | 검증 통과, PR 미발행 | validate-tasks | verification exit 0 확인 후 |
| `failed` | 검증 실패 | validate-tasks | verification exit ≠ 0 |
| `pr_opened` | PR 생성됨, 리뷰 미제출 | gh-pr-open | `gh pr create` 성공 후 |
| `reviewed` | 인라인 리뷰 제출됨 | gh-pr-review | `gh api .../reviews` 성공 후 |
| `merged` | 사람이 PR 머지 | sync-pr-state.sh | `gh pr view` state=MERGED 감지 |

## 불변 규칙

- 각 전이는 **한 방향**. `reviewed → pr_opened` 같은 역행은 금지.
- 재시도는 `failed → not_started → implementing`로만 돌린다 (직접 점프 금지).
- `pipeline_stage`와 `status`는 독립:
  - `status`는 태스크 구현이 끝났는지 (task-executor가 set)
  - `pipeline_stage`는 PR 파이프라인 상의 위치

## Stop hook 스캔 우선순위

`mini-stop.sh`의 `mini-execute` case는 아래 순서로 스캔하여 가장 먼저 매칭된 것에 대한 강제 액션을 block-reason으로 발행한다:

1. `validated` 태스크 존재 → `/gh-pr-open`
2. `pr_opened` 태스크 존재 → `/gh-pr-review`
3. `failed` 태스크 존재 → `/mini-execute` 재실행
4. `not_started` / `implementing` 태스크 존재 → `/mini-execute` 계속
5. 전부 `reviewed`인데 `pr_state=open` → 머지 게이트 (사람 대기)
6. 전부 `merged` → `/mini-compound`

## 안전장치

`state.json.pipeline_attempts["task-N"].{pr_open|review}` 카운터가 있다.
동일 단계 강제 재시도가 3회 초과되면 에스컬레이션 메시지로 block하고 사용자 개입을 요청한다.

## 신규 단계 추가 시

자가수정(auto-fix), 머지 후 deploy 등을 추가하려면:

1. 이 파일의 전이도/표 업데이트
2. `mini-stop.sh` 스캐너에 우선순위 규칙 추가
3. 해당 단계를 책임지는 주체(스킬/스크립트) 구현
4. 역행 금지 원칙 유지
