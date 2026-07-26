### `packages/webapp/src/components/design/AppHeader.tsx:34`

```
      <Link href="/" aria-label="回首頁 Home" style={{ flexShrink: 0 }}>
```

risk: unguarded exit from a live game — pre-PR the game header logo was not a link, and compact rendered no logo at all. Measured at 375px: 26×26 tap target next to the scrolling chip strip, click navigates `/dev` → `/` and unmounts the board. Add `brandHref`/`brandInteractive` props so `GameHeader` can route the brand click through its exit path instead of `href="/"`, and pad the compact hit area to ≥44×44.

### `packages/webapp/src/components/design/AppHeader.tsx:36`

```
        <Logo size={compact ? 'sm' : 'md'} iconOnly={compact} />
```

Only consumer of `Logo`, and it never asks for `lg` — `STAR_BOX.lg`, `STAR_RADIUS`, and the `big` branches in `Logo.tsx` are dead. Drop them (−15 lines, gate stays green).

### `packages/webapp/src/components/design/AppHeader.tsx:16`

```
  right?: React.ReactNode;
```

nit: both callers always pass `right`. Make it required — `tsc --noEmit` passes.

### `packages/webapp/src/components/design/Logo.tsx:13`

```
// Radius scales with the tile so small sizes stay a rounded square, not a circle.
const STAR_RADIUS: Record<NonNullable<LogoProps['size']>, number> = {
```

Three-entry map for one 2px difference (`md` and `lg` are both 12). Replace with `borderRadius: size === 'sm' ? 10 : 12`. Also `sm` is a 26px tile, so 12px was never a circle — the comment overstates.

### `packages/webapp/src/components/design/AppHeader.test.tsx:39`

```
    const lobby = shellOf(<LobbyNav />);
```

risk: this equality cannot fail. `shellOf` reads `[data-testid="app-header"]` — a node `AppHeader` renders — from both components, so neither caller can make it diverge. Wrapping `GameHeader`'s `<AppHeader>` in a 96px red div with a 9px lime divider keeps all 59 tests green, i.e. the B-004 regression is unguarded. Measure `container.firstElementChild` of each component instead, and assert desktop literals (`minHeight: '72px'`, `background: 'var(--paper)'`, `borderBottom: '1.5px solid var(--paper-3)'`) the way the compact test already does.

### `packages/webapp/src/components/design/AppHeader.test.tsx:50`

```
  it('game header keeps sticky positioning without changing resting visuals', () => {
```

6 of these 10 lines re-run the previous test's `expect(game.style).toEqual(lobbyStyle)`. Keep only `expect(game.el.style.position).toBe('sticky')` — 59 tests still pass.
