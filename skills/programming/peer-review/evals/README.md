# peer-review evals

Everything for testing this skill lives here, alongside the skill itself.

```
peer-review/
├── SKILL.md
└── evals/
    ├── README.md          ← you are here
    ├── evals.json         ← the only file you hand-edit
    └── iteration-N/<eval-name>/
        ├── eval_metadata.json      generated from evals.json
        ├── with_skill/outputs/
        └── without_skill/outputs/
```

`evals.json` is the single source of truth for prompts and assertions.
`eval_metadata.json` is generated, so change an assertion in one place only:

```bash
pnpm eval-init programming/peer-review 2
```

Re-running it against an existing iteration refreshes the metadata and leaves any
captured outputs untouched.

## Running an iteration

Each test case gets two subagents spawned in the same turn — one told to read
`SKILL.md`, one given the bare prompt. Both are told the exercise is offline with no
permission to write to GitHub, because letting a review agent comment on a real
repository to satisfy a benchmark is not an acceptable trade. That makes "did not post"
useless as a discriminator, so `awaits-post-confirmation` carries that weight instead.

Each run writes four files to its `outputs/` directory:

| File | Contents |
| --- | --- |
| `report.md` | the full report the run would give the user in chat |
| `thread.md` | drafted thread-level PR comment, empty if none warranted |
| `inline.md` | drafted line-anchored PR comments, empty if none warranted |
| `transcript-notes.md` | every verification and falsification command actually run, with its real result |

`transcript-notes.md` is what most assertions grade against — it is the difference
between a review that ran experiments and one that narrated them.

Capture `total_tokens` and `duration_ms` into `timing.json` per run as each task
notification arrives; that data is not recoverable later.

## Status

Iteration 1 is a partial run, read qualitatively rather than graded. Three of six runs
are recorded — the old eval-0 in both configurations, eval-1 with-skill. eval-1 baseline
and both eval-2 runs were never spawned, and there is no `benchmark.json`, so no pass
rate should be read out of this directory.

## What iteration 1 taught

The one complete pair did not discriminate, and that is the finding. On a fourteen-line
CI diff (PR #409) the baseline independently built a synthetic git repo, replayed the old
and new guard bodies across eight worktree states, reproduced the quoted-path defect, and
rejected two of its own suspected bugs — at near-identical cost, 94.9k tokens and 474s
with the skill against 93.0k and 472s without. A diff that small does not tempt anyone
into reasoning instead of running, so the skill had nothing to add. eval-0 is now PR #432
instead, chosen because it contains a claim that is plausible, obvious, and false.

Three differences did hold up on close reading, and each is now something the skill asks
for explicitly:

- **The rejected pile.** With the skill, seven killed claims were reported with the command
  that killed each, and kept out of the drafted comments. The baseline report has no
  rejected section at all — it mentions dismissing two suspicions in passing and drops
  them. That record is the skill's clearest contribution.
- **Comment discipline.** With the skill, `thread.md` was 17 lines and the inline comments
  were problem-then-fix. The baseline's `thread.md` was a 51-line essay with scenario
  tables, and its inline comments carried verification narrative — "I confirmed that in a
  scratch repo" — into the author's PR.
- **Fixes tested too.** With the skill, the recommended pathspec fix was itself run through
  a six-scenario matrix, with a paste-able command. The baseline proposed an untested
  filter change. `proposed-fix-itself-tested` now covers this.

And one thing the skill got wrong: the with-skill run replayed the guard under
`bash --noprofile --norc -eo pipefail` and called that "GitHub Actions' own shell
contract". The baseline read the actual run log — `shell: /usr/bin/bash -e {0}`, no
`pipefail`. The conclusion survived, but the evidence came from a different system than
the one under review. `SKILL.md` now treats the execution environment the same way it
treats library semantics: read it from the log or the config, never from recall, and
`execution-contract-read-not-assumed` checks for it.

What has happened instead: a single inline dry run of the skill against
ocftw/open-star-ter-village#409. It found one real latent defect in the PR and, more
usefully, five defects in the skill — unconditional worktree setup, a baseline step that
assumed the repo gate always applies, no stale-head fallback, a missing experiment shape
for stdlib-versus-hand-rolled claims, and no distinction between latent and live
findings. All five are fixed in the current `SKILL.md`. Treat that as a smoke test, not
a benchmark.

## Iteration 2 automated grading

Human review is still required before treating these grades as final. The automated pass
produced:

| Metric | With skill | Without skill | Delta |
| --- | --- | --- | --- |
| Assertion pass rate | 70.1% | 50.7% | +19.5 points |
| Mean wall time | 963.8s | 733.7s | +230.0s |
| Mean tokens | 157,966 | 121,170 | +36,796 |

The cleanest skill contribution is testing its own proposed fix: 3/3 skilled runs pass
`proposed-fix-itself-tested`, versus 0/3 baselines. Preserving killed claims with their
commands is 3/3 versus 1/3. The counterexample matters too: on PR #425, the baseline
live-tested stale-credential demotion while the skilled run accepted it from source
reading, so `pr-body-claims-run-not-read` favors the baseline.

Two intended behaviors fail in all six runs: explicitly waiting for posting confirmation,
and attaching a runnable verification command to every finding. Draft separation is weak
in both configurations. These are candidates for the next skill revision, not reasons to
inflate this iteration's score.

There is one run per configuration for each of three different evals. The benchmark's
standard deviation is therefore spread across heterogeneous cases, not repeated-run
variance; it is not a flakiness estimate or a statistical-significance result.
