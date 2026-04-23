# mini-harness

Hook-based autonomous development workflow for Claude Code.

---

## Overview

mini-harness is a stop-hook-driven pipeline that takes a goal and autonomously chains structured decision-making, task planning, implementation, validation, and learning capture — without manual intervention between steps.

The entry point is `/mini-harness [goal]`. From there, the chain runs: `interview → council → mini-specify → taskify → dependency-resolve → mini-execute → mini-compound`. Each skill is a trigger point; `scripts/mini-stop.sh` is the actual orchestrator. It reads `.dev/harness/runs/run-{run_id}.json` after every skill exits, decides what runs next, and either blocks Claude from stopping or approves exit.

> **kiosk/ is not the product.** It is a DDD mini-project (self-service kiosk ordering system) used purely as a sandbox to exercise and stress-test the harness. The architectural decisions, ADRs, and learnings it generates are artifacts of harness validation — not of the kiosk domain itself.

---

## Full Pipeline

```
/mini-harness [goal]
      │
      ▼  [PreToolUse: mini-pre-tool-use.sh → creates state.json + session pointer under run-{run_id}/]
  mini-harness skill
      │
      ▼  [Stop: mini-stop.sh → BLOCK → "run /interview run_id:xxx"]
  /interview
      │   Socratic questioning: 3 rounds × 2 questions = 6 total.
      │   Round 1: current state. Round 2: desired change. Round 3: boundaries.
      │   Synthesizes refined_goal. AskUserQuestion for user confirmation.
      │   Writes .dev/harness/runs/run-{run_id}/interview/interview.json
      │
      ▼  [Stop: mini-stop.sh → BLOCK → "run /council refined_goal interview:<path>"]
   /council
      │   Loads interview.json. Uses refined_goal as debate topic.
      │   Mandatory panelists: product-owner + domain expert + devil's advocate.
      │   Mandatory lens: 사용자 가치 / 요구사항 충족도.
      │   Phase 1: structured opinions. Phase 2: direct rebuttals.
      │   Writes ADR to .dev/harness/runs/run-{run_id}/adr/YYYY-MM-DD-{slug}.md
      │
      ▼  [Stop: mini-stop.sh → BLOCK → "run /mini-specify adr:<path>"]
  /mini-specify
      │   Loads ADR. Searches .mini-harness/learnings/ by tag/keyword.
      │   Surfaces past friction rules.
      │   Writes .dev/harness/runs/run-{run_id}/requirement/requirements.json
      │
      ▼  [Stop: mini-stop.sh → BLOCK → "run /taskify run_id:xxx"]
   /taskify
      │   Reads requirements.json. Auto-detects tech stack.
      │   Breaks each requirement into tasks: action + steps + verification command.
      │   Writes .dev/harness/runs/run-{run_id}/spec/spec.json
      │
      ▼  [Stop: mini-stop.sh → BLOCK → "run /dependency-resolve run_id:xxx"]
  /dependency-resolve
      │   Analyzes step text for cross-references and layer ordering.
      │   Builds dependencies[] per task. Validates no circular deps.
      │   Assigns priority: P0 (no deps) → P1 (has deps) → P2 (terminal).
      │   TaskCreate per task → Claude task ID → writes task_id to spec.json.
      │   Builds DAG via TaskUpdate(addBlockedBy).
      │
      ▼  [Stop: mini-stop.sh → BLOCK → "run /mini-execute run_id:xxx"]
  /mini-execute  ◄──────────────────────────────────────────────┐
      │   Reads DAG from TaskList. Dispatches task-executor        │
      │   sub-agents in parallel (blockedBy=[] tasks first).       │
      │   validate-tasks agent owns spec.json status updates.      │
      │   Records friction from agent summaries.                   │
      │                                                            │
      ▼  [Stop Hook #1: execute-stop.sh — ralph loop]              │
  validate-tasks agent                                            │
      │   Reruns verifications for all completed tasks.           │
      │   Reverts failed tasks to "not_start".                    │
      │                                                           │
      ├── tasks remain? ──── YES ─────────────────────────────────┘
      │
      NO  (all tasks status = "end")
      │
      ▼  [Stop Hook #2: mini-stop.sh → BLOCK → "run /mini-compound run_id:xxx"]
  /mini-compound
      │   Reads session/learnings.json.
      │   Converts each entry to dated .mini-harness/learnings/*.md with frontmatter.
      │   Deletes session/learnings.json.
      │
      ▼  [Stop Hook #2: mini-stop.sh → DELETE run state + session pointer → APPROVE exit]
     DONE
```

---

## Hook Roles

| Hook | Script | Role |
|---|---|---|
| PreToolUse (Skill) | `mini-pre-tool-use.sh` | Creates `run-{run_id}/state/state.json` + session pointer on first call; updates `skill_name` on subsequent calls |
| PostToolUse (Skill) | `mini-post-tool-use.sh` | Keeps `status = "processing"` on `mini-harness` to prevent premature exit |
| Stop #1 | `execute-stop.sh` | Ralph loop controller: alternates `execute ↔ validate` until all tasks pass |
| Stop #2 | `mini-stop.sh` | **Main orchestrator**: reads run state, decides next skill, blocks or approves exit |
| SessionStart (compact) | `mini-start-session.sh` | Compact recovery guard: reconnects new session_id to active run, blocks if tasks remain |

Hook configuration lives in `.claude/settings.json`. Two Stop hooks fire sequentially: `execute-stop.sh` handles the execute/validate alternation and approves when done, then `mini-stop.sh` advances the chain. A shared `scripts/harness-lib.sh` provides `resolve_run_state` and `generate_run_id` helpers used by all scripts.

---

## Skills

### `/mini-harness [goal]`
Entry point. Accepts a goal string. The `mini-pre-tool-use.sh` hook generates a `run_id`, creates `.dev/harness/runs/run-{run_id}/state/state.json` with the goal and run-scoped paths, and registers a session pointer at `.dev/harness/runs/run-{run_id}/sessions/{session_id}.run_id`. The skill itself does minimal work — its purpose is to be the first hook trigger. `mini-stop.sh` then blocks exit and instructs Claude to run `/interview`.

### `/interview`
Socratic requirements interview. Asks 6 structured questions across 3 rounds (current state → desired change → boundaries), synthesizes answers into a `refined_goal`, and writes `interview/interview.json` under the run directory. Uses `EnterPlanMode` to confirm the synthesized requirements before saving. The refined goal and constraints are then passed to `/council` as context.

### `/council`
Structured architectural debate that produces an ADR. Loads `interview.json` when available (passed via `interview:` arg from `mini-stop.sh`), using `refined_goal` as the debate topic. Always includes a **product-owner** panelist and a **사용자 가치 / 요구사항 충족도** lens. Derives 3–5 analysis lenses from the topic, spawns panelists in parallel via `TeamCreate` (including a devil's advocate), runs a two-phase debate (initial positions → direct rebuttals), and writes the final ADR to `adr/YYYY-MM-DD-{slug}.md` under the run directory. Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in env.

### `/mini-specify [goal] [adr:<path>]`
Bridges the ADR to a task list. Optionally loads the ADR from the `adr:` parameter (passed automatically by `mini-stop.sh`). Searches `.mini-harness/learnings/*.md` by tag/keyword match and surfaces relevant past rules before planning begins. Writes `requirement/requirements.json` under the run directory.

### `/taskify`
Converts requirements to an executable task spec. Auto-detects the tech stack (pytest.ini → Python, package.json → Node.js, etc.). Each task gets: an `action` (verb + object), `step` (3–5 imperative implementation steps), and `verification` (a runnable CLI command). Writes `spec/spec.json` under the run directory.

### `/dependency-resolve`
Infers inter-task dependencies by analyzing step text for class/method cross-references and domain layer ordering (domain → application → infrastructure). Validates no circular dependencies via DFS. Assigns priority: P0 (no deps, run first), P1 (has deps), P2 (terminal). Rewrites `spec.json` in place. TaskCreate 반환 Claude task ID를 즉시 spec.json의 `task_id`로 저장. TaskUpdate(addBlockedBy)로 의존성 DAG를 Claude task 시스템에 등록.

### `/mini-execute`
task-executor 서브 에이전트에 구현을 위임. DAG의 `blockedBy`가 비어 있는 태스크들을 단일 메시지에 병렬 Agent 호출로 dispatch. validate-tasks가 spec.json status 업데이트를 담당. 마찰은 task-executor summary 기반으로 session/learnings.json에 기록.

### `/mini-compound`
Promotes transient session learnings to permanent, searchable files. Reads `session/learnings.json`, converts each entry to a dated markdown file with frontmatter (`date`, `tags`) in `.mini-harness/learnings/`, then deletes the session file. Deletion unlocks `mini-stop.sh` to approve exit.

---

## The Ralph Loop (execute ↔ validate)

The most non-obvious mechanism in the harness. `execute-stop.sh` controls it via a `last_action` field in `state.json`.

```
mini-execute exits
      │
      ▼
execute-stop.sh checks: any tasks with status != "end"?
      │
      ├── NO → approve exit → delegate to mini-stop.sh
      │
      └── YES
            │
            ├── last_action = "execute"
            │     → set last_action = "validate"
            │     → BLOCK: run validate-tasks agent
            │
            └── last_action = "validate"
                  → set last_action = "execute"
                  → BLOCK: re-run /mini-execute
```

The alternation prevents infinite loops: each iteration switches the toggle, so the loop only re-runs execute after a validation pass has run.

---

## Learning Loop

Every implementation run feeds the next one.

```
mini-execute encounters friction
           │
           ▼
  session/learnings.json  (transient, one run)
    { problem, cause, rule, tags }
           │
      /mini-compound
           │
           ▼
  .mini-harness/learnings/YYYY-MM-DD-{slug}.md  (permanent)
    ---
    date: YYYY-MM-DD
    tags: [tag1, tag2]
    ---
    ## Problem / ## Cause / ## Rule
           │
    /mini-specify  (next run)
           │
           ▼
  searches learnings by tag/keyword
  → surfaces relevant rules before planning begins
```

Quality gate: `mini-execute` only records entries where a clear, reusable rule can be stated. Vague or descriptive entries are skipped.

---

## Run Artifacts

Every run of the harness produces a self-contained directory under `.dev/harness/runs/run-{run_id}/` with five artifact kinds, each written by a specific skill and read by the next one in the chain. The whole directory is the single source of truth for the run — no artifact is written outside of it.

```
.dev/harness/runs/run-{run_id}/
  state/state.json              ← mini-pre-tool-use.sh  (live, mutable)
  interview/interview.json      ← /interview
  adr/YYYY-MM-DD-{slug}.md      ← /council
  requirement/requirements.json ← /mini-specify
  spec/spec.json                ← /taskify  (mutated by /dependency-resolve, /mini-execute, validate-tasks)
  sessions/{session_id}.run_id  ← session→run pointer (empty file, name is the mapping)
```

### `state/state.json` — live run state

Created by `mini-pre-tool-use.sh` on the first `/mini-harness` call, mutated throughout the run, deleted by `mini-stop.sh` when `mini-compound` completes.

```json
{
  "run_id": "20260419-074829-890e",
  "skill_name": "mini-harness | interview | council | mini-specify | taskify | dependency-resolve | mini-execute | mini-compound",
  "status": "processing | end",
  "goal": "<original goal string>",
  "timestamp": "<ISO-8601 UTC>",
  "paths": {
    "run_dir":      ".dev/harness/runs/run-{run_id}",
    "state":        ".dev/harness/runs/run-{run_id}/state/state.json",
    "interview":    ".dev/harness/runs/run-{run_id}/interview/interview.json",
    "requirements": ".dev/harness/runs/run-{run_id}/requirement/requirements.json",
    "spec":         ".dev/harness/runs/run-{run_id}/spec/spec.json",
    "adr_dir":      ".dev/harness/runs/run-{run_id}/adr",
    "sessions_dir": ".dev/harness/runs/run-{run_id}/sessions"
  },
  "last_action": "execute | validate"
}
```

`paths` is the authoritative map that every hook and skill uses to locate artifacts — skills must not reconstruct paths from `run_id`. `last_action` is only present during `/mini-execute` (ralph loop toggle). `skill_name` is advanced before each skill; `status` flips to `"end"` during transitions by `mini-stop.sh`.

### `interview/interview.json` — Socratic output

Written by `/interview`. Input to `/council`.

```json
{
  "run_id": "20260419-074829-890e",
  "original_goal": "<user's raw goal>",
  "refined_goal":  "<synthesized goal after 6 questions>",
  "problem":       "<problem statement>",
  "users":            ["<persona>", ...],
  "success_criteria": ["<measurable outcome>", ...],
  "out_of_scope":     ["<explicitly excluded>", ...],
  "constraints":      ["<hard constraint>", ...]
}
```

`refined_goal` becomes the debate topic for `/council`; `constraints` + `out_of_scope` seed the devil's-advocate lens.

### `adr/YYYY-MM-DD-{slug}.md` — council decision

Written by `/council` as Markdown (not JSON — ADRs are prose). Standard ADR sections: **Context**, **Options considered** (one per panelist), **Rebuttals**, **Decision**, **Consequences**. The slug is derived from `refined_goal`. One ADR per run; `/mini-specify` loads it via the `adr:` arg from `mini-stop.sh`.

### `requirement/requirements.json` — planning output

Written by `/mini-specify`. Input to `/taskify`. Each requirement is a single bounded deliverable that maps to 1–N tasks downstream.

```json
{
  "run_id": "20260419-074829-890e",
  "goal":   "<refined_goal, copied from interview>",
  "requirements": [
    { "index": 1, "content": "<what must be built, in one sentence>" },
    { "index": 2, "content": "..." }
  ]
}
```

### `spec/spec.json` — executable task DAG

The most heavily mutated artifact. Written by `/taskify`, enriched by `/dependency-resolve` (adds `task_id`, `dependencies`, `priority`), and mutated by `validate-tasks` (flips `status`).

```json
{
  "run_id": "20260419-074829-890e",
  "goal":   "<refined_goal>",
  "tasks": [
    {
      "task_id":      "<Claude task ID assigned by TaskCreate>",
      "action":       "<verb + object, one line>",
      "step":         ["<imperative step 1>", "<step 2>", "..."],
      "verification": "<runnable CLI command, e.g. pytest tests/x.py::test_y -v>",
      "status":       "not_start | in_progress | end",
      "dependencies": [0, 1],
      "priority":     "P0 | P1 | P2"
    }
  ]
}
```

- `dependencies` are **indices into the `tasks` array** (not task_ids). `/dependency-resolve` infers them from step text, then calls `TaskUpdate(addBlockedBy)` to mirror the DAG into Claude's task system.
- `priority`: P0 = no deps (run first), P1 = has deps, P2 = terminal (depended upon by nothing else).
- `status` is the single source of truth for ralph-loop termination — `execute-stop.sh` exits when every task has `status: "end"`.
- `verification` must be a single shell command returning non-zero on failure; `validate-tasks` runs it verbatim.

### `sessions/{session_id}.run_id` — session pointer

An empty marker file whose filename maps the current Claude session to this run. Recreated automatically after compact by `mini-start-session.sh`, so a mid-run compact can reattach the new session_id without losing state. Deleted alongside the run directory on completion.

---

## Quick Start

```bash
# Run the full harness on a goal
/mini-harness "add discount feature to kiosk"
```

The harness takes over from there. Each skill will be invoked automatically by the stop hooks. If the session is interrupted mid-execute, `mini-start-session.sh` will block the next user message and instruct you to re-run `/mini-execute` to resume.

---

## Repository Layout

```
scripts/
  mini-stop.sh             # Main orchestrator (Stop hook #2)
  execute-stop.sh          # Ralph loop controller (Stop hook #1)
  mini-pre-tool-use.sh     # Run state initialization (PreToolUse hook)
  mini-post-tool-use.sh    # Status guard (PostToolUse hook)
  mini-start-session.sh    # Compact recovery guard (SessionStart hook)
  harness-lib.sh           # Shared helpers: resolve_run_state, generate_run_id

.claude/
  settings.json            # Hook configuration + env vars
  skills/                  # Skill definitions
  agents/                  # Sub-agent definitions
    task-executor.md       # Implements exactly one spec task, returns Done/Failed JSON
    validate-tasks.md      # Re-verifies "end" tasks, reverts failures to "not_start"

.mini-harness/
  learnings/               # Permanent learning library (*.md, tagged)
  session/                 # Transient friction log (learnings.json)

.dev/
  harness/
    runs/
      run-{run_id}/        # one directory per active run, deleted on completion
        state/state.json              # live run state (mini-pre-tool-use.sh)
        interview/interview.json      # /interview output
        adr/YYYY-MM-DD-{slug}.md      # /council output
        requirement/requirements.json # /mini-specify output
        spec/spec.json                # /taskify → /dependency-resolve → /mini-execute
        sessions/{session_id}.run_id  # session→run pointer (empty marker)

kiosk/                     # Mini-project sandbox — test vehicle for the harness
  domain/                  # DDD domain models (entities, value objects, repositories)
  application/             # Use cases
  infrastructure/          # In-memory repository implementations
  cli.py                   # Interactive CLI entry point

tests/                     # Test suite for kiosk (used as harness verification targets)
docs/
  harness.md               # Detailed harness skill reference
```

<!-- harness-eval-badge:start -->
![Harness Score](https://img.shields.io/badge/harness-5.9%2F10-red)
![Harness Grade](https://img.shields.io/badge/grade-D-red)
![Last Eval](https://img.shields.io/badge/eval-2026--04--23-blue)
<!-- harness-eval-badge:end -->
