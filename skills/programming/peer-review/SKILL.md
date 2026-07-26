---
name: "homunculus-programming-peer-review"
description: "Two-lens pull request review where every finding is proven by experiment before it reaches the author. Runs a correctness lens and an over-engineering lens, materializes the PR head, runs the repo's own gate, then falsifies each finding by reverting or deleting the code it targets to see whether a test actually breaks. Produces a chat report separating valid from rejected claims, fix recommendations with test steps, and a draft of terse PR comments split into thread-level and line-anchored. Use whenever the user asks to review a pull request or merge request, re-review after new commits, validate or sanity-check review findings, check whether a reviewer's suggestion is real, or asks what can be deleted or simplified in a diff — and use it even when they only paste a PR URL with no other instruction. Never posts to the forge until the user says post."
---

# Validated PR Review

Two lenses catch different classes of problem, and neither is trustworthy unaudited.
A correctness lens invents plausible bugs; an over-engineering lens claims code is
redundant when it is load-bearing. Both failure modes look identical to the author:
a confident reviewer who is wrong, costing them a debate they should not have to have.

The fix is cheap. The code is right there — delete the thing you claim is dead, revert
the fix you claim is unnecessary, and run the suite. The diff tells you who was right.
Reviews built this way earn the author's trust, and the claims you kill never come back
in a later pass.

## Workflow

### 1. Read the patch, then decide whether you need the head

Always fetch metadata and the full patch. Read the whole thing before forming opinions.

```bash
gh pr view <N> --json title,body,headRefOid,headRefName,state,isDraft,mergeStateStatus,changedFiles
gh pr diff <N> --patch > <scratch>/pr<N>.diff
```

Check out the head only when you need to execute the project's code. A dependency
install on a large repo costs minutes, and a fourteen-line CI-workflow diff never
touches the app — paying for a worktree there is pure waste. When you do need it, use
somewhere disposable, never the user's working tree, and derive any server ports from
the PR number so parallel work never collides.

```bash
git worktree add <scratch>/pr<N> <head-sha> --detach
```

Old heads are a live hazard: a PR from months ago may no longer resolve against the
current lockfile. When the install or the gate cannot run on the head, say so in the
report and mark every claim that depended on it as resting on reading rather than
running. That is honest and still useful. Silently reviewing a different commit is not.

### 2. Establish a baseline that exercises the change

Run the verification that actually covers what the patch touches, and record the real
numbers. For application code that is the project's own gate — typecheck, lint, unit,
end-to-end — in CI's order, because a red baseline changes the whole review.

But the gate is a means, not the goal. Plenty of diffs are invisible to it: a CI
workflow, a Dockerfile, a shell guard, a deploy script. Running the app suite against
those proves nothing, and reporting it as evidence is the same failure as not testing
at all. Build the smallest synthetic reproduction instead — a throwaway git repo, a
scratch container, a hand-made input file — and use that as the baseline.

Whatever you run, a review that claims "tests pass" without having watched them pass
is the thing this skill exists to prevent.

### 3. Run both lenses

Apply them independently over the same patch so neither anchors the other. Each lens
has its own skill; read them for the checklists rather than reinventing them here:

- **Correctness** — `homunculus-programming-code-review`, in the sibling
  `code-review/` directory. Security, performance, correctness, maintainability.
  Add CI wiring and deploy fidelity to its list: a green suite proves nothing about
  a workflow step that was moved or a server the tests never boot. Ask what breaks
  and for whom.
- **Over-engineering** — the `ponytail-review` skill, if installed. Dead code,
  speculative flexibility, hand-rolled standard library, dependencies duplicating
  platform features, abstractions with one caller, churn with no behavior change.
  Ask what the diff looks like shorter. Without it, apply the same list directly.

Neither lens outputs findings you can trust yet. Both produce hypotheses, which is
what the next step is for.

Chase the claims the patch description makes. When a PR body says a feature "creates an
unlisted match" or "returns 404 in production", find the code or the library internals
that make it true. Library behavior counts as evidence — read `node_modules`, the
vendored source, the lockfile. Guessing at a dependency's semantics is how invalid
findings get written.

### 4. Falsify every finding

A finding that survives an attempt to kill it is worth the author's time. Match the
experiment to the claim:

| Claim | Experiment |
| --- | --- |
| "This code is redundant / the platform does it" | Delete it, run the suite. Passing means the claim holds; a failure names the behavior it was buying. |
| "This fix is unnecessary" | Revert it, run the suite. |
| "This test is load-bearing" | Revert the fix it guards, confirm that test and only that test fails. |
| "This is a bug" | Construct the failing input. Reach for a real run over a thought experiment. |
| "This is dead / unreferenced" | `rg` for every caller, including tests, configs, and generated output. |
| "This claim in the PR body is false" | Run the thing the claim describes and read what it prints. |
| "The stdlib / platform does this better" | Run both implementations over the same synthetic inputs and diff the outputs. Identical on the normal case plus a divergence on an edge case is the strongest version of this claim, because it upgrades a style note into a defect. |

Restore the tree after each experiment and confirm it is clean before the next one.

Two outcomes matter equally. A confirmed finding ships with the experiment as its
evidence. A killed finding goes in the chat report as rejected, with the command that
killed it — that is what stops the next reviewer, human or agent, from raising it again.

Surviving is not the same as firing. A mechanism you proved in a scratch repo may need
an input the codebase does not currently produce. Say which it is and what would trigger
it — "fails the day a test title contains a space" is actionable, while presenting the
same thing as a live break burns the credibility the experiments bought you.

### 5. Recommend fixes and test steps

For each surviving finding give the smallest diff that resolves it, and say how to
verify it. Prefer a command the user can paste. Name new coverage where none exists:
if nothing today catches the bug, the fix is not done until something does.

Separate blocking from follow-up. Blocking means the merge is wrong without it.
A latent defect is rarely blocking; a live one usually is. Everything else is a
follow-up, and say so plainly — a review that marks nine simplifications as blockers
reads as noise and gets ignored wholesale.

### 6. Draft comments, then stop

Report to the user in chat first: valid findings with their evidence, rejected claims
with what killed them, fixes, test steps, and a merge verdict. The rejected claims stay
in chat. They are useful to the user and they are noise to the author.

Then draft the PR comments in two sections, and wait.

**Thread comment** — items with no single line to point at: missing documentation,
process, cross-cutting follow-ups.

**Inline comments** — everything anchored to code. One finding per line reference.

Both use the same terse shape — the `caveman-review` skill's format if it is installed:
location, problem, fix. `<problem>. <fix>.`
Exact symbol names in backticks, exact line numbers, a concrete fix rather than
"consider refactoring". Drop throat-clearing, restatement of what the line does, and
hedging — if unsure, ask a question instead of implying a defect. Severity words
(`risk:`, `nit:`, `q:`) earn their place when the list mixes severities. Keep the
comment body to actionable items; verification narrative belongs in the chat report,
not on the author's PR.

Show both sections and stop. Posting is the user's call, not a step in this workflow.

### 7. Post only on the word

When the user says post, send inline comments as one review and the thread comment
separately. Inline comments only anchor to lines present in the diff, so verify the
anchors afterward rather than assuming they landed.

```bash
gh api repos/<owner>/<repo>/pulls/<N>/reviews --input review.json --jq '{id,state,html_url}'
gh pr comment <N> -F thread.md
gh api repos/<owner>/<repo>/pulls/<N>/comments \
  --jq '.[] | select(.pull_request_review_id==<id>) | "\(.path):\(.line // .original_line)"'
```

`review.json` carries `commit_id` (the head SHA), `event: "COMMENT"`, and a `comments`
array of `{path, line, side}` or `{path, start_line, line, side, start_side}` for a
range. Use `event: "COMMENT"` unless the user asks to approve or request changes —
those are their judgment to give, not yours.

## Re-review

When new commits land, diff the old head against the new one and review only the delta,
plus one confirmation per previously-raised finding. Fixes get the same treatment as
findings: revert the fix, prove the new test fails, restore. Check whether the PR body
absorbed the documentation items. Report what is fixed, what is new, and what is still
open, and keep the fixed items out of the draft comment — the author already did that work.

## Scope

Two things stay off the table regardless of what the diff tempts you into: pushing
commits and posting to the forge. Both are the user's to initiate. Everything else —
worktrees, installs, full suites, reverting code inside the scratch tree — is fair game,
because none of it is visible outside the sandbox.
