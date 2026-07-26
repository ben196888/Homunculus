---
name: "homunculus-programming-code-review"
description: "Review code changes for security, performance, and correctness. Trigger with a PR URL or diff, \"review this before I merge\", \"is this code safe?\", or when checking a change for N+1 queries, injection risks, missing edge cases, or error handling gaps. This is the correctness lens used by [[homunculus-programming-peer-review]]; on its own it reports findings without proving them."
argument-hint: "<PR URL, diff, or file path>"
---

# /code-review

Review code changes with a structured lens on security, performance, correctness, and maintainability.

A finding produced by this lens is a hypothesis, not a fact. When the code is
available to run, `homunculus-programming-peer-review` wraps this lens in an
experiment loop that tests each finding before it reaches the author.

## Usage

```
/code-review <PR URL or file path>
```

Review the provided code changes: @$1

If no specific file or URL is provided, ask what to review.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                      CODE REVIEW                                   │
├─────────────────────────────────────────────────────────────────┤
│  STANDALONE (always works)                                       │
│  ✓ Paste a diff, PR URL, or point to files                      │
│  ✓ Security audit (OWASP top 10, injection, auth)               │
│  ✓ Performance review (N+1, memory leaks, complexity)           │
│  ✓ Correctness (edge cases, error handling, race conditions)    │
│  ✓ Style (naming, structure, readability)                        │
│  ✓ Actionable suggestions with code examples                    │
├─────────────────────────────────────────────────────────────────┤
│  WITH gh CLI                                                     │
│  + Pull the PR diff and CI state directly                        │
│  + Check the PR body's claims against the code                   │
└─────────────────────────────────────────────────────────────────┘
```

## Review Dimensions

### Security
- SQL injection, XSS, CSRF
- Authentication and authorization flaws
- Secrets or credentials in code
- Insecure deserialization
- Path traversal
- SSRF

### Performance
- N+1 queries
- Unnecessary memory allocations
- Algorithmic complexity (O(n²) in hot paths)
- Missing database indexes
- Unbounded queries or loops
- Resource leaks

### Correctness
- Edge cases (empty input, null, overflow)
- Race conditions and concurrency issues
- Error handling and propagation
- Off-by-one errors
- Type safety

### Maintainability
- Naming clarity
- Single responsibility
- Duplication
- Test coverage
- Documentation for non-obvious logic

## Output

```markdown
## Code Review: [PR title or file]

### Summary
[1-2 sentence overview of the changes and overall quality]

### Critical Issues
| # | File | Line | Issue | Severity |
|---|------|------|-------|----------|
| 1 | [file] | [line] | [description] | 🔴 Critical |

### Suggestions
| # | File | Line | Suggestion | Category |
|---|------|------|------------|----------|
| 1 | [file] | [line] | [description] | Performance |

### What Looks Good
- [Positive observations]

### Verdict
[Approve / Request Changes / Needs Discussion]
```

## Pulling the change

With the `gh` CLI available, fetch the diff and its CI state rather than asking the
user to paste anything:

```bash
gh pr view <N> --json title,body,headRefOid,state,mergeStateStatus,statusCheckRollup
gh pr diff <N> --patch
```

Read the whole patch before forming opinions, and check the PR body's claims against
the code — a description that says a route returns 404 or a match is created on demand
is a claim to verify, not context to accept.

## Tips

1. **Provide context** — "This is a hot path" or "This handles PII" helps me focus.
2. **Specify concerns** — "Focus on security" narrows the review.
3. **Include tests** — I'll check test coverage and quality too.
