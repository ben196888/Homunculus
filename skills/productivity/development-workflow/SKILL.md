---
name: "homunculus-productivity-development-workflow"
description: "Use when a task is large enough to benefit from an explicit plan, clarifications, documentation, implementation, and verification workflow."
---

# Development Workflow

Use this skill for non-trivial engineering work that benefits from explicit sequencing.

## Workflow

1. Plan
2. Clarify open questions when they materially affect the solution
3. Document the approach when the change is large or cross-cutting
4. Implement
5. Verify

## Guidance

- Start by understanding the task, affected systems, and the proposed change.
- Ask questions only when a reasonable assumption would be risky.
- For large or cross-cutting design, run `homunculus-productivity-visual-plan` with the **rfc** template before implementation. For a concrete behavior or system change that needs human approval before coding (decision callout, before/after, unchanged, status), use the **implementation-plan** template instead. If the user overrode sections or named another template, follow that.
- After implementation, run the relevant checks and call out any gaps.
- Do not claim deployment or monitoring work unless it actually happened.
