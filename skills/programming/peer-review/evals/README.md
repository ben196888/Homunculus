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

Iteration 1 has never executed. Six agents were spawned and all six died on a monthly
spend limit before producing output, so there is no grading, no benchmark, and no
baseline comparison yet.

What has happened instead: a single inline dry run of the skill against
ocftw/open-star-ter-village#409. It found one real latent defect in the PR and, more
usefully, five defects in the skill — unconditional worktree setup, a baseline step that
assumed the repo gate always applies, no stale-head fallback, a missing experiment shape
for stdlib-versus-hand-rolled claims, and no distinction between latent and live
findings. All five are fixed in the current `SKILL.md`. Treat that as a smoke test, not
a benchmark.
