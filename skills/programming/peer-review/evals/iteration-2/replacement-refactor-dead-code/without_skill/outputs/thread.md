> **Not posted.** Drafted only — this review was read-only. Also note #423 is already
> merged (`3486d0c2`), so this would be a post-merge note rather than review feedback.

Reviewed this retroactively with the question "did the mirror → overtime-token swap
actually remove the old mechanism, or just stop calling it." **It removed it.** Verified at
the merge commit and again on current `main`:

- `mirror.ts` and `actionConfig.ts` deleted outright.
- `mirror` is gone from every seam it touched, not just the entry point: the move registry
  in `action.ts`, the `ActionMoves` / `ActionMoveName` union, `actionSlots` initial state and
  `reset`, the rule config, `UserActionMoves`, the `ACTION_CONFIGS` / `MirrorableActionName`
  layer, the `data-testid="overtime-status"` legend in `JobMarket.tsx`, and E2E Scenario 9.
- `git grep -il mirror origin/main -- packages/webapp/src packages/webapp/e2e` → no hits.
  `git grep -n overtime-status origin/main` → no hits. No orphaned test IDs, no dangling
  imports (the now-unused `ActionSlotSelector` import in `JobMarket.tsx` went with it).

The replacement is better factored than what it replaced. `applyActionCost` gives AP charging
and slot resolution a single choke point, and every move is validate-then-mutate, so
"a rejected move never consumes the token" is structural rather than something each move has
to remember. `ContextAction` calling the same `validateOvertime` the server move calls means
the UI's block reason cannot drift from the rule that rejects it.

I also checked the AP change against `docs/rulebook.md` §f — the old 2 AP really was a
double-charge, since placing on the Overtime slot *is* the repeat in physical play. And
rulebook Q5 still works, because eligibility reads `getActionTokenCost` dynamically instead of
hardcoding which actions qualify.

Independently verified: `tsc --noEmit` clean, `next lint` clean, 114/114 Jest. I added six
throwaway probe tests for edges the suite doesn't cover — 0 AP rejection, slot stays occupied
after redemption, legacy snapshot with no `token.overtime`, `useOvertime: false` on an occupied
slot, and a truthy non-boolean `useOvertime` from a hostile client. All six behaved correctly;
no exploit.

Two things worth a follow-up issue, neither blocking and neither a reason to revert:

1. **`validateOvertime` doesn't check that *you* used the slot.** The rulebook says "an action
   you have already completed this turn," but the check is just `isOccupied`. Unreachable today
   because `refill` resets `actionSlots` in `turn.onEnd`, so an occupied slot always belongs to
   the acting player — but that invariant lives in `game.ts` with nothing asserting it. If slots
   ever become round-scoped and shared (the Standard-mode board shape), overtime would silently
   repeat other players' actions. A comment naming the dependency plus a regression test would
   pin it.

2. **`Table.round` / `getRound` / `getTotalRounds` are dead.** Added as groundwork for the header
   round badge; five days on, nothing reads them. Mildly ironic in the PR that deletes a
   single-consumer config layer. Land the badge or drop the three symbols.

Last thing, process rather than code: 31 files, a game-rule mechanism swap, and a state-shape
change merged with zero recorded reviews. The evidence table in the description is genuinely
excellent and the work holds up — but findings 1 and 2 are exactly what a second reader catches.
