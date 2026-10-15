Went through the description claim by claim against the merged tree (`6cfedcb4`) in a throwaway clone — full `pnpm install`, `next lint`, `tsc` on both configs, `jest --runInBand`, Playwright on 3425/3426, plus a few extra probe specs aimed at the specific promises. Almost everything checks out: the three-choice dialog really does block navigation until you choose, Escape/backdrop/focus-restoration all behave in a real browser (the jest tests only fire a synthetic `cancel`, so I verified that separately), the terminated overlay is genuinely non-dismissible with an inert background and survives a reload, and planting a bogus credential blob does get you 回到桌子 in the lobby followed by a clean demotion to observer mode. `next lint` clean, both `tsc --noEmit` clean, jest 140/140, multiplayer spec 16/16.

One functional gap that the PR's own e2e can't see, though.

**回大廳 loses the room entirely once every seated player has stepped out.** 回大廳 keeps the seat name but drops the socket. `isAbandonedMatch` (`packages/webapp/src/app/lobby/actions.ts:64-67`) marks a match abandoned when *every* player is `!name || isConnected === false`, and `toVisibleMatch` filters `Abandoned` rooms out of the lobby completely. So the moment the last connected player uses 回大廳, the room vanishes from the lobby of the very players whose seats are still reserved in it.

Reproduced with three players who joined, started, then all chose 回大廳. Server metadata right after:

```json
{"players":[{"id":0,"name":"P0","data":{"started":true},"isConnected":false},
            {"id":1,"name":"P1","isConnected":false},
            {"id":2,"name":"P2","isConnected":false}]}
```

Lobby row count for that room: 0. 回到桌子 button count: 0. Only a bookmarked `/game/<id>` recovers it.

The e2e passes because Bob and Charlie stay connected while Alice steps out. The realistic failure is the whole group taking a break at once, or Alice using 回大廳 while the other two just close their tabs.

`isAbandonedMatch` came in with #424 so this isn't a regression from this PR — but this is the PR that promises re-entry, so it feels like it owns the gap. Two directions that would fix it: don't let connection state alone abandon a match whose seats are still named and whose host has `data.started === true`, or give the lobby a "rooms you have a seat in" section that bypasses the visibility filter (the lobby already knows this from `mySeatMatchIDs`).

Separately, the Evidence block is pinned to `0e82a9d3`, but `ec4282db` landed after it and rewrote `Modal.tsx`'s Escape wiring (manual `cancel` listener + `onCloseRef` → React's `onCancel` prop), changed `jest.setup.ts`, and reworked ExitDialog's labelling. The merged tree is 140 jest tests / 7 ExitDialog tests, not the 139 / 6 stated. The late change is fine — React 18 attaches `cancel` non-delegated so `onCancel` does fire, and I confirmed Escape works — but per CONTRIBUTING the numbers should have been re-run against the final head.
