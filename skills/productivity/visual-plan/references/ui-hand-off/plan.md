# Mock plan: confirm before refilling job cards (換人力)
<!-- template: implementation-plan -->

Worked example only. Product, copy, and file names are illustrative, not requirements for other plans.

## Decision needed

**Proposal:** Add a confirm step to 換人力. Tapping 換人力 enters a selection mode; new job cards are dealt only after 確認人力. 取消 restores the current hand.

## Wireframes

**Desktop · current**
```text
┌ 1280px ──────────────────────────────────────────┐
│ 人力區                                [換人力]     │
│ ┌──────┐ ┌──────┐ ┌──────┐                        │
│ │ 工人A │ │ 工人B │ │ 工人C │                        │
│ └──────┘ └──────┘ └──────┘                        │
└──────────────────────────────────────────────────┘
```

**Desktop · target** (changed: header actions, selection marks — proposed)
```text
┌ 1280px ──────────────────────────────────────────┐
│ 人力區                      [取消] [確認人力]       │
│ ┌──────┐ ┌──────┐ ┌──────┐                        │
│ │ 工人A │ │ 工人B │ │ 工人C │   still-current faces  │
│ │  [×] │ │      │ │  [×] │                        │
│ └──────┘ └──────┘ └──────┘                        │
└──────────────────────────────────────────────────┘
```

**Mobile · current**
```text
┌ 375px ───────────┐
│ 人力區   [換人力] │
│ [工人A][工人B]    │
│ [工人C]           │
└──────────────────┘
```

**Mobile · target**
```text
┌ 375px ───────────┐
│ 人力區            │
│ [工人A×][工人B]   │
│ [工人C×]          │
│ [取消] [確認人力] │
└──────────────────┘
```

| Label | Component / file | Change |
| --- | --- | --- |
| `換人力` | `src/ui/HandHeader.tsx` | Enters selection mode instead of refilling |
| `[×]` | `src/ui/JobCard.tsx` | Marks card for replacement; does not flip or deal |
| `確認人力` (proposed) | `src/ui/HandHeader.tsx` | Only action that deals new cards |
| `取消` (proposed) | `src/ui/HandHeader.tsx` | Clears marks, restores hand |

Extra state frame, after tapping ×, before confirm (no new faces shown):
```text
│ │ 工人A │ → ghost: 待補 │   marked cards stay as current faces or ghosts, never new faces
```

Hidden information: until 確認人力, ×, swap, and 取消 show backs, ghosts, or still-current faces only. No new face appears in any frame or transition before confirm. Cards slide in only after 確認人力.

## Implementation

1. Add selection state to `HandHeader.tsx`.
2. Mark/unmark on `JobCard.tsx`.
3. Deal on confirm only; animate after confirm.

## Unchanged

Deck order, deal rules, and the hand size limit.

## Status

- [x] Plan
- [ ] Approval
- [ ] PR
