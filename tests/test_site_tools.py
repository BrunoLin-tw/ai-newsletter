import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import site_tools


VALID_SEARCH_HTML = """<script>
function escapeRegExp(value) { return value; }
const node = document.createElement('mark');
node.textContent = 'result';
</script>
"""


class SiteToolsTest(unittest.TestCase):
    def write_report(self, output, date, body="Body", time="08:30"):
        year, month, day = date.split("/")
        path = output / year / month / f"{day}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# 📰 AI Daily Newsletter — {year}年{month}月{day}日 {time}\n{body}\n",
            encoding="utf-8",
        )
        return path

    def make_complete_site(self, output, site):
        reports = site / "reports"
        for md_file in site_tools.markdown_files(output):
            year, month, day = site_tools.path_date(md_file, output)
            html = reports / year / month / f"{day}.html"
            html.parent.mkdir(parents=True, exist_ok=True)
            html.write_text("report", encoding="utf-8")
        (site / "index.html").write_text("index", encoding="utf-8")
        (site / "archive.html").write_text(
            "<details><ul><li>report</li></ul></details>", encoding="utf-8"
        )
        (site / "search.html").write_text(VALID_SEARCH_HTML, encoding="utf-8")
        site_tools.write_search_data(output, site / "assets/search_data.json", "")

    def test_normalize_base_path_and_markdown_path_helpers(self):
        self.assertEqual(site_tools.normalize_base_path("/ai-newsletter/"), "/ai-newsletter")
        self.assertEqual(site_tools.normalize_base_path("/"), "")
        self.assertEqual(site_tools.normalize_base_path(""), "")
        with self.assertRaisesRegex(ValueError, "start with /"):
            site_tools.normalize_base_path("ai-newsletter")

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            later = self.write_report(output, "2026/08/17")
            earlier = self.write_report(output, "2025/12/01")
            self.assertEqual(site_tools.markdown_files(output), [earlier, later])
            self.assertEqual(
                site_tools.path_date(later, output), ("2026", "08", "17")
            )
            invalid = output / "2026" / "8" / "17.md"
            invalid.parent.mkdir(parents=True, exist_ok=True)
            invalid.touch()
            with self.assertRaises(ValueError):
                site_tools.path_date(invalid, output)

    def test_search_records_are_newest_first_with_safe_content(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            self.write_report(output, "2026/08/16", 'A "quote" and \\slash\tTabbed')
            self.write_report(output, "2026/08/17", "Newest\nsecond line")

            records = site_tools.create_search_records(output, "/ai-newsletter/")

            self.assertEqual([record["date"] for record in records], ["2026/08/17", "2026/08/16"])
            self.assertEqual(records[0]["url"], "/ai-newsletter/reports/2026/08/17.html")
            self.assertEqual(records[0]["title"], "📰 AI Daily Newsletter — 2026年08月17日 08:30")
            self.assertIn("Newest second line", records[0]["content"])
            self.assertIn('A "quote" and \\slash\tTabbed', records[1]["content"])

    def test_write_search_data_is_parseable_utf8_json(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            self.write_report(output, "2026/08/17", "繁體中文")
            destination = root / "nested" / "search_data.json"

            site_tools.write_search_data(output, destination, "")

            raw = destination.read_bytes()
            self.assertTrue(raw.endswith(b"\n"))
            self.assertIn("繁體中文", raw.decode("utf-8"))
            self.assertEqual(json.loads(raw)[0]["date"], "2026/08/17")

    def test_validate_source_reports_invalid_ledger_and_title(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            report = self.write_report(output, "2026/08/17")
            report.write_text("# Wrong title\nBody\n", encoding="utf-8")
            ledger = root / "ledger.json"
            ledger.write_text("not json", encoding="utf-8")

            errors = site_tools.validate_source(output, ledger)

            self.assertTrue(any("invalid ledger JSON" in error for error in errors))
            self.assertTrue(any("invalid title" in error for error in errors))

    def test_validate_source_reports_path_title_date_mismatch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "output"
            report = self.write_report(output, "2026/08/17")
            report.write_text(
                "# 📰 AI Daily Newsletter — 2026年08月16日 08:30\nBody\n",
                encoding="utf-8",
            )
            ledger = root / "ledger.json"
            ledger.write_text("{}", encoding="utf-8")

            errors = site_tools.validate_source(output, ledger)

            self.assertTrue(any("title does not match path date" in error for error in errors))

    def test_validate_site_reports_incomplete_unbalanced_site(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output, site = root / "output", root / "site"
            self.write_report(output, "2026/08/17")
            site.mkdir()
            (site / "archive.html").write_text("<details><ul>", encoding="utf-8")

            errors = site_tools.validate_site(output, site)

            self.assertTrue(any("index" in error for error in errors))
            self.assertTrue(any("search" in error for error in errors))
            self.assertTrue(any("missing report" in error for error in errors))
            self.assertTrue(any("unbalanced" in error for error in errors))

    def test_validate_site_accepts_complete_site_and_rejects_stale_report(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output, site = root / "output", root / "site"
            self.write_report(output, "2026/08/16")
            self.write_report(output, "2026/08/17")
            site.mkdir()
            self.make_complete_site(output, site)
            self.assertEqual(site_tools.validate_site(output, site), [])

            stale = site / "reports/2020/01/01.html"
            stale.parent.mkdir(parents=True)
            stale.write_text("stale", encoding="utf-8")
            self.assertTrue(
                any("stale report" in error for error in site_tools.validate_site(output, site))
            )

    def test_validate_site_rejects_inner_html_and_cli_reports_errors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output, site = root / "output", root / "site"
            self.write_report(output, "2026/08/17")
            site.mkdir()
            self.make_complete_site(output, site)
            with (site / "search.html").open("a", encoding="utf-8") as search:
                search.write("node.innerHTML = value;")

            errors = site_tools.validate_site(output, site)
            self.assertTrue(any("innerHTML" in error for error in errors))

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(site_tools.__file__)),
                    "validate-site",
                    "--output",
                    str(output),
                    "--site",
                    str(site),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ERROR:", result.stderr)


if __name__ == "__main__":
    unittest.main()
