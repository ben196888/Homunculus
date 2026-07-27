Verified at head `3646a5eb`: local `lint` / `tsc --noEmit` / `test --runInBand` (114/114) / `e2e` (26/26) all green, matching CI.

`mirror` is fully gone — repo-wide grep finds zero code references, and `ActionSlots = Record<ActionMoveName, ActionSlot>` makes a leftover slot a compile error rather than a silent `undefined`. Nothing blocking. Three follow-ups:

- **Doc drift.** `docs/phase-1-simplified-mode-spec.md` got the "Superseded by #423" note on Task 12 only. Task 10 (L193), Task 11 (L205), and the Task 13 Scenario 9 row (L265) still describe `mirror.ts`, the `onMirror` wizard, and "costs 2 AP total" — the last one now contradicts the shipped rule and the e2e assertion. Add the same note to those sections and correct the Scenario 9 row.
- **Dead code.** `Table.round`, `TableSlice.getRound`, and `RuleSelector.getTotalRounds` have no consumers. Deleting all 16 lines keeps `tsc`, `lint`, and 114/114 green. Either defer them to the badge PR or add a test that `playEvent` increments the round.
- **No `ContextAction` component test.** The overtime UI path is covered only by e2e Scenario 9, and only for `removeAndRefillJobs`. The `never` guard below covers most of the risk without new tests.
