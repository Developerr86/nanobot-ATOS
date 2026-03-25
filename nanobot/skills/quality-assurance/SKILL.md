---
name: quality-assurance
description: Standardized playbook for evaluating code quality, running test suites, and producing APPROVE or REJECT verdicts.
---

# Quality Assurance Skill

## Objective
Evaluate every new build delivered by the `@coder` agent with zero tolerance for regressions, security flaws, or deviations from the `@architect` specification. Your output is always one of two verdicts: **APPROVE** or **REJECT**.

---

## Step 1: Orientation
Before executing any tests, obtain:
1. The file paths of the generated code from the `@coder` completion signal.
2. The original architectural specification from `@architect` (read from the agreed-upon spec file).

Use `list_dir` to confirm the target directory structure matches the spec.

---

## Step 2: Static Analysis & Linting
Run the appropriate linter for the project type via the `exec` tool:

```bash
# JavaScript / TypeScript
npm run lint
npx eslint . --ext .js,.ts,.tsx

# Python
flake8 .
ruff check .
```

Flag any error-level lint violations as automatic grounds for **REJECT**.

---

## Step 3: Unit & Integration Tests
Run the full test suite via the `exec` tool:

```bash
# JavaScript / TypeScript
npm run test
npm run test -- --coverage

# Python
pytest --tb=short
pytest --cov=. --cov-report=term-missing
```

Capture the full terminal output. A single failing test is grounds for **REJECT**.

---

## Step 4: AI Code Review (Manual Inspection)
Use `read_file` to inspect the highest-risk components:
- Entry points and route handlers.
- Any function that touches the database or external APIs.
- Authentication / authorization logic.
- Any file flagged by the linter with warnings (not just errors).

Evaluate each file against these criteria:
| Criterion | Question |
|---|---|
| **Spec Adherence** | Does this match the `@architect` specification exactly? |
| **Security** | Are there injection risks, hardcoded secrets, or unvalidated inputs? |
| **Maintainability** | Are functions under 50 lines? Are there meaningful comments? |
| **Error Handling** | Are all async calls wrapped in try/catch or equivalent? |

---

## Step 5: Verdict

### ✅ APPROVE Payload
If all tests pass, lint is clean, and the code review finds no critical issues:
```
VERDICT: APPROVE
Build: [build ID or file path]
Tests: PASS ([X] passed, [0] failed)
Lint: CLEAN
Review: No critical issues found.
Handoff: Ready for deployment.
```

### ❌ REJECT Payload
If any test fails, lint has errors, or the code review finds a critical issue:
```
VERDICT: REJECT
Build: [build ID or file path]
Reason: [Concise root cause — e.g., "3 failing unit tests in auth.py"]
Details:
  - [File]: [Line X] — [Description of bug/flaw]
  - [File]: [Line Y] — [Description of bug/flaw]
Action Required: Return to @coder with the above bug report. Do not deploy.
```

Always send the REJECT payload directly to the `@coder` agent for remediation.
