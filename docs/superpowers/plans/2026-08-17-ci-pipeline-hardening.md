# CI Pipeline Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the newsletter P0-P2 build and deployment path so malformed output cannot deploy, pull requests are checked before merge, generated artifacts have one owner, search is safe and deterministic, and source Markdown matches deployed content.

**Architecture:** Keep Bash as the Pandoc/site assembly orchestrator and add one standard-library Python module for search-data generation and source/site validation. Treat `output/**/*.md` as the sole content source, rebuild ignored site artifacts from scratch, and split GitHub Actions behavior so pull requests validate while main pushes and manual runs validate then deploy.

**Tech Stack:** Bash 4+, Python 3 standard library and `unittest`, Pandoc 3.8.3, GitHub Actions, static HTML/JavaScript

---

## File Map

- Create `scripts/site_tools.py`: deterministic search-data generation plus source and generated-site validation CLI.
- Create `tests/test_site_tools.py`: isolated unit tests for search records, title rules, JSON parsing, report parity, archive balance, and search-page safety markers.
- Create `.gitignore`: exclude all generated HTML and search JSON while preserving authored assets/templates.
- Modify `scripts/normalize-md.sh`: make the one-time migration deterministic, support one-digit times, and keep it as an explicit manual repair tool only.
- Modify all `output/**/*.md`: normalize the first line once so source and deployed titles match.
- Modify `scripts/build-html.sh`: strict mode, clean build, configurable base path, fixed archive loop, Python-generated JSON, safe search DOM rendering, and validation gates.
- Modify `scripts/render.sh` and `scripts/publish.sh`: apply strict Shell error handling consistently to all entry points.
- Modify `.github/workflows/ai-newsletter.yml`: PR validation, conditional deployment, pinned Pandoc version, and configured base path.
- Modify `README.md`: document the canonical build/validation commands, generated-artifact policy, and base-path override.
- Modify `docs/README.md`: align page behavior with the generated site and remove stale claims.
- Stop tracking `docs/reports/**/*.html`, `docs/index.html`, `docs/archive.html`, `docs/search.html`, and `docs/assets/search_data.json`.

### Task 1: Add Tested Search Generation and Validation Tooling

**Files:**
- Create: `scripts/site_tools.py`
- Create: `tests/test_site_tools.py`

- [ ] **Step 1: Write the failing unit tests**

Create `tests/test_site_tools.py` with fixture-only tests so they do not depend on the repository's currently non-normalized Markdown:

```python
import json
import tempfile
import unittest
from pathlib import Path

from scripts.site_tools import (
    create_search_records,
    normalize_base_path,
    validate_site,
    validate_source,
    write_search_data,
)


VALID_TITLE = "# 📰 AI Daily Newsletter — 2026年08月17日 08:55"


class SiteToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.output = self.root / "output"
        self.site = self.root / "docs"
        self.ledger = self.root / "data" / "news-ledger.json"
        self.md_file = self.output / "2026" / "08" / "17.md"
        self.md_file.parent.mkdir(parents=True)
        self.md_file.write_text(
            VALID_TITLE + '\n\nA "quoted" item with \\ and\ttab.\n',
            encoding="utf-8",
        )
        self.ledger.parent.mkdir(parents=True)
        self.ledger.write_text('{"entries": []}\n', encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_normalize_base_path_supports_project_and_root_sites(self):
        self.assertEqual(normalize_base_path("/ai-newsletter/"), "/ai-newsletter")
        self.assertEqual(normalize_base_path("/"), "")
        self.assertEqual(normalize_base_path(""), "")
        with self.assertRaisesRegex(ValueError, "start with /"):
            normalize_base_path("ai-newsletter")

    def test_search_records_are_sorted_and_use_full_dates(self):
        older = self.output / "2026" / "08" / "16.md"
        older.write_text(
            "# 📰 AI Daily Newsletter — 2026年08月16日 09:00\nOlder\n",
            encoding="utf-8",
        )
        records = create_search_records(self.output, "/ai-newsletter")
        self.assertEqual([record["date"] for record in records], ["2026/08/17", "2026/08/16"])
        self.assertEqual(records[0]["url"], "/ai-newsletter/reports/2026/08/17.html")
        self.assertIn('"quoted"', records[0]["content"])
        self.assertIn("\\", records[0]["content"])

    def test_write_search_data_emits_parseable_utf8_json(self):
        destination = self.site / "assets" / "search_data.json"
        write_search_data(self.output, destination, "/ai-newsletter")
        data = json.loads(destination.read_text(encoding="utf-8"))
        self.assertEqual(data[0]["title"], VALID_TITLE.removeprefix("# "))
        self.assertEqual(data[0]["date"], "2026/08/17")

    def test_validate_source_reports_bad_title_and_bad_ledger(self):
        self.md_file.write_text("Newsletter without heading\n", encoding="utf-8")
        self.ledger.write_text("not-json\n", encoding="utf-8")
        errors = validate_source(self.output, self.ledger)
        self.assertTrue(any("invalid title" in error for error in errors))
        self.assertTrue(any("invalid ledger JSON" in error for error in errors))

    def test_validate_source_rejects_title_date_mismatching_path(self):
        self.md_file.write_text(
            "# 📰 AI Daily Newsletter — 2026年08月18日 08:55\n",
            encoding="utf-8",
        )
        errors = validate_source(self.output, self.ledger)
        self.assertTrue(any("does not match path date" in error for error in errors))

    def test_validate_site_reports_unbalanced_archive_and_missing_report(self):
        (self.site / "assets").mkdir(parents=True)
        (self.site / "index.html").write_text("<html></html>", encoding="utf-8")
        (self.site / "search.html").write_text(
            "escapeRegExp textContent createElement('mark')", encoding="utf-8"
        )
        (self.site / "archive.html").write_text("<details><ul>", encoding="utf-8")
        write_search_data(self.output, self.site / "assets" / "search_data.json", "")
        errors = validate_site(self.output, self.site)
        self.assertTrue(any("unbalanced <details>" in error for error in errors))
        self.assertTrue(any("unbalanced <ul>" in error for error in errors))
        self.assertTrue(any("missing generated report" in error for error in errors))

    def test_validate_site_accepts_complete_output(self):
        report = self.site / "reports" / "2026" / "08" / "17.html"
        report.parent.mkdir(parents=True)
        report.write_text("<html></html>", encoding="utf-8")
        (self.site / "assets").mkdir(parents=True)
        (self.site / "index.html").write_text("<html></html>", encoding="utf-8")
        (self.site / "archive.html").write_text(
            "<details><ul></ul></details>", encoding="utf-8"
        )
        (self.site / "search.html").write_text(
            "escapeRegExp textContent createElement('mark')", encoding="utf-8"
        )
        write_search_data(self.output, self.site / "assets" / "search_data.json", "")
        self.assertEqual(validate_site(self.output, self.site), [])

    def test_validate_site_rejects_inner_html_search_rendering(self):
        self.site.mkdir(parents=True)
        (self.site / "search.html").write_text(
            "escapeRegExp textContent createElement('mark') innerHTML",
            encoding="utf-8",
        )
        errors = validate_site(self.output, self.site)
        self.assertTrue(any("must not use innerHTML" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify they fail for the expected reason**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: `ERROR` with `ModuleNotFoundError: No module named 'scripts.site_tools'`.

- [ ] **Step 3: Implement the minimal Python module and CLI**

Create `scripts/site_tools.py`:

```python
#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path


TITLE_RE = re.compile(
    r"^# 📰 AI Daily Newsletter — (\d{4})年(\d{2})月(\d{2})日 (\d{2}):(\d{2})$"
)
DATE_RE = re.compile(r"^\d{4}/\d{2}/\d{2}$")


def normalize_base_path(base_path):
    if base_path == "/":
        return ""
    if base_path and not base_path.startswith("/"):
        raise ValueError("base path must start with /")
    return base_path.rstrip("/")


def markdown_files(output_dir):
    return sorted(Path(output_dir).rglob("*.md"))


def path_date(md_file, output_dir):
    relative = md_file.relative_to(output_dir)
    if len(relative.parts) != 3 or relative.suffix != ".md":
        raise ValueError(f"invalid newsletter path: {md_file}")
    year, month, filename = relative.parts
    day = Path(filename).stem
    if not re.fullmatch(r"\d{4}", year) or not re.fullmatch(r"\d{2}", month) or not re.fullmatch(r"\d{2}", day):
        raise ValueError(f"invalid newsletter path: {md_file}")
    return year, month, day


def create_search_records(output_dir, base_path):
    output_dir = Path(output_dir)
    base_path = normalize_base_path(base_path)
    records = []
    for md_file in markdown_files(output_dir):
        year, month, day = path_date(md_file, output_dir)
        text = md_file.read_text(encoding="utf-8")
        first_line = text.splitlines()[0] if text.splitlines() else ""
        title = first_line.removeprefix("# ") or "AI Daily Newsletter"
        relative_html = md_file.relative_to(output_dir).with_suffix(".html").as_posix()
        records.append(
            {
                "title": title,
                "url": f"{base_path}/reports/{relative_html}",
                "content": " ".join(text.splitlines()),
                "date": f"{year}/{month}/{day}",
            }
        )
    return sorted(records, key=lambda record: record["date"], reverse=True)


def write_search_data(output_dir, destination, base_path):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    records = create_search_records(output_dir, base_path)
    destination.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def validate_source(output_dir, ledger_path):
    output_dir = Path(output_dir)
    errors = []
    try:
        json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"invalid ledger JSON: {ledger_path}: {error}")

    for md_file in markdown_files(output_dir):
        try:
            year, month, day = path_date(md_file, output_dir)
        except ValueError as error:
            errors.append(str(error))
            continue
        lines = md_file.read_text(encoding="utf-8").splitlines()
        first_line = lines[0] if lines else ""
        match = TITLE_RE.fullmatch(first_line)
        if not match:
            errors.append(f"invalid title: {md_file}: {first_line!r}")
            continue
        if match.group(1, 2, 3) != (year, month, day):
            errors.append(f"title does not match path date: {md_file}: {first_line!r}")
    return errors


def validate_site(output_dir, site_dir):
    output_dir = Path(output_dir)
    site_dir = Path(site_dir)
    errors = []
    for required in ("index.html", "archive.html", "search.html", "assets/search_data.json"):
        if not (site_dir / required).is_file():
            errors.append(f"missing generated file: {site_dir / required}")

    expected = {
        md.relative_to(output_dir).with_suffix(".html").as_posix()
        for md in markdown_files(output_dir)
    }
    reports_dir = site_dir / "reports"
    actual = {
        report.relative_to(reports_dir).as_posix()
        for report in reports_dir.rglob("*.html")
    } if reports_dir.is_dir() else set()
    for missing in sorted(expected - actual):
        errors.append(f"missing generated report: {missing}")
    for stale in sorted(actual - expected):
        errors.append(f"stale generated report: {stale}")

    archive_path = site_dir / "archive.html"
    if archive_path.is_file():
        archive = archive_path.read_text(encoding="utf-8")
        if archive.count("<details") != archive.count("</details>"):
            errors.append("unbalanced <details> elements in archive.html")
        if archive.count("<ul") != archive.count("</ul>"):
            errors.append("unbalanced <ul> elements in archive.html")

    search_path = site_dir / "assets" / "search_data.json"
    if search_path.is_file():
        try:
            search_data = json.loads(search_path.read_text(encoding="utf-8"))
            if len(search_data) != len(expected):
                errors.append("search record count does not match Markdown count")
            dates = [record.get("date", "") for record in search_data]
            if any(not DATE_RE.fullmatch(date) for date in dates):
                errors.append("search data contains a date outside YYYY/MM/DD format")
            if dates != sorted(dates, reverse=True):
                errors.append("search data is not sorted newest-first")
        except json.JSONDecodeError as error:
            errors.append(f"invalid search JSON: {search_path}: {error}")

    search_page = site_dir / "search.html"
    if search_page.is_file():
        html = search_page.read_text(encoding="utf-8")
        if "innerHTML" in html:
            errors.append("search.html must not use innerHTML")
        for marker in ("escapeRegExp", "textContent", "createElement('mark')"):
            if marker not in html:
                errors.append(f"search.html is missing safe rendering marker: {marker}")
    return errors


def print_errors(errors):
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 1 if errors else 0


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate-search")
    generate.add_argument("--output", required=True)
    generate.add_argument("--destination", required=True)
    generate.add_argument("--base-path", default="/ai-newsletter")

    source = subparsers.add_parser("validate-source")
    source.add_argument("--output", required=True)
    source.add_argument("--ledger", required=True)

    site = subparsers.add_parser("validate-site")
    site.add_argument("--output", required=True)
    site.add_argument("--site", required=True)

    args = parser.parse_args()
    if args.command == "generate-search":
        write_search_data(args.output, args.destination, args.base_path)
        return 0
    if args.command == "validate-source":
        return print_errors(validate_source(args.output, args.ledger))
    return print_errors(validate_site(args.output, args.site))


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests and verify they pass**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: `Ran 8 tests` followed by `OK`.

- [ ] **Step 5: Verify the CLI rejects the current non-normalized source**

Run:

```bash
python3 scripts/site_tools.py validate-source --output output --ledger data/news-ledger.json
```

Expected: non-zero exit with one or more `ERROR: invalid title:` lines. This failure is intentional until Task 2.

- [ ] **Step 6: Commit the tooling and tests**

```bash
git add scripts/site_tools.py tests/test_site_tools.py
git commit -m "test: add newsletter site validation tooling"
```

### Task 2: Normalize Markdown Titles Once

**Files:**
- Modify: `scripts/normalize-md.sh:1-38`
- Modify: `output/**/*.md:1`

- [ ] **Step 1: Strengthen the migration script before changing data**

Update `scripts/normalize-md.sh` to use strict mode and support one- or two-digit hours:

```bash
#!/bin/bash
set -euo pipefail

echo "🔧 Normalizing MD titles in output/ to consistent format..."

find output -name "*.md" -type f -print0 | while IFS= read -r -d '' md_file; do
  [[ -s "$md_file" ]] || { echo "⚠️ Skipping empty: $md_file"; continue; }

  date_path=$(printf '%s\n' "$md_file" | sed -n 's|^output/\([0-9]\{4\}\)/\([0-9]\{2\}\)/\([0-9]\{2\}\)\.md$|\1\2\3|p')
  [[ -n "$date_path" ]] || { echo "⚠️ Invalid path: $md_file"; continue; }

  year="${date_path:0:4}"
  month="${date_path:4:2}"
  day="${date_path:6:2}"
  first_line=$(IFS= read -r line < "$md_file"; printf '%s' "$line")
  existing_header=$(sed -n '1,3p' "$md_file" | grep -m1 'AI Daily Newsletter' || true)
  time="09:00"
  if [[ "$existing_header" =~ ([0-9]{1,2}):([0-9]{2})$ ]]; then
    printf -v time '%02d:%02d' "$((10#${BASH_REMATCH[1]}))" "$((10#${BASH_REMATCH[2]}))"
  elif [[ "$first_line" =~ ([0-9]{1,2}):([0-9]{2})$ ]]; then
    printf -v time '%02d:%02d' "$((10#${BASH_REMATCH[1]}))" "$((10#${BASH_REMATCH[2]}))"
  fi

  new_title="# 📰 AI Daily Newsletter — ${year}年${month}月${day}日 ${time}"
  second_line=$(sed -n '2p' "$md_file")
  third_line=$(sed -n '3p' "$md_file")
  if [[ "$first_line" == "---" && "$second_line" == *"AI Daily Newsletter"* && "$third_line" == "---" ]]; then
    temp_file=$(mktemp)
    {
      printf '%s\n' "$new_title"
      tail -n +4 "$md_file"
    } > "$temp_file"
    mv "$temp_file" "$md_file"
    echo "✅ Collapsed legacy header: $md_file"
  elif [[ "$first_line" != "$new_title" ]]; then
    sed -i.bak "1c$new_title" "$md_file"
    rm -f "$md_file.bak"
    echo "✅ Fixed: $md_file"
  fi
done

echo "✅ Normalization complete!"
```

- [ ] **Step 2: Run the one-time migration**

Run:

```bash
bash scripts/normalize-md.sh
```

Expected: each nonconforming file prints `Fixed`; the legacy front-matter case prints `Collapsed legacy header`; no `.bak` files remain.

- [ ] **Step 3: Verify all titles and ledger now pass source validation**

Run:

```bash
python3 scripts/site_tools.py validate-source --output output --ledger data/news-ledger.json
python3 - <<'PY'
from pathlib import Path
for path in Path('output').rglob('*.md'):
    first_three = path.read_text(encoding='utf-8').splitlines()[:3]
    assert sum('AI Daily Newsletter' in line for line in first_three) == 1, path
print('no duplicate legacy titles')
PY
```

Expected: source validation exits 0 with no `ERROR` lines, then prints `no duplicate legacy titles`.

- [ ] **Step 4: Confirm the migration only changed first lines**

Run:

```bash
git diff --stat -- output scripts/normalize-md.sh
git diff --check
```

Expected: all newsletter files show one-line title replacements; `git diff --check` has no output.

- [ ] **Step 5: Commit the deterministic source migration**

```bash
git add scripts/normalize-md.sh output
git commit -m "fix: normalize newsletter source titles"
```

### Task 3: Make Generated Site Files Build-Only Artifacts

**Files:**
- Create: `.gitignore`
- Stop tracking: `docs/reports/**/*.html`
- Stop tracking: `docs/index.html`
- Stop tracking: `docs/archive.html`
- Stop tracking: `docs/search.html`
- Stop tracking: `docs/assets/search_data.json`

- [ ] **Step 1: Add exact generated paths to `.gitignore`**

Create `.gitignore`:

```gitignore
# Generated by scripts/build-html.sh
/docs/reports/
/docs/index.html
/docs/archive.html
/docs/search.html
/docs/assets/search_data.json
```

- [ ] **Step 2: Remove generated files from the Git index without deleting local copies**

Run:

```bash
git rm -r --cached docs/reports
git rm --cached docs/index.html docs/archive.html docs/search.html docs/assets/search_data.json
```

Expected: Git stages deletion of 20 generated files; files remain available locally and are ignored.

- [ ] **Step 3: Verify authored docs assets remain tracked**

Run:

```bash
git check-ignore docs/reports/2026/02/11.html docs/index.html docs/assets/search_data.json
git ls-files docs/assets/style.css docs/templates/header.html docs/templates/footer.html docs/README.md
```

Expected: the first command prints all three ignored paths; the second prints all four authored paths.

- [ ] **Step 4: Commit the artifact ownership change**

```bash
git add .gitignore
git commit -m "build: stop tracking generated site artifacts"
```

### Task 4: Harden and Validate the Site Build

**Files:**
- Modify: `scripts/build-html.sh:1-367`

- [ ] **Step 1: Add strict setup, base-path validation, source validation, and clean output**

Replace the opening setup in `scripts/build-html.sh` with:

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

SITE_DIR="docs"
BASE_PATH="${BASE_PATH-/ai-newsletter}"
BASE_PATH="${BASE_PATH%/}"
if [[ -n "$BASE_PATH" && "$BASE_PATH" != /* ]]; then
    echo "BASE_PATH must be empty or start with /" >&2
    exit 1
fi

python3 scripts/site_tools.py validate-source \
    --output output \
    --ledger data/news-ledger.json

rm -rf "$SITE_DIR/reports"
rm -f "$SITE_DIR/index.html" "$SITE_DIR/archive.html" \
    "$SITE_DIR/search.html" "$SITE_DIR/assets/search_data.json"
mkdir -p "$SITE_DIR/reports"
```

Delete the existing `./scripts/normalize-md.sh` build-time call. Replace every `/$PROJECT_NAME/...` and hardcoded `/ai-newsletter/...` URL with `${BASE_PATH}/...` in non-JavaScript heredocs; Step 4 handles the quoted search-page heredoc separately.

- [ ] **Step 2: Fix the archive subshell bug**

Replace the archive report loop with process substitution so `last_month` survives after the loop:

```bash
    while read -r f; do
        rel="${f#$SITE_DIR/}"
        date_part="${rel#reports/}"
        nice_date="${date_part%.html}"
        month="${nice_date%/*}"

        if [[ "$month" != "$last_month" ]]; then
            if [[ -n "$last_month" ]]; then
                echo "        </ul></details>" >> "$tmp"
            fi
            echo "        <details class='month-group glass-effect' open><summary><h3>$month</h3></summary><ul>" >> "$tmp"
            last_month="$month"
        fi

        title=$(sed -n 's:.*<title>\(.*\)</title>.*:\1:p' "$f" | head -n1)
        title=${title:-$(basename "$f")}
        echo "          <li><span class='date'>$nice_date</span> - <a href=\"${BASE_PATH}/${rel}\">$title</a></li>" >> "$tmp"
    done < <(find "$SITE_DIR/reports" -name "*.html" -type f | sort -r)

    if [[ -n "$last_month" ]]; then
        echo "        </ul></details>" >> "$tmp"
    fi
```

- [ ] **Step 3: Replace shell-built search JSON with the Python generator**

Replace `generate_search_data()` with:

```bash
generate_search_data() {
    DATA_FILE="$SITE_DIR/assets/search_data.json"
    python3 scripts/site_tools.py generate-search \
        --output output \
        --destination "$DATA_FILE" \
        --base-path "$BASE_PATH"
    echo "✅ Search data updated: $DATA_FILE"
}
```

- [ ] **Step 4: Replace unsafe search-result rendering with DOM construction**

In the generated `search.html`, use this JavaScript implementation. Keep the heredoc quoted and use the literal `__BASE_PATH__` placeholder so Bash cannot alter JavaScript regex or backslash syntax:

```javascript
let searchData = [];

async function loadSearchData() {
  try {
    const response = await fetch('__BASE_PATH__/assets/search_data.json');
    if (!response.ok) throw new Error('HTTP ' + response.status);
    searchData = await response.json();
  } catch (error) {
    console.error('Failed to load search data:', error);
  }
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function appendHighlightedText(parent, text, query) {
  const regex = new RegExp('(' + escapeRegExp(query) + ')', 'gi');
  let cursor = 0;
  for (const match of text.matchAll(regex)) {
    parent.append(document.createTextNode(text.slice(cursor, match.index)));
    const mark = document.createElement('mark');
    mark.textContent = match[0];
    parent.append(mark);
    cursor = match.index + match[0].length;
  }
  parent.append(document.createTextNode(text.slice(cursor)));
}

function performSearch(query) {
  const resultsContainer = document.getElementById('search-results');
  resultsContainer.replaceChildren();
  if (!query) return;

  const normalizedQuery = query.toLowerCase();
  const filtered = searchData.filter(item =>
    item.title.toLowerCase().includes(normalizedQuery) ||
    item.content.toLowerCase().includes(normalizedQuery) ||
    item.date.includes(query)
  );

  if (filtered.length === 0) {
    const empty = document.createElement('p');
    empty.textContent = '找不到符合的內容';
    resultsContainer.append(empty);
    return;
  }

  for (const item of filtered) {
    const card = document.createElement('div');
    card.className = 'newsletter-card glass-effect';

    const title = document.createElement('h3');
    appendHighlightedText(title, item.title, query);

    const date = document.createElement('div');
    date.className = 'date';
    date.textContent = item.date;

    const summary = document.createElement('div');
    summary.className = 'summary';
    const preview = item.content.length > 150 ? item.content.slice(0, 150) + '...' : item.content;
    appendHighlightedText(summary, preview, query);

    const link = document.createElement('a');
    link.href = item.url;
    link.className = 'btn shine';
    link.textContent = '閱讀全文';

    card.append(title, date, summary, link);
    resultsContainer.append(card);
  }
}

document.getElementById('search-input').addEventListener('input', event => {
  performSearch(event.target.value);
});

loadSearchData();
```

After the quoted heredoc closes, replace only the controlled placeholder:

```bash
SEARCH_BASE_PATH="$BASE_PATH" python3 - "$SEARCH_PAGE" <<'PY'
import os
import sys
from pathlib import Path

search_page = Path(sys.argv[1])
html = search_page.read_text(encoding="utf-8")
search_page.write_text(
    html.replace("__BASE_PATH__", os.environ["SEARCH_BASE_PATH"]),
    encoding="utf-8",
)
PY
```

- [ ] **Step 5: Add the generated-site validation gate**

After all four generation functions run, add:

```bash
python3 scripts/site_tools.py validate-site \
    --output output \
    --site "$SITE_DIR"

echo "✅ Build complete and validated!"
```

- [ ] **Step 6: Run unit tests before the integration build**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: all 8 tests pass.

- [ ] **Step 7: Run and validate a project-path build**

Run:

```bash
BASE_PATH=/ai-newsletter bash scripts/build-html.sh
python3 scripts/site_tools.py validate-site --output output --site docs
python3 -c 'from pathlib import Path; assert len(list(Path("docs/reports").rglob("*.html"))) == len(list(Path("output").rglob("*.md")))'
```

Expected: build ends with `Build complete and validated`; both Python commands exit 0.

- [ ] **Step 8: Verify root deployment path generation**

Run:

```bash
BASE_PATH= bash scripts/build-html.sh
python3 -c 'import json; data=json.load(open("docs/assets/search_data.json")); assert data[0]["url"].startswith("/reports/")'
```

Expected: build succeeds and generated report URLs begin with `/reports/`.

- [ ] **Step 9: Rebuild the normal project path and commit only source files**

Run:

```bash
BASE_PATH=/ai-newsletter bash scripts/build-html.sh
git status --short
```

Expected: generated files do not appear because they are ignored; only `scripts/build-html.sh` is modified.

```bash
git add scripts/build-html.sh
git commit -m "fix: harden newsletter site generation"
```

### Task 5: Add Pull Request Validation and Conditional Deployment

**Files:**
- Modify: `.github/workflows/ai-newsletter.yml:1-55`

- [ ] **Step 1: Replace the workflow with separate validation and deployment behavior**

Use this workflow:

```yaml
name: Build and Deploy AI Newsletter

on:
  push:
    branches: [main]
    paths:
      - 'output/**'
      - 'data/news-ledger.json'
      - 'docs/**'
      - 'scripts/**'
      - 'tests/**'
      - '.github/workflows/**'
  pull_request:
    branches: [main]
    paths:
      - 'output/**'
      - 'data/news-ledger.json'
      - 'docs/**'
      - 'scripts/**'
      - 'tests/**'
      - '.github/workflows/**'
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: pages-${{ github.ref }}
  cancel-in-progress: true

env:
  BASE_PATH: /ai-newsletter

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install pandoc
        uses: r-lib/actions/setup-pandoc@v2
        with:
          pandoc-version: '3.8.3'

      - name: Run tests
        run: python3 -m unittest discover -s tests -v

      - name: Build and validate site
        run: bash scripts/build-html.sh

      - name: Setup Pages
        if: github.event_name != 'pull_request'
        uses: actions/configure-pages@v4

      - name: Upload artifact
        if: github.event_name != 'pull_request'
        uses: actions/upload-pages-artifact@v3
        with:
          path: docs/

  deploy:
    if: github.event_name != 'pull_request'
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    permissions:
      pages: write
      id-token: write
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Validate workflow syntax structurally**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
workflow = Path('.github/workflows/ai-newsletter.yml').read_text()
for required in ('pull_request:', "github.event_name != 'pull_request'", 'pandoc-version:', 'Run tests'):
    assert required in workflow, required
print('workflow structure OK')
PY
```

Expected: `workflow structure OK`.

- [ ] **Step 3: Commit the workflow**

```bash
git add .github/workflows/ai-newsletter.yml
git commit -m "ci: validate newsletter pull requests before deploy"
```

### Task 6: Harden Remaining Shell Entry Points and Update Documentation

**Files:**
- Modify: `scripts/render.sh:4`
- Modify: `scripts/publish.sh:4`
- Modify: `README.md:5-38,110-123`
- Modify: `docs/README.md:3-37`

- [ ] **Step 1: Apply strict mode to the remaining Shell entry points**

In both `scripts/render.sh` and `scripts/publish.sh`, replace:

```bash
set -e
```

with:

```bash
set -euo pipefail
```

- [ ] **Step 2: Correct the root README build and artifact documentation**

Update the project tree to identify `build-html.sh` as canonical and `docs/` HTML/JSON as generated. Replace the manual operation section with:

````markdown
## 📝 手動建置與驗證

```bash
# 執行單元測試
python3 -m unittest discover -s tests -v

# 建置並驗證 GitHub Pages 網站
BASE_PATH=/ai-newsletter bash scripts/build-html.sh

# 僅驗證內容來源
python3 scripts/site_tools.py validate-source \
  --output output \
  --ledger data/news-ledger.json
```

`docs/reports/`、`docs/index.html`、`docs/archive.html`、`docs/search.html`
與 `docs/assets/search_data.json` 都是建置產物，不納入 Git 追蹤。

如部署在網域根目錄，可使用 `BASE_PATH= bash scripts/build-html.sh`。
````

Retain the existing newsletter selection and ledger documentation unchanged.

- [ ] **Step 3: Align `docs/README.md` with current behavior**

State that the index displays the latest three reports, archive groups all generated reports by month, search uses full dates and safe client-side highlighting, and generated pages must be produced with `scripts/build-html.sh`. Remove the stale claims about displaying 7-10 days and collapsible index cards.

- [ ] **Step 4: Run Shell syntax and documentation consistency checks**

Run:

```bash
bash -n scripts/build-html.sh scripts/normalize-md.sh scripts/render.sh scripts/publish.sh
python3 - <<'PY'
from pathlib import Path
readme = Path('README.md').read_text()
docs = Path('docs/README.md').read_text()
assert './scripts/render.sh' not in readme
assert 'scripts/build-html.sh' in readme
assert '最近 3' in docs
print('documentation structure OK')
PY
```

Expected: `bash -n` exits 0 and Python prints `documentation structure OK`.

- [ ] **Step 5: Commit operational tooling and documentation updates**

```bash
git add scripts/render.sh scripts/publish.sh README.md docs/README.md
git commit -m "docs: align newsletter operational workflow"
```

### Task 7: Run Full P0-P2 Verification

**Files:**
- Verify all files changed in Tasks 1-6.

- [ ] **Step 1: Run the complete unit suite**

Run:

```bash
python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Validate source content independently**

Run:

```bash
python3 scripts/site_tools.py validate-source --output output --ledger data/news-ledger.json
```

Expected: exit 0, no errors.

- [ ] **Step 3: Perform a clean production-equivalent build**

Run:

```bash
BASE_PATH=/ai-newsletter bash scripts/build-html.sh
```

Expected: all Markdown files render and the final line reports a validated build.

- [ ] **Step 4: Verify production invariants explicitly**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path

markdown = list(Path('output').rglob('*.md'))
reports = list(Path('docs/reports').rglob('*.html'))
search = json.loads(Path('docs/assets/search_data.json').read_text())
archive = Path('docs/archive.html').read_text()

assert len(markdown) == len(reports) == len(search)
assert archive.count('<details') == archive.count('</details>')
assert archive.count('<ul') == archive.count('</ul>')
assert all(len(item['date']) == 10 for item in search)
assert [item['date'] for item in search] == sorted(
    (item['date'] for item in search), reverse=True
)
print(f'verified {len(markdown)} newsletters')
PY
```

Expected: `verified 154 newsletters` (or the current source count if newsletters were added during implementation).

- [ ] **Step 5: Verify generated artifacts remain ignored and the tree is clean**

Run:

```bash
git status --short
git diff --check
```

Expected: no uncommitted files and no whitespace errors.

- [ ] **Step 6: Inspect final commit history**

Run:

```bash
git log --oneline -7
```

Expected: separate commits for tooling/tests, source normalization, generated-artifact ownership, build hardening, CI, documentation, plus the design-spec commit.
