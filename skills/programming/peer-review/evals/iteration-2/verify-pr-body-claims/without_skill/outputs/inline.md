# Line-anchored comments (drafts — not posted)

---

### `packages/webapp/src/app/game/[matchID]/page.tsx` — lines 143-147

```ts
  const isTerminated =
    Boolean(match) && hasStarted && match!.players.some((player) => !hasPlayerName(player));
```

The description says this keys off "a **mixed** named/unnamed seat list" and that "dev-harness matches (all seats unnamed) are unaffected". The condition is actually *some* unnamed, not *mixed* — an all-unnamed started match would trip it. The behaviour is still right, but only because the dev harness is a local match on `/dev` that never renders this page, not because of anything in this expression. Worth fixing the changelog wording (or adding the mixed check the wording implies), otherwise someone later reads the description, sees the mismatch, and "fixes" the wrong side.

---

### `packages/webapp/src/app/game/[matchID]/page.tsx` — line 155

```ts
  usePolling(pollMatch, 3_000, !isExpired);
```

This replaced a condition that stopped polling once the board was up, so every client now hits the metadata endpoint every 3s for the room's whole lifetime. Measured 3 requests per 10s per client while the board was showing. That's the intended cost for termination detection during play, but it also keeps polling forever once the terminated overlay is up and after game over, where nothing can change the outcome. Suggest latching: once `isTerminated` is true, drop out of the poll.

---

### `packages/webapp/src/components/board/GameHeader.tsx` — lines 82-102 (the `role="menu"` block)

The `aria-haspopup` and 44px claims hold, but the menu isn't keyboard-operable: no Escape-to-close, no arrow-key navigation between `menuitem`s, and the dismiss layer is an `aria-hidden` div with `onClick` only. A keyboard user who opens the ⋯ menu can tab into the item but can't dismiss without activating something. Small enough to fold into the follow-up that adds the hints and bug-report entries (#426), since the menu is growing anyway.

---

### `packages/webapp/src/app/globals.css` — the added `.modal` block

The description states twice that "no `.Mui*` CSS remains". True of the app, but not this PR's doing: the net diff for `globals.css` here is 65 insertions and **zero** deletions — `330fbb61` on the branch removed those 15 lines against a pre-#424 base, and #424 had already landed the same removal. Just an attribution nit in the changelog.

---

### `packages/webapp/src/components/BoardGame.tsx` — the migrated `GameOverDialog` return block (~lines 335-425)

Dropping the `<Dialog>`/`<DialogContent>` wrappers left the inner JSX at the old nesting depth, so the block reads two levels deeper than it sits. Lint passes so it's cosmetic, but a re-indent would make the migration diff easier to trust at a glance. (Also: the description points at `GameOverDialog.tsx`, which doesn't exist — the component lives here.)

---

### `packages/webapp/src/components/board/ExitDialog.tsx` — lines 32-49 (`handleLeaveSeat`)

Not a defect in this PR, just noting for the follow-up: after a leave terminates the match, the *remaining* players' localStorage credentials for the dead room are never cleared (confirmed still present after termination). Harmless today because the room is filtered out of the lobby as Abandoned, but it means dead keys accumulate per browser and any future change to the visibility filter would resurface them as ghost 回到桌子 rows.
