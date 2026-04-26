# Phase D — 시스템 자기 강화 + 외부 결합 (Steps 18–27)

이 phase 의 목표는 학습자의 **mini-harness × worktree × 외부 트리거 × 다일 자율 × 이식** 까지 — Boris 워크플로우의 *컴파운딩 layer 전체* 를 본인 시스템 위에 얹는 것이다.

이 phase 가 가장 큰 (10 step) 이유: 학습자가 *이미 mini-harness 를 운영* 하기에, 그 위에 얹는 컴파운딩 layer 가 가장 풍부한 essence 분화가 가능하다.

---

## Step 18. mini-harness 의 worktree 자동 생성

### 핵심
본인 harness 가 worktree 까지 fan-out — **본인 시스템과 Boris 패턴의 결합**.

### 전제
- Step 16 — `/batch` 경험 (수동 fan-out)
- 본인 harness 운영 (현재)

### 목표 역량
`dependency-resolve` 가 독립 노드를 식별하면 자동으로:
1. `git worktree add` 실행
2. task-executor 서브에이전트 spawn (또는 `claude --bare -p "..."` 호출)
3. spec.json 의 해당 task 가 worktree 안에서 실행

`spec.json` 에 `isolation: worktree` 필드 도입하여 *어느 노드를 worktree 격리할지* 명시.

### 실습

#### 1. spec.json 스키마 확장
```json
{
  "tasks": [
    {
      "id": "task-1",
      "description": "Add Receipt entity",
      "isolation": "worktree",
      "depends_on": []
    },
    {
      "id": "task-2",
      "description": "Add ReceiptRepository",
      "isolation": "worktree",
      "depends_on": ["task-1"]
    }
  ]
}
```

#### 2. mini-execute 보강
`.claude/skills/mini-execute/SKILL.md` 에 isolation:worktree 핸들링 추가:
- 의존이 모두 완료된 task 를 식별
- 그 중 isolation:worktree 인 task 를 위해 `git worktree add ../{repo}-{task-id} {branch-name}`
- task-executor agent 를 그 worktree 에서 spawn

#### 3. dependency-resolve 보강
`.claude/skills/dependency-resolve/SKILL.md` 에 자동 isolation 판단:
- 노드가 다른 노드와 *공유 파일을 수정* 하지 않으면 → `isolation: worktree`
- 공유 파일 수정이 있으면 → `isolation: none` (순차 실행)

### 빈도
**2주 동안 자동 worktree 로 처리된 task ≥10건**

### Eval
- spec.json 에 isolation:worktree 표시된 task 가 자동 worktree 에서 실행됐다는 trace (`.dev/harness/runs/run-{id}/state.json` 의 worktree 필드)
- 학습자 손 worktree 생성 횟수 (직접 `git worktree add` 입력) 가 시작 대비 70%+ 감소
- 학습 일지에 *자동 worktree 가 잡지 못한 케이스* ≥1건 (있으면 dependency-resolve 보강)

### 이 step 에서 얻은 것
mini-harness 가 단순 task runner 에서 **worktree 오케스트레이터** 로 진화. 학습자가 *DAG 만 정의* 하면 시스템이 worktree 를 알아서 만든다.

### 다음 step 으로의 다리
worktree 자동화처럼, *슬래시 명령 자체* 도 자동으로 추출되도록 한 단계 더 올라간다.

---

## Step 19. 빈도 임계 → 스킬 자동 추출

### 핵심
두 번 한 일은 *세 번* 하지 않는다 — **그 결정도 자동화**.

### 전제
- Step 17 — `/go` 같은 슬래시 명령 정착
- Step 15 — 자동 갱신 패턴 (GitHub Action 가능)

### 목표 역량
슬래시 명령 사용 빈도 ≥5인 항목을 매주 식별하고, 정식 스킬 (`SKILL.md` + `reference/`) 로 승격하는 GitHub Action 또는 `/loop`.

### 실습

#### 1. 빈도 측정 스크립트
- `.claude/transcripts/` 또는 shell history 에서 슬래시 명령 호출 추출
- 명령별 호출 횟수 카운트
- 빈도 ≥5 인 명령 목록 출력

```bash
# 예시: scripts/count-slash-commands.sh
grep -h '^/' ~/.claude/transcripts/*.txt | sort | uniq -c | sort -rn | head -20
```

#### 2. 자동 추출 GitHub Action 또는 `/loop`
- 매주 일요일 트리거
- 빈도 ≥5 인 명령에 대해 Claude 에게 prompt:
  > *"명령 `/{name}` 이 지난주 N회 사용됐다. 정식 스킬로 승격해줘. 본인 mini-harness 의 다른 SKILL.md 컨벤션을 따라:*
  > - *SKILL.md (description, allowed_tools, instructions)*
  > - *reference/templates 또는 examples (있다면)*
  > - *기존 명령 파일은 SKILL.md 의 wrapper 로 단순화"*
- 결과를 PR 로 생성

#### 3. 학습자 검토만
PR 을 검토하고 머지 — Claude 가 만든 스킬을 그대로 받지 말고, 컨벤션 확인 + 1줄 정정 정도만.

### 빈도
**1달 동안 자동 추출 PR ≥2건**

### Eval
- `.claude/skills/` 의 새 스킬 ≥2개
- 둘 다 빈도 측정 trace 보유 (`metadata.frequency` 또는 PR description 에 카운트)
- 추출된 스킬이 학습자 외 *다른 세션* (서브에이전트 또는 새 worktree) 에서 ≥3 회 자동 호출됨 (= 진짜로 재사용된다는 증거)

### 이 step 에서 얻은 것
**도구 만들기의 자동화**. 학습자가 *어떤 명령을 스킬로 만들지* 매주 의식적으로 결정할 필요 없음 — 빈도가 결정한다.

### 다음 step 으로의 다리
시스템이 *내부 빈도* 로 자기 개선하면, 다음 도전은 *외부* 신호로 일을 시작하는 것. Step 20 의 외부 트리거.

---

## Step 20. 외부 트리거 → fix 흐름 (`/fix-this <issue-url>`)

### 핵심
*외부에서 들어온 신호* 가 즉시 작업 큐가 된다 — Boris 의 Slack-paste 등가.

### 전제
- Step 17 — `/go` 흐름화
- Step 18 — 자동 worktree

### 목표 역량
GitHub issue · 이메일 · 텍스트 등 외부 신호를 paste → *"fix this"* 한 마디로 worktree 생성·DAG 분해·PR 머지까지 자동.

### 실습

#### 1. `.claude/commands/fix-this.md` 만들기
```markdown
---
description: External trigger to internal fix flow
allowed_tools: Bash, Read, Edit, Task
---
인자: GitHub issue URL 또는 텍스트 dump

흐름:
1. **이슈 본문 fetch**: `gh issue view {arg}` (URL 일 경우) 또는 그대로 사용 (텍스트일 경우)
2. **DAG 분해**: 본인 mini-harness 의 `/taskify` + `/dependency-resolve` 호출
3. **자동 worktree**: Step 18 의 isolation:worktree 흐름 시작
4. **`/go` 시퀀스**: Step 17 의 verify + simplify + PR 자동
5. **PR description 자동 첨부**: 원 이슈 링크 + acceptance criteria + 행동 검증 결과

학습자에게 보고는 다음 형식:
✓ Issue parsed: 5 tasks identified (DAG: linear)
✓ Worktrees created: 3 (kiosk-fix-{N})
✓ All tasks completed
✓ PRs opened: #N1, #N2, #N3 (linked to issue #M)
```

#### 2. compound-practice 에 의도적 GitHub issue 5건 등록
- 키오스크 또는 mini-harness 의 *실제* 개선/버그 항목
- 각 이슈는 본문에 sufficient detail (재현 단계, expected behavior 명시)

#### 3. 5건 모두 `/fix-this <url>` 로 처리
학습자가 spec·worktree·PR 흐름 *직접 입력 0회*.

### 빈도
**5건의 issue → fix → 머지** — 3주

### Eval
- 5건 모두 학습자가 spec / worktree create / PR open 직접 입력 0회 (transcript 검증)
- 이슈 등록부터 PR 머지까지 평균 시간 측정 → 학습 일지에 1줄 정리
- 5건 중 ≥1건은 학습자 *없이* (자율) 처리됨 (다음 step 23 의 다일 자율 실행 prerequisite)

### 이 step 에서 얻은 것
**시스템의 entry point** 가 외부 신호. 학습자가 *작업을 식별하고 분해하는* 일에서 해방됨 — 이슈만 잘 쓰면 된다.

### 다음 step 으로의 다리
외부 트리거가 작동한다는 건 *역할 분담* 의 마지막 단계. 시스템이 내부 자산 (서브에이전트) 으로 무장돼 있어야 외부 신호를 다양하게 처리할 수 있다.

---

## Step 21. 서브에이전트 라이브러리 ≥7

### 핵심
역할은 *독립 에이전트 자산* 으로 누적된다.

### 전제
- 본인 서브에이전트 운영 (현재)
- Step 18 — worktree 자동화
- Step 19 — 스킬 자동화

### 목표 역량
`.claude/agents/` 에 ≥7 서브에이전트 누적. 메인 세션은 *오케스트레이터* 로만 — 실제 일은 서브에이전트들이.

권장 라이브러리:
1. **verify-kiosk** — Order 상태 머신·DTO·결제 e2e 검증
2. **code-simplifier** — 생성 후 코드 정리, CLAUDE.md 준수 확인
3. **test-writer** — 커버리지 부족 영역 테스트 자동 추가
4. **adr-writer** — `.dev/adr/` 형식 ADR 자동 작성
5. **dag-decomposer** — feature 를 DAG 로 분해 (Step 6 peer-review 자동화)
6. **conflict-resolver** — Step 13 의 rebase 위임 정형화
7. **harness-curator** — mini-harness 자체 검토·정리

### 실습

#### 1. 안 만든 것 추가
현재 운영 중인 서브에이전트 외에 위 목록에서 부족한 것 추가.

#### 2. 각 서브에이전트가 mini-harness 의 어느 step 에 연결되는지 매핑
예: `verify-kiosk` ← `/go` Step 17 / `dag-decomposer` ← `/taskify` 후처리 / `harness-curator` ← `/mini-compound` 의 hook

이 매핑을 `.claude/agents/README.md` 또는 `docs/boris-claude-code/curriculum/agent-map.md` 에 정리.

### 빈도
**2달 동안 ≥7 서브에이전트 누적, 각 ≥5회 호출**

### Eval
- `.claude/agents/` 파일 ≥7
- 각 에이전트의 호출 빈도 trace (transcripts 에 그 이름 등장 ≥5)
- 메인 세션 평균 컨텍스트 사용량 시작 (Phase A 베이스라인) 대비 30%+ 감소 (서브에이전트가 격리된 컨텍스트로 일하기에)

### 이 step 에서 얻은 것
서브에이전트가 *자산 라이브러리* 임을 체감. 새 작업이 와도 *기존 라이브러리 조합* 으로 대부분 해결.

### 다음 step 으로의 다리
이제 도구·자동화·자산 모두 갖춰졌다. 마지막은 *지속 가능한 동시 운영 규모* — Boris 의 솔로 등가 도달점.

---

## Step 22. 5+ 동시 세션 — 작업 3 + analysis 1 + harness loop 1

### 핵심
Boris 도달점의 솔로 현실판.

### 전제
- Step 11 — 4 세션 안정
- Step 18 — harness × worktree 결합

### 목표 역량
매일 worktree 3 (작업) + analysis 1 + **harness instance 1 (자율 ralph loop)** = 5세션 동시. 인지 과부하 0.

`harness instance` 는 `/loop` 로 자율 — 사용자 입력 없이 ralph 가 spec.json 진척 처리.

### 실습

#### 1. harness instance 자율 운영
- 별도 worktree (`compound-practice-harness-loop`)
- `/loop "지속적으로 .dev/harness/runs/ 에서 미완료 task 가 있으면 mini-execute 진행"` 시작
- Stop 훅이 다음 iteration 자동 트리거

#### 2. 학습자는 작업 worktree 3 에 집중
- harness 는 알림으로만 추적 — *학습자 개입 필요* 한 케이스 (예: spec 모호함, 충돌 등) 만 발생할 때 알림
- analysis worktree 가 harness loop 의 진척도 매일 체크

#### 3. 매일 운영 패턴
- 아침: harness instance 시작 + 작업 worktree 3 시작
- 낮: 작업 worktree 3 에 집중. harness 는 background.
- 저녁: analysis worktree 에서 하루 진척 검토 → 학습 일지

### 빈도
**3주 연속, 평일 매일 ≥4시간 5세션 동시**

### Eval
- 3주간 매일 ≥3 active branch (`git for-each-ref --format='%(refname)' refs/heads/`)
- 머지 PR 수 Step 11 (Phase B 도달점) 대비 ≥1.5배
- 인지 과부하 사례 학습 일지에 *솔직 기록* — 빈도 감소 추세 (3주 시작 vs 끝 비교)

### 이 step 에서 얻은 것
**Boris 의 솔로 현실판 도달점**. 5 = 작업 3 + analysis 1 + harness 1 의 균형이 *지속 가능* 한 상태.

### 다음 step 으로의 다리
하루 4시간 동시는 가능해도, *컴퓨터 끄고 자도 시스템이 일하는가* 는 다른 차원. 다일 자율이 그 essence.

---

## Step 23. 다일 자율 실행 (`/loop` + Stop 훅 1–3일)

### 핵심
**컴퓨터 끄고 자도 시스템이 일한다.**

### 전제
- Step 22 — 5세션 안정
- Step 18 — harness × worktree
- Step 17 — `/go` 결정론 시퀀스

### 목표 역량
명확히 정의된 backlog 를 24–72시간 자율 실행. Stop 훅이 `/loop` 다음 iteration 자동 트리거.

backlog 예시:
- 키오스크의 모든 use case 에 logging migration (Step 16 fan-out 의 확장판)
- mini-harness 의 모든 skill 에 reference 보강
- 도메인 모델의 모든 value object 에 invariant 강화

### 실습

#### 1. backlog spec 1개 작성
- ≥10 task
- 각 task 의 acceptance + verify 명시
- 의존 그래프 명시 (DAG)
- spec.json 으로 `.dev/harness/runs/run-{id}/` 에 commit

#### 2. `/loop` 시작 (3일 한도)
```
/loop "다음 spec.json 의 모든 task 를 진행해줘. 막히면 학습자에게 알림 후 다음 task 로. {경로}"
```

#### 3. 매일 1회 진척 확인
- analysis worktree 에서:
  - 완료된 task 수 / 전체
  - Stop 훅이 막은 task 의 차단 사유
  - 자율 PR 머지 가능 상태인 것 / 학습자 개입 필요 / 차단된 것

#### 4. 3일 후 결과 검토
- 머지 가능 PR vs 학습자 개입 필요 vs 차단된 것 분류
- 차단 사유 분류 — *spec 결함* (학습자가 사전에 막을 수 있는 것) vs *환경 결함* (외부 의존, 권한 등)

### 빈도
**2회의 다일 자율 실행 (각 24–72시간)**

### Eval
- 두 번 모두 자율 실행 종료 시점에 ≥3 PR 이 학습자 손대지 않고 *머지 가능 상태*
- 차단된 task 의 차단 사유 분류 학습 일지 — *spec 결함* 비율과 *환경 결함* 비율
- 두 번째 다일 실행에서 spec 결함 비율이 첫 번째보다 ≥30% 감소 (학습자가 spec 작성을 개선했다는 증거)

### 이 step 에서 얻은 것
**시간 차원의 위임**. 학습자의 깨어있는 시간이 *작업 시간* 의 상한이 아니다.

### 다음 step 으로의 다리
시스템이 자율로 일하는 동안, 학습자는 *다른 차원* 의 일을 한다 — 학습. Step 24 의 output styles.

---

## Step 24. Output styles 활용 (Explanatory + Learning)

### 핵심
Claude 의 *말투* 도 도구다 — **자기 학습용 layer**.

### 전제
Step 22 — 5세션 안정 (시스템이 작동 중이어야 자기 학습할 시간이 생김)

### 목표 역량
- **Explanatory style** — 낯선 코드 탐색 시 (Claude 가 프레임워크·패턴 설명 추가)
- **Learning style** — 어려운 디버깅/이해 시 (Claude 가 학습자에게 질문하며 코칭)

`/config` 로 의식적으로 켜고 끄는 능력.

### 실습

#### 1. mini-harness 의 잘 모르는 skill 1개를 Explanatory style 로 탐색
예: `.claude/skills/council/` 가 어떻게 multi-panel debate 를 실행하는지 깊게 이해.
- `/config` → output style: Explanatory
- *"council skill 의 각 panel 이 어떻게 spawn 되고 결과가 어떻게 합쳐지는지 코드 trace 와 함께 설명해줘"*
- 학습한 내용을 `.mini-harness/learnings/` 에 frontmatter 형식으로:
  ```yaml
  ---
  date: 2026-XX-XX
  tags: [skill, council, multi-panel, harness-internals]
  ---
  ## What I learned
  ...
  ```

#### 2. 키오스크 의 잘 모르는 영역 (또는 새 도메인 추가 시) Learning style
- `/config` → output style: Learning
- *"이 use case 의 도메인 invariant 를 이해하고 싶어. 내가 모를 만한 부분을 짚어줘."*
- Claude 가 질문 → 학습자가 답 → 답 못 하는 부분이 학습 포인트

#### 3. 4건 (Explanatory 2 + Learning 2) — 2주
- `.mini-harness/learnings/` 에 frontmatter 형식으로 4 commit

### 빈도
**4건 (Explanatory 2 + Learning 2) — 2주**

### Eval
- 4건 모두 `.mini-harness/learnings/` 에 commit
- 각 학습 항목이 Step 3 의 CLAUDE.md 습관과 *겹치지 않는 종류* 임을 분리:
  - **CLAUDE.md** = Claude 행동 교정 (시스템 facing)
  - **learnings** = 학습자 자신의 이해 (사람 facing)
- 학습 일지에 *Explanatory vs Learning style 의 적용 케이스* 1줄씩 정리

### 이 step 에서 얻은 것
시스템이 자율로 일하는 동안 *학습자가 진화* 하는 자산. CLAUDE.md 와 learnings 가 두 layer 로 분리.

### 다음 step 으로의 다리
시스템이 진화하고 학습자도 진화한다. 마지막 productivity layer 는 *학습자의 입력 처리량* — Step 25.

---

## Step 25. 음성·키바인딩·색 polish (Boris 의 *"voice 3x faster"* 자산화)

### 핵심
인지 처리량 (입력 속도·세션 식별·키 동선) 의 마지막 productivity layer.

### 전제
Step 22 — 5세션이 일상이 된 후 (그 전에 polish 하면 풀어야 할 더 큰 문제부터 푸는 게 좋음 — 빠른 입력은 더 큰 문제가 다 풀린 후 의미)

### 목표 역량
- 음성 입력으로 prompt 작성 (macOS `fn × 2`, Windows `Win+H`)
- `/keybindings` 커스텀 매핑
- `/color` 다중 세션 시각화가 *기본 환경*

### 실습

#### 1. 음성 입력
- macOS: `fn × 2`
- Windows: `Win+H`
- prompt 의 절반 이상을 음성으로 작성 시도
- 처음엔 부정확 — 학습자의 발화 속도·악센트가 학습됨

#### 2. `~/.claude/keybindings.json`
커스텀 매핑 ≥5:
- plan mode 토글
- /color 단축
- harness skill 호출 단축키 (예: Ctrl+T 가 /taskify, Ctrl+G 가 /go)
- /rewind 단축
- /compact 단축

#### 3. 세션 색·이름 매핑 영구화
`.bashrc`/`.zshrc` 에 Step 8 의 zk 함수 + 색 환경변수.

### 빈도
**2주 동안 매일 음성 입력 ≥30%, 커스텀 키바인딩 ≥5**

### Eval
- `~/.claude/keybindings.json` commit (≥5 매핑)
- 셸 색 매핑 dotfile commit
- 학습 일지에 음성 입력 비율 측정 1주 (transcript 길이 vs 학습자 손 입력 시간 추정 비교)
- 학습 일지에 *음성 입력이 안 되는 prompt 종류* 1줄 (예: 코드 블록 dictation 은 어렵다 → 그건 손으로)

### 이 step 에서 얻은 것
*입력 처리량* 자산화. Boris 의 *"voice 3x faster"* 가 본인 케이스에서 어느 정도인지 데이터로 확인.

### 다음 step 으로의 다리
시스템·자산·입력 모두 갖춰졌다. 마지막은 *주기적 자기 평가* — 매주 시스템 전체 점검.

---

## Step 26. 주간 메타-회고 — 시스템 자체 진화 측정

### 핵심
도구도 코드처럼 진화시킨다 — 그리고 **측정한다**.

### 전제
Step 1–25 모두 (시스템 작동 중)

### 목표 역량
매주 금요일 1시간 회고 — `/mini-compound` 활용. **6 layer 점검**:

1. **CLAUDE.md** — 새 항목 검토, 사장된 항목 archive, 중복 항목 통합
2. **settings.json** — auto mode 분류기가 막은 동작 검토, 새 안전 패턴 추가
3. **`.claude/commands/`** — 빈도 0 명령 archive, Step 19 의 자동 추출 후보 검토
4. **`.claude/agents/`** — 호출 빈도 측정, 안 쓰는 에이전트 정리
5. **`.mini-harness/learnings/`** — 한 주의 weekly retro 항목 추가
6. **observe-run / Step 14** — 행동 검증으로 잡힌 버그 패턴 분석

### 실습

#### 1. 매주 금요일 `/mini-compound` 호출
이미 본인 mini-harness 의 일부 — *학습 promotion* 흐름. 거기에 위 6 layer 점검 단계 추가.

#### 2. weekly retro template
```yaml
---
date: 2026-XX-XX (Friday)
type: weekly-retro
tags: [retro, week-N]
---

## CLAUDE.md
- 추가: N건 (대표 항목 1줄)
- archive: N건
- 중복 통합: N건

## settings.json
- 새 allow: N건
- 새 deny: N건
- auto mode 가 막은 동작 분석 1줄

## .claude/commands/
- 빈도 0 archive: [목록]
- 자동 추출 후보: [목록]

## .claude/agents/
- 호출 빈도 top 3: [목록]
- 사용 0 에이전트: [목록 → archive 검토]

## learnings 추가
- N건 (대표 1줄)

## observe-run 잡은 버그 패턴
- 1줄

## 다음 주 1순위
- 1줄
```

### 빈도
**6주 연속**

### Eval
- 6 weekly retro 모두 `.mini-harness/learnings/` 에 commit (frontmatter 정형화)
- 6주 사이 시스템 자체 변화:
  - CLAUDE.md ≥15줄 성장
  - `.claude/agents/` 또는 `.claude/skills/` ≥2 추가
  - `.claude/commands/` archive ≥1
- 6주의 *"다음 주 1순위"* 가 실제로 다음 주 회고에서 다뤄진 비율 ≥80%

### 이 step 에서 얻은 것
*시스템이 시스템적으로 개선됨* 의 직접 증거. 도구가 코드처럼 진화하고, 그 진화가 측정된다.

### 다음 step 으로의 다리
이 시스템이 *진짜* 시스템인지의 마지막 검증 — *재현 가능* 한가? Step 27 의 이식.

---

## Step 27. 시스템 다른 레포에 이식 — 컴파운딩의 한계 시험 (졸업)

### 핵심
시스템이 *재현 가능* 한지 = **진짜 시스템인지 검증**.

### 전제
Step 26 — 자기 진화 6주

### 목표 역량
새 빈 레포에 본인 mini-harness + Boris 패턴 시스템을 24시간 안에 부트스트랩. 1주 만에 첫 worktree 발 PR 머지.

### 실습

#### 1. 새 작은 프로젝트 1개
도메인은 키오스크와 다른 게 좋음 (이식의 한계 시험):
- 간단한 CLI 도구 (예: 일정 관리, 인벤토리, 메모 앱)
- 또는 다른 언어 (예: Go, TypeScript) — 더 어려운 이식 검증

#### 2. 의도 기반 재구성 (복붙 X)
compound-practice 의 .claude/, CLAUDE.md, .mini-harness/, .dev/harness/runs/ 컨벤션을 *그대로 복사하지 말고* 의도 기반으로 재구성:
- 새 레포의 도메인에 맞게 .claude/agents/ 의 agent 이름·역할 재정의
- 새 레포의 build 시스템에 맞게 .claude/settings.json 의 allow 규칙 재정의
- mini-harness 의 어느 skill 이 *이 도메인에서도 필요* 한지 판단 — 필요 없는 건 빼기

#### 3. 24시간 내 부트스트랩 + 1주 내 첫 worktree PR
```
Day 1: .claude/settings.json + CLAUDE.md + ≥1 슬래시 명령 + ≥1 서브에이전트 운영 시작
Day 2-7: 첫 작업 — DAG 분해 + worktree + PR 머지 (revert 없음)
```

### 빈도
**1회 (성공이 곧 졸업)**

### Eval
- 24시간 내 .claude/settings + CLAUDE.md + ≥1 슬래시 + ≥1 서브에이전트 운영 시작 (timestamp 측정)
- 1주 내 worktree 발 PR ≥1건 머지 (revert 없음)
- "이번 이식에서 사장된 컨벤션" / "새 레포에 안 통한 패턴" ≥3건 학습 일지 — **시스템의 *한계* 인지**

### 이 step 에서 얻은 것
**컴파운딩의 한계 인식** — 어느 부분이 진짜 *재사용 가능한 시스템* 이고 어느 부분이 *키오스크 특화* 였는지의 분리. 이게 졸업의 진짜 의미.

### 졸업 — Boris 수준 95% 도달
27 step 모두 통과 시 Boris 의 *기술적 essence* 95% 체득.

남는 5%:
- **Anthropic 서피스 (20–30 PR/day)** — 솔로 단일 도메인엔 PR 후보 부족
- **Slack/BigQuery/Sentry MCP** — 외부 서비스 신호 없음 (Step 20 의 `/fix-this` 가 essence 보존)
- **모바일/teleport** — 라이프스타일, 역량 무관
- **팀 peer review** — 솔로엔 동료 없음 (Step 6 의 self-paired 등가)

이 5% 는 *조직적 환경 변수* 라 솔로 커리큘럼이 줄일 수 없다. 실제 팀에 합류하면 자연 도달.

---

## Phase D 졸업 체크 = 전체 졸업 체크

- [ ] Step 18: spec.json isolation:worktree 자동 실행 ≥10건, 학습자 직접 worktree 생성 70% 감소
- [ ] Step 19: 자동 추출 스킬 ≥2개, 다른 세션에서 ≥3 자동 호출
- [ ] Step 20: `/fix-this` 5건 처리, 학습자 직접 입력 0회
- [ ] Step 21: ≥7 서브에이전트, 컨텍스트 사용량 30%+ 감소
- [ ] Step 22: 5세션 동시 3주, 머지 PR 1.5배 증가
- [ ] Step 23: 다일 자율 2회, 자율 머지 가능 PR ≥3건/회, spec 결함 비율 30% 감소
- [ ] Step 24: 4 learnings frontmatter commit, CLAUDE.md vs learnings 분리
- [ ] Step 25: keybindings.json ≥5 매핑, 음성 입력 비율 데이터
- [ ] Step 26: 6 weekly retro, 시스템 변화 metric 모두 통과
- [ ] Step 27: 새 레포 이식 성공, 사장된 컨벤션 ≥3건 식별

[graduation-checklist.md](./graduation-checklist.md) 에 27 step 모든 eval 한 페이지 요약.
