# Child Task Orchestrator

`child-task-orchestrator` is a Codex skill-only plugin for long-running work that needs a real, user-visible child task instead of a temporary subagent.

It adds a small state protocol around Codex tasks:

- create a resumable task in the Codex sidebar;
- isolate code changes in a worktree when needed;
- keep collaborative children active until the user explicitly closes them;
- record idempotent contracts, checkpoints, and final handoffs under `.codex-child-tasks/`;
- let the parent verify and accept the result separately.

The protocol state is local. The parent and child task must run on the same host and be able to access the parent checkout's protocol directory; remote-host state transport is intentionally out of scope for version 0.1.0.

## Commands

- `开子任务：<topic>` — open a collaborative child task.
- `收子任务` — finalize the current child and submit its handoff.
- `回收子任务` — review and accept or return a child handoff from the parent.

English requests such as “open a visible child task” work as well.

## Repository layout

```text
.codex-plugin/plugin.json
skills/child-task-orchestrator/
├── SKILL.md
├── agents/openai.yaml
├── scripts/child_task.py
├── references/
├── tests/
└── evals/
```

The Python helper uses only the standard library. Run the checks with:

```bash
python3 -m unittest discover -s skills/child-task-orchestrator/tests -v
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  skills/child-task-orchestrator
```

## License

MIT. See [LICENSE](LICENSE). The repository also includes a [privacy notice](PRIVACY.md), [terms](TERMS.md), and [official submission test cases](submission/TEST_CASES.md).
