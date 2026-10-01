### `packages/webapp/src/components/board/ContextAction.tsx` — L251 (`handleConfirm` switch)

risk: dropping `ACTION_CONFIGS: Record<RegularActionName, ActionConfig>` lost compile-time exhaustiveness; this `switch` has no `default`, so a missing case is a silent no-op. Deleting the `case 'recruit':` block passes `tsc`, `lint`, and 114/114 unit tests — only e2e catches it. Add `default: { const _exhaustive: never = actionName; return _exhaustive; }` (verified: clean today, `TS2322` when a case is dropped).

### `packages/webapp/src/components/board/ContextAction.tsx` — L113 (board-activation `useEffect` switch)

risk: same missing-case hazard as `handleConfirm` — a new action silently activates no board elements. Add the same `default: { const _exhaustive: never = currentAction; }` guard.

### `packages/webapp/src/components/board/ContextAction.tsx` — L36

nit: `type RegularActionName = ActionMoveName;` is a pure alias now that `mirror` is gone. Inline `ActionMoveName` at its three use sites.

### `packages/webapp/src/game/store/slice/table.ts` — L16, L32, L39, L50

`round`, `playEvent`'s increment, and `getRound` have no consumers; deleting them keeps `tsc`, `lint`, and 114/114 green. Defer to the header-badge PR, or add a test asserting `playEvent` increments `round`.

### `packages/webapp/src/game/store/slice/rule.ts` — L295

`getTotalRounds` has no callers. Same call as `Table.round` — defer with the badge or cover it.

### `docs/phase-1-simplified-mode-spec.md` — L265

Scenario 9 still reads "mirror (Doin' Overtime): repeats removeAndRefillJobs, costs 2 AP total". Redemption now costs only the action's own 1 AP, which is what the updated e2e asserts. Rewrite the row and add the "Superseded by #423" note to Tasks 10 and 11.
