# Parallel Work with Git Worktree: 5 Gradient Steps

git worktree를 활용한 병렬 작업 내재화 로드맵.
각 Step은 이전 Step 위에 쌓이며, **모든 Step은 Git Bash에서 `claude` CLI로 실행한다.**

---

## 핵심 원칙

```
task : worktree : branch : claude 세션 = 1 : 1 : 1 : 1
```

각 worktree 디렉토리에서 `claude`를 실행하면 그 세션은 해당 worktree만 바라본다.
독립 task는 Git Bash 창 N개에서 동시에 실행된다.

---

## 터미널 레이아웃 기본 패턴

```
┌─────────────────────────┬─────────────────────────┐
│  Git Bash #1 (main)     │  Git Bash #2 (task-1)   │
│  조율·merge·모니터링    │  cd .worktrees/task-1   │
│                         │  claude                 │
├─────────────────────────┼─────────────────────────┤
│  Git Bash #3 (task-2)   │  Git Bash #4 (task-3)   │
│  cd .worktrees/task-2   │  cd .worktrees/task-3   │
│  claude                 │  claude                 │
└─────────────────────────┴─────────────────────────┘
```

---

## Step 1 — 수동 Worktree 격리 (1 worktree, 1 claude 세션)

> **목표**: worktree 1개 + `claude` 1개 실행 사이클을 손에 익힌다.

### 흐름

```
worktree 생성 → 해당 dir에서 claude 실행 → 프롬프트로 task 지시 → 완료 후 main에서 merge → worktree 제거
```

### Git Bash 명령어

```bash
# [터미널 1 — main] worktree 생성
git worktree add .worktrees/task-1 -b task/task-1
git worktree list

# [터미널 2 — task-1] worktree 디렉토리에서 claude 실행
cd .worktrees/task-1
claude
# → claude 세션이 .worktrees/task-1을 working directory로 인식함

# [터미널 1 — main] 구현 완료 후 merge
git merge task/task-1 --no-ff -m "feat(task-1): ..."
git worktree remove .worktrees/task-1
git branch -d task/task-1
```

### claude에게 지시하는 프롬프트 패턴

```
"현재 디렉토리가 task-1 worktree야.
{프로젝트 루트}/spec.json의 task-1을 구현해줘.
작업은 이 디렉토리 안에서만 해. 완료되면 알려줘."
```

> spec.json은 main 디렉토리에 있으므로 절대경로 또는 `../spec.json`으로 참조.

### 모니터링 (터미널 1에서 상태 확인)

```bash
# 모든 worktree 목록 + 브랜치
git worktree list

# task-1 worktree의 최신 커밋 확인
git -C .worktrees/task-1 log --oneline -5

# task-1 worktree의 변경 파일 확인
git -C .worktrees/task-1 status
```

### 이터레이션 목표
- worktree 생성 → claude 실행 → 구현 → merge → 제거 사이클 체화
- 예상 소요: task당 5~10분

---

## Step 2 — DAG 기반 순차 실행 (의존성 있는 task)

> **목표**: dependency graph를 읽고 의존 순서대로 worktree를 생성·실행·merge한다.

### 흐름

```
spec.json DAG 확인 → in-degree=0 task worktree 생성 → claude에서 구현
→ main merge → 다음 task worktree 생성 (main 최신 상태 기반) → 반복
```

### DAG 확인 후 지시 패턴 (터미널 1 — main)

```bash
# spec.json에서 의존성 없는 task 확인 후
git worktree add .worktrees/task-1 -b task/task-1

# 터미널 2에서
cd .worktrees/task-1
claude
# → "spec.json의 task-1 구현해줘"

# task-1 완료 후 main에서
git merge task/task-1 --no-ff -m "feat(task-1): ..."
git worktree remove .worktrees/task-1

# task-1에 의존하는 task-3 worktree 생성 (merge 후)
git worktree add .worktrees/task-3 -b task/task-3
# task-3은 이미 task-1이 반영된 main 기준으로 생성됨
```

### 의존 task가 같은 파일을 건드릴 때 rebase

```bash
# task-2가 완료됐는데 task-1보다 먼저 merge됐다면
cd .worktrees/task-3
git rebase main
# conflict 해결 후
git rebase --continue
```

### spec.json 확장 (수동 기입)

```json
{
  "id": "task-3",
  "status": "not_start",
  "dependencies": ["task-1"],
  "worktree": ".worktrees/task-3",
  "branch": "task/task-3"
}
```

### 이터레이션 목표
- DAG 순서를 worktree 생명주기로 번역하는 연습
- rebase conflict 패턴 파악

---

## Step 3 — 병렬 Worktree (독립 task 동시 실행)

> **목표**: 의존성 없는 task들을 Git Bash 창 N개에서 동시에 claude로 실행한다.

### 흐름

```
독립 task 목록 확인 → worktree N개 생성 → Git Bash 창 N개에서 각각 claude 실행
→ 완료 순으로 main에 merge
```

### 병렬 시작 (터미널 1 — main 조율)

```bash
# 독립 task 2개 worktree 동시 생성
git worktree add .worktrees/task-1 -b task/task-1
git worktree add .worktrees/task-2 -b task/task-2

git worktree list
# compound-practice          abc1234 [main]
# compound-practice/.worktrees/task-1  def5678 [task/task-1]
# compound-practice/.worktrees/task-2  ghi9012 [task/task-2]
```

### 각 터미널에서 claude 실행

```bash
# [터미널 2 — task-1 전용]
cd /c/Users/USER/IdeaProjects/compound-practice/.worktrees/task-1
claude
```

```bash
# [터미널 3 — task-2 전용]
cd /c/Users/USER/IdeaProjects/compound-practice/.worktrees/task-2
claude
```

### 각 claude 세션에 붙여넣을 프롬프트

```
[task-1 세션]
"현재 디렉토리는 task-1 worktree야.
/c/Users/USER/IdeaProjects/compound-practice/spec.json의 task-1을 구현해줘.
이 디렉토리 밖 파일은 수정하지 마. 완료되면 커밋하고 알려줘."
```

```
[task-2 세션]
"현재 디렉토리는 task-2 worktree야.
/c/Users/USER/IdeaProjects/compound-practice/spec.json의 task-2를 구현해줘.
이 디렉토리 밖 파일은 수정하지 마. 완료되면 커밋하고 알려줘."
```

### 병렬 모니터링 (터미널 1)

```bash
# 모든 worktree 커밋 상태 한눈에 보기
for wt in .worktrees/*/; do
  echo "=== $wt ==="
  git -C "$wt" log --oneline -3
  git -C "$wt" status -s
  echo ""
done

# 2초마다 갱신
while true; do
  clear
  for wt in .worktrees/*/; do
    echo "=== $wt ==="
    git -C "$wt" log --oneline -2
    git -C "$wt" status -s
    echo ""
  done
  sleep 2
done
```

### 완료 순서대로 merge (터미널 1)

```bash
# task-2가 먼저 완료됐다면
git merge task/task-2 --no-ff -m "feat(task-2): ..."
git worktree remove .worktrees/task-2

# task-1 완료 후
git merge task/task-1 --no-ff -m "feat(task-1): ..."
git worktree remove .worktrees/task-1
```

### 이터레이션 목표
- 2~3개 병렬 실행 → 15분 이내 결과 확인
- task 크기 = 파일 1~3개 수정 단위 유지

---

## Step 4 — PR + Issue 연동 (각 worktree claude 세션에서 gh 사용)

> **목표**: 각 worktree의 claude 세션이 구현 완료 후 직접 Issue + PR을 생성한다.

### 흐름

```
[터미널 1] worktree 생성 + issue 번호 확인
[터미널 N] claude 세션 → 구현 → PR 생성 (issue 링크)
[터미널 1] PR 리뷰 → merge → worktree 제거
```

### 각 worktree claude 세션에 붙여넣을 프롬프트 (구현 + PR까지)

```
"현재 디렉토리는 task-2 worktree야.
spec.json의 task-2를 구현하고:
1. 구현 완료 후 커밋
2. gh pr create로 PR 올려줘
   - base: main, head: task/task-2
   - title: spec.json task-2의 title
   - body: 구현 내용 요약 + 'closes #이슈번호'
완료되면 PR URL 알려줘."
```

### Issue 생성 프롬프트 (터미널 1 또는 해당 세션)

```
"spec.json의 task-2 내용으로 GitHub Issue 만들어줘.
label: task, assignee: suzhanlee"
```

### PR 리뷰 + merge (터미널 1 — main 조율)

```bash
# PR 리뷰
# claude 세션에서: "/gh-pr-review PR#N"

# merge (리뷰 완료 후)
gh pr merge N --merge --delete-branch
git worktree remove .worktrees/task-2
git fetch origin
git pull
```

### spec.json에 PR 정보 수동 기입

```json
{
  "id": "task-2",
  "status": "end",
  "dependencies": [],
  "worktree": ".worktrees/task-2",
  "branch": "task/task-2",
  "issue_url": "https://github.com/suzhanlee/compound-practice/issues/5",
  "pr_url": "https://github.com/suzhanlee/compound-practice/pull/6"
}
```

### 이터레이션 목표
- task → 구현 → PR → merge 한 사이클 5분 이내
- 병렬 PR이 DAG 순서대로 merge되는 흐름 체화

---

## Step 5 — 반자동 Skill 통합

> **목표**: 반복되는 프롬프트·명령 패턴을 Skill로 추출해 명령 1줄로 단축한다.

### 추출할 Skill 후보

| 반복 패턴 | Skill 이름 |
|---|---|
| spec.json 읽어서 worktree 일괄 생성 | `worktree-create` |
| 각 worktree claude 세션에 task 지시 자동 전달 | `worktree-dispatch` |
| 완료된 worktree → PR 자동 생성 | `worktree-pr` |
| DAG 기준 merge 순서 결정 + 실행 | `worktree-merge` |
| 모든 worktree 상태 한눈에 출력 | `worktree-status` |

### 최종 이상적 흐름 (Step 5 도달 후)

```bash
# [터미널 1 — main] 목표 입력 → spec 생성 → worktree 일괄 생성
/mini-specify "멤버십 포인트 적립 기능 추가"
/worktree-create   # spec.json 읽어서 독립 task worktree + branch 일괄 생성

# [터미널 2,3,4] 각각 worktree에서 claude 실행 후 /worktree-dispatch
cd .worktrees/task-1 && claude
# → /worktree-dispatch task-1  (spec에서 지시 자동 로드)

# [터미널 1] 완료된 것부터 순서대로
/worktree-merge    # DAG topological order로 PR merge
```

---

## 현재 위치 체크

```
[Step 1] 수동 Worktree 격리 + claude 1세션     ← 여기서 시작
[Step 2] DAG 기반 순차 실행 + rebase
[Step 3] 병렬 Worktree (Git Bash 창 N개 + claude N세션)
[Step 4] PR + Issue 연동 (gh 사용)
[Step 5] Skill 통합 (명령 단축)
```

### Step 1 첫 실습 명령어

```bash
# [터미널 1 — main]
git worktree add .worktrees/task-test -b task/task-test
git worktree list

# [터미널 2 — task-test 전용]
cd /c/Users/USER/IdeaProjects/compound-practice/.worktrees/task-test
claude
# → "현재 디렉토리는 task-test worktree야. ..."

# [터미널 1] 모니터링
while true; do clear; git worktree list; echo "---"; git -C .worktrees/task-test log --oneline -3; sleep 2; done
```
