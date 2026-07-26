Shell unification verified in Chromium at `43fe0c32`: lobby and desktop game headers both measure `height: 72`, `oklch(0.985 0.012 75)`, game `position: sticky`; compact is 52px, icon-only, chip strip `scrollWidth 417` vs `clientWidth 171` with page overflow 0. Core claim holds.

Three evidence-table corrections:

- Lobby header changed too — measured 69px/transparent before, 72px/`var(--paper)` after. Risks section only flags the game header. Add the lobby's +3px and note the background is a no-op because `body.app-root` is already `var(--paper)` (`globals.css:92`).
- `borderBottom: 1.5px` is the inline value; Chromium computes `1px` at DPR 1.
- Test count is 59, not 58.

Follow-up, no line to anchor to: `Logo`'s `lg` size has never had a caller (`git log -S'size="lg"' -- packages/webapp/src` is empty), and after this PR `AppHeader` is `Logo`'s only consumer, so `export { default as Logo }` in `design/index.ts` is unused too. Deleting `lg`, `STAR_BOX.lg`, `STAR_RADIUS`, `big` and the barrel export removes 15 lines with tests/lint/`tsc` green.
