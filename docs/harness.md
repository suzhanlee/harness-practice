# Mini-Harness: Self-Orchestrating Development Workflow

## Overview

**Mini-Harness** is a hook-based, self-orchestrating skill pipeline that automates the entire development workflow: from structured architectural decision-making through code implementation to learning capture. A single `/mini-harness [goal]` command triggers a complete chain of skills, with orchestration handled entirely by shell scripts reacting to Claude Code lifecycle events.

The harness is designed for **compound-practice**, a repository for practicing sophisticated software engineering patterns including Domain-Driven Design, architectural decision processes, and structured learning.

---

## Quick Start

```bash
/mini-harness "add shopping cart feature"
```

This single command:
1. Runs `/interview` to clarify requirements via Socratic questioning → `interview.json`
2. Runs `/council` to debate architectural decisions (informed by interview.json)
3. Runs `/mini-specify` to understand requirements
4. Runs `/taskify` to break requirements into executable tasks
5. Runs `/dependency-resolve` to order tasks by dependencies
6. Runs `/mini-execute` to implement tasks (with alternating validation loop)
7. Runs `/mini-compound` to promote learnings to permanent files

No manual intervention needed between steps.

---

## Skill Chain: What Each Skill Does

### 1. `/mini-harness [goal]`

**Entry point.** Registers the goal in `state.json` and delegates to the chain.

- **Input**: Goal string (e.g., "add shopping cart")
- **Output**: `state.json` created with `{skill_name, goal, timestamp, status}`
- **Action**: Minimal work; orchestration delegated to Stop hooks

### 2. `/interview [run_id:xxx]` (Socratic Requirements Interview)

**Clarifies the goal via structured questioning before architectural debate.**

- **Input**: run_id (reads original goal from state.json)
- **Output**: `.dev/requirements/run-{RUN_ID}/interview.json`
- **Flow**:
  1. Round 1 (Current State): 2 questions — what exists now, what triggered the need
  2. Round 2 (Desired Change): 2 questions — what changes after completion, how to measure success
  3. Round 3 (Boundaries): 2 questions — what's excluded, design constraints
  4. Synthesizes all answers into `refined_goal` (format: `[verb] [what] [for whom / to solve what]`)
  5. EnterPlanMode: shows synthesized interview.json for user confirmation
  6. Writes interview.json after ExitPlanMode approval
- **Output schema**: `original_goal`, `refined_goal`, `problem`, `users`, `success_criteria`, `out_of_scope`, `constraints`

### 3. `/council [topic]` (Structured Debate → ADR)

**Deliberative decision-making panel.** Uses 4-panel teams to debate architectural decisions.

- **Input**: Topic (automatically passed from mini-harness or manually specified)
- **Output**: ADR file written to `.dev/adr/YYYY-MM-DD-{slug}.md`
- **Flow**:
  1. Derives 3–5 analysis lenses from the topic
  2. Spawns 3–4 panelists in parallel (domain experts + devil's advocate) via `TeamCreate`
  3. Phase 1: Each panelist sends structured opinion (using `opinion-template.md`)
  4. Phase 2: Panelists debate via direct rebuttals
  5. Final ADR synthesized from all positions with tradeoff analysis
- **Reference**: `.claude/skills/council/reference/` (adr-template.md, opinion-template.md, rebuttal-template.md, summary-template.md)

### 4. `/mini-specify [goal] [adr:<path>]` (Requirement Planning)

**Bridges ADR to task breakdown.** Searches past learnings and generates a prioritized requirement list.

- **Input**: Goal + optional ADR path (passed from council)
- **Output**: `.dev/requirements/requirements.json` (3–6 items)
- **Flow**:
  1. Extracts keywords from goal
  2. Searches `.mini-harness/learnings/*.md` for matching rules (tag + rule text)
  3. Displays any relevant past learnings (closed feedback loop)
  4. Generates task list informed by past friction points
- **Output schema**: Array of requirement objects with `index`, `content`

### 5. `/taskify` (Task Breakdown)

**Converts requirements into executable task specs.**

- **Input**: `.dev/requirements/requirements.json`
- **Output**: `.dev/task/spec.json`
- **Tech Stack Detection**: Auto-detects pytest/jest/vitest/gradle/go test by scanning for pytest.ini, package.json, build.gradle, go.mod
- **Task Schema**: Each task has `index`, `action` (verb+object), `step` (3–5 implementation steps), `verification` (runnable CLI command), `status: "not_start"`
- **Reference**: `.claude/skills/taskify/reference/` (formats.md, jq-commands.md, templates/)

### 6. `/dependency-resolve` (Task Ordering)

**Infers and validates inter-task dependencies.**

- **Input**: `.dev/task/spec.json`
- **Output**: Same file, augmented with `dependencies: []` and `priority` fields
- **Dependency Inference**: Parses step text for:
  - Class/method name cross-references
  - Domain-layer ordering (domain → application → infrastructure)
  - File creation/modification order
  - Test dependency patterns
- **Validation**: Rejects circular dependencies via DFS
- **Priority Assignment**: P0 (no deps), P1 (has deps), P2 (chain terminal)

### 7. `/mini-execute` (Implementation Loop + Ralph Loop)

**Implements all tasks in dependency order and records friction.**

- **Input**: `.dev/task/spec.json` (must have `dependencies` field from prior `/dependency-resolve`)
- **Output**: Updated spec with `status: "end"` for successful tasks; friction logged to `.mini-harness/session/learnings.json`
- **Flow**:
  1. Computes topological execution order
  2. Sets `status = "processing"` for each task
  3. Implements all `step` items
  4. Runs `verification` command
  5. Exit code 0 → `status = "end"` ✓
  6. Exit code != 0 → `status = "not_start"`, continues
  7. After each task, self-assesses friction: Was approach changed? Was workaround used? Appends entry to `session/learnings.json` if reusable rule found
- **Ralph Loop** (Stop hook #1): After mini-execute exits:
  - Remaining incomplete tasks + `last_action = "execute"` → block, run `validate-tasks` agent, set `last_action = "validate"`
  - Remaining incomplete tasks + `last_action = "validate"` → block, re-run `/mini-execute`
  - No remaining tasks → approve, hand off to mini-compound

### 8. `/mini-compound` (Learning Promotion)

**Promotes session learnings to permanent searchable files.**

- **Input**: `.mini-harness/session/learnings.json`
- **Output**: `.mini-harness/learnings/YYYY-MM-DD-{slug}.md` files (date-slugged markdown)
- **Flow**:
  1. Converts each JSON entry to standalone markdown with frontmatter (`date`, `tags`)
  2. Generates slug from rule keyword (falls back to first tag if in Korean)
  3. Appends `-2`, `-3` suffix for same-day duplicates
  4. Deletes `session/learnings.json` (unlock for exit)
  5. Deletes `state.json` (chain complete)

---

## Hook Chain: Orchestration Layer

Four lifecycle events are hooked in `.claude/settings.json`. All hooks react to events; no manual prompting between steps.

### Hook 1: SessionStart (compact) — `scripts/mini-start-session.sh`

**Compact recovery guard.** Fires when a new session starts after context compaction.

- Step 1: Looks up `.dev/harness/sessions/{session_id}.run_id` to find active run
- Step 2: If no pointer, scans `.dev/harness/runs/` for a single active run and auto-recovers
- Step 3: If active run has incomplete tasks → blocks, instructs user to re-run `/mini-execute run_id:xxx`
- Handles the case where compact generates a new `session_id` but a run was in progress

### Hook 2: PreToolUse (Skill) — `scripts/mini-pre-tool-use.sh`

**Run state lifecycle manager.** Fires before any Skill tool call.

- First call (`mini-harness`): generates a `run_id`, creates `.dev/harness/runs/run-{run_id}.json` with goal + run-scoped `paths`, registers `.dev/harness/sessions/{session_id}.run_id`
- Subsequent calls: resolves state file via session pointer, updates `skill_name` while preserving `goal` and `paths`
- Special case: `mini-execute` also sets `last_action = "execute"` (for ralph loop alternation)
- If no session pointer found (manual invocation without harness): hook is a no-op

### Hook 3: PostToolUse (Skill) — `scripts/mini-post-tool-use.sh`

**Guard for mini-harness.** Fires after any Skill tool call.

- Resets `status = "processing"` in the run state file for the `mini-harness` skill specifically
- Prevents premature chain termination

### Hook 4: Stop (Two Sequential Hooks)

#### Stop Hook #1: `scripts/execute-stop.sh` (Ralph Loop Controller)

Only acts when `skill_name == "mini-execute"`. Implements the alternating execute ↔ validate loop.

- Reads spec.json: are there remaining tasks with `status != "end"`?
  - **Yes, `last_action == "execute"`** → transitions to `last_action = "validate"`, blocks exit, runs `validate-tasks` agent
  - **Yes, `last_action == "validate"`** → transitions back to `last_action = "execute"`, blocks exit, re-runs `/mini-execute`
  - **No remaining tasks** → approves exit to Stop Hook #2

#### Stop Hook #2: `scripts/mini-stop.sh` (Main Orchestrator)

Drives the entire skill chain via state machine.

```
state.json doesn't exist
  → compound guard: if session/learnings.json exists, block exit, ask to run /mini-compound
  → else approve exit

state.json exists, skill_name is:
  mini-harness         → set status=end, block, instruct: /interview run_id:xxx
  interview            → set status=end, block, instruct: /council refined_goal interview:path run_id:xxx
  council              → set status=end, block, instruct: /mini-specify [adr:path]
  mini-specify         → set status=end, block, instruct: /taskify
  taskify              → set status=end, block, instruct: /dependency-resolve
  dependency-resolve   → set status=end, block, instruct: /mini-execute
  mini-execute         → (delegate to execute-stop.sh ralph loop)
  mini-compound        → delete state.json, approve exit
```

---

## State Machine: run state files

**Location**: `.dev/harness/runs/run-{run_id}.json` — one file per active run.

**Session pointer**: `.dev/harness/sessions/{session_id}.run_id` — maps the current Claude session to a `run_id`. Re-registered whenever a hook fires and detects a new `session_id` (post-compact recovery).

**Schema:**
```json
{
  "run_id": "20260419-153042-a3f1",
  "skill_name": "mini-harness | interview | council | mini-specify | taskify | dependency-resolve | mini-execute | mini-compound",
  "status": "processing | end",
  "goal": "<original goal string>",
  "timestamp": "ISO-8601 UTC",
  "paths": {
    "requirements": ".dev/requirements/run-{run_id}/requirements.json",
    "spec": ".dev/task/run-{run_id}/spec.json"
  },
  "last_action": "execute | validate"
}
```

- **Created**: Fresh on first `/mini-harness` call by PreToolUse hook; `run_id` format: `YYYYMMDD-HHMMSS-{4hex}`
- **Updated**: `skill_name` before each Skill invocation; `status = "end"` when Stop hooks transition
- **paths**: Run-scoped file locations read by all downstream skills and hooks via `jq '.paths.spec'`
- **last_action**: Alternates "execute" ↔ "validate" during ralph loop (mini-execute only)
- **Deleted**: Run state file + session pointer deleted by `mini-stop.sh` when `mini-compound` completes

---

## Learnings System: Session → Permanent

Two-layer feedback loop ensuring past implementation friction shapes future task planning.

### Session Layer (Transient)

During `/mini-execute`, when a task deviates from expectations, an entry is appended to `.mini-harness/session/learnings.json`:

```json
{
  "problem": "Description of issue encountered",
  "cause": "Root cause analysis",
  "rule": "Actionable directive for future work",
  "tags": ["tag1", "tag2"]
}
```

**Quality filter**: Only recorded if a clear, reusable rule can be derived. Vague or purely descriptive entries are rejected.

### Permanent Layer (Searchable)

`/mini-compound` converts each session entry to a markdown file:

```
.mini-harness/learnings/2026-04-18-frozen-dataclass-mutation.md
```

With frontmatter:
```yaml
---
date: 2026-04-18
tags: [ddd, frozen-dataclass, value-object]
---

## Problem
...

## Cause
...

## Rule
...
```

### Retrieval & Feedback

`/mini-specify` searches `.mini-harness/learnings/*.md` by globbing and grepping for keyword/tag matches, displaying relevant rules to the user during requirement planning. This closes the loop: friction discovered during implementation directly informs future task scope.

### Promotion Guard

Stop Hook #2's **compound guard** ensures learning promotion cannot be skipped:
- If `session/learnings.json` exists and `state.json` does not → every exit attempt is blocked
- Blocks until `/mini-compound` runs and deletes the session file

---

## Data Files Reference

| File | Purpose | Lifecycle |
|---|---|---|
| `.dev/harness/runs/run-{run_id}.json` | Run orchestration state (created/updated by hooks) | Deleted by `mini-stop.sh` at chain completion |
| `.dev/harness/sessions/{session_id}.run_id` | Session→run_id pointer | Created on first hook fire; deleted with run state |
| `.dev/requirements/run-{RUN_ID}/interview.json` | Socratic interview results (written by /interview) | Injected as /council context |
| `.dev/requirements/run-{RUN_ID}/requirements.json` | Business requirements (written by /mini-specify) | Read by /taskify |
| `.dev/task/run-{RUN_ID}/spec.json` | Executable task breakdown (written by /taskify, augmented by /dependency-resolve) | Read/written by /mini-execute |
| `.dev/adr/YYYY-MM-DD-{slug}.md` | Architecture decision records (written by /council) | Referenced by /mini-specify |
| `.mini-harness/session/learnings.json` | Transient friction logs (appended during /mini-execute) | Promoted to permanent .md files by /mini-compound |
| `.mini-harness/learnings/*.md` | Permanent searchable rules (written by /mini-compound) | Searched by /mini-specify |

---

## Complete Data Flow

```
User: /mini-harness "add shopping cart"
  ↓
mini-pre-tool-use.sh → creates .dev/harness/runs/run-{run_id}.json
                      + .dev/harness/sessions/{session_id}.run_id
  ↓
[mini-harness executes — registers goal only]
  ↓
mini-stop.sh case:mini-harness → BLOCK: "/interview run_id:xxx"
  ↓
mini-pre-tool-use.sh → updates run state {skill_name: "interview"}
  ↓
[interview: 3 rounds of AskUserQuestion → user confirms → writes .dev/requirements/run-xxx/interview.json]
  ↓
mini-stop.sh case:interview → BLOCK: "/council refined_goal interview:.dev/requirements/run-xxx/interview.json run_id:xxx"
  ↓
mini-pre-tool-use.sh → updates run state {skill_name: "council"}
  ↓
[council loads interview.json → spawns product-owner + expert + devil's advocate → writes ADR]
  ↓
mini-stop.sh case:council → BLOCK: "/mini-specify goal adr:.dev/adr/YYYY-MM-DD-slug.md run_id:xxx"
  ↓
mini-pre-tool-use.sh → updates run state {skill_name: "mini-specify"}
  ↓
[mini-specify searches learnings, writes .dev/requirements/run-xxx/requirements.json]
  ↓
mini-stop.sh case:mini-specify → BLOCK: "/taskify run_id:xxx"
  ↓
mini-pre-tool-use.sh → updates run state {skill_name: "taskify"}
  ↓
[taskify reads requirements.json, detects tech, writes .dev/task/run-xxx/spec.json]
  ↓
mini-stop.sh case:taskify → BLOCK: "/dependency-resolve run_id:xxx"
  ↓
mini-pre-tool-use.sh → updates run state {skill_name: "dependency-resolve"}
  ↓
[dependency-resolve infers deps, assigns priority, rewrites spec.json]
  ↓
mini-stop.sh case:dependency-resolve → BLOCK: "/mini-execute run_id:xxx"
  ↓
mini-pre-tool-use.sh → updates run state {skill_name: "mini-execute", last_action: "execute"}
  ↓
[mini-execute implements tasks in topo order, records friction]
  ↓
execute-stop.sh (Stop Hook #1) ralph loop:
  ├─ remaining tasks + last_action=execute
  │  → set last_action=validate → BLOCK: run validate-tasks agent
  │  → validate-tasks re-runs verification, reverts failed tasks
  │  → set last_action=execute → BLOCK: "/mini-execute run_id:xxx"
  │  [repeat until all tasks end]
  └─ no remaining tasks → APPROVE (pass through to mini-stop.sh)
  ↓
mini-stop.sh (Stop Hook #2) case:mini-execute → BLOCK: "/mini-compound run_id:xxx"
  ↓
mini-pre-tool-use.sh → updates run state {skill_name: "mini-compound"}
  ↓
[mini-compound: session/learnings.json → .mini-harness/learnings/*.md → deletes session file]
  ↓
mini-stop.sh case:mini-compound → DELETE run-{run_id}.json + session pointer → APPROVE exit
```

---

## Configuration

`.claude/settings.json` sets `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` to enable `council` to use team-based parallel debate.

---

## Troubleshooting

**Loop recovery blocked exit?**
- Re-run `/mini-execute`. If still failing, check spec.json for `status: "end"` tasks; if any have non-zero verification exit codes, set them back to `"not_start"` and re-run.

**session/learnings.json persisting after /mini-compound?**
- Mini-compound should delete it. If it persists, Stop Hook #2 compound guard will block exit until file is manually deleted and `/mini-compound` is re-run.

**state.json persisting after chain completion?**
- Should be deleted by mini-compound's final Stop Hook #2 case. If it persists, manually delete it to unblock exit; then audit the last skill's hook firing.

---

## References

- ADR and decision records: `.dev/adr/`
- Learnings: `.mini-harness/learnings/`
- Skill templates and references: `.claude/skills/{council,mini-specify,taskify,dependency-resolve,mini-execute,mini-compound}/`
