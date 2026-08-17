import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocumentationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root_readme = (ROOT / "README.md").read_text(encoding="utf-8")
        cls.docs_readme = (ROOT / "docs/README.md").read_text(encoding="utf-8")

    def test_operational_commands_use_the_canonical_build(self):
        for command in (
            "python3 -m unittest discover -s tests -v",
            "BASE_PATH=/ai-newsletter bash scripts/build-html.sh",
            "python3 scripts/site_tools.py validate-source --output output "
            "--ledger data/news-ledger.json",
            "BASE_PATH= bash scripts/build-html.sh",
        ):
            with self.subTest(command=command):
                self.assertIn(command, self.root_readme)
        self.assertNotIn("./scripts/render.sh", self.root_readme)

    def test_root_readme_identifies_generated_site_artifacts(self):
        self.assertIn("scripts/build-html.sh", self.root_readme)
        for artifact in (
            "docs/reports/",
            "docs/index.html",
            "docs/archive.html",
            "docs/search.html",
            "docs/assets/search_data.json",
        ):
            with self.subTest(artifact=artifact):
                self.assertIn(artifact, self.root_readme)
        self.assertIn("不納入 Git 追蹤", self.root_readme)
        self.assertNotRegex(
            self.root_readme, r"最新一期:\s*`?/reports/\d{4}/\d{2}/\d{2}\.html"
        )

    def test_docs_readme_describes_current_generated_pages(self):
        for phrase in (
            "最新 3 期",
            "按月份分組",
            "所有",
            "完整日期",
            "安全",
            "scripts/build-html.sh",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.docs_readme)
        self.assertNotIn("最近 7-10 天", self.docs_readme)
        self.assertNotIn("點擊展開/收起", self.docs_readme)

    def test_legacy_shell_scripts_enable_strict_mode(self):
        for relative in ("scripts/render.sh", "scripts/publish.sh"):
            with self.subTest(script=relative):
                script = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("set -euo pipefail", script)


if __name__ == "__main__":
    unittest.main()
