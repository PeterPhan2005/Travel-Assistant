# Task Workflow

Each task must be independently reviewable and should normally fit in one focused Codex run.

## Status values

- `todo`
- `in_progress`
- `blocked`
- `done`

## Standard Codex prompt

```text
Implement tasks/<TASK_FILE>. Read the root and nested AGENTS.md files plus every context file listed by the task. Stay strictly within scope. Run all required checks and update docs/context/12-progress-tracker.md. Do not start another task.
```

## Rules

- One task per branch/commit.
- API contract changes receive their own task.
- Schema migrations receive their own task.
- UI and backend implementation should be split unless the task is explicitly an end-to-end vertical slice.
- A task is not done without acceptance evidence.
