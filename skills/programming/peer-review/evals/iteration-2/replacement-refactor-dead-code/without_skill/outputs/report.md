# Review — ocftw/open-star-ter-village PR #423

`fix(webapp): per-player overtime token replaces nested mirror move`
Author: ben196888 · base `main` · head `fix/418-overtime-token` · +560 / −453 across 31 files

## Heads-up first: this PR is already merged

**State: MERGED** at 2026-07-22T21:35:39Z, merge commit `3486d0c2`. Zero human or bot
reviews were recorded (`reviewCount: 0`) — it went in on green CI alone. Two further
commits have landed on `main` since (`6cfedcb4`, `795d3d4c`).

So "is it safe to merge" is retrospective. I reviewed it as "is it safe to *keep*, and
is there anything that needs a follow-up." Answer: **yes, keep it — the swap is clean and
the old mechanism is genuinely gone.** Three follow-ups below, none blocking.

---

## 1. Is the old mechanism really gone?

Yes. This is the strongest part of the PR. I checked at the merge commit and again on
current `origin/main`.

**Files deleted** (`git diff --diff-filter=D 3486d0c2^1 3486d0c2`):
- `packages/webapp/src/game/core/stage/action/move/mirror.ts`
- `packages/webapp/src/components/board/actionConfig.ts`

**Every seam the old `mirror` mechanism touched was closed, not just the entry point:**

| Seam | Old | Now |
|---|---|---|
| Move registry | `mirror` in `action.ts` `moves:` | absent |
| Type union | `ActionMoves.mirror` → `ActionMoveName` | 5 keys only, `move/type.d.ts` |
| Action slots | `actionSlots.mirror` | 5 slots, `store/slice/actionSlots.ts` |
| Rule config | `actionSlots.mirror.available` | replaced by `player.overtimeTokens` / `overtimeMaxActionCost` |
| Validator | `validateMirror` | `validateOvertime` |
| UI enum | `UserActionMoves.Mirror` | absent from `lib/reducers/actionStepSlice.ts` |
| UI config layer | `ACTION_CONFIGS` / `MirrorableActionName` | deleted; `ContextAction` handles the closed 5-action set directly |
| Board legend | `data-testid="overtime-status"` in `JobMarket.tsx` reading `actionSlots.mirror` | removed, no orphan reference anywhere |
| E2E | Scenario 9 drove the mirror wizard | Scenario 9 drives the token flow |

Verification:

    git grep -il 'mirror' origin/main -- packages/webapp/src packages/webapp/e2e   # → no hits
    git grep -n 'overtime-status' origin/main                                      # → no hits
    rg -n 'ACTION_CONFIGS|actionConfig' packages/webapp/src                        # → no hits

The only `mirror` strings left in the repo at merge time were prose in
`docs/phase-1-simplified-mode-spec.md` (Tasks 10/11 and the E2E scenario table row 9, which
still said *"mirror (Doin' Overtime): repeats removeAndRefillJobs, costs 2 AP total"*). That
was genuinely stale doc drift on the day of merge — the PR annotated only Task 12 as
superseded. **It has since been resolved incidentally:** #431 archived that doc, and
`git grep -il mirror origin/main -- docs` now returns nothing. Nothing left to do.

Also confirmed the dangling reference `mirrorOccupied` in `JobMarket.tsx` was removed along
with its now-unused `ActionSlotSelector` import — i.e. the deletion was carried through to
imports, not left half-done.

## 2. Is the replacement correct?

The new design is tight, and the ordering discipline is the reason it holds up.

**Validation-first, single choke point.** All five regular moves follow an identical shape:
call the shared validator, `throw ActionValidationError` on failure, *then* mutate — with
`applyActionCost(G, playerID, name, options)` as the single place AP is charged and the slot
is resolved. That means "a rejected move never consumes the token" is structural, not a
property each move has to remember. `applyActionCost` is 12 lines and does exactly one thing.

**Client/server rule drift is designed out.** `ContextAction` calls the *same*
`validateOvertime` / `validate*` functions the server move calls, and re-runs the preflight at
click time (`handleConfirm` → `getPreflightFailure()`) because multiplayer state can move under
the selection. The UI's block reason is derived from the validator's own result, so the message
the player sees cannot diverge from the rule that rejects them.

**Against the rulebook.** `docs/rulebook.md` §f: *"Doin' Overtime — Cost: 1 action point.
Repeat one one-action-point action you have already completed this turn."* The old `mirror`
charged 2 AP (1 for the mirror slot + 1 more through the nested sub-move call). The PR's claim
that this was a double-charge is correct: in physical play, placing on the Overtime slot *is*
the repeat. New behavior charges the action's own 1 AP and nothing else — matches. Rulebook Q5
(a project reduced to 1 AP becomes overtime-eligible) also works, because eligibility reads
`RuleSelector.getActionTokenCost` dynamically against `overtimeMaxActionCost` rather than
hardcoding a list.

**Test coverage is real, not nominal.** 114/114 Jest pass. The overtime block in `game.test.ts`
covers all four eligible actions end-to-end plus create-project's 2-AP rejection, free-slot
rejection, spent-token rejection, atomicity, once-per-turn, and turn-end restore.
`validators.test.ts` pins one assertion per `OVERTIME_*` reason code.

I wrote six additional probe tests for edges the suite doesn't cover. All six passed:
- rejecting overtime at 0 AP leaves the token intact
- the slot stays occupied after redemption (so a 3rd attempt still needs a token)
- a legacy snapshot with no `token.overtime` is rejected cleanly — no `NaN` written
- `{ useOvertime: false }` on an occupied slot still returns `ACTION_OCCUPIED` (no bypass)
- a truthy non-boolean `useOvertime` from a hostile client behaves identically to `true`
  (charges 1 AP, spends the token) — no exploit
- (see finding A below)

`tsc --noEmit` clean, `next lint` clean, CI on the head commit all green including the
Playwright job (`pnpm webapp e2e`).

## 3. Findings

### A. Latent — overtime does not verify *you* used the slot (currently unreachable)

`validateOvertime` (`validators.ts`) gates on `ActionSlotSelector.isOccupied(...)` only. The
rulebook says *"an action **you** have already completed this turn."* My probe P6 confirms the
validator alone will happily let player `1` redeem against a slot occupied by player `0`.

It is **not exploitable today**: `refill` runs in `turn.onEnd` (`game.ts:62`) and calls
`ActionSlotsMutator.reset(G.table.actionSlots)`, so slots are per-turn and an occupied slot
always belongs to the acting player. But that is an implicit invariant held in a different
file, with nothing asserting it. If action slots ever become round-scoped and shared (which is
exactly the Standard-mode board shape), overtime would silently start repeating other players'
actions. Worth a one-line comment in `validateOvertime` naming the dependency, plus a
regression test pinning "slots reset at turn end."

### B. Minor — the PR introduces dead code while removing dead code

`Table.round`, `TableSelector.getRound`, and `RuleSelector.getTotalRounds` were added as
"groundwork for the header round badge." Five days on,
`git grep 'getRound\|getTotalRounds' origin/main -- packages/webapp/src` hits only their own
definitions and exports. `G.table.round` increments on every event card and is read by nothing.
The badge never landed. It's harmless and cheap, but slightly ironic in a PR whose headline
cleanup is deleting a single-consumer config layer. Either land the badge or drop the three
symbols.

### C. Nit — `useOvertimeToken` has no floor

    const useOvertimeToken = (state: Players, playerId: PlayerID): void => {
      state[playerId].token.overtime -= 1;
    };

`getNumOvertimeTokens` defends legacy snapshots with `?? 0`, but the mutator doesn't — an
undefined field would write `NaN`, and there's no clamp at zero. Unreachable given the
validate-then-mutate ordering (probe P3 confirms), so this is defense-in-depth only.

### D. Scope nit

Two unrelated chores rode along: the `@sentry/react` → `@types/react@18` peer pin in
`pnpm-workspace.yaml`, and the Playwright gitignore entries. Both are fine changes; they just
make `git log -S` on the overtime work noisier. Not worth acting on retroactively.

### E. Process observation

31 files, a game-rule mechanism swap, and a state-shape change merged with `reviewCount: 0`.
The work happens to be good, and the PR body's evidence table is unusually thorough — but the
project's own `CLAUDE.md` calls for review before merge, and nothing here caught the eye of a
second pair. Findings A and B are precisely the kind of thing a reviewer catches.

## 4. Risk that was accepted

`Player.token` and `Table` shapes changed, breaking in-flight matches. The PR flags this and
argues it's acceptable because the server is in-memory. I verified that's still true —
`src/server.ts` on `main` constructs `Server({ games, origins })` with no `db:` option, so a
deploy already resets matches. Note for whoever lands persistence (the #424/#425 stack): a
resurrected pre-#423 snapshot would have `table.round === undefined`, and `state.round += 1`
would write `NaN` with no fallback, unlike the overtime field which does have one.

## Verdict

Safe. The mechanism swap is complete — no orphaned types, slots, config, test IDs, imports, or
UI branches survive, on the merge commit or on current `main`. The replacement is better
factored than what it replaced (one shared cost function instead of a nested move call, one
shared validator instead of client/server duplication) and it fixes a genuine 2-AP overpay
against the printed rules. Nothing here warrants a revert.

Worth opening a small follow-up issue for **A** (pin the per-turn slot invariant before anyone
touches slot scoping) and **B** (land or drop the round-counter groundwork).
