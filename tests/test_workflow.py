import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/ai-newsletter.yml"
ACTION_VERSIONS = {
    "actions/checkout": "v4",
    "r-lib/actions/setup-pandoc": "v2",
    "actions/configure-pages": "v4",
    "actions/upload-pages-artifact": "v4",
    "actions/deploy-pages": "v4",
}


def indented_block(text, header, indent=0):
    lines = text.splitlines()
    marker = f"{' ' * indent}{header}:"
    start = next(
        (index for index, line in enumerate(lines) if line.rstrip() == marker), None
    )
    if start is None:
        return ""

    block = []
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        block.append(line)
    return "\n".join(block)


class WorkflowContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.events = indented_block(cls.workflow, "on")
        cls.jobs = indented_block(cls.workflow, "jobs")
        cls.build = indented_block(cls.jobs, "build", 2)
        cls.deploy = indented_block(cls.jobs, "deploy", 2)

    def assert_path_filters(self, event):
        event_block = indented_block(self.events, event, 2)
        paths = indented_block(event_block, "paths", 4)
        expected = {
            "output/**",
            "data/news-ledger.json",
            "docs/**",
            "scripts/**",
            "tests/**",
            ".github/workflows/**",
        }
        actual = set(re.findall(r"^\s*-\s*['\"]?([^'\"\s]+)['\"]?\s*$", paths, re.M))
        self.assertEqual(actual, expected)

    def test_events_and_path_filters_validate_pushes_and_pull_requests(self):
        for event in ("push", "pull_request"):
            with self.subTest(event=event):
                event_block = indented_block(self.events, event, 2)
                self.assertRegex(event_block, r"(?m)^\s+branches:\s*\[\s*main\s*\]\s*$")
                self.assert_path_filters(event)
        self.assertRegex(self.events, r"(?m)^\s+workflow_dispatch:\s*$")

    def test_global_security_and_build_environment_contract(self):
        permissions = indented_block(self.workflow, "permissions")
        self.assertEqual(permissions.strip(), "contents: read")
        self.assertEqual(indented_block(self.workflow, "concurrency"), "")
        env = indented_block(self.workflow, "env")
        self.assertRegex(env, r"(?m)^\s+BASE_PATH:\s*['\"]?/ai-newsletter['\"]?\s*$")

    def test_builds_cancel_only_older_runs_for_the_same_ref(self):
        concurrency = indented_block(self.build, "concurrency", 4)
        self.assertRegex(concurrency, r'(?m)^\s+group:\s*["\']?pages-\$\{\{ github\.ref \}\}["\']?\s*$')
        self.assertRegex(concurrency, r"(?m)^\s+cancel-in-progress:\s*true\s*$")

    def test_build_uses_pinned_pandoc_tests_and_validated_build(self):
        self.assertIn("uses: actions/checkout@", self.build)
        self.assertIn("uses: r-lib/actions/setup-pandoc@", self.build)
        self.assertRegex(self.build, r"(?m)^\s+pandoc-version:\s*['\"]3\.8\.3['\"]\s*$")
        test_step = "run: python3 -m unittest discover -s tests -v"
        build_step = "run: bash scripts/build-html.sh"
        self.assertIn(test_step, self.build)
        self.assertIn(build_step, self.build)
        self.assertLess(self.build.index(test_step), self.build.index(build_step))

    def test_executable_actions_are_pinned_to_full_commit_shas(self):
        references = []
        for value in re.findall(r"(?m)^\s+uses:\s+(.+?)\s*$", self.workflow):
            reference = re.fullmatch(
                r"([^@\s]+)@([0-9a-f]{40})\s+#\s+(v\d+)", value
            )
            self.assertIsNotNone(reference, f"action is not SHA-pinned: {value}")
            references.append(reference.groups())
        self.assertEqual(
            {name: version for name, _, version in references}, ACTION_VERSIONS
        )
        self.assertEqual(len(references), len(ACTION_VERSIONS))
        self.assertNotIn("r-lib/actions/setup-pandoc@v2", self.workflow)

    def test_pull_requests_cannot_upload_or_deploy(self):
        condition = "if: github.event_name != 'pull_request'"
        upload_step = re.search(
            r"(?ms)^\s+- name: [^\n]+\n(?P<body>(?:\s{8,}[^\n]*\n)*?\s+uses: actions/upload-pages-artifact@[0-9a-f]{40}[^\n]*(?:\n|$))",
            self.build,
        )
        self.assertIsNotNone(upload_step, "missing upload-pages-artifact step")
        self.assertIn(condition, upload_step.group("body"))
        self.assertRegex(
            self.build,
            r"(?ms)uses: actions/upload-pages-artifact@[0-9a-f]{40}.*?\n\s+with:\s*\n\s+path:\s*docs/\s*$",
        )
        self.assertNotIn("actions/configure-pages@", self.build)
        self.assertEqual(indented_block(self.build, "permissions", 4), "")

        self.assertRegex(self.deploy, rf"(?m)^\s+{re.escape(condition)}\s*$")
        self.assertRegex(self.deploy, r"(?m)^\s+needs:\s*build\s*$")
        permissions = indented_block(self.deploy, "permissions", 4)
        self.assertEqual(
            set(re.findall(r"(?m)^\s+([\w-]+:\s*\w+)\s*$", permissions)),
            {"pages: write", "id-token: write"},
        )
        environment = indented_block(self.deploy, "environment", 4)
        self.assertIn("name: github-pages", environment)
        self.assertIn("url: ${{ steps.deployment.outputs.page_url }}", environment)
        configure = "uses: actions/configure-pages@"
        deploy = "uses: actions/deploy-pages@"
        self.assertIn(configure, self.deploy)
        self.assertIn(deploy, self.deploy)
        self.assertLess(self.deploy.index(configure), self.deploy.index(deploy))

    def test_deployments_are_serialized_without_cancelling_in_progress(self):
        concurrency = indented_block(self.deploy, "concurrency", 4)
        self.assertRegex(concurrency, r"(?m)^\s+group:\s*pages\s*$")
        self.assertRegex(concurrency, r"(?m)^\s+cancel-in-progress:\s*false\s*$")


if __name__ == "__main__":
    unittest.main()
