# GitHub Actions v4 SHA Pin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `upload-pages-artifact` to v4 while restoring immutable SHA references for every executable GitHub Action.

**Architecture:** Keep the workflow structure and contract tests unchanged. Replace only four user-edited mutable action tags with verified v4 commit SHAs, preserving the existing Pandoc action pin.

**Tech Stack:** GitHub Actions YAML, Python `unittest`, GitHub API

---

### Task 1: Pin v4 Actions

**Files:**
- Modify: `.github/workflows/ai-newsletter.yml:38,53,72,76`
- Test: `tests/test_workflow.py`

- [ ] **Step 1: Verify the existing contract test fails**

Run:

```bash
python3 -m unittest tests.test_workflow -v
```

Expected: failures report mutable `actions/checkout@v4` and the unrecognized mutable upload action reference.

- [ ] **Step 2: Replace mutable tags with verified SHAs**

Use exactly these references:

```yaml
- uses: actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4
- uses: actions/upload-pages-artifact@7b1f4a764d45c48632c6b24a0339c27f5614fb0b # v4
- uses: actions/configure-pages@1f0c5cde4bc74cd7e1254d0cb4de8d49e9068c7d # v4
- uses: actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e # v4
```

Do not change `r-lib/actions/setup-pandoc` or workflow behavior.

- [ ] **Step 3: Verify upstream tag targets**

Run:

```bash
test "$(gh api repos/actions/checkout/git/ref/tags/v4 --jq '.object.sha')" = "11d5960a326750d5838078e36cf38b85af677262"
test "$(gh api repos/actions/upload-pages-artifact/git/ref/tags/v4 --jq '.object.sha')" = "7b1f4a764d45c48632c6b24a0339c27f5614fb0b"
test "$(gh api repos/actions/configure-pages/git/ref/tags/v4 --jq '.object.sha')" = "1f0c5cde4bc74cd7e1254d0cb4de8d49e9068c7d"
test "$(gh api repos/actions/deploy-pages/git/ref/tags/v4 --jq '.object.sha')" = "d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e"
```

Expected: all four commands exit 0.

- [ ] **Step 4: Run focused and full tests**

Run:

```bash
python3 -m unittest tests.test_workflow -v
python3 -m unittest discover -s tests -v
```

Expected: 7 workflow tests and the complete suite pass.

- [ ] **Step 5: Inspect and commit only intended changes**

Run:

```bash
git diff --check
git diff -- .github/workflows/ai-newsletter.yml
git status --short
```

Expected: the workflow diff contains exactly four action-reference replacements; the plan file may also be untracked.

Commit:

```bash
git add .github/workflows/ai-newsletter.yml docs/superpowers/plans/2026-08-18-actions-v4-sha-pin.md
git commit -m "ci: pin Pages artifact action v4"
```
