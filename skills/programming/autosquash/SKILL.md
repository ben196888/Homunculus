---
name: homunculus-programming-autosquash
description: Safely clean a feature branch by folding existing fixup! and squash! commits, preserving dirty work, verifying the final tree, and updating the remote with an exact force-with-lease. Use when the user explicitly asks to autosquash, clean up marked fixup/squash commits, or prepare those marked commits for handoff. Do not use for general history editing, single-commit squashing, or merely opening a PR.
argument-hint: "[--base <ref>] [--remote <name>]"
---

# Safe Autosquash

Clean only commits that Git already marks with `fixup!` or `squash!`. The helper
owns the mechanical safety checks; you own base selection, synthesized messages,
verification selection, and conflict judgment.

## 1. Inspect the plan

Run from the repository being cleaned:

```bash
python3 <autosquash-skill>/scripts/autosquash.py plan $ARGUMENTS
```

The helper fetches the selected remote, then reports the inferred base, remote
branch, divergence, and every marked commit with its target. Pass `--base` when
PR/MR metadata and the remote default disagree or inference is unavailable.

Stop if the plan does not match the user's branch intent. V1 deliberately rejects
detached HEADs, protected branches, merge commits in the rewrite range, missing or
ambiguous targets, and targets outside the feature-branch range.

If there are no marked commits, report the no-op. Do not reinterpret ordinary
commits as fixups and do not push.

## 2. Prepare squash messages and verification

`fixup!` discards its own message and preserves the target message. For each target
receiving a `squash!` commit, synthesize one message that captures the combined
intent. Its subject must use Conventional Commits, imperative mood, and fewer than
72 characters. Add a body only when the result would otherwise be non-obvious.

Inspect the repository's `AGENTS.md`, README, package manifest, and CI configuration
for the smallest fast checks that exercise the affected files. Pass each discovered
check as a separate `--verify` argument. If no relevant check exists, the helper's
committed-tree identity check remains mandatory; say explicitly that no project
check was available.

## 3. Apply

```bash
python3 <autosquash-skill>/scripts/autosquash.py apply $ARGUMENTS \
  --squash-message '<target-sha>=<conventional message>' \
  --verify '<fast repository check>'
```

Omit `--squash-message` when the plan contains only `fixup!` commits. Repeat it for
multiple squash targets and repeat `--verify` for multiple checks.

The helper:

- records dirty tracked, staged, and untracked state and stashes it;
- rebases local work onto a newly fetched remote branch when necessary;
- runs Git's interactive autosquash silently by overriding both the sequence and
  commit-message editors, so the user's configured terminal or GUI editor never opens;
- verifies that autosquash preserved the committed tree;
- runs the selected checks while the saved dirty state is still isolated;
- restores and fingerprints the dirty state before any push; and
- pushes with an explicit fetched-SHA lease, or sets `origin` as upstream for a
  new branch.

It reports the old and new SHAs. Recovery intentionally uses the reflog rather than
a backup branch.

Do not remove the helper's `GIT_SEQUENCE_EDITOR` or `GIT_EDITOR` overrides. They are
what makes the workflow non-interactive; `squash!` messages come from the validated
`--squash-message` values instead of an editor prompt.

## 4. Handle conflicts conservatively

If reconciliation or autosquash stops on a conflict, inspect the base, target commit,
marked commit, and surrounding code. Resolve only when the intended combined result
is clear, stage the resolution, then resume:

```bash
python3 <autosquash-skill>/scripts/autosquash.py continue
```

Ask the user when the conflict requires a product or semantic choice. To roll the
whole operation back and restore the saved workspace:

```bash
python3 <autosquash-skill>/scripts/autosquash.py abort
```

Never bypass a failed lease, failed verification, changed-tree check, or failed
workspace restoration. Report the retained stash SHA and recovery instructions.

## Report

Return the resolved base and remote, folded commit count, old and new SHAs,
verification results, workspace restoration, push result, and the reflog recovery
command. Keep ordinary unmarked commits visibly out of scope.
