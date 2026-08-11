# Official Submission Test Cases

These cases are designed for an OpenAI reviewer using a disposable local Git repository. No private fixture data or authentication is required beyond access to Codex task features.

## Positive cases

### 1. Visible code child

- Prompt: `Open a visible child task to update a small function and its tests. Keep it active until I explicitly close it.`
- Expected behavior: Create a durable collaborative contract, create a Codex worktree task, record `clientThreadId` if setup is pending, and bind the real `threadId` and `hostId` when ready.
- Expected result: The child appears in the sidebar, uses a worktree, remains `active`, and the local snapshot contains the contract and task binding.
- Fixture: A disposable Git repository with one Python function and test.

### 2. Visible read-only child

- Prompt: `Create a visible child task to review this repository's test layout without changing files.`
- Expected behavior: Create an analysis contract and a same-host local task without requiring a worktree.
- Expected result: The child remains available for follow-up discussion and returns structured checkpoint data without file changes.
- Fixture: Any disposable repository.

### 3. Collaborative checkpoint

- Prompt: `Implement the first draft, but keep the child open because I will review it and request changes.`
- Expected behavior: Work in the existing child, run focused checks, and submit a checkpoint only.
- Expected result: Status remains `active`; no close request, final handoff, parent acceptance, or close-only commit occurs.
- Fixture: The child created in case 1.

### 4. Explicit close and final handoff

- Prompt: `收子任务`
- Expected behavior: Run `request-close`, verify the final state, create a close-phase commit when code changed, and submit the latest final handoff.
- Expected result: Status becomes `handoff_submitted`; the child does not mark itself accepted.
- Fixture: The active child from case 3.

### 5. Parent review

- Prompt: `回收子任务`
- Expected behavior: Read the latest final handoff, inspect its referenced diff and test evidence, and record `accepted` only after verification.
- Expected result: `parent-ack.json` references the latest final handoff revision and the canonical status becomes `accepted`.
- Fixture: The submitted final handoff from case 4.

## Negative cases

### 1. No real task capability

- Scenario: Neither `create_thread` nor `fork_thread` is available.
- Expected fallback: Report that a user-visible task cannot be created.
- Why not complete: A temporary subagent is not a visible, resumable Codex task and must not be presented as one.

### 2. Remote host cannot access local state

- Scenario: The selected project runs on a host that cannot access the parent's local protocol root.
- Expected fallback: Explain the same-host requirement and ask the user to choose a compatible local project or another workflow.
- Why not complete: Binding an inaccessible remote child would make checkpoint and final state operations fail.

### 3. Ambiguous pending task resolution

- Scenario: Task creation returned `clientThreadId`, and task listing shows multiple indistinguishable recent candidates.
- Expected fallback: Keep the child in `creating`/`thread_setup_pending` and ask the user which task is correct.
- Why not complete: Guessing could bind the contract to the wrong user task and corrupt later handoffs.
