# Protocol Schemas

## Contract

The CLI creates `contract.json`. Required inputs are:

| Field | Meaning |
|---|---|
| `title` | Human-readable sidebar title |
| `objective` | Resolved child outcome |
| `acceptance_criteria[]` | Stable `id` and testable `text` |
| `mode` | `analysis` or `code` |
| `session_mode` | `collaborative` by default; `execution` only for explicit one-shot work |
| `finalization_policy` | `explicit_close` for collaborative sessions |
| `parent_context_revision` | Durable parent context used by the child |
| `writable_paths[]` | Project-relative write ownership |
| `operation_id` | Stable idempotency key for creation |

Generated fields include `schema_version`, `project_id`, `child_id`, timestamps, and an operation fingerprint.

`binding.json` may first store a pending `client_thread_id`. This is setup identity only and must never be passed where a real `thread_id` is required. Once ready, preserve the exact `thread_id` and `host_id` returned by Codex; never hard-code the host.

In collaborative mode, acceptance criteria must not use commit or final submission as work criteria. Those actions belong to the explicit close phase after `request-close`.

## Handoff Payload

Every payload contains all fields below. Use empty arrays rather than omitting fields.

```json
{
  "summary": "What changed and the resulting behavior.",
  "criteria_results": [
    {
      "id": "ac-1",
      "status": "passed",
      "evidence": ["tests/test_gate.py", "commit:abc123"]
    }
  ],
  "changed_files": ["host_agent_mining/gate.py"],
  "artifacts": [
    {"path": "reports/refine-funnel.json", "type": "report", "sha256": "optional"}
  ],
  "tests": [
    {"command": "pytest -q", "exit_code": 0, "result": "passed"}
  ],
  "decisions_made": [],
  "decision_proposals": [],
  "risks": [],
  "open_questions": [],
  "next_steps": []
}
```

Criterion status is one of `passed`, `failed`, `partial`, or `not_attempted`. A final handoff reports every contract criterion. Paths are project-relative and may not escape the project root.

`based_on_context_revision` must equal the immutable revision in the child contract. If durable parent context changes, reconcile before allowing another handoff.

## Ownership

| File | Writer | Meaning |
|---|---|---|
| `project.json` | Parent/orchestrator | Project identity and context revision |
| `contract.json` | Parent/orchestrator | Delegated task contract |
| `binding.json` | Parent/orchestrator | Codex task and environment binding |
| `child-status.json` | Child through CLI | Execution state and revision |
| `handoffs/*.json` | Child through CLI | Immutable checkpoint or final submissions |
| `parent-ack.json` | Parent through CLI | Accepted or needs-changes decision |
| `registry.json` | CLI | Rebuildable status view |

The Codex transcript is not a protocol state source. Markdown summaries are optional views, not canonical records.
