---
name: homunculus-create-printable-html
description: Create or adapt self-contained printable HTML documents from supplied content, documents, pages, or drafting requests. Use for print-first letters, forms, reports, CVs, and reference sheets, including multilingual documents; not general website development or format conversion.
---

# Create printable HTML

Deliver a complete, offline-capable UTF-8 `.html` file. Prioritize content accuracy, Unicode rendering, readable printing, then screen appearance. Do not generate or convert to PDF, including temporary verification artifacts.

## Understand and preserve the content

- Infer purpose, hierarchy, and language from the request and source. Default to A4 portrait, natural page length, professional/minimal styling, 10–11 pt body text, and approximately 10–15 mm margins. Ask only when missing information materially affects the document.
- Preserve supplied wording and factual details exactly, including names, dates, identifiers, addresses, and diacritics. Do not translate, transliterate, normalize identifiers, or compress prose unless requested. Escape source text correctly when inserting it into HTML; do not import scripts or active markup from source pages.
- For drafting requests, generate the requested prose but never invent missing factual details. Ask for required facts or use clearly identified placeholders when suitable for a draft. Remove starter examples from the deliverable.
- Preserve meaningful reading order and relationships. Choose a letter, report, form, or other appropriate structure instead of blindly stacking paragraphs. Use semantic tables for tabular data and grids for parallel party/contact information. Include signature space only when appropriate; never fabricate a signature.

## Build the document

Start from [assets/printable.html](assets/printable.html) and adapt it; the sample layout is not mandatory. Keep CSS inline, embed necessary available images as data URLs, and include no remote dependencies or local asset paths. Do not fetch external fonts by default.

- Keep the doctype, UTF-8 declaration, viewport, and an appropriate root `lang`. Use an empty or unobtrusive title. Do not add incidental source URLs, file paths, timestamps, or print metadata to the document; preserve these when they are actual supplied content.
- Configure both the literal `@page` size/margins and the screen preview variables together. Examples: A4 portrait 210 × 297 mm, A4 landscape 297 × 210 mm, Letter 8.5 × 11 in, Legal 8.5 × 14 in, or requested custom dimensions. Do not rely on CSS variables inside `@page` descriptors.
- Let `@page` supply printed margins. Reset screen paper width, minimum height, padding, shadow, and margins for print so they do not create double margins or extra pages. Never use fixed heights or hidden overflow to force page fit.
- Use restrained hierarchy, approximately 16–20 pt headings and 1.35–1.6 body line height. Prefer physical units. Color must not be the sole carrier of meaning; request exact print colors only when useful.
- Keep short cards, addresses, signature blocks, and headings with their following content together where practical. Allow long sections and tables to span pages; do not apply `break-inside: avoid` to entire long tables. Repeat table headers, avoid splitting short rows, and allow oversized rows/blocks to break when necessary.
- Make signature lines with borders and reserve physical writing space. Constrain images to the available width without distorting them.

## Languages and typography

Infer language without changing content. Use `en`, `vi`, or `zh-Hant` for the three primary cases. Use a regional tag such as `zh-Hant-TW` only when the region is established. Tag passages in other languages with their own `lang`; choose the main document language for the root.

- **English:** use a readable local Latin font stack, normal word wrapping, and restrained typography.
- **Traditional Chinese:** prefer `PingFang TC`, `Noto Sans TC`, `Microsoft JhengHei`, `Heiti TC`, then sans-serif. Keep normal CJK line breaking, avoid arbitrary tracking or `word-break: break-all`, and account for character density when choosing spacing and type size.
- **Vietnamese:** prefer locally available fonts with Vietnamese coverage, such as Arial, Noto Sans, or DejaVu Sans. Preserve tone marks and combining characters exactly; allow enough line height to avoid accent clipping. Do not turn text into unaccented ASCII.
- **Other scripts:** keep Unicode intact and select suitable local fallbacks. Do not promise every script renders on every machine. Set `dir="rtl"` for predominantly right-to-left content, use logical alignment/spacing, and isolate mixed-direction identifiers with `bdi` or explicit direction when needed. Do not reverse strings manually. Avoid forced word breaking that damages script shaping; use targeted overflow wrapping for long URLs/identifiers.
- Mixed-language inline passages need language tags too; check that their font fallback and line height work together. Preserve the reading order when adapting columns.

## Page fit

For an explicit page target, first reduce unnecessary whitespace, choose compact semantic layouts, then adjust paragraph spacing, line height, and margins moderately. Reduce body type only slightly as a last resort; ordinarily stay at or above 9.5 pt. Do not sacrifice script legibility or signature writing space.

Never shorten supplied text silently. If a strict page limit cannot be met readably, explain the conflict and ask whether to edit wording or relax the limit. Without a strict limit, allow a clean additional page. A screen sheet's minimum height is not evidence of printed pagination.

## Verify and deliver

1. Save with explicit UTF-8 encoding and read it back strictly as UTF-8. Compare supplied text and factual fields against the source, decoding HTML entities when comparing text. Check that images and styles work offline and no starter content remains.
2. When a browser is available, inspect the screen rendering and print-media layout for missing glyphs, clipped accents, horizontal overflow, misplaced signatures, and awkward table/heading breaks. Use an actual print preview if available without generating another format. Print-media emulation alone does not verify page count.
3. If a browser or print preview is unavailable, perform static checks and report the limitation. Never claim verified printed pagination from CSS inspection or screen screenshots alone. Do not install a rendering dependency just to complete this workflow unless requested.
4. Deliver a clickable link to the saved HTML. Briefly state the intended paper size and orientation and advise disabling browser **Headers and footers** when needed. Browser-generated title/URL/date metadata cannot be reliably suppressed by document CSS; do not use layout-damaging hacks. Mention any unverified pagination or font-coverage limitation relevant to the result.
