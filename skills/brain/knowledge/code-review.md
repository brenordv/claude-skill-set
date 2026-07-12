# Code Review Best Practices

These guidelines apply to code review processes regardless of language or project.

---

## 1. Review Mindset

- **Be constructive**: Frame feedback as opportunities to improve, not criticisms.
- **Be specific**: Reference exact files, lines, and provide examples.
- **Prioritize**: Distinguish critical issues from nice-to-haves.
- **Educate**: Explain *why* something is an issue, not just *what*.
- **Acknowledge good work**: Call out well-written code.
- **Stay objective**: Focus on code quality, not personal preferences.
- **Remember Lessons learned**: Look into the `brain/gotchas` folder for any relevant problemas we already faced and learned how to fix.

---

## 2. Review Dimensions

> For concrete, checkable patterns under each dimension below, work through `review-heuristics.md`; it
> turns these categories into specific things to flag.

### Correctness

- Does the code do what it's supposed to?
- Are edge cases handled?
- Is error handling appropriate?
- Are business logic invariants maintained?

### Security

- Input validation at boundaries?
- No injection vulnerabilities?
- Secrets not exposed?
- Authentication/authorization enforced?
- No machine-identifying details (absolute local paths, usernames, hostnames)? See `machine-privacy.md`;
  on touched lines this blocks approval.

### Performance

- Appropriate algorithmic complexity?
- No unnecessary allocations or I/O in hot paths?
- Resources properly managed (connections, files, memory)?

### Maintainability

- Is the code easy to understand and modify?
- Does it follow project conventions?
- Are dependencies justified and minimal?
- Is there unnecessary complexity?
- Does comment/doc prose pass `writing-style.md`? (Concrete greps: `review-heuristics.md` §Prose.)

### Testing

- Are new code paths covered by tests?
- Do tests follow Arrange-Act-Assert?
- Are error conditions tested?
- Are tests deterministic and independent?

---

## 3. Review Outcomes

| Outcome | Criteria |
|---------|----------|
| **Approved** | All critical checks pass, code is production-ready |
| **Changes Requested** | Specific, actionable issues that must be addressed |
| **Rejected** | Fundamental design problems requiring rethink |

---

## 4. Feedback Structure

```
## Critical (Must Fix)
1. [Issue with file:line reference and fix suggestion]

## Important (Should Fix)
1. [Issue with reasoning]

## Suggestions (Nice to Have)
1. [Improvement idea]
```

---

## 5. Anti-Patterns in Reviews

- Nitpicking style when a formatter should handle it.
- Blocking on personal preferences vs. actual issues.
- Rubber-stamping without actually reading the code.
- Reviewing too much at once (>400 lines loses effectiveness).
- Not checking that tests actually test meaningful behavior.
