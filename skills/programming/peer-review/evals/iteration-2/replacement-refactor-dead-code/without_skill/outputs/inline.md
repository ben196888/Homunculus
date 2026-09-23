> **Not posted.** Drafted only — read-only review, and #423 is already merged
> (`3486d0c2`), so these are line references on merged code rather than live review threads.

---

### 1. `packages/webapp/src/game/core/stage/action/validate/validators.ts` — `validateOvertime`, the `isOccupied` check

Anchor: the final guard in `validateOvertime`

    if (!ActionSlotSelector.isOccupied(G.table.actionSlots[actionName])) {
      return invalid('OVERTIME_TARGET_NOT_USED');
    }

**Severity: latent / non-blocking.**

`docs/rulebook.md` §f says "Repeat one one-action-point action **you** have already completed
this turn," but this only asks whether the slot is occupied — not by whom. I confirmed with a
throwaway test that the validator alone will let player `1` redeem against a slot occupied by
player `0`.

Not exploitable today: `refill` runs in `turn.onEnd` (`game.ts:62`) and calls
`ActionSlotsMutator.reset(G.table.actionSlots)`, so slots are per-turn and an occupied slot
necessarily belongs to the acting player. But that's an implicit invariant living in another
file, unasserted. Standard mode's board has shared slots; if slot scoping ever changes,
overtime starts silently repeating other players' actions and nothing fails.

Suggested: name the dependency here, and pin it with a test.

    // Per-turn slots: `refill` resets actionSlots in turn.onEnd, so an occupied
    // slot is always one the acting player used this turn. If slot scope ever
    // becomes round-wide/shared, this must also check the occupying player.
    if (!ActionSlotSelector.isOccupied(G.table.actionSlots[actionName])) {

---

### 2. `packages/webapp/src/game/store/slice/players.ts` — `useOvertimeToken`

    const useOvertimeToken = (state: Players, playerId: PlayerID): void => {
      state[playerId].token.overtime -= 1;
    };

**Severity: nit.**

`getNumOvertimeTokens` two functions up defends legacy snapshots with `?? 0`, but the mutator
doesn't, and there's no clamp at zero — an undefined field writes `NaN`, and a double-call
writes `-1`. Unreachable given the validate-then-mutate ordering in `applyActionCost` (I
confirmed a legacy snapshot is rejected before this runs), so this is defense-in-depth only.
If the fallback in the selector was worth writing, the symmetric guard here probably is too:

    state[playerId].token.overtime = Math.max(0, (state[playerId].token.overtime ?? 0) - 1);

---

### 3. `packages/webapp/src/game/store/slice/table.ts` — `round` field and `getRound`

Anchors: `round: 0` in `initialState`, `state.round += 1` in `playEvent`, and `getRound`.
Same finding applies to `RuleSelector.getTotalRounds` in `store/slice/rule.ts`.

**Severity: minor.**

Added as "groundwork for the header round badge." Five days after merge,
`git grep 'getRound\|getTotalRounds' origin/main -- packages/webapp/src` matches only the
definitions and their export entries; nothing reads `G.table.round` either. The badge never
landed.

Harmless, but this is the same PR that deletes `ACTION_CONFIGS` for being a single-consumer
layer with no consumers — worth applying the standard consistently. Either land the badge or
drop the three symbols and re-add them with the feature.

Secondary note for the persistence work in #424/#425: `state.round += 1` has no `?? 0`
fallback, unlike `token.overtime`. A resurrected pre-#423 snapshot would set `round` to `NaN`.
