# OV Agent Worktrees

Temporary Git worktrees for the VOLUNTEERS ONLY agent pipeline.

Normal two-line task:

- agent/terra-a/<task> -> _agent_worktrees/terra-a-<task>
- agent/terra-b/<task> -> _agent_worktrees/terra-b-<task>
- agent/integration/<task> -> _agent_worktrees/integration-<task>

Rules:

- Terra A and Terra B never edit the same working directory.
- Terra Medium performs first implementation.
- DeepSeek MAX tests each line.
- Failed line escalates to Terra High.
- Sol Medium integrates passed lines.
- DeepSeek MAX performs final QA.
- Temporary worktrees and temporary agent branches are removed after integration.
- Never place worktrees inside Assets/.
