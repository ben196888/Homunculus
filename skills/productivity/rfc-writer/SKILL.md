---
name: "homunculus-productivity-rfc-writer"
description: "Use when a requested change is cross-cutting, architectural, or needs alignment before implementation."
---

# RFC Writer

Write an RFC before implementation when a change affects multiple systems, introduces breaking contracts, or requires architectural alignment.

## Output

Follow the user's requested destination and format. If none is specified, show the complete RFC in the response; do not create a file or publish it elsewhere by default. When multiple outputs are explicitly requested, deliver each one.

| Requested output | Delivery |
|------------------|----------|
| Repository issue | Create an issue in the requested repository using `gh` for GitHub or `glab` for GitLab. Use the RFC title as the issue title and its Markdown content as the body. Infer the repository from context or the Git remote when unambiguous. |
| Cloud document | Create or update the requested file in Google Drive, OneDrive, or another specified external system using its available connector or tools. Follow relevant document skills when available. Read an existing document before editing and preserve unrelated content. |
| HTML file | Write a standalone, readable `.html` file with semantic headings, styled tables, and the full RFC content. Use the supplied path; otherwise choose a descriptive filename in the workspace and report it. Creating HTML does not imply hosting or publishing it. |
| Response (default) | Show the complete RFC as Markdown directly in the response. |
| Local filesystem path | Create or update the file at the user's supplied path. Honor the requested format or infer it from the extension; use Markdown when neither specifies a format. Read an existing file before editing and preserve unrelated content. |

Use a short, lowercase, hyphenated slug when choosing a filename. Do not automatically write to `docs/rfc/` unless the user requests that location.

Ask only for destination details that cannot be inferred, such as an ambiguous repository or cloud document. An explicit request to create an issue or create/update a cloud file authorizes that delivery; do not require a second confirmation unless an applicable rule requires it. Do not publish externally when the user only asks for a draft or preview.

For CLI issue creation, pass the body through a temporary UTF-8 file (`gh --body-file` or the supported `glab` file-input mechanism) to preserve Markdown and avoid shell interpolation. If a tool, authentication, or destination is unavailable, provide the complete RFC in the response and explain what prevented the requested delivery. Do not claim it was saved or published.

After writing or publishing, verify the result and return its link or absolute local path with a brief summary.

## Status

Every RFC must include:

```text
Status: Draft | In Review | Approved | Implemented
```

## Template

```markdown
# RFC: <Title>

Status: Draft

## Problem

What is the problem and why does it matter?

## Goals

- Goal

## Non-goals

- Out of scope

## Proposal

Describe the chosen approach, including architecture, data flow, interfaces, and rollout.

## Alternatives Considered

| Option | Pros | Cons | Why rejected |
|--------|------|------|--------------|
| ...    | ...  | ...  | ...          |

## Impact

- Systems affected
- Breaking changes
- Rollout plan
- Risks and rollback strategy

## Open Questions

- [ ] Outstanding question

## Timeline / Milestones

| Milestone | Target |
|-----------|--------|
| RFC approved | -- |
| Implementation start | -- |
| Feature complete | -- |
```
