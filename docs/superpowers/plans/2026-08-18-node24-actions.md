# Node 24 Actions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove GitHub Actions Node.js 20 deprecation warnings while preserving the Pages build and deployment behavior.

**Architecture:** Update only the SHA-pinned action references in the workflow. Keep the workflow contract test as the executable record of required major versions, then run the complete Python test suite.

**Tech Stack:** GitHub Actions YAML, Python stdlib unittest

---

### Task 1: Update the workflow contract

**Files:**
- Modify: `tests/test_workflow.py:8-14`

- [ ] **Step 1: Change the expected action versions**

```python
ACTION_VERSIONS = {
    "actions/checkout": "v5",
    "r-lib/actions/setup-pandoc": "v2",
    "actions/configure-pages": "v6",
    "actions/upload-pages-artifact": "v5",
    "actions/deploy-pages": "v5",
}
```

- [ ] **Step 2: Run the contract test to verify it fails**

Run: `python3 -m unittest tests.test_workflow.WorkflowContractTest -v`

Expected: FAIL because the current workflow still declares v4 actions.

### Task 2: Upgrade the workflow actions

**Files:**
- Modify: `.github/workflows/ai-newsletter.yml:38,53,72,76`

- [ ] **Step 1: Replace the action references with the approved immutable SHAs**

```yaml
uses: actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09 # v5
uses: actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9 # v5
uses: actions/configure-pages@45bfe0192ca1faeb007ade9deae92b16b8254a0d # v6
uses: actions/deploy-pages@cd2ce8fcbc39b97be8ca5fce6e763baed58fa128 # v5
```

- [ ] **Step 2: Run the full suite**

Run: `python3 -m unittest discover -s tests -v`

Expected: PASS with no failures.
