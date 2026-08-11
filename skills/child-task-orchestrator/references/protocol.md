# Child Task Protocol

## Contents

- CLI setup
- Create and bind a visible task
- Collaborative turns and explicit close
- Parent review
- Status and recovery

## CLI Setup

```bash
# Resolve SKILL_ROOT from the loaded skill's SKILL.md location. Do not assume
# the skill is installed directly under CODEX_HOME; plugins use cache paths.
SKILL_ROOT="<absolute path to the loaded child-task-orchestrator skill>"
CLI="${SKILL_ROOT:?}/scripts/child_task.py"
# Parent setup: initialize both roots from the parent checkout.
PROTOCOL_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
WORKSPACE_ROOT="$PROTOCOL_ROOT"
```

In the child task, copy the protocol root from the bootstrap and resolve only the workspace root from the child worktree:

```bash
PROTOCOL_ROOT="<exact Protocol project root from bootstrap>"
WORKSPACE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
```

All CLI state commands use `--project-root "$PROTOCOL_ROOT"`. `WORKSPACE_ROOT` is only for editing, tests, diffs, and project-relative evidence paths. The state protocol is local: select a project on the same host, and do not create a remote child that cannot access `PROTOCOL_ROOT`. All commands print JSON except `bootstrap`. Use a stable operation ID for retries. Do not pass secrets in titles, objectives, handoffs, or operation IDs.

## Create And Bind A Visible Task

### Discover capabilities first

Codex App tools can be eagerly injected, deferred, or namespaced. Treat `create_thread` and `codex_app__create_thread` as the same capability. Search the available tool catalog before declaring a capability missing.

Use this order:

1. Use `create_thread` when available. Call `list_projects` unless a valid current project ID is already known.
2. If project discovery is unavailable and no project ID is known, use `fork_thread` rather than failing.
3. If `set_thread_title` is unavailable, continue with the generated title and record the desired title locally.
4. Fail only when neither `create_thread` nor `fork_thread` exists. Never substitute `spawn_agent` or claim a visible task was created.

Initialize project state. Pass `--parent-thread-id` only when the current task ID is actually available; never invent it.

```bash
python3 "$CLI" --project-root "$PROTOCOL_ROOT" init
```

Create a code contract:

```bash
python3 "$CLI" --project-root "$PROTOCOL_ROOT" create \
  --title "Host Agent refine filter" \
  --objective "Improve the refine quality gate and preserve review outputs." \
  --acceptance-criteria '[{"id":"ac-1","text":"Focused tests pass"},{"id":"ac-2","text":"Existing output schema remains compatible"}]' \
  --mode code \
  --session-mode collaborative \
  --parent-context-revision 1 \
  --writable-path host_agent_mining/ \
  --writable-path tests/ \
  --operation-id create-host-agent-refine-v1
```

Collaborative is the default. Initial acceptance criteria describe the work topic; do not add commit or final submission as criteria. Use `--session-mode execution` only when the user explicitly requests a one-shot autonomous task.

The result contains `child_id`. Render the bootstrap:

```bash
python3 "$CLI" --project-root "$PROTOCOL_ROOT" bootstrap <child_id>
```

Use the rendered text as the initial prompt to `create_thread`:

Use the current Codex App target shape exactly. `environment` is nested inside `target`, and the key is `projectId`:

```json
{
  "prompt": "<rendered bootstrap>",
  "target": {
    "type": "project",
    "projectId": "<project ID returned by list_projects>",
    "environment": {"type": "worktree"}
  }
}
```

For `analysis`, replace the nested environment with `{"type":"local"}`. Do not move `environment` beside `target`, write `project_id`, or add a branch-name field.

Creation is non-blocking. If `create_thread` returns `clientThreadId`, record it immediately:

```bash
python3 "$CLI" --project-root "$PROTOCOL_ROOT" pending <child_id> \
  --client-thread-id <returned_client_thread_id> \
  --expected-revision 1
```

Do not pass `clientThreadId` to any task tool that requires `threadId`. Use task listing to resolve the newly ready task without creating another one. Match the project, title, and recent creation; if resolution is ambiguous, keep status `creating` and ask the user instead of binding the wrong task.

When `create_thread` returns or task listing resolves the real `threadId` and `hostId`, call `set_thread_title` when available, then bind both exact values:

```bash
python3 "$CLI" --project-root "$PROTOCOL_ROOT" bind <child_id> \
  --thread-id <returned_thread_id> \
  --host-id <returned_host_id> \
  --workspace-kind worktree \
  --expected-revision 1
```

If thread creation fails or the result is unknown, do not create another child ID. Run `reconcile`, inspect recent Codex tasks, and bind the existing task when found.

### Fork fallback

When `create_thread` or project discovery is unavailable, call `fork_thread` on the current task. Use `environment: {"type":"worktree"}` for code and `{"type":"same-directory"}` for analysis. A same-directory fork returns a task ID immediately. A worktree fork may first return `clientThreadId`; record it with `pending`, then use task listing and reconciliation to resolve the resulting real `threadId` and `hostId` before binding. Send the rendered bootstrap as the first follow-up message when messaging is available.

Inherited parent history is a fallback tradeoff, not a reason to use a temporary subagent. Mention it only when it materially affects context isolation.

## Collaborative Turns And Explicit Close

Read current state before writing:

```bash
python3 "$CLI" --project-root "$PROTOCOL_ROOT" status <child_id>
```

Write the handoff payload to a JSON file using the fields in `schemas.md`, then submit:

```bash
python3 "$CLI" --project-root "$PROTOCOL_ROOT" submit <child_id> \
  --kind checkpoint \
  --payload /absolute/path/to/checkpoint.json \
  --based-on-context-revision 1 \
  --operation-id checkpoint-1 \
  --expected-status-revision 2
```

After a checkpoint, remain in the child task for the next user turn. Do not commit or submit final just because the current request has been implemented.

When the user says `收子任务`, request close first:

```bash
python3 "$CLI" --project-root "$PROTOCOL_ROOT" request-close <child_id> \
  --reason "User said 收子任务" \
  --expected-revision <current_revision>
```

Only after status becomes `finalizing` should the child run final verification, create a close-phase commit when code changed, and submit `--kind final`. Final requires every acceptance criterion. Repeating the same operation ID with identical content is safe; changed content with the same ID is rejected.

Use `transition` for execution states such as `waiting_user`, `blocked`, or returning `needs_changes` to `active`:

```bash
python3 "$CLI" --project-root "$PROTOCOL_ROOT" transition <child_id> \
  --to blocked \
  --reason "Waiting for the requested data export" \
  --expected-revision <current_revision>
```

## Parent Review

Validate referenced paths, inspect the diff or artifacts, and rerun critical checks. Then record the decision:

```bash
python3 "$CLI" --project-root "$PROTOCOL_ROOT" review <child_id> \
  --handoff-revision 1 \
  --decision accepted \
  --reason "Acceptance criteria and evidence verified" \
  --expected-status-revision <current_revision>
```

Use `needs_changes` when evidence or behavior is incomplete. Send the revision request to the same Codex child task so its multi-turn context remains available.

## Status And Recovery

```bash
python3 "$CLI" --project-root "$PROTOCOL_ROOT" list
python3 "$CLI" --project-root "$PROTOCOL_ROOT" reconcile
```

`thread_not_bound` means local state exists without any recorded Codex task. `thread_setup_pending` means a `clientThreadId` was recorded but the real task is not ready or resolved yet. `parent_context_stale` means the parent changed durable decisions after the child contract was created. `finalizing` means the user explicitly requested collection and the child may perform close-phase work. `awaiting_parent_review` is a reconcile issue; the canonical child status remains `handoff_submitted` until parent review.

When durable parent decisions change, increment the revision:

```bash
python3 "$CLI" --project-root "$PROTOCOL_ROOT" bump-context --expected-revision 1
```

The current schema treats the child contract revision as immutable. After a durable parent decision changes, do not submit a handoff against a guessed newer revision; create a replacement child contract or explicitly return the stale handoff for rework.
