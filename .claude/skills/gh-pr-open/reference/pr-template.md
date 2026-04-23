# PR Body Template

placeholder는 `{{var}}` 표기. `gh-pr-open` SKILL.md의 render 함수가 치환한다.

---

Closes #{{issue_number}}

> 🤖 mini-harness · run `{{run_id}}` · task `{{task_id}}` · base `{{base_branch}}` · head `{{head_sha_short}}`

## Summary
{{action}}

## Changes
{{#files_modified}}
- `{{.}}`
{{/files_modified}}

## Verification
```bash
{{verification}}
```
✅ `validate-tasks` 통과 (head `{{head_sha_short}}`)

## Design alignment

이 PR이 따르는 의사결정:

- **ADR:** [{{adr.title}}]({{adr.github_url}})
  - _{{adr.decision_summary}}_
- **Design review verdict:** {{review.verdict}} — [review]({{review.github_url}})
- **Spec task:** [spec.json#task-{{task_id}}]({{spec.github_url}})

<details>
<summary>Implementation steps (from spec)</summary>

{{#step}}
- [x] {{.}}
{{/step}}
</details>

## DAG / merge order

{{#dependencies}}
- depends on #{{parent.pr_number}} (task-{{parent.task_id}}) — state: `{{parent.pr_state}}`
{{/dependencies}}
{{^dependencies}}
_(independent — can merge immediately after review)_
{{/dependencies}}

{{#is_draft}}
> ⚠️ 부모 PR 미머지 → 이 PR은 draft. 부모 머지 후 `sync-pr-state.sh`가 base를 `main`으로 재지정합니다.
{{/is_draft}}

## Automated review

이 PR에는 `gh-pr-review` 스킬이 인라인 코드리뷰 코멘트를 자동 게시합니다. 사람 리뷰어가 최종 승인 및 머지를 결정하세요.

---
_`gh-pr-open` auto-generated. 전체 설계 컨텍스트는 Issue #{{issue_number}}에 있습니다._
