---
agent: synthesizer
timestamp: 2026-04-23T00:00:00Z
phase: synthesis
---

# Harness Full Evaluation Report

**Score: 5.9/10 (D)**
**Date: 2026-04-23**
**Mode: Full**

---

## Dimension Scores

| Category | Dimension | Score | Weight | Status |
|---|---|---|---|---|
| Basic Quality | Correctness | 7/10 | 0.50 | pass |
| Basic Quality | Safety | 4/10 | 0.50 | warning |
| Basic Quality | Completeness | 6/10 | 0.50 | warning |
| Basic Quality | Consistency | 6/10 | 0.50 | warning |
| Operational | Actionability | 7/10 | 0.25 | pass |
| Operational | Testability | 3/10 | 0.25 | fail |
| Operational | Cost Efficiency | 7/10 | 0.25 | pass |
| Operational | Contract-Based Testing | 4/10 | 0.25 | warning |
| Design Quality | Agent Communication | 7/10 | 0.25 | pass |
| Design Quality | Context Management | 6/10 | 0.25 | warning |
| Design Quality | Feedback Loop Maturity | 9/10 | 0.25 | pass |
| Design Quality | Evolvability | 6/10 | 0.25 | warning |

**Category Averages:**
- Basic Quality: (7 + 4 + 6 + 6) / 4 = **5.75**
- Operational: (7 + 3 + 7 + 4) / 4 = **5.25**
- Design Quality: (7 + 6 + 9 + 6) / 4 = **7.00**

**Overall: (5.75 × 0.50) + (5.25 × 0.25) + (7.00 × 0.25) = 2.875 + 1.3125 + 1.75 = 5.9**

---

## Executive Summary

The compound-practice harness demonstrates a sophisticated feedback-loop architecture — the ralph-loop (execute/validate alternation), compound-guard (learning promotion gate), and run-scoped artifact directories are mature, well-implemented patterns that earned a near-perfect Feedback Loop Maturity score of 9/10. However, the harness is pulled down severely by three structural deficits: an entirely open security posture (empty permissions and deny lists, no secret gate), zero automated testing of any harness component (all 6 shell scripts and the sole agent are untested), and an external plugin path that does not resolve on this machine, making the harness non-portable. Basic Quality averages 5.75 due to these gaps; Operational averages 5.25 with Testability at 3/10 being the single largest score anchor. The Python domain code is separately strong — 20 test files, realistic fixtures, single-command pytest — and does not contribute to the harness-layer problems. Reaching grade C requires closing the deny list and harness self-test gaps; reaching grade B further requires JSON schema contracts and CLAUDE.md decomposition.

---

## Detailed Findings

### Basic Quality

**Correctness (7/10 — pass)**
The Python domain layer is well-implemented: 20 test files covering domain models, use cases, integration flows, and admin use cases all pass with a single `pytest` command. One documented test discrepancy exists — `tests/test_order.py::test_add_duplicate_item_raises` expects an exception but the implementation merges quantities instead; the correct behavior is captured in `test_cart_integration.py::TestAddToCart::test_add_duplicate_item_increases_quantity`. Harness shell correctness is unverified since no tests exist for it.

**Safety (4/10 — warning)**
Three FAIL-level findings define this score. `settings.json` contains empty `permissions` and `deny` arrays — with Bash fully enabled there is no blocker for `rm -rf`, `git push --force`, `curl|bash`, or credential reads. The external plugin reference (`../../PycharmProjects/harness`) does not resolve on this machine, silently breaking any plugin-provided skills. No secret-detection regex gate exists on any hook despite hooks having access to `tool_input` JSON. Two additional WARN findings: hook scripts interpolate user-controlled strings (GOAL, RUN_ID) into `echo "{...}"` JSON output without escaping, and no hook script uses `set -euo pipefail`.

**Completeness (6/10 — warning)**
Skill SKILL.md files are well-structured with numbered steps, explicit decision branches, and output format templates. The mini-harness artifact ownership table is exemplary. However three FAILs reduce this score: the stale run-20260419 state.json shows `status=processing` while all spec tasks are `end` — any new session will auto-recover to a spurious block. The sole agent (`validate-tasks.md`) lacks YAML frontmatter. All 6 hook scripts have zero automated tests. No JSON schemas exist for state.json, spec.json, interview.json, or requirements.json.

**Consistency (6/10 — warning)**
Hook scripts use atomic write (`jq ... > tmp && mv tmp`) consistently for state.json mutations — good pattern. However, stdout hook decisions mix `echo "{\"decision\":...}"` (fragile) with `jq -n` (safe) inconsistently across scripts. `validate-tasks.md` lacks frontmatter while all in-repo SKILL.md files have it. `mini-*` skills have frontmatter but do not declare `allowed-tools`, inconsistent with `commit` and `mini-compound`. The SessionStart hook uses matcher `compact` while Stop hooks use `""` — matcher convention is undocumented.

---

### Operational

**Actionability (7/10 — pass)**
Skills are highly actionable: numbered workflows, explicit fallback paths, and block messages that embed the exact next skill name and `run_id` argument. The single gap is zero command files (collector: commands count = 0) — the harness has no `/commands` shorthand, only skills. Error recovery handles missing STATE_FILE and circular dependencies but does not gracefully degrade when `jq` is absent.

**Testability (3/10 — fail)**
The Python domain tests are excellent (score 9 at the subdimension level). The harness itself has no tests whatsoever: no bash unit tests for execute-stop.sh, mini-stop.sh, harness-lib.sh, mini-pre-tool-use.sh, mini-post-tool-use.sh, or mini-start-session.sh. No mock state.json fixtures, no end-to-end replay scripts. The ralph-loop state machine correctness (validate/execute alternation, multi-run detection, compact recovery) depends entirely on manual observation of real runs. A change to the block message format or any jq query would break orchestration silently.

**Cost Efficiency (7/10 — pass)**
No hardcoded `model: opus` anywhere — all agents and skills inherit the session ambient model. Tool lists are reasonably minimal. Main inefficiencies: the 7-skill Stop-hook chain pays 7x full system-prompt + CLAUDE.md ingestion per `/mini-harness` invocation; root CLAUDE.md at 456 lines is loaded every session; council and taskify reference files total ~1500 lines and load on every invocation of those skills. These are WARN-level, not blocking.

**Contract-Based Testing (4/10 — warning)**
Skill frontmatter provides partial machine-readable contracts (allowed-tools, description) for skills with frontmatter. The mini-harness artifact ownership table is the strongest contract document in the codebase. Critical gaps: `validate-tasks` has no machine-readable contract at all; no JSON schemas exist for any interchange format; the stale run proves no automated check catches incoherent state. The hook-to-skill block message format (implicit contract) is tested only by live runs.

---

### Design Quality

**Agent Communication (7/10 — pass)**
Orchestration is explicit: `mini-stop.sh` encodes the full skill chain with JSON state passed via `state.json`. Skills declare their I/O paths in SKILL.md Args sections. The main weakness is that I/O contracts are prose-described rather than schema-enforced, and the sole in-repo agent (`validate-tasks`) is the only agent while most chain skills come from the unresolvable external plugin.

**Context Management (6/10 — warning)**
Root `CLAUDE.md` is 456 lines — above the 200-line density warning threshold. The structure is logical (17 sections) and conventions are actionable, but there are no module-level CLAUDE.md files despite clear subsystem boundaries (domain/, application/, infrastructure/, admin/, tests/admin/). Harness guidance in CLAUDE.md duplicates content in `docs/harness.md`.

**Feedback Loop Maturity (9/10 — pass)**
This is the harness's strongest dimension. The ralph-loop (`execute-stop.sh` alternates execute/validate via `last_action` field with infinite-loop guard) and compound-guard (mini-stop.sh blocks exit while session/learnings.json has pending entries) are robustly implemented. Evidence of closure: 7 learnings already promoted from session to `.mini-harness/learnings/*.md`. `mini-specify` re-ingests past learnings before planning. Run-scoped directories preserve history. The one gap is human-in-the-loop — the chain has no manual approval step between planning (taskify/dependency-resolve) and execution (mini-execute).

**Evolvability (6/10 — warning)**
Skills and hooks are modular — `harness-lib.sh` centralizes shared helpers, each hook is independently executable with stdin/stdout. However the skill chain order is hardcoded as a `switch/case` in `mini-stop.sh`: adding, removing, or reordering a skill requires shell edits. The external plugin path is machine-local and non-portable. No CONTRIBUTING guide or skill template exists, making it difficult for a new contributor to add a skill correctly.

---

## Critical Issues (Fix Immediately)

1. **Empty deny list and permissions allowlist** — `settings.json` has no `deny` or `permissions` entries. With Bash unrestricted, there is no blocker for destructive operations (`rm -rf`, `git push --force`) or credential reads (`.env`, `.aws/credentials`, `id_rsa`). The ralph-loop automation amplifies this risk since Bash-heavy skills are re-invoked automatically. (File: `.claude/settings.json`)

2. **External plugin path does not resolve** — `extraKnownMarketplaces.harness.source.path = "../../PycharmProjects/harness"` points to a path that does not exist on this machine. The enabled plugin `harness-session@harness` and all skills it provides (council, interview, mini-specify, taskify, dependency-resolve, mini-execute) silently fail to load, making the harness non-portable. (File: `.claude/settings.json:63-69`)

3. **No secret-pattern gate on any hook** — `mini-pre-tool-use.sh` fires on every Skill invocation and has access to `tool_input` JSON but performs zero inspection for tokens, API keys, or credential file paths. With no deny list as a backstop, credential exfiltration via a crafted Bash command would pass unchallenged. (File: `scripts/mini-pre-tool-use.sh`)

4. **Stale run-20260419 blocks every new session** — `state.json` for run-20260419-074829-890e shows `status=processing` and `skill_name=mini-harness` while all 5 spec tasks are `end`. `mini-start-session.sh` will auto-recover to this stale run on every compact event and issue a spurious block until manually resolved. (File: `.dev/harness/runs/run-20260419-074829-890e/state/state.json`)

5. **All 6 hook scripts have zero automated tests** — The entire harness orchestration layer (ralph-loop alternation, compact recovery, multi-run detection, skill chain transitions) has no test coverage. A single jq query change or block message format change would break orchestration silently. (File: `scripts/`)

6. **validate-tasks agent lacks YAML frontmatter** — `validate-tasks.md` begins with a Markdown heading instead of YAML frontmatter, so Claude Code cannot machine-parse the allowed-tools list. Tool permission enforcement for this agent is prose-only. (File: `.claude/agent/validate-tasks.md:1`)

---

## Improvement Roadmap

### Next Grade: C (6.0)

To reach grade C, the minimum-viable fixes raise the overall score from 5.9 to approximately 6.3. Focus on closing the two hardest-hitting gaps (Safety and Testability) since they drag the Basic Quality and Operational category averages below 6.0.

1. **Populate settings.json deny list and permissions allowlist** — Add at minimum: `Bash(rm -rf *)`, `Bash(git push --force*)`, `Bash(git reset --hard*)`, `Bash(git clean -f*)`, `Bash(curl * | *sh)`, `Bash(wget * | *sh)`, `Read(.env)`, `Read(**/.aws/credentials)`, `Read(**/id_rsa)`. Add a positive permissions list per skill. Expected impact: +2.5 to Safety score (4 → 6.5), raising Basic Quality average by ~0.6.

2. **Fix or vendor the external plugin path** — Either vendor `harness-session` plugin into `.claude/plugins/harness/`, switch to a git-url marketplace entry, or at minimum document the required sibling checkout and add a setup script that validates the path at session start. Expected impact: +2.0 to Safety score, +1.0 to Evolvability (portability), combined lift ~+0.4 to overall.

3. **Resolve stale run-20260419 and add done-run guard** — Run `/mini-compound run_id:20260419-074829-890e` or manually delete `state/state.json`. Then add a guard in `mini-start-session.sh` that treats `specTasksAllComplete=true AND skill_name != mini-compound` as a done run rather than recoverable, preventing recurrence. Expected impact: +1.5 to Completeness (6 → 7.5), +0.4 to overall.

4. **Add bash unit tests for hooks** — Create `tests/harness/` with bats or plain bash assert scripts covering: `harness-lib.sh:resolve_run_state`, `execute-stop.sh` block/approve decision matrix (remaining>0, last_action=execute/validate), and `mini-stop.sh` skill-chain transitions. Even 10 targeted tests would raise Testability from 3 to ~5. Expected impact: +2.0 to Testability score, +0.25 to Operational average, +0.1 to overall.

5. **Add secret-pattern gate in mini-pre-tool-use.sh** — Match against a regex bundle: `-----BEGIN (RSA|OPENSSH|EC) PRIVATE KEY-----`, `sk-[A-Za-z0-9]{40,}`, `ghp_[A-Za-z0-9]{36}`, `AKIA[0-9A-Z]{16}`, plus path patterns `(\.env|\.aws/credentials|id_rsa)`. Emit `{"decision":"block","reason":"..."}` on match and log to `.dev/harness/security.log`. Expected impact: +1.5 to Safety, +0.3 to overall.

6. **Add validate-tasks YAML frontmatter** — Convert `validate-tasks.md` to standard frontmatter (name, description, allowed-tools: [Read, Bash], model: null) and remove unused Write from allowed tools. Expected impact: +1.0 to Consistency, +1.0 to Contract-Based Testing, combined +0.2 to overall.

7. **Replace echo-JSON hook outputs with jq -n** — Replace all `echo "{\"decision\"...}"` constructions in hook scripts with `jq -n --arg reason "..." '{decision:"block", reason:$reason}'`. Add `set -euo pipefail` plus a `jq` preflight to every script. Expected impact: +1.0 to Safety, +1.0 to Consistency, combined +0.2 to overall.

8. **Add JSON schemas for state.json, spec.json, interview.json, requirements.json** — Place under `.dev/harness/schemas/`. Add validation step in `mini-pre-tool-use.sh` before state updates. Expected impact: +2.0 to Contract-Based Testing (4 → 6), +0.2 to Operational average.

9. **Add explicit allowed-tools frontmatter to mini-* skills** — Scope each skill to its actual tool needs (e.g., mini-compound: `[Read, Write, Bash(rm*)]`; taskify: `[Read, Write, Bash(jq*)]`). This closes the inherited-toolset gap and reduces per-turn tool schema overhead. Expected impact: +0.5 to Safety, +0.5 to Cost Efficiency, combined +0.1 to overall.

10. **Decompose root CLAUDE.md into module-level files** — Reduce root CLAUDE.md from 456 to ~150 lines of project-wide conventions. Create `kiosk/domain/CLAUDE.md` (value-object invariants, Order state machine, ~80 lines), `kiosk/application/CLAUDE.md` (use-case and DTO conventions, ~60 lines), `tests/CLAUDE.md` (fixture and pytest patterns, ~40 lines). Move harness section to a one-line reference to `docs/harness.md`. Expected impact: +1.0 to Context Management (6 → 7), +0.5 to Cost Efficiency (token savings), +0.1 to overall.

### Long-term Goals

- **Make the skill chain data-driven**: Extract the hardcoded `switch/case` in `mini-stop.sh` into a declarative `.dev/harness/chain.json` listing skills and their successors. This lets new skills be registered without shell edits, makes the pipeline inspectable at a glance, and enables conditional branching (e.g., skip council on trivial tasks). Would raise Evolvability from 6 to ~8.

- **Add a manual approval gate between planning and execution**: Insert a human-in-the-loop checkpoint after `dependency-resolve` and before `mini-execute`. This gives the user a chance to review the task breakdown before automation begins executing, reducing the cost of course-correcting mid-run and raising Feedback Loop Maturity from 9 toward a full 10.

- **Comprehensive harness self-test suite with CI**: Expand `tests/harness/` into a full test suite that replays recorded runs against mock state, verifies hook decision correctness, and runs on every commit. This would raise Testability from 3 to ~8 and provide the regression safety net needed to evolve the harness confidently.

---

## Score History

No previous evaluations found. This is the first recorded full evaluation for compound-practice. Future evaluations will show trend data here.

---

## Linked Artifacts

- Collector output: `.dev/harness/evals/collector-output.json`
- Safety evaluator: `.dev/harness/evals/safety-eval.json`
- Completeness evaluator: `.dev/harness/evals/completeness-eval.json`
- Design evaluator: `.dev/harness/evals/design-eval.json`
