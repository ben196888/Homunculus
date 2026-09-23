Post-merge simplification pass. Not blocking — all follow-up.

The diff is smaller than it reads: 341 of the 861 added lines are tests/config/docs
and 172 source lines were removed. The one place with real volume left is
`DevToolsWidget.tsx` (205 lines, 18 inline style objects, two copy-pasted radio
fieldsets). Moving its static styles to a `.dev-tools*` block in `globals.css` and
extracting one generic `RadioGroup` takes it to 102 lines and lets `Modal`'s new
`style` prop — currently a one-consumer escape hatch on a shared design component —
become `className`. Net −80 lines; verified against `tsc`, `next lint`, `jest`
(147/147) and `playwright` (37/37).

For the record, four things that look deletable and are not, so they don't come back
in a later pass: the `Modal` focus trap, its radio-group filter, `GameView`'s
`boardKey`, and the production e2e harness. Each was deleted in a scratch tree and
each broke something (the harness costs 1.7s of test time on a build CI already ran).

`e2e:production` hand-copies `.next/static` and `public` into the standalone dir,
duplicating `Dockerfile:58-60`. If the Dockerfile gains a copy step, the production
e2e stops matching the deploy without failing. Worth a cross-reference comment on
both sides.
