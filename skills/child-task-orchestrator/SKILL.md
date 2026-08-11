---
name: child-task-orchestrator
description: Use when a long Codex task needs a user-visible, resumable child task for isolated multi-turn collaboration or handoff, including requests such as 开子任务, 启动子任务, 收子任务, 回收子任务, or 返回主任务.
---

# Child Task Orchestrator

## Overview

Create a real Codex sidebar task for ongoing collaboration. Keep its detailed discussion isolated and return a versioned handoff only when the user explicitly closes the child. Store protocol state locally, so the parent and child must run on the same host and both must be able to access the parent protocol root.

## Short Commands

| User phrase | Meaning |
|---|---|
| `开子任务：<topic>` | Create a collaborative child and keep it active |
| `收子任务` | In the child, request close, verify, commit, and submit final |
| `回收子任务` | In the parent, verify the final handoff and accept or return it |

Infer title, mode, scope, and provisional acceptance criteria from context. Ask only when a missing decision materially changes the task.

## Lifecycle Gate

The default `session_mode` is `collaborative`:

```text
creating -> active -> finalizing -> handoff_submitted -> accepted
```

- Completing one work turn does not complete the child.
- While `active`, allow more user discussion, edits, and tests. Use checkpoints only.
- Do not create a Git commit or submit final merely because the objective appears satisfied.
- Only the exact close intent `收子任务` authorizes `request-close` and moves the child to `finalizing`.
- Only `finalizing` permits close-phase verification, commit, and final handoff.
- Only the parent can mark the handoff `accepted`.

Do not put “create a commit” or “submit final” in initial acceptance criteria. Those are close-phase protocol actions, not the initial work objective.

## Create The Sidebar Task

Create a real Codex task, never a temporary `spawn_agent`. Discover available and deferred tools by capability suffix: bare and namespaced forms such as `create_thread` and `codex_app__create_thread` are equivalent. Missing `set_thread_title` never blocks creation.

| Available capabilities | Action |
|---|---|
| `list_projects` + `create_thread` | Preferred minimal-context child |
| `create_thread` + known project ID | Create directly |
| `fork_thread` only | Visible-task fallback; worktree for code |
| Neither create nor fork | Report the missing real-task capability |

| Child work | Environment |
|---|---|
| Read-only analysis or planning | project `local` |
| Code or file edits | project `worktree` |

For code children, use exactly:

```json
{"prompt":"<bootstrap>","target":{"type":"project","projectId":"<id>","environment":{"type":"worktree"}}}
```

Omit `startingState` unless the user explicitly requests current uncommitted state. Set the title afterward, bind the returned task ID, and never invent a branch-name field.

Creation is asynchronous. A ready result contains `threadId` and `hostId`; bind both exact values. A setup-in-progress result contains `clientThreadId`, which is not a task ID. Record it with the CLI `pending` command, use task listing to resolve the ready task, and bind only the resulting real `threadId` and `hostId`. Never hard-code `hostId` or retry creation blindly.

## Parent Workflow

1. Create a collaborative CLI contract with objective, stable acceptance IDs, scope, decision revision, and writable paths.
2. Discover task capabilities, render the minimal bootstrap, and create or fork a real task.
3. Record pending setup when necessary, then bind the ready task ID and host ID. The child is now visible and resumable.
4. On `回收子任务`, read the final handoff and referenced evidence, not the transcript. Record `accepted` or `needs_changes`.

## Child Workflow

1. Remain active after each turn and invite the next user instruction naturally.
2. Submit checkpoint handoffs at durable milestones without committing solely to end the turn.
3. On `收子任务`, run `request-close`, perform final checks, create the close-phase commit if code changed, and submit final.
4. Send only `handoff ready` to the parent when messaging is available.

Read [references/protocol.md](references/protocol.md) for commands and recovery. Read [references/schemas.md](references/schemas.md) for payload fields.
