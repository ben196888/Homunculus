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

Iteration 1 is half run. Three of six planned runs are recorded here — eval-0 both
configurations, eval-1 with-skill. eval-1 baseline and both eval-2 runs were never
spawned, nothing has been graded, and there is no `benchmark.json`, so no pass rate
should be read out of this directory yet.

The one complete pair looks non-discriminating. On eval-0 the baseline independently
built a synthetic git repo, replayed the old and new guard bodies across 8 worktree
states, reproduced the quoted-path defect, and rejected two of its own suspected bugs
— most of what the skill is meant to induce — at near-identical cost (94.9k tokens and
474s with the skill, 93.0k and 472s without). A fourteen-line CI diff is probably too
easy a case to separate the two. The differences that remain, unconfirmed by grading,
are that the with-skill run kept seven killed claims out of its drafts and reported each
with the command that killed it, and that its `thread.md` is 17 lines against 51.

Treat replacing eval-0 with a harder case as the more useful next move than grading it.

What has happened instead: a single inline dry run of the skill against
ocftw/open-star-ter-village#409. It found one real latent defect in the PR and, more
usefully, five defects in the skill — unconditional worktree setup, a baseline step that
assumed the repo gate always applies, no stale-head fallback, a missing experiment shape
for stdlib-versus-hand-rolled claims, and no distinction between latent and live
findings. All five are fixed in the current `SKILL.md`. Treat that as a smoke test, not
a benchmark.
