# PR #423 review — `fix(webapp): per-player overtime token replaces nested mirror move`

`ocftw/open-star-ter-village` · head `3646a5eb` · base `main` · 31 files, +560/−453

**Heads up before anything else: this PR is already merged** (2026-07-22T21:35:39Z, landed as
`3486d0c2`). Nothing below is a merge gate any more; read it as post-merge findings and
follow-up work.

## Direct answers

**Is the old mechanism really gone?** Yes. Completely, and the type system now enforces it.
A repo-wide case-insensitive grep for `mirror` at the PR head returns **zero code hits** —
the only survivors are historical prose in `docs/phase-1-simplified-mode-spec.md`, an
unrelated `packages/webapp/README.md` sentence about mirroring uptime checks, and two
homepage content cards about Mirror Media. Every identifier from the old mechanism is gone:
`mirror.ts`, `Mirror`/`onMirror`, `validateMirror`, `MirrorableActionName`, `ignoreOccupied`,
`ACTION_CONFIGS`, `actionConfig.ts`, the `mirror` action slot, the `mirror` rule config, and
the `overtime-status` legend testid.

The removal is structurally enforced rather than merely tidy: `ActionSlots` is
`Record<ActionMoveName, ActionSlot>` and `ActionMoveName = keyof ActionMoves`, so dropping
`Mirror` from `ActionMoves` makes a stray `actionSlots.mirror` a compile error, not a silent
`undefined`. Same for `Rule.actionSlots` and `ActionRules`.

**Is it safe to merge?** Yes — it was. The full CI gate is green on the head, both on GitHub
and reproduced locally, and the three failure modes I actually tried to construct all got
killed by the code. The only leftovers are follow-ups, none blocking.

## Baseline (reproduced locally at head `3646a5eb`)

Disposable detached worktree at `/private/tmp/pr423-review-cace19/head`, CI's own order:

| Step | Result |
| --- | --- |
| `pnpm install --frozen-lockfile` | clean, 11.6s |
| `pnpm webapp lint` | No ESLint warnings or errors |
| `pnpm webapp exec tsc --noEmit` | clean |
| `pnpm webapp test --runInBand` | **114 passed / 114** |
| `pnpm webapp e2e` (ports 3423/3424) | **26 passed / 26**, 1.2m |

GitHub check-runs on the same SHA: `Webapp baseline` success, `Homepage baseline` success,
`Required baseline` success, `Required evidence` success.

## Valid findings

All three are **follow-up**, not blocking.

### 1. Dead code shipped: the round counter has no consumers

`Table.round`, `TableSlice.selectors.getRound`, and `RuleSelector.getTotalRounds` are added
by commit 2/7 and referenced by nothing outside their own definitions. The PR body is candid
that this is "groundwork for the header round badge" — but groundwork with no consumer is
speculative state on a shape the same PR flags as a save-compat hazard, and it rode in on a
PR whose title is about something else.

*Experiment:* deleted all three (the interface field, the `round: 0` initialiser, the
`state.round += 1` in `playEvent`, `getRound`, `getTotalRounds`, and both selector
registrations — 16 lines across `table.ts` and `rule.ts`). `tsc --noEmit` clean, `lint`
clean, **114/114 still pass**. Nothing in the codebase was buying anything from it.

*Fix:* either revert the round counter to the PR that renders the badge, or leave it and
accept the (small) cost. If it stays, it wants one test asserting `getRound` increments per
`playEvent`, because today nothing would notice if `playEvent` stopped incrementing.

### 2. Deleting `ACTION_CONFIGS` traded away compile-time exhaustiveness

`actionConfig.ts` held `ACTION_CONFIGS: Record<RegularActionName, ActionConfig>`. A `Record`
over a closed union is *total* — adding a sixth action to `ActionMoves` was a compile error
until you filled in its config. Commit 5/7 replaced it with two bare `switch` statements in
`ContextAction.tsx`: the board-activation `useEffect` (~line 113) and `handleConfirm`
(~line 251). A `switch` with no `default` in a `void`-returning function is not exhaustive-
checked by TypeScript, so a missing case is a silent no-op.

Deleting the config layer was the right call — it had exactly one consumer once `mirror`
was gone, which is precisely the abstraction this kind of refactor should collect. The
finding is only that the safety property it carried wasn't carried over.

*Experiment:* deleted the entire `case 'recruit':` block from `handleConfirm`. `tsc --noEmit`
**clean**, `lint` **clean**, `pnpm webapp test` **114/114 pass**. The recruit button just
silently does nothing. Only Playwright caught it — `pnpm webapp e2e` went to 24 passed / 2
failed (Scenario 3, Scenario 10).

*Fix, and I ran it both ways:*

```ts
      default: {
        const _exhaustive: never = actionName;
        return _exhaustive;
      }
```

Added to the `handleConfirm` switch: `tsc` clean, `lint` clean, 114/114 pass — no regression.
Then with the `recruit` case removed on top of it:
`src/components/board/ContextAction.tsx(271,15): error TS2322: Type '"recruit"' is not
assignable to type 'never'.` The guard fires exactly when it should and is silent otherwise.
The same guard belongs on the `useEffect` switch.

### 3. Spec doc still documents the removed mechanism

`docs/phase-1-simplified-mode-spec.md` got a "Superseded by #423" note on **Task 12** only.
Left untouched describing code that no longer exists:

- **Task 10** (line 193) — "Enable and fix mirror (Doin' Overtime) action", `mirror.ts`,
  the slot-reset trick, `available: true` in `rule.ts`.
- **Task 11** (line 205) — the "Mirror UI" 2-step wizard row and `onMirror(target, ...params)`.
- **Task 13** (line 265) — the Scenario 9 row: "mirror (Doin' Overtime): repeats
  removeAndRefillJobs, costs 2 AP total". The AP figure is wrong under the new rule: the
  redeemed action costs only its own 1 AP, which is what e2e Scenario 9 now asserts.

Adding the note to one of four spots reads as an oversight, not a decision. Cheapest fix is
one superseded note per stale section plus a corrected Scenario 9 row.

### 4. Nit: `RegularActionName` is now a pure alias

`ContextAction.tsx:36` — `type RegularActionName = ActionMoveName;`. It earned its name when
it meant `Exclude<ActionMoveName, 'mirror'>`. Now it's a synonym that costs a hop when
reading, and the file casts through it three times. Inline `ActionMoveName`.

## Coverage gap (follow-up)

There is no component test for `ContextAction`. The overtime UI path — chip states, the
occupied-action prompt, and threading `{ useOvertime: true }` into the right move — is
exercised only by e2e Scenario 9, and only for `removeAndRefillJobs`. The move layer is well
covered for all five actions; the *UI dispatch* for the other three eligible actions
(`recruit`, `contributeOwnedProjects`, `contributeJoinedProjects`) rests on the switch that
finding 2 shows is unguarded. Fixing finding 2 largely closes this without new tests.

## Claims I raised and then killed

These are for you, not for the author. Each one is a plausible-sounding objection that the
code actually survives, so they should not come back in a later pass.

**"`useOvertime` on a free slot silently burns the token / bypasses slot occupation."**
This was genuinely true in commit 3/7, where `applyActionCost` read
`if (options?.useOvertime && ActionSlotSelector.isOccupied(slot))` and the validator only
entered the overtime branch when `occupied`. Commit **7/7 ("reject overtime on free actions")
closed it**: `validateSlotAndActionTokens` now delegates to `validateOvertime` for any
`useOvertime` request, and `validateOvertime` returns `OVERTIME_TARGET_NOT_USED` when the
slot is free. *Experiment:* reverted the guard to `if (opts?.useOvertime && occupied)` —
2 tests fail immediately ("move validators reject useOvertime on a free slot" and "rejects
overtime on a free slot without mutating state"). The fix is load-bearing and guarded. If
you only skim the branch history, note the bug existed mid-PR and was fixed in the final
commit — the merged state is correct.

**"The mirror double-charge could regress unnoticed."** *Experiment:* changed
`applyActionCost` to charge `cost + 1` when `useOvertime` — **4 tests fail**. The no-surcharge
rule is genuinely pinned, not just asserted in the PR body.

**"`applyActionCost` now spends the token unconditionally, so any caller that forgets to
validate double-spends."** Real in the abstract, not reachable today: all five callers
(`createProject`, `recruit`, `contributeOwnedProjects`, `contributeJoinedProjects`,
`removeAndRefillJobs`) run their validator and `throw new ActionValidationError` before
reaching it, and the "failed validation never consumes the token (atomicity)" test covers
the ordering. The function's docstring states the precondition. Not worth the author's time.

**"The `Player.token` / `Table` shape change breaks in-flight matches."** `src/server.ts`
constructs `Server({ games, origins })` with no `db` option, so boardgame.io falls back to
in-memory storage — a deploy already resets every match. The PR's risk note is accurate as
written, not hand-waving.

**"A player who ends their turn early doesn't get the overtime token back."** `refill` is
invoked from `turn.onEnd` in `game.ts:62` for every player, and it resets the overtime token
on the same line-pair as the AP reset. Parity is structural; the "refill at turn end restores
the overtime token" test pins it.

**"`getNumOvertimeTokens`'s `?? 0` is unreachable dead defense."** True under the type
(`overtime: number` is non-optional) and true in practice (in-memory storage), so the legacy-
snapshot branch can't fire. It's two characters and it's correct in intent. Not worth raising.

**"The AP dots hardcode `Array.from({ length: 4 })` instead of reading
`RuleSelector.getPlayerMaxActionTokens`."** Pre-existing; this PR only re-indented the block
when wrapping it in the new flex row. Flagging re-indented lines as new findings is how a
review loses credibility.

## Verdict

**Safe.** The replacement is clean, the old mechanism is genuinely and structurally gone, the
central rule change (no AP surcharge) is pinned by tests that fail when you break it, and the
one real bug introduced mid-PR was caught and fixed by the author's own last commit. Merging
was the right call.

Three follow-ups worth a small cleanup PR: the exhaustiveness guard on the two `ContextAction`
switches (the only one with any teeth), the unused round counter, and the stale spec sections.
