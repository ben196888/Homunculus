# PR #411 — `fix(webapp): unify lobby and game headers behind AppHeader shell (B-004)`

`ocftw/open-star-ter-village` · head `43fe0c32` · +232/−104 across 6 files

## First, the headline on "safe to merge"

**It is already merged.** `gh pr view 411` reports `state: MERGED`, merge commit
`a61dfcb1`, merged 2026-07-20. The merge was clean: `git diff 43fe0c32 a61dfcb1 -- packages/webapp/src`
is empty, so the code that landed is byte-identical to the head I reviewed. `AppHeader.tsx`,
`AppHeader.test.tsx`, `Logo.tsx` and `LobbyNav.tsx` are still byte-identical on today's
`main` (`795d3d4c`); only `GameHeader.tsx` has moved on (+88 lines, from #425).

So the question becomes retrospective, and the answer is: the gate was green and the
visual claims are true, but one behavior change slipped in undocumented and **later
commits on `main` have made it actively wrong** (V1 below). That one is worth a
follow-up PR today.

## Baseline I actually ran (worktree at `43fe0c32`, offline yarn zero-install)

| Gate | Result |
| --- | --- |
| `yarn workspace @open-star-ter-village/webapp test` | 3 suites, **59 passed** |
| `yarn workspace @open-star-ter-village/webapp lint` | `✔ No ESLint warnings or errors` |
| `tsc --noEmit -p packages/webapp/tsconfig.json` | exit 0 |
| Next dev on **:3411** + Playwright Chromium | measurements below |

Note: the head predates the pnpm migration — at `43fe0c32` the repo is `yarn@3.4.1`
with a committed `.yarn/cache`, so `YARN_ENABLE_NETWORK=0 yarn install --immutable`
reproduced the PR-era dependency tree exactly. Every claim below is from running that
tree, not from reading it, except where marked.

---

## Valid findings

### V1 — `risk` (live on `main`): the shared brand block is an unguarded exit from a live game

`AppHeader` unconditionally wraps the logo in `<Link href="/">`. Before this PR the game
header rendered `{!compact && <Logo size="sm" />}` — a bare, non-clickable logo on desktop
and **nothing at all** on mobile. After it, every game surface has a link out of the board,
and on mobile that link is the only brand element and sits at the left edge of the bar.

Proven in a real browser at head (375×812, board mounted via `/dev`):

```
compact logo link box: {"w":26,"h":26,"x":52,"y":170.375,"href":"/"}
urlBefore= http://localhost:3411/dev  urlAfter= http://localhost:3411/
board still mounted? false
```

A 26×26 tap target — below the 44×44 touch guideline — immediately adjacent to a
horizontally-scrolling chip strip, that unmounts the board. That was already sloppy at
merge time, when Leave was itself a plain `<Link href="/lobby">`. It is worse now: #425
turned Leave into `<button onClick={openExit}>` routing through `ExitDialog`, and the
`GameHeader` docblock on `main` now claims

> Leaving always goes through the explicit exit-choice dialog (#420).

`git grep 'beforeunload\|router.events\|onNavigate' origin/main -- packages/webapp/src`
returns **nothing**, and `AppHeader.tsx` is unchanged on `main`. So "always" is false:
the brand link bypasses the dialog entirely.

**Fix (follow-up PR, not a revert):** give `AppHeader` control over the brand target —
`brandHref?: string` plus `onBrandClick?: () => void`, or `brandInteractive = false` —
and have `GameHeader` either render a non-interactive brand or route the click through
`openExit`. Bump the compact hit area to ≥44×44 with padding while keeping the 26px tile.

**Verify:** add to `AppHeader.test.tsx` —
`expect(render(<GameHeader gameContext={gameContext} compact />).container.querySelector('a[href="/"]')).toBeNull();`
That test fails on `main` today, which is exactly the point.

### V2 — `risk`: the two "shell values are identical" tests cannot fail

Both equality tests read `getByTestId('app-header')` — a node rendered by `AppHeader`
itself — from each component and compare the two. Since neither caller can influence
those styles, the assertion is a tautology. Two experiments:

**A. Re-introduce the exact regression B-004 was about.** Wrapped `GameHeader`'s
`<AppHeader>` in `<div style={{minHeight:96, background:'red', borderBottom:'9px dotted lime', padding:'30px 4px'}}>`:

```
Tests:  59 passed, 59 total
```

A 96px red bar with a lime dotted divider on the game surface only, and the suite is green.

**B. Break the shell values themselves.** Set `minHeight: compact ? 52 : 999` and
`borderBottom: '9px dotted lime'` in `AppHeader`:

```
● shared application header shell › compact mobile variant keeps only the star tile…
Tests:  1 failed, 58 passed, 59 total
```

Only the *compact* test fires — because it is the one test that asserts literals. The
desktop shell's 72px / `var(--paper)` / `1.5px var(--paper-3)` are pinned by nothing.

**Fix:** assert the literals on the desktop shell the way the compact test already does,
and take the measured node from each component's **outermost rendered element**
(`container.firstElementChild`) rather than the shared `app-header` testid, so a
re-introduced wrapper is caught.

**Verify:** apply experiment A after the fix and confirm the equality test fails.

### V3 — deletable: `Logo`'s `lg` size is dead, and so is its barrel export

`size="lg"` has no caller anywhere in `packages/webapp/src` or `e2e`, and
`git log -S'size="lg"' -- packages/webapp/src` returns **no commits** — it was never used.
After this PR `AppHeader` is `Logo`'s only consumer, which also strands
`export { default as Logo }` in `design/index.ts`. Still true on `main`.

Deleted `lg` from the union, `STAR_BOX.lg`, the whole `STAR_RADIUS` map (see V4), the
`big` flag and its three ternaries, and the barrel export — **−15 net lines**:

```
Tests:  59 passed, 59 total
tsc_exit=0
✔ No ESLint warnings or errors
```

### V4 — deletable: `STAR_RADIUS` is a three-entry map for one 2px difference

`md: 12` and `lg: 12` are identical; only `sm: 10` differs. Replaced the map with
`borderRadius: size === 'sm' ? 10 : 12` in the V3 experiment above — green.

Separately, the comment above it (*"so small sizes stay a rounded square, not a circle"*)
overstates: `sm` is a 26px tile, so a 12px radius was never a circle (that needs 13).

### V5 — deletable: 6 of the sticky test's 10 lines duplicate the test above it

`it('game header keeps sticky positioning without changing resting visuals')` re-renders
`LobbyNav`, re-captures its style and re-runs `expect(game.style).toEqual(lobbyStyle)` —
byte-for-byte the assertion from the previous test. Collapsed to the `position` assertion
alone: `Tests: 59 passed, 59 total`.

### V6 — `nit`: `right?` is optional but always supplied

Both call sites pass `right`. Changed to `right: React.ReactNode` — `tsc_exit=0`.

### V7 — evidence accuracy (three small things)

Measured the lobby bar in Chromium at 1280px, at head and with `LobbyNav.tsx` swapped
back to its pre-PR version (`git show cea7b902:…`):

| | height | background | padding |
| --- | --- | --- | --- |
| pre-PR | **69px** | `rgba(0,0,0,0)` | `18px 36px` |
| head | **72px** | `oklch(0.985 0.012 75)` | `0px 36px` |

- The body says *"Lobby values are the source of truth"* and flags only the game header
  as ~4px taller. The **lobby grew 3px too** (69 → 72). Worth one line in the risks section.
- The background change is a visual no-op — `body.app-root` is already `background: var(--paper)`
  (`globals.css:92`) — but the header is now opaque rather than inheriting, which is
  what makes the sticky game variant safe. Say so; it reads as accidental otherwise.
- The evidence table quotes `borderBottom: 1.5px …`. That is the inline style; Chromium
  computes it to `1px solid oklch(0.93 0.022 75)` at DPR 1. And the test count is 59, not
  the 58/58 in the table.

---

## Claims I killed (these stay out of the PR comments)

| Claim I formed from reading | What killed it |
| --- | --- |
| "The compact chip strip overflows the page horizontally" | At 375×812: `documentElement.scrollWidth − clientWidth = 0`; strip `scrollWidth 417` vs `clientWidth 171` — contained scroll, page clean. The PR body's claim is correct. |
| "Two `AppHeader`s can co-render (duplicate landmark, ambiguous testid)" — `app/game/[matchID]/page.tsx` renders `LobbyNav` in four branches and `BoardGame` in another | The board branch and the `LobbyNav` branches are mutually exclusive early returns. Browser reported `count: 1` at 1280px and 375px. |
| "`justifyContent: 'flex-end'` is redundant given `flex: 1` on the chip strip" | On desktop the chip strip has no `flex`, so `flex-end` is the only thing right-aligning chips + Leave. Load-bearing. |
| "The evidence table's oklch values are invented" | `--paper: oklch(0.985 0.012 75)`, `--paper-3: oklch(0.93 0.022 75)` in `globals.css:17,19`; the browser reported the same computed background. |
| "The core 'both headers share one shell' claim is unverified" | Measured: lobby 72px and desktop game 72px, both `oklch(0.985 0.012 75)`, game `position: sticky`, compact 52px with `wordmark: false`. Every headline claim in the PR body is true. |
| "Dropping the `Logo` barrel export breaks a consumer" | No consumer; `tsc`, lint and tests all green without it. |
| "The `sticky` prop is speculative flexibility" | Lobby is non-sticky, game is sticky. Two real callers, two values. Keep. |

---

## Verdict

**Nothing blocking, and nothing to revert.** The refactor does what it says, the gate is
green, and the visual parity claim survived a real browser. Two follow-ups worth opening:

1. **V1** — the brand link out of a live game, now bypassing the exit dialog `main`'s own
   comment promises is unavoidable. Small, real, user-visible.
2. **V2** — re-point the shell tests at the outer node and assert desktop literals, so
   B-004 cannot silently come back.

Deletion total available right now, all verified green: **~21 lines** (V3 −15, V5 −6),
plus the V6 one-character type tightening.
