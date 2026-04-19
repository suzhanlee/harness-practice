# mini-harness

Hook-based autonomous development workflow for Claude Code.

---

## Overview

mini-harness is a stop-hook-driven pipeline that takes a goal and autonomously chains structured decision-making, task planning, implementation, validation, and learning capture — without manual intervention between steps.

The entry point is `/mini-harness [goal]`. From there, the chain runs: `interview → council → mini-specify → taskify → dependency-resolve → mini-execute → mini-compound`. Each skill is a trigger point; `scripts/mini-stop.sh` is the actual orchestrator. It reads `.claude/state/state.json` after every skill exits, decides what runs next, and either blocks Claude from stopping or approves exit.

> **kiosk/ is not the product.** It is a DDD mini-project (self-service kiosk ordering system) used purely as a sandbox to exercise and stress-test the harness. The architectural decisions, ADRs, and learnings it generates are artifacts of harness validation — not of the kiosk domain itself.

---

## Full Pipeline

```
/mini-harness [goal]
      │
      ▼  [PreToolUse: mini-pre-tool-use.sh → creates state.json]
  mini-harness skill
      │
      ▼  [Stop: mini-stop.sh → BLOCK → "run /interview run_id:xxx"]
  /interview
      │   Socratic questioning: 3 rounds × 2 questions = 6 total.
      │   Round 1: current state. Round 2: desired change. Round 3: boundaries.
      │   Synthesizes refined_goal. EnterPlanMode for user confirmation.
      │   Writes .dev/requirements/run-{RUN_ID}/interview.json
      │
      ▼  [Stop: mini-stop.sh → BLOCK → "run /council refined_goal interview:<path>"]
   /council
      │   Loads interview.json. Uses refined_goal as debate topic.
      │   Mandatory panelists: product-owner + domain expert + devil's advocate.
      │   Mandatory lens: 사용자 가치 / 요구사항 충족도.
      │   Phase 1: structured opinions. Phase 2: direct rebuttals.
      │   Writes ADR to .dev/adr/YYYY-MM-DD-{slug}.md
      │
      ▼  [Stop: mini-stop.sh → BLOCK → "run /mini-specify adr:<path>"]
  /mini-specify
      │   Loads ADR. Searches .mini-harness/learnings/ by tag/keyword.
      │   Surfaces past friction rules. Writes .dev/requirements/requirements.json
      │
      ▼  [Stop: mini-stop.sh → BLOCK → "run /taskify"]
   /taskify
      │   Reads requirements.json. Auto-detects tech stack.
      │   Breaks each requirement into tasks: action + steps + verification command.
      │   Writes .dev/task/spec.json
      │
      ▼  [Stop: mini-stop.sh → BLOCK → "run /dependency-resolve"]
  /dependency-resolve
      │   Analyzes step text for cross-references and layer ordering.
      │   Builds dependencies[] per task. Validates no circular deps.
      │   Assigns priority: P0 (no deps) → P1 (has deps) → P2 (terminal).
      │   Rewrites spec.json with dependencies and priority fields.
      │
      ▼  [Stop: mini-stop.sh → BLOCK → "run /mini-execute"]
  /mini-execute  ◄──────────────────────────────────────────────┐
      │   Topological sort. Implements tasks in order.            │
      │   Runs verification command after each task.              │
      │   Records friction → .mini-harness/session/learnings.json │
      │                                                           │
      ▼  [Stop: execute-stop.sh — ralph loop]                     │
  validate-tasks                                                  │
      │   Reruns verifications for all completed tasks.           │
      │   Reverts failed tasks to "not_start".                    │
      │                                                           │
      ├── tasks remain? ──── YES ─────────────────────────────────┘
      │
      NO  (all tasks status = "end")
      │
      ▼  [Stop: mini-stop.sh → BLOCK → "run /mini-compound"]
  /mini-compound
      │   Reads session/learnings.json.
      │   Converts each entry to dated .mini-harness/learnings/*.md with frontmatter.
      │   Deletes session/learnings.json.
      │
      ▼  [Stop: mini-stop.sh → DELETE state.json → APPROVE exit]
     DONE
```

---

## Hook Roles

| Hook | Script | Role |
|---|---|---|
| PreToolUse (Skill) | `mini-pre-tool-use.sh` | Creates/updates `state.json` before each skill invocation |
| PostToolUse (Skill) | `mini-post-tool-use.sh` | Keeps `status = "processing"` on `mini-harness` to prevent premature exit |
| Stop | `execute-stop.sh` | Ralph loop controller: alternates `execute ↔ validate` until all tasks pass |
| Stop | `mini-stop.sh` | **Main orchestrator**: reads `state.json`, decides next skill, blocks or approves exit |
| UserPromptSubmit | `mini-start-session.sh` | Recovery guard: blocks user input if session was interrupted mid-execute |

Hook configuration lives in `.claude/settings.json`. Two Stop hooks fire sequentially: `execute-stop.sh` handles the execute/validate alternation and delegates to `mini-stop.sh` once all tasks are done.

---

## Skills

### `/mini-harness [goal]`
Entry point. Accepts a goal string. The `mini-pre-tool-use.sh` hook creates `.claude/state/state.json` with the goal and timestamp. The skill itself does minimal work — its purpose is to be the first hook trigger. `mini-stop.sh` then blocks exit and instructs Claude to run `/council`.

### `/interview`
Socratic requirements interview. Asks 6 structured questions across 3 rounds (current state → desired change → boundaries), synthesizes answers into a `refined_goal`, and writes `.dev/requirements/run-{RUN_ID}/interview.json`. Uses `EnterPlanMode` to confirm the synthesized requirements before saving. The refined goal and constraints are then passed to `/council` as context.

### `/council`
Structured architectural debate that produces an ADR. Loads `interview.json` when available (passed via `interview:` arg from `mini-stop.sh`), using `refined_goal` as the debate topic. Always includes a **product-owner** panelist and a **사용자 가치 / 요구사항 충족도** lens. Derives 3–5 analysis lenses from the topic, spawns panelists in parallel via `TeamCreate` (including a devil's advocate), runs a two-phase debate (initial positions → direct rebuttals), and writes the final ADR to `.dev/adr/`. Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in env.

### `/mini-specify [goal] [adr:<path>]`
Bridges the ADR to a task list. Optionally loads the ADR from the `adr:` parameter (passed automatically by `mini-stop.sh`). Searches `.mini-harness/learnings/*.md` by tag/keyword match and surfaces relevant past rules before planning begins. Writes `.dev/requirements/requirements.json`.

### `/taskify`
Converts requirements to an executable task spec. Auto-detects the tech stack (pytest.ini → Python, package.json → Node.js, etc.). Each task gets: an `action` (verb + object), `step` (3–5 imperative implementation steps), and `verification` (a runnable CLI command). Writes `.dev/task/spec.json`.

### `/dependency-resolve`
Infers inter-task dependencies by analyzing step text for class/method cross-references and domain layer ordering (domain → application → infrastructure). Validates no circular dependencies via DFS. Assigns priority: P0 (no deps, run first), P1 (has deps), P2 (terminal). Rewrites `spec.json` in place.

### `/mini-execute`
Topologically sorts tasks by dependencies, then implements each one. After each task, runs its `verification` command. Pass (exit 0) → `status = "end"`. Fail → `status = "not_start"`. After all tasks are attempted, records friction to `session/learnings.json` only when a clear, actionable rule can be derived. The ralph loop then validates completed tasks and re-runs execute if any remain.

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

## State Machine (`state.json`)

**Location**: `.claude/state/state.json` — exists only during an active run.

```json
{
  "skill_name": "mini-harness | interview | council | mini-specify | taskify | dependency-resolve | mini-execute | mini-compound",
  "status": "processing | end",
  "goal": "<original goal string>",
  "timestamp": "<ISO-8601 UTC>",
  "last_action": "execute | validate"
}
```

`last_action` is only present when `skill_name = "mini-execute"` (ralph loop state).

**Lifecycle**: Created by `mini-pre-tool-use.sh` on the first skill call. `skill_name` is updated before each subsequent skill. `status` is set to `"end"` by `mini-stop.sh` when transitioning to the next step. Deleted by `mini-stop.sh` when `mini-compound` completes.

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
  mini-stop.sh             # Main orchestrator (Stop hook)
  execute-stop.sh          # Ralph loop controller (Stop hook)
  mini-pre-tool-use.sh     # State initialization (PreToolUse hook)
  mini-post-tool-use.sh    # Status guard (PostToolUse hook)
  mini-start-session.sh    # Recovery guard (UserPromptSubmit hook)

.claude/
  settings.json            # Hook configuration + env vars
  skills/                  # Skill definitions
  state/                   # Runtime state (state.json, created/deleted per run)

.mini-harness/
  learnings/               # Permanent learning library (*.md, tagged)
  session/                 # Transient friction log (learnings.json)

.dev/
  adr/                     # Architecture Decision Records (output of /council)
  requirements/            # run-{RUN_ID}/interview.json (output of /interview) + requirements.json (output of /mini-specify)
  task/                    # spec.json (output of /taskify + /dependency-resolve)

kiosk/                     # Mini-project sandbox — test vehicle for the harness
  domain/                  # DDD domain models (entities, value objects, repositories)
  application/             # Use cases
  infrastructure/          # In-memory repository implementations
  cli.py                   # Interactive CLI entry point

tests/                     # Test suite for kiosk (used as harness verification targets)
docs/
  harness.md               # Detailed harness skill reference
```
