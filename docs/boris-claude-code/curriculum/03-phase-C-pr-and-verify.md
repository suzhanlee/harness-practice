# Phase C — PR + 검증 통합 흐름 (Steps 12–17)

이 phase 의 목표는 **worktree 의 commit 들** 을 **메인 main 에 안전 통합** 까지 흐름화. 충돌 처리·시각/행동 검증·@claude GitHub Action·fan-out·`/go` 자동 시퀀스 모두.

Phase B 가 *commit 까지* 만 다뤘다면, 이 phase 가 *통합과 검증* 을 닫는다. 끝나면 worktree 의 종료가 단일 슬래시 명령 (`/go`) 으로 처리되는 상태가 된다.

---

## Step 12. PR-per-worktree 첫 머지 (단순)

### 핵심
분리된 작업이 *통합으로 닫힐 때* 비로소 PR 워크플로우가 된다.

### 전제
Step 11 — 3-worktree + analysis 안정

### 목표 역량
각 worktree 의 commit 시리즈를 GitHub PR 로 만들어 main 으로 머지. 충돌 없는 단순 케이스만 (충돌은 다음 step).

### 실습

#### 1. PR 생성 — `gh-pr-open` 활용
이미 `.claude/skills/gh-pr-open/` 운영 중이므로:
```
worktree A 안에서:
/gh-pr-open
```

PR description 자동 생성 — Step 2 의 spec-prompt 첫 메시지 + 변경 요약 + acceptance criteria 자동 매핑.

#### 2. 머지 순서
- DAG 의 *루트 노드* 에 해당하는 worktree 부터 머지 (Step 5 의 dependency 그래프 참조)
- 머지 후 다른 worktree 들은 `git pull --rebase origin main` (Step 9 의 SessionStart 훅이 자동)

#### 3. PR description 의 acceptance criteria
Step 2 에서 설정한 acceptance criteria 가 PR description 에 *그대로* 들어가야 한다 — 리뷰어가 그걸 보고 검증.

### 빈도
**2주 동안 worktree 발 PR ≥3건 머지**

### Eval
- 3건 모두 revert 없이 main 에 머지
- 3건 모두 PR description 에 acceptance criteria 명시
- 학습 일지에 *PR 워크플로우 첫 경험에서 가장 어색한 부분* 1줄 기록

### 이 step 에서 얻은 것
worktree 가 *작업 단위* 일 뿐 아니라 *PR 단위* 임을 체감. 1 worktree = 1 PR 의 깔끔한 매핑.

### 다음 step 으로의 다리
3건 모두 충돌 없는 단순 케이스라면 운이 좋은 것. 자연 발생할 충돌을 *피하지 말고 학습* 해야 한다.

---

## Step 13. 충돌 처리 — Claude 에 rebase 위임

### 핵심
충돌 해결도 위임 가능, 학습자는 *검토만*.

### 전제
Step 12 — 단순 PR 머지 경험 (충돌 패턴 인식 가능)

### 목표 역량
PR 충돌 시 학습자가 직접 rebase 안 함. 해당 worktree 에서 정형 prompt 로 위임:
> *"main 을 rebase 해주고, 충돌은 두 변경 의도를 모두 보존하는 방향으로 해결해줘. 의미적으로 의심스러운 부분은 따로 표시해서 알려줘."*

학습자 역할: rebase 결과 *검토* + 의심 표시 부분만 직접 판단.

### 실습

#### 1. 의도적 충돌 1건
- worktree A 와 B 가 같은 파일 (예: `kiosk/cli.py` 의 `build_dependencies()`) 을 동시에 수정
- A 머지 → B 에서 충돌 발생
- Claude 에게 rebase 위임

#### 2. 자연 발생 충돌 4건
- Phase B Step 11 의 4-세션 운영 중 자연 발생할 것
- 발생할 때마다 위임

#### 3. 위임 결과 검토 체크리스트
- 두 변경의 *의도* 가 모두 보존됐는가?
- 새로운 logical bug 가 생기지 않았는가?
- 테스트가 여전히 통과하는가?

### 빈도
**2주 동안 충돌 해결 5건** (의도 1 + 자연 4)

### Eval
- 5건 모두 학습자가 직접 rebase command 실행 0회 (학습자의 git 명령 history 에 `git rebase` 없음)
- 사후 동질화 commit 0 (Claude 의 rebase 결과를 학습자가 다시 다듬는 commit 없음)
- 학습 일지에 *Claude 가 못 푼 충돌 패턴* 식별 ≥1건 (있으면 그 케이스를 prompt 에 미리 가이드 추가)

### 이 step 에서 얻은 것
git 작업조차 *위임 가능한 일* 임을 체감. Claude 가 못 푸는 부분만 학습자가 본다는 *역할 분담* 명확화.

### 다음 step 으로의 다리
PR 머지가 흐름이 됐지만 *기능* 통과 (pytest) 는 *행동* 통과 (실제 실행) 가 아니다. Boris 가 강조하는 *"the most important thing"* 이 다음 step.

---

## Step 14. 시각·행동 검증 — CLI 실행·관찰·반복

### 핵심
**pytest 통과는 기능 검증이지 행동 검증이 아니다.**

Boris: *"Probably the most important thing to get great results out of Claude Code — give Claude a way to verify its work. If Claude has that feedback loop, it will 2-3x the quality of the final result."*

### 전제
Step 13 — PR 흐름이 안정된 후 검증을 추가하는 게 비용 효율 (불안정한 PR 흐름 위에 검증 추가는 디버깅 지옥).

### 목표 역량
Claude 가 자신의 변경을 *실제로 실행* 하고 결과를 관찰할 수 있게:
- 키오스크는 CLI 라 `python cli.py` 실행 + 사용자 입력 시뮬레이션 + 출력 검증
- 향후 UI 추가 시 Chrome extension / Playwright 동등물

### 실습

#### 1. `.claude/commands/observe-run.md` 만들기
```markdown
---
description: Run kiosk CLI with simulated input and observe behavior
allowed_tools: Bash, Edit, Read
---
다음 시나리오를 `subprocess` 또는 `pexpect` 로 자동 실행:

1. `python cli.py` 시작
2. 메뉴 진입 → 첫 화면 출력 검증
3. 1번 (메뉴 보기) → 메뉴 목록 출력 검증
4. 2번 (장바구니 추가) → 메뉴 ID 입력 → 수량 입력 → 추가 성공 메시지 검증
5. 5번 (체크아웃) → 주문 확정 메시지 검증
6. 6번 (결제) → 결제 방법 입력 → 결제 완료 메시지 검증
7. 7번 (종료) → graceful exit 검증

각 단계의 출력을 캡처하고 expected 와 비교. 불일치 시 actual + expected 둘 다 출력.

PR description 에 attach 가능한 형식으로 결과 요약.
```

#### 2. 새 feature PR 마다 observe-run 결과를 PR description 에 첨부
```
## 행동 검증 (observe-run)
- [x] 메뉴 진입 ✓
- [x] 메뉴 목록 출력 ✓
- [x] 장바구니 추가 ✓
- [x] 체크아웃 ✓
- [x] 결제 ✓
- [x] graceful exit ✓
```

#### 3. 향후 UI 추가 시
같은 패턴으로 Playwright 또는 Chrome extension — `.claude/commands/observe-ui.md` 로 확장.

### 빈도
**2주 동안 observe-run 통과 ≥5 PR**

### Eval
- 5 PR 모두 description 에 행동 검증 trace 첨부
- observe-run 이 잡은 버그 ≥1건 (pytest 는 통과했지만 실제 실행 시 fail — 예: CLI 의 입력 prompt 변경, exit code 불일치, 출력 포맷 깨짐)
- 학습 일지에 *pytest vs observe-run 의 차이* 가 잡은 버그 카테고리 분석 1회

### 이 step 에서 얻은 것
*행동 검증의 차원* 추가. 단위 테스트 통과는 시작이지 끝이 아니다 — 실제 실행이 검증의 *최종 심급*.

### 다음 step 으로의 다리
PR 의 품질이 행동 검증 통과까지 올라갔으니, 이제 PR *리뷰 자체가 시스템을 개선* 할 수 있는 단계. Compounding Engineering 의 직접 구현.

---

## Step 15. PR 리뷰 → @claude → CLAUDE.md GitHub Action

### 핵심
리뷰 자체가 시스템 개선 — Boris 의 **Compounding Engineering**.

### 전제
- Step 3 — CLAUDE.md 즉시 추가 습관
- Step 12 — PR 흐름
- Step 14 — 검증으로 PR 품질이 충분히 높아졌음

### 목표 역량
PR comment 의 `@claude` → GitHub Action 이 (1) PR diff + 리뷰 코멘트를 읽고 (2) 패턴화 가능한 항목을 CLAUDE.md 에 자동 commit + push.

### 실습

#### 1. `.github/workflows/claude-md-update.yml` 작성
```yaml
name: Update CLAUDE.md from PR review

on:
  issue_comment:
    types: [created]

jobs:
  update-claude-md:
    if: contains(github.event.comment.body, '@claude') && github.event.issue.pull_request != null
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main
          fetch-depth: 0
      
      - name: Get PR diff and comments
        run: |
          gh pr diff ${{ github.event.issue.number }} > /tmp/pr.diff
          gh pr view ${{ github.event.issue.number }} --comments --json comments > /tmp/pr-comments.json
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Run Claude Code to extract patterns
        run: |
          claude -p "다음 PR diff 와 리뷰 코멘트를 읽고, 패턴화 가능한 학습 항목을 추출해 CLAUDE.md 에 한 줄씩 추가해줘. 코멘트가 일회성 의견이면 무시. 반복될 만한 패턴만." \
            --add-dir . --bare
      
      - name: Commit and push
        run: |
          git config user.name "claude-bot"
          git config user.email "noreply@anthropic.com"
          git add CLAUDE.md
          git diff --staged --quiet || git commit -m "compound: PR #${{ github.event.issue.number }} 리뷰 학습 반영"
          git push
```

#### 2. 테스트 PR 1건으로 검증
- 의도적으로 patternable 코멘트 작성 (예: *"여기 Money 객체가 amount 직접 접근하고 있는데, 이전 PR 에서도 봤던 패턴이야. value object 의 method 로 캡슐화해야 함"*)
- `@claude` 트리거 → action 작동 → CLAUDE.md 갱신 commit 확인

#### 3. 학습자가 매주 PR 리뷰에 *의도적으로* 반복 패턴 코멘트
4주간 매주 ≥3건의 `@claude` 트리거 발생.

### 빈도
**1달 동안 매주 ≥3 자동 갱신** (총 ≥12건)

### Eval
- 자동 갱신 commit 누적 ≥12건 (`git log --author="claude-bot" -- CLAUDE.md`)
- 동일 패턴 PR 코멘트 재발률 50%+ 감소 (이전 자동 갱신 항목이 적용된 후의 동일 패턴 발생 빈도 추적)
- 학습 일지에 *자동 갱신이 잡지 못한 패턴* 분석 1회 (있으면 prompt 보강)

### 이 step 에서 얻은 것
**Compounding 의 자동화 layer** — 학습자가 *기억해서* 추가하는 게 아니라, PR 리뷰가 자동으로 시스템을 개선. Step 3 의 수동 습관 위에 자동화 layer 가 얹힘.

### 다음 step 으로의 다리
한 PR 의 리뷰가 시스템을 개선한다면, *수십 개 PR* 을 동시에 만드는 패턴은? 동일 패턴 변경의 fan-out 이 다음 essence.

---

## Step 16. `/batch` fan-out 마이그레이션

### 핵심
동일 패턴 변경은 worktree 6개로 *동시 fan-out* 한다.

### 전제
- Step 13 — 충돌 안전 처리
- Step 5 — DAG 분해 (각 use case 가 독립 노드)

### 목표 역량
키오스크의 모든 use case (≥6개) 에 동일 변경을 6 worktree 동시:
- 모든 `execute()` 시작에 logging decorator
- 모든 DTO 에 새 필드 추가
- 모든 use case 의 docstring 형식 통일

### 실습

#### 1. 변경 패턴 정의 (스펙 1개)
```markdown
# Pattern: logging-decorator-on-execute

모든 `kiosk/application/use_cases/` 의 use case 클래스의 `execute()` 메서드 시작에 `@log_use_case` 데코레이터 추가.

- 데코레이터 정의: `kiosk/application/decorators/logging.py` (신규)
- 적용 대상: `cart_use_cases.py`, `get_menu.py`, `place_order.py`, `process_payment.py`, ... (≥6 파일)
- 변경 후 모든 기존 테스트 통과해야 함
```

#### 2. fan-out 실행
- 각 use case 파일마다 worktree 1개 → 6 worktree
- `/batch` 또는 본인 mini-harness 의 `dependency-resolve` 변형 활용
- 각 worktree 가 자기 use case 만 변경 + 데코레이터 import 만 추가

#### 3. 통합
- 6 PR 동시 생성
- 일관성 lint (모든 변경이 동일 패턴인지 확인)
- 머지 순서: 데코레이터 정의 PR 먼저 → use case PR 6개

#### 4. 두 번째 패턴
또 다른 fan-out (예: 모든 DTO 에 `created_at` 필드 추가) 으로 두 번째 시도.

### 빈도
**2회 성공** (서로 다른 종류 패턴)

### Eval
- 두 번 다 모든 use case 에 일관 변경 적용 (`grep` 으로 패턴 통일성 확인)
- 누락 0 (변경 안 된 use case 0개)
- 사후 동질화 commit 0 (한 worktree 의 결과가 다른 worktree 와 다르게 했다고 다시 통일하는 commit 없음)

### 이 step 에서 얻은 것
*동일 변경의 병렬화* 라는 새 차원. Step 11 의 4-세션은 *서로 다른* feature 였지만, 이건 *같은 패턴* 의 fan-out — 다른 종류의 병렬성.

### 다음 step 으로의 다리
이제 PR 흐름·충돌·검증·자동화·fan-out 모두 갖췄다. 매 worktree 종료를 *단일 명령으로* 흐름화하는 게 마지막.

---

## Step 17. `/go` — verify + simplify + PR 자동 시퀀스

### 핵심
작업 종료의 결정론 시퀀스를 **한 명령으로**.

### 전제
- Step 12–16
- 본인 verify 서브에이전트 (현재 운영 중)

### 목표 역량
worktree 작업이 끝났을 때 학습자가 입력하는 단일 명령:
```
/go
```

이 명령이 자동으로:
1. **verify-kiosk subagent** — Order 상태 머신 e2e 검증
2. **observe-run** (Step 14) — 행동 검증
3. **code-simplifier subagent** — 생성 후 정리
4. **`gh-pr-open`** — PR 생성 with description

각 단계가 fail 하면 그 단계에서 멈추고 Claude 에게 fix 요청.

### 실습

#### 1. `.claude/commands/go.md` 작성
```markdown
---
description: End-of-work verify + simplify + PR sequence
allowed_tools: Bash, Edit, Read, Task
---
현재 worktree 의 작업을 마무리하기 위해 다음 시퀀스를 실행:

1. **verify-kiosk subagent 호출**
   - Order 상태 머신 가드 모두 검증
   - DTO 일치성 검증
   - 도메인 invariant 검증
   - fail 시: 다음 단계 진행 안 함, 학습자에게 보고
   
2. **observe-run 명령 실행**
   - `python cli.py` 시뮬레이션
   - 행동 검증 통과 확인
   - fail 시: pytest 는 통과했지만 행동 fail — Claude 에게 fix 요청
   
3. **code-simplifier subagent 호출**
   - 중복 제거
   - CLAUDE.md 컨벤션 준수 확인
   - 단순화 후 verify-kiosk 재실행
   
4. **`gh-pr-open` 호출**
   - PR description 에 acceptance criteria + verify 결과 + observe-run 결과 첨부
   - PR 생성

각 단계의 결과를 학습자에게 한 줄로 보고:
✓ verify-kiosk: 통과
✓ observe-run: 7/7 시나리오 통과
✓ code-simplifier: 12 lines removed
✓ PR opened: https://github.com/.../pull/123
```

#### 2. 매 worktree 종료마다 `/go`
2주간 worktree 종료의 ≥80% 가 `/go` 사용 (`/go` 호출 횟수 / 머지된 PR 수).

### 빈도
**2주 동안 worktree 종료의 ≥80% 가 `/go`** (≥10 호출)

### Eval
- `/go` 호출 ≥10건 (transcript 기록)
- `/go` 가 lint/test fail 시 PR 안 만들고 fix 시킨 사례 ≥2건
- 학습 일지에 *`/go` 가 막은 false-done* 케이스 ≥1건 정리

### 이 step 에서 얻은 것
**작업 종료의 결정론화**. 학습자가 매번 verify·simplify·PR 단계를 *기억* 할 필요 없음 — 명령이 보장.

### 다음 step 으로의 다리
이제 단일 worktree 의 *시작 → 끝* 이 모두 흐름화됐다. 다음은 *시작* 자체도 자동화 — 학습자가 worktree 를 만들 필요조차 없게. Phase D Step 18 의 mini-harness × worktree 결합이 그 essence.

---

## Phase C 졸업 체크

- [ ] Step 12: worktree 발 PR ≥3건 머지, description 에 acceptance criteria
- [ ] Step 13: 충돌 5건 위임 처리, 학습자 직접 rebase 0회
- [ ] Step 14: `.claude/commands/observe-run.md` + 5 PR 행동 검증 첨부 + 1 버그 잡음
- [ ] Step 15: GitHub Action 운영 + 자동 갱신 ≥12건
- [ ] Step 16: 2회 fan-out 성공, 누락 0
- [ ] Step 17: `/go` 호출 ≥10건, false-done 막은 사례 ≥1건

다음: [04-phase-D-self-reinforcing.md](./04-phase-D-self-reinforcing.md)
