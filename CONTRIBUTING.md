# Git workflow

Move each issue through this sequence:

**Backlog → Ready → Create Branch → Implementation → Tests → PR → Review → CI → Merge → Done**

Use this branch naming format:

```text
<type>/<issue-id>-<short-desc>
```

Examples:

```text
feat/FE-US-07-shopping-session-form
fix/BUG-042-unknown-price-zero
test/QA-018-budget-fit-e2e
```

Open a pull request for changes to `main`, link the related issue with `Closes #123`, and use Squash and Merge after review and required CI checks pass.
