# Phase B — 병렬 worktree 척추 (Steps 7–11)

이 phase 의 목표는 **단일 worktree 익숙** 에서 **매일 작업 3 + analysis 1 = 4세션 동시** 까지 점진. 사용자의 핵심 갭 중 첫 번째 (병렬 worktree 미경험) 을 닫는다.

Phase A 가 *독립적으로 분해된 DAG 노드* 를 만들어줬으니, 이 phase 는 그 노드들을 *동시에 굴리는* 인지·환경 부담을 단계적으로 익힌다.

---

## Step 7. 첫 2-worktree 동시 (단순 케이스)

### 핵심
독립 노드 둘은 *지금 바로* 동시에 굴린다.

### 전제
- Step 5 — DAG 분해 능숙
- Step 6 — peer-plan-review 로 독립성 사전 확인됨
- 단일 worktree 익숙 (현재 수준)

### 목표 역량
Phase A 의 DAG 에서 의존 없는 노드 2개를 두 worktree 에서 동시. **첫 경험은 *충돌 없을 게 명백한* 두 노드** — 너무 욕심내면 첫 경험에서 실망한다.

### 실습
키오스크에 두 *완전 독립* feature 동시:

예시 후보 (import 관계 없음 사전 확인):
- (a) 메뉴 카테고리 추가 (`kiosk/domain/models/menu_category.py` 신규)
- (b) 영수증 entity 추가 (`kiosk/domain/models/receipt.py` 신규)
- (c) 결제 환불 use case (`kiosk/application/use_cases/refund_payment.py`)

운영 흐름:
```bash
# main 에서
git worktree add ../kiosk-feat-a feat-menu-category
git worktree add ../kiosk-feat-b feat-receipt-entity

# 터미널 탭 1
cd ../kiosk-feat-a && claude --worktree kiosk-feat-a

# 터미널 탭 2 (별도 창/탭)
cd ../kiosk-feat-b && claude --worktree kiosk-feat-b
```

각 세션이 끝날 때마다 OS 알림으로 어느 쪽이 입력 필요한지 추적.

### 빈도
**2주 동안 2-worktree 동시 운영 ≥5회**

### Eval
- 5회 모두 두 worktree 가 충돌 0 으로 각자 commit
- 메인 워킹 카피 (`compound-practice/`) 의 `git status` 가 5회 모두 깨끗
- 학습 일지에 *2-worktree 동시 운영의 첫 인지 부담* 기록 1회 (어느 부분이 가장 헷갈렸는가)

### 이 step 에서 얻은 것
worktree 격리의 *심리적 경험* — 한 worktree 의 실수가 다른 worktree 를 망치지 않는다는 안도감. 이게 있어야 더 많은 worktree 로 확장 가능.

### 다음 step 으로의 다리
2개도 헷갈리면 5개는 불가능하다. Step 8 이 *인지 부담을 외주화* 하는 환경 셋업.

---

## Step 8. 색·번호·OS 알림으로 다중 세션 추적

### 핵심
인지 부담은 시각·청각 신호로 외주화한다.

### 전제
Step 7 — 2-worktree 운영의 인지 부담 *경험* 후에야 어떤 부담을 외주화할지 알 수 있다.

### 목표 역량
- `/color` — prompt 색 구분
- `/statusline` — worktree 이름 + branch + context % 표시
- iTerm2 / Windows Terminal / Ghostty 알림 — Claude 가 입력 필요할 때
- 셸 alias — `zk1`, `zk2`, `zk3` 단일 키로 worktree 이동

### 실습

#### 1. 색 매핑 정의
`~/.claude/settings.json` 또는 worktree 별 settings 에:
```json
{
  "color": {
    "kiosk-feat-a": "blue",
    "kiosk-feat-b": "green",
    "kiosk-feat-c": "magenta",
    "kiosk-analysis": "gray"
  }
}
```

#### 2. statusline 커스터마이즈
worktree 이름 + 현재 branch + context 사용량 (%) 표시:
```bash
/statusline
# Set format: [kiosk-feat-a] feat-menu-category | 23% ctx
```

#### 3. 셸 함수 (`~/.bashrc` 또는 `~/.zshrc`)
```bash
zk() {
  local n=$1
  case $n in
    1) cd ~/compound-practice-feat-a && claude --worktree kiosk-feat-a ;;
    2) cd ~/compound-practice-feat-b && claude --worktree kiosk-feat-b ;;
    3) cd ~/compound-practice-feat-c && claude --worktree kiosk-feat-c ;;
    a) cd ~/compound-practice-analysis && claude --worktree kiosk-analysis ;;
    *) echo "Usage: zk {1|2|3|a}" ;;
  esac
}
```

#### 4. OS 알림 (Windows Terminal)
Windows Terminal 설정에서 `bellStyle: "window,taskbar"` — Claude 가 입력 prompt 띄울 때 알림.

### 빈도
**1주 동안 매일 ≥2 worktree 가 색·이름 구분된 상태로 운영**

### Eval
- 색 매핑 settings.json commit
- `zk` 셸 함수 정의 dotfile commit (또는 .mini-harness/ 안에 docs)
- statusline 표시 캡처 1장 (학습 일지 첨부)

### 이 step 에서 얻은 것
다중 세션이 *시각적으로 구분 가능* 해진다. 인지 부담의 가장 큰 부분이 "지금 어느 worktree 에 있는가" 파악인데, 이게 외주화됨.

### 다음 step 으로의 다리
worktree 가 시각적으로 구분되는 건 *내적* 셋업. 외적으로 worktree 들이 *같은 머리로* 일하려면 컨텍스트 공유가 필요. Step 9 가 그 essence.

---

## Step 9. worktree 컨텍스트 동기화 — CLAUDE.md, settings, agents

### 핵심
5세션이 한 머리로 일하려면 컨텍스트가 *git 을 통해* 공유돼야 한다.

### 전제
- Step 7 — worktree 동시 운영 경험
- Step 3 — CLAUDE.md 즉시 추가 습관 (그 갱신이 모든 worktree 에 전파돼야 의미)

### 목표 역량
CLAUDE.md / `.claude/settings.json` / `.claude/agents/` / `.claude/commands/` 변경이 *모든 worktree* 에 즉시 반영. SessionStart 훅에 자동 `git fetch` 추가하여 worktree 가 stale 한 채 시작 안 되게.

### 실습

#### 1. SessionStart 훅에 git fetch 추가
`.claude/settings.json` 의 `hooks.SessionStart`:
```json
{
  "matcher": "*",
  "hooks": [
    {
      "type": "command",
      "command": "git fetch origin main 2>/dev/null && git rebase origin/main 2>/dev/null || true"
    }
  ]
}
```

#### 2. 5건의 동기화 시나리오 검증
- worktree A 에서 CLAUDE.md 에 한 줄 추가 → commit → main 에 머지
- worktree B/C 에서 다음 세션 시작 시 `git pull --rebase` 자동 실행되는지 확인
- 다음 prompt 가 *그 새 규칙* 을 인지하는지 (Claude 에게 명시적으로 *"방금 추가된 CLAUDE.md 규칙 X 를 알고 있는가?"* 질문)

#### 3. settings.json 충돌 회피 패턴
- 두 worktree 가 동시에 settings.json 의 다른 부분을 수정 → 머지 시 충돌 발생
- mini-harness 의 ralph loop 가 동일 패턴 직면했을 가능성 높음 — 그 해법 차용

### 빈도
**2주 동안 변경 → 머지 → 다른 worktree 자동 인지가 정상 동작한 사례 5건**

### Eval
- 5건 모두 git log 에 추적 가능 trail (worktree A commit → main merge → worktree B pull → worktree B 다음 prompt 가 인지)
- SessionStart 훅 commit
- 학습 일지에 *settings.json 충돌 회피 패턴* 1줄 정리

### 이 step 에서 얻은 것
다중 worktree 가 *분산* 이 아니라 *하나의 시스템* 임을 git 이 보장. CLAUDE.md 의 학습이 모든 머리에 전파.

### 다음 step 으로의 다리
모든 worktree 가 동기화된다는 건 *작업 worktree* 만의 얘기가 아니다. *관찰* 전용 worktree 도 있어야 한다. Step 10 의 analysis worktree.

---

## Step 10. analysis worktree 상시 운영

### 핵심
작업과 관찰을 *물리적으로* 분리한다 (Boris 별도 운영 패턴).

### 전제
Step 7–9 — worktree 운영의 인지 부담을 분리할 만큼 익숙해진 후

### 목표 역량
작업 worktree 와 별개의 **analysis worktree 1개 상시 운영**. 거기서는:
- 로그 분석
- `pytest -v` 실행
- mini-harness state inspection (`.dev/harness/runs/` 분석)
- BigQuery 가 향후 추가되면 그 쿼리만
- *코드 편집은 0*

작업 worktree 의 컨텍스트를 깨끗하게 유지하기 위함.

### 실습

#### 1. analysis worktree 생성
```bash
git worktree add ../compound-practice-analysis main
```

#### 2. 거기서 분석 작업
- `.dev/harness/runs/` 의 state.json·spec.json 분석
  - 어느 task 가 자주 fail 하는가?
  - 어느 skill 이 가장 많이 호출되는가?
  - dependency-resolve 의 DAG 가 사후 변경된 비율?
- 키오스크 pytest -v 결과를 거기서만
- 학습한 패턴은 작업 worktree 의 *학습 일지 commit* 으로만 전달 (코드 변경 X)

#### 3. 매일 fresh session 으로 시작
analysis 는 컨텍스트 누적이 의미 없는 영역 — 매번 *현재 상태 vs 어제 상태* 의 diff 만 본다.

### 빈도
**2주 동안 매일 analysis worktree 가 fresh session 으로 살아있음**

### Eval
- 2주간 analysis worktree 의 git log 에 *편집 commit 0* (오직 학습 일지에 추가만)
- 작업 worktree 의 commit 메시지에 analysis 결과를 *인용* 한 사례 ≥3건 (예: "fix: analysis 에서 식별한 retry-loop 패턴 적용")
- 새로 식별한 패턴이 학습 일지에 ≥3건 누적

### 이 step 에서 얻은 것
*관찰* 의 독립 머리. 작업 중인 머리가 자기 작업을 객관적으로 보는 건 어렵다 — 별도 worktree 의 별도 세션이 그걸 한다.

### 다음 step 으로의 다리
이제 작업 worktree 2 + analysis 1 = 3 세션 안정. 마지막 한 세션을 더 늘려 *Phase B 의 도달점 4 세션* 으로.

---

## Step 11. 3-worktree + analysis = 4 세션 동시

### 핵심
단일 → 4 세션까지 *인지 부담 없이* 올라간다.

### 전제
Step 7–10 — worktree 색·동기화·역할 분리 정착

### 목표 역량
매일 작업 worktree 3 + analysis 1 = 4 세션 동시. 인지 과부하 0.

### 실습
3개의 독립 feature 를 동시 진행:
- DAG 가 큰 feature 한 건의 의존 없는 3 노드, 또는
- 작은 feature 셋 (예: 환불 use case + 영수증 출력 + 메뉴 카테고리)

운영 패턴:
- 각 worktree 마다 본인 mini-harness skill 시퀀스 사용 가능
- analysis 가 4개 모두 추적 — 어느 게 stuck 인지, 어느 게 거짓 완료 했는지
- 학습자는 *어느 worktree 에 input 줄지* 결정만, 실제 작업은 Claude

### 빈도
**2주 연속, 평일 매일 ≥2시간 4-세션 동시 운영**

### Eval
- 2주간 동시 4세션 캡처 ≥10회 (스크린샷 또는 `tmux ls` 출력)
- 동일 기간 머지된 PR 수가 그 직전 2주 대비 ≥1.5배 (Phase A 의 베이스라인 vs)
- 인지 과부하로 멈춘 사례 학습 일지에 *솔직 기록* — 횟수 감소 추세

### 이 step 에서 얻은 것
다중 세션이 *일상* 이 됐다. 단일 세션으로 돌아가는 게 어색하게 느껴지는 시점.

### 다음 step 으로의 다리
4 세션이 *commit* 까지는 잘 도달하지만, 그것들이 *통합* (PR 머지) 되는 흐름은 아직 학습 안 됨. Phase C 가 그 마지막 마일.

---

## Phase B 졸업 체크

- [ ] Step 7: 2-worktree 동시 운영 5회, 충돌 0
- [ ] Step 8: 색 매핑 + zk 셸 함수 + statusline 캡처
- [ ] Step 9: 동기화 시나리오 5건 git trail + SessionStart 훅 commit
- [ ] Step 10: analysis worktree 2주, 편집 commit 0, 식별 패턴 ≥3건
- [ ] Step 11: 4-세션 동시 ≥10회, 머지 PR 1.5배 증가, 과부하 사례 솔직 기록

다음: [03-phase-C-pr-and-verify.md](./03-phase-C-pr-and-verify.md)
