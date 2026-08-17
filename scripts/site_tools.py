#!/usr/bin/env python3

import argparse
import json
import re
import sys
from pathlib import Path


TITLE_PATTERN = re.compile(
    r"^# 📰 AI Daily Newsletter — (\d{4})年(\d{2})月(\d{2})日 (\d{2}:\d{2})$"
)
DATE_PATTERN = re.compile(r"^\d{4}/\d{2}/\d{2}$")


def normalize_base_path(base_path):
    if not base_path or base_path == "/":
        return ""
    if not base_path.startswith("/"):
        raise ValueError("base path must start with /")
    return base_path.rstrip("/")


def markdown_files(output_dir):
    return sorted(Path(output_dir).rglob("*.md"))


def path_date(md_file, output_dir):
    relative = Path(md_file).relative_to(Path(output_dir))
    match = re.fullmatch(r"(\d{4})/(\d{2})/(\d{2})\.md", relative.as_posix())
    if not match:
        raise ValueError(f"invalid newsletter path: {relative}")
    return match.groups()


def create_search_records(output_dir, base_path):
    output_dir = Path(output_dir)
    base_path = normalize_base_path(base_path)
    records = []
    for md_file in markdown_files(output_dir):
        year, month, day = path_date(md_file, output_dir)
        lines = md_file.read_text(encoding="utf-8").splitlines()
        title = lines[0].removeprefix("# ") if lines else ""
        records.append(
            {
                "title": title,
                "url": f"{base_path}/reports/{year}/{month}/{day}.html",
                "content": " ".join(lines),
                "date": f"{year}/{month}/{day}",
            }
        )
    return sorted(records, key=lambda record: record["date"], reverse=True)


def write_search_data(output_dir, destination, base_path):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    data = create_search_records(output_dir, base_path)
    destination.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def validate_source(output_dir, ledger_path):
    errors = []
    try:
        json.loads(Path(ledger_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        errors.append(f"invalid ledger JSON: {error}")

    output_dir = Path(output_dir)
    for md_file in markdown_files(output_dir):
        try:
            first_line = md_file.read_text(encoding="utf-8").splitlines()[0]
        except (IndexError, OSError, UnicodeError):
            first_line = ""
        match = TITLE_PATTERN.fullmatch(first_line)
        if not match:
            errors.append(f"invalid title: {md_file}")
            continue
        year, month, day = path_date(md_file, output_dir)
        if match.groups()[:3] != (year, month, day):
            errors.append(f"title does not match path date: {md_file}")
    return errors


def validate_site(output_dir, site_dir):
    output_dir = Path(output_dir)
    site_dir = Path(site_dir)
    errors = []
    required = {
        "index": site_dir / "index.html",
        "archive": site_dir / "archive.html",
        "search": site_dir / "search.html",
        "search_data": site_dir / "assets/search_data.json",
    }
    for name, path in required.items():
        if not path.is_file():
            errors.append(f"missing {name}: {path}")

    expected_reports = {
        f"{year}/{month}/{day}.html"
        for md_file in markdown_files(output_dir)
        for year, month, day in [path_date(md_file, output_dir)]
    }
    reports_dir = site_dir / "reports"
    actual_reports = (
        {path.relative_to(reports_dir).as_posix() for path in reports_dir.rglob("*.html")}
        if reports_dir.is_dir()
        else set()
    )
    for report in sorted(expected_reports - actual_reports):
        errors.append(f"missing report: {report}")
    for report in sorted(actual_reports - expected_reports):
        errors.append(f"stale report: {report}")

    archive_path = required["archive"]
    if archive_path.is_file():
        archive = archive_path.read_text(encoding="utf-8")
        for element in ("details", "ul"):
            openings = len(re.findall(fr"<{element}(?:\s|>)", archive, re.IGNORECASE))
            closings = len(re.findall(fr"</{element}\s*>", archive, re.IGNORECASE))
            if openings != closings:
                errors.append(f"unbalanced <{element}> elements in archive")

    search_data_path = required["search_data"]
    if search_data_path.is_file():
        try:
            records = json.loads(search_data_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            errors.append(f"invalid search JSON: {error}")
        else:
            if not isinstance(records, list):
                errors.append("invalid search JSON: expected a list")
            else:
                if len(records) != len(expected_reports):
                    errors.append("search JSON count does not match reports")
                dates = []
                for record in records:
                    date = record.get("date") if isinstance(record, dict) else None
                    if not isinstance(date, str) or not DATE_PATTERN.fullmatch(date):
                        errors.append("search JSON date must use YYYY/MM/DD")
                    else:
                        dates.append(date)
                if dates != sorted(dates, reverse=True):
                    errors.append("search JSON is not newest-first")

    search_path = required["search"]
    if search_path.is_file():
        search = search_path.read_text(encoding="utf-8")
        for token in ("escapeRegExp", "textContent", "createElement('mark')"):
            if token not in search:
                errors.append(f"search HTML missing {token}")
        if "innerHTML" in search:
            errors.append("search HTML must not contain innerHTML")
    return errors


def build_parser():
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
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "generate-search":
        write_search_data(args.output, args.destination, args.base_path)
        return 0
    if args.command == "validate-source":
        errors = validate_source(args.output, args.ledger)
    else:
        errors = validate_site(args.output, args.site)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return bool(errors)


if __name__ == "__main__":
    sys.exit(main())
