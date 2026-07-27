Reviewed at `ec4282db`. Gate is green locally (jest 140/140, lint, both tsc configs, Playwright 16/16 on `multiplayer.spec.ts` in isolation) and CI is 30/30, so this is follow-up only — nothing blocking.

Two behaviors the description promises that don't hold in cases it doesn't cover. Both are edge cases, both reproduce.

**1. `回到桌子` disappears once every seated player has stepped out.** `回大廳` drops the socket, so boardgame.io persists `isConnected: false` for that player. When all seats are disconnected, `isAbandonedMatch` → `'Abandoned'` → `toVisibleMatch` returns `null` and the room leaves `listPublicMatches`. `mySeatMatchIDs` is built from that already-filtered list, so the row can't come back. Reproduced with 3 Chromium contexts: after one player leaves, `match-return` is there; after all three leave, `match-row-<id>` count is 0 in every lobby — while `/game/<id>` still resumes the seat with no observer banner. Fix: derive owned rows from the raw match list (`loadCredentials(m.matchID) !== null`) instead of the filtered one.

**2. A finished game reads as "terminated, no scores" if anyone leaves their seat afterwards** — see the inline comment on `isTerminated`.

Worth filing 2 first; it shows players a factually wrong message about a game they actually completed.

Two small a11y nits on the `⋯` menu are inline.
