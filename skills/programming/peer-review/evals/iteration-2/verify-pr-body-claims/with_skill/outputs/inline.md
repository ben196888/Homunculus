### `packages/webapp/src/app/game/[matchID]/page.tsx` — L143-145

risk: `isTerminated` never checks `gameover`, so a normally-finished game whose seat is later vacated shows `有玩家離席，遊戲已終止` / `這局不會計算勝負` instead of the result — the round did count. Gate on `gameover` in both predicates, not just this one:

```ts
const isFinished = match ? match.gameover !== undefined : false;
const isTerminated =
  Boolean(match) && hasStarted && !isFinished && match!.players.some((p) => !hasPlayerName(p));
const shouldShowBoard =
  Boolean(match) && hasStarted && (allSeatsFilled || isFinished) && !isExpired;
```

Branch matrix for `finished + seat vacated`: today `terminated-overlay`; with only the `isTerminated` change `waiting-room`; with both changes `board`. Needs a test — nothing covers it.

---

### `packages/webapp/src/components/board/GameHeader.tsx` — L31-34

nit: `openExit` unmounts `menu-leave` in the same handler that opens the dialog, so `Modal`'s `document.contains(invoker)` guard skips focus restore and focus lands on `<body>`. Verified: desktop returns to `header-leave`, mobile returns `BODY`. Keep the menu mounted until the dialog closes, or pass `header-menu` as the restore target.

---

### `packages/webapp/src/components/board/GameHeader.tsx` — L86-90

nit: `role="menu"` with no Escape handler and an `aria-hidden` click-only dismiss surface — keyboard users can open the menu but not close it. Add `onKeyDown` on the wrapper closing on `Escape`.
