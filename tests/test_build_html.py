import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts/build-html.sh"


class BuildHtmlContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = BUILD_SCRIPT.read_text(encoding="utf-8")

    def test_build_is_portable_strict_and_validated(self):
        self.assertTrue(os.access(BUILD_SCRIPT, os.X_OK))
        self.assertIn("set -euo pipefail", self.script)
        self.assertIn('SCRIPT_DIR=', self.script)
        self.assertIn('cd "$PROJECT_ROOT"', self.script)
        self.assertIn("validate-source --output output --ledger data/news-ledger.json", self.script)
        self.assertIn("validate-site --output output --site docs", self.script)
        self.assertNotIn("normalize-md.sh", self.script)

    def test_base_path_is_configurable_without_project_name(self):
        self.assertIn('${BASE_PATH-/ai-newsletter}', self.script)
        self.assertIn('BASE_PATH="${BASE_PATH%/}"', self.script)
        self.assertIn('while [[ "$BASE_PATH" == */ ]]; do', self.script)
        self.assertNotIn("PROJECT_NAME", self.script)
        self.assertNotIn('href="/ai-newsletter', self.script)
        self.assertNotIn("fetch('/ai-newsletter", self.script)

    def test_archive_loop_preserves_final_month_state(self):
        self.assertIn('done < <(find "$SITE_DIR/reports" -name "*.html" -type f | sort -r)', self.script)
        self.assertIn('if [ -n "$last_month" ]; then', self.script)
        self.assertIn('</ul></details>', self.script)

    def test_search_generation_uses_safe_dom_contract(self):
        self.assertIn("generate-search --output output", self.script)
        self.assertIn("__BASE_PATH__", self.script)
        self.assertIn("escapeRegExp", self.script)
        self.assertIn("document.createElement('mark')", self.script)
        self.assertIn("textContent", self.script)
        self.assertNotIn("innerHTML", self.script)


if __name__ == "__main__":
    unittest.main()
