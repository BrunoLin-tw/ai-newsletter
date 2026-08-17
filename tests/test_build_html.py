import json
import os
import shutil
import subprocess
import tempfile
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

    def make_project(self, root, extra_body="Body", pandoc_exit=0):
        scripts = root / "scripts"
        scripts.mkdir()
        shutil.copy2(BUILD_SCRIPT, scripts / "build-html.sh")
        shutil.copy2(ROOT / "scripts/site_tools.py", scripts / "site_tools.py")

        (root / "data").mkdir()
        (root / "data/news-ledger.json").write_text("{}\n", encoding="utf-8")
        report = root / "output/2026/08/17.md"
        report.parent.mkdir(parents=True)
        report.write_text(
            "# 📰 AI Daily Newsletter — 2026年08月17日 08:30\n"
            f"{extra_body}\n",
            encoding="utf-8",
        )

        assets = root / "docs/assets"
        assets.mkdir(parents=True)
        (assets / "style.css").write_text("authored-style\n", encoding="utf-8")
        (root / "docs/README.md").write_text("authored-readme\n", encoding="utf-8")
        (root / "docs/index.html").write_text("stale-generated\n", encoding="utf-8")

        bin_dir = root / "bin"
        bin_dir.mkdir()
        pandoc = bin_dir / "pandoc"
        pandoc.write_text(
            f"#!/bin/sh\ncat \"$1\"\nexit {pandoc_exit}\n", encoding="utf-8"
        )
        pandoc.chmod(0o755)
        return bin_dir

    def run_build(self, root, bin_dir, base_path, tmp_dir=None):
        env = os.environ.copy()
        env["BASE_PATH"] = base_path
        env["PATH"] = f"{bin_dir}:{env['PATH']}"
        if tmp_dir is not None:
            env["TMPDIR"] = str(tmp_dir)
        return subprocess.run(
            ["bash", str(root / "scripts/build-html.sh")],
            cwd=root.parent,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_base_path_accepts_root_project_and_safe_nested_paths(self):
        cases = (
            ("", "/reports/2026/08/17.html"),
            ("/ai-newsletter", "/ai-newsletter/reports/2026/08/17.html"),
            ("/safe/nested._~-///", "/safe/nested._~-/reports/2026/08/17.html"),
        )
        for base_path, expected_url in cases:
            with self.subTest(base_path=base_path), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "project"
                root.mkdir()
                bin_dir = self.make_project(root)

                result = self.run_build(root, bin_dir, base_path)

                self.assertEqual(result.returncode, 0, result.stderr)
                records = json.loads(
                    (root / "docs/assets/search_data.json").read_text(encoding="utf-8")
                )
                self.assertEqual(records[0]["url"], expected_url)

    def test_base_path_rejects_adversarial_values_before_cleanup(self):
        invalid_paths = (
            '/bad"path',
            "/bad'path",
            "/bad);path",
            "/bad path",
            "/double//slash",
            "relative",
        )
        for base_path in invalid_paths:
            with self.subTest(base_path=base_path), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary) / "project"
                root.mkdir()
                bin_dir = self.make_project(root)

                result = self.run_build(root, bin_dir, base_path)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("BASE_PATH", result.stderr)
                self.assertEqual(
                    (root / "docs/index.html").read_text(encoding="utf-8"),
                    "stale-generated\n",
                )

    def test_many_headings_do_not_trigger_pipefail_sigpipe(self):
        many_headings = "\n".join(
            f"# Heading {number}\n<title>Body title {number}</title>"
            for number in range(10000)
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            bin_dir = self.make_project(root, extra_body=many_headings)

            result = self.run_build(root, bin_dir, "/ai-newsletter")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotEqual(result.returncode, 141)

    def test_missing_pandoc_does_not_delete_generated_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            bin_dir = self.make_project(root)
            (bin_dir / "pandoc").unlink()
            for command in ("dirname", "python3"):
                (bin_dir / command).symlink_to(shutil.which(command))

            env = os.environ.copy()
            env["BASE_PATH"] = "/ai-newsletter"
            env["PATH"] = str(bin_dir)
            result = subprocess.run(
                ["/bin/bash", str(root / "scripts/build-html.sh")],
                cwd=root.parent,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("pandoc", result.stderr)
            self.assertEqual(
                (root / "docs/index.html").read_text(encoding="utf-8"),
                "stale-generated\n",
            )

    def test_failed_pandoc_cleans_dedicated_build_temp_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            root.mkdir()
            bin_dir = self.make_project(root, pandoc_exit=1)
            tmp_dir = root / "tmp"
            tmp_dir.mkdir()

            result = self.run_build(root, bin_dir, "/ai-newsletter", tmp_dir)

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(tmp_dir.iterdir()), [])

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

    def test_title_extraction_has_no_head_pipeline(self):
        self.assertNotIn("| head -n 1", self.script)


if __name__ == "__main__":
    unittest.main()
