# Child Task Orchestrator

[![GitHub release](https://img.shields.io/github/v/release/fyydnz53/child-task-orchestrator)](https://github.com/fyydnz53/child-task-orchestrator/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Codex Skill](https://img.shields.io/badge/Codex-Skill-111111)](skills/child-task-orchestrator/SKILL.md)

`child-task-orchestrator` is a Codex skill-only plugin for long-running work that needs a real, user-visible child task instead of a temporary subagent.

It adds a small state protocol around Codex tasks:

- create a resumable task in the Codex sidebar;
- isolate code changes in a worktree when needed;
- keep collaborative children active until the user explicitly closes them;
- record idempotent contracts, checkpoints, and final handoffs under `.codex-child-tasks/`;
- let the parent verify and accept the result separately.

The protocol state is local. The parent and child task must run on the same host and be able to access the parent checkout's protocol directory; remote-host state transport is intentionally out of scope for version 0.1.0.

## Install

### Public GitHub / Codex

```bash
git clone https://github.com/fyydnz53/child-task-orchestrator.git
mkdir -p ~/.codex/skills
cp -R child-task-orchestrator/skills/child-task-orchestrator ~/.codex/skills/
```

Restart Codex after installation. The Skill activates on requests such as `开子任务`、`启动子任务`、`收子任务`、`回收子任务` and `返回主任务`.

### ByteDance AgentBuddy

ByteDance users can install the internally published package from [AgentBuddy](https://skills.bytedance.net/skill/skills:skills.byted.org/jiangguangkun/agent_skills/child-task-orchestrator):

```bash
npm_config_registry="https://bnpm.byted.org" npx agentbuddy@latest skill add \
  skills.byted.org/jiangguangkun/agent_skills --skill child-task-orchestrator
```

Related collection: [Codex 子任务协作](https://skills.bytedance.net/collection/otsqGvts).

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
