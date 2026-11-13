`packages/webapp/src/components/dev/DevToolsWidget.tsx:44`
18 inline `style` objects and a 24-line `isMobile ? {} : {}` ternary are static CSS.
Move to a `.dev-tools*` block in `globals.css`; 205 lines -> 102.

`packages/webapp/src/components/dev/DevToolsWidget.tsx:132`
The Perspective and Transport fieldsets are the same markup in two idioms (object
array vs inline `as const` tuples). Extract one local `RadioGroup<T>` and call it twice.

`packages/webapp/src/components/dev/DevToolsWidget.tsx:137`
`data-testid="dev-perspective-*"` has no consumer — e2e selects these radios by
accessible name. Delete the attribute.

`packages/webapp/src/components/design/Modal.tsx:35`
`style?: React.CSSProperties` has exactly one consumer, `DevToolsWidget`. A styling
escape hatch on a shared design component for a dev-only surface. Swap for `className`.

`packages/webapp/src/app/dev/page.tsx:9`
`getFirstValue` duplicates the private copy in `devConfig.ts:94`, already imported
from for `SearchParamValue`. Export that one, delete this.

`packages/webapp/src/components/playerNameMap.ts:4`
nit: `stubPlayerNameMap` is exported but only used on line 21 of this file. Drop `export`.

`packages/webapp/src/components/dev/DevGameHost.tsx:74`
`handlePerspectiveChange` is `(next) => setPerspective(next)`. Pass `setPerspective`
directly. (`handleTransportChange` earns its place — it no-op guards and resets `matchID`.)

`packages/webapp/src/components/dev/DevGameHost.tsx:89`
q: `hasLocalSetupOverrides` is a three-hop prop for one hint paragraph with no
coverage. Keep the copy and add a test, or drop the prop?

`packages/webapp/src/app/dev/page.tsx:34`
`role="alert"` on `<main>` overrides the `main` landmark. Put the role on an inner `<div>`.

`packages/webapp/package.json:20`
`e2e:production` hand-copies `.next/static` and `public`, duplicating `Dockerfile:58-60`.
Add a cross-reference comment on both sides so the two lists don't drift.

`packages/webapp/src/components/dev/DevGameHost.tsx:17`
nit: `createMatchID()` duplicates the `dev-${randomUUID()}` format in `dev/page.tsx:39`.
Export one helper.
