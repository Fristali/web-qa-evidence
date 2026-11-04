#!/usr/bin/env python3
"""Render tester-supplied QA observations as a portable HTML report and CSV."""

import argparse
from collections import Counter
import csv
import hashlib
import json
from html import escape
from pathlib import Path
import stat
import sys


STATUSES = ("pass", "fail", "blocked", "not_run")
CSV_FIELDS = ("id", "title", "status", "severity", "steps", "expected", "actual", "evidence")


def require_text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")


def require_strings(value, field, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        raise ValueError(f"{field} must be {'a nonempty' if nonempty else 'an'} array of strings")
    for index, item in enumerate(value):
        require_text(item, f"{field}[{index}]")


def validate(data):
    if not isinstance(data, dict):
        raise ValueError("Input must be a JSON object")
    for field in ("title", "build", "tested_at", "scope"):
        require_text(data.get(field), field)
    environment = data.get("environment")
    if not isinstance(environment, dict):
        raise ValueError("environment must be an object")
    for field in ("browser", "os"):
        require_text(environment.get(field), f"environment.{field}")
    require_strings(environment.get("viewports"), "environment.viewports")
    require_strings(data.get("limitations"), "limitations")
    if not isinstance(data.get("cases"), list) or not data["cases"]:
        raise ValueError("cases must be a nonempty array")
    ids = set()
    for index, case in enumerate(data["cases"]):
        location = f"cases[{index}]"
        if not isinstance(case, dict):
            raise ValueError(f"{location} must be an object")
        for field in ("id", "title", "expected", "actual", "status"):
            require_text(case.get(field), f"{location}.{field}")
        if case["id"] in ids:
            raise ValueError(f"{location}.id is a duplicate: {case['id']!r}")
        ids.add(case["id"])
        if case["status"] not in STATUSES:
            raise ValueError(f"{location}.status must be one of {', '.join(STATUSES)}")
        require_strings(case.get("steps"), f"{location}.steps", nonempty=True)
        require_strings(case.get("evidence"), f"{location}.evidence")
        if case["status"] == "fail" and case.get("severity") not in ("high", "medium", "low"):
            raise ValueError(f"{location}.severity must be high, medium, or low for a fail case")


def collect_evidence(data, source):
    """Validate all evidence and retain bytes before any output is written."""
    assets = {}
    for case in data["cases"]:
        copied = []
        for relative in case["evidence"]:
            path = Path(relative)
            label = f"Case {case['id']!r} evidence {relative!r}"
            if (path.is_absolute() or ".." in path.parts or ":" in relative
                    or "\\" in relative or "\0" in relative):
                raise ValueError(f"{label}: use a relative path inside the input directory")
            candidate = source
            for part in path.parts:
                candidate = candidate / part
                if candidate.is_symlink():
                    raise ValueError(f"{label}: symlinks are not supported")
            try:
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(source)
                if not stat.S_ISREG(resolved.stat().st_mode):
                    raise ValueError("not a regular file")
                content = resolved.read_bytes()
            except (OSError, ValueError, RuntimeError) as error:
                raise ValueError(f"{label}: cannot read a regular file inside the input directory ({error})") from error
            suffix = path.suffix.lower()
            matches = ((suffix == ".png" and content.startswith(b"\x89PNG\r\n\x1a\n"))
                       or (suffix in (".jpg", ".jpeg") and content.startswith(b"\xff\xd8\xff"))
                       or (suffix == ".webp" and content[:4] == b"RIFF" and content[8:12] == b"WEBP"))
            if not matches:
                raise ValueError(f"{label}: expected a PNG, JPG/JPEG, or WebP image with matching signature")
            suffix = ".jpg" if suffix == ".jpeg" else suffix
            name = f"assets/{hashlib.sha256(content).hexdigest()}{suffix}"
            assets[name] = content
            copied.append(name)
        case["evidence"] = copied
    return assets


def check_output(input_path, output_path):
    source = input_path.parent
    if output_path.is_symlink():
        raise ValueError("Output directory must not be a symlink")
    destination = output_path.resolve()
    if destination in (input_path, source):
        raise ValueError("Output must not alias the input file or its directory")
    if output_path.exists():
        if not output_path.is_dir():
            raise ValueError("Output must be a directory")
        if any(output_path.iterdir()):
            raise ValueError("Output directory is nonempty; choose a new or empty directory")


def render(data):
    text = lambda value: escape(value, quote=True)
    counts = Counter(case["status"] for case in data["cases"])
    environment = data["environment"]
    sections = []
    for case in data["cases"]:
        steps = "".join(f"<li>{text(step)}</li>" for step in case["steps"])
        severity = f" · {text(case['severity'])} severity" if case["status"] == "fail" else ""
        evidence = "".join(
            f'<figure><img src="{text(path)}" alt="Evidence {index} for {text(case["id"])}" loading="lazy">'
            f'<figcaption>Evidence {index} · <a href="{text(path)}">Open image</a></figcaption></figure>'
            for index, path in enumerate(case["evidence"], 1)
        ) or "<p>No evidence supplied.</p>"
        sections.append(f"""<article><p>{text(case['id'])} · {text(case['status'])}{severity}</p>
<h2>{text(case['title'])}</h2><h3>Steps</h3><ol>{steps}</ol>
<h3>Expected</h3><p>{text(case['expected'])}</p><h3>Actual</h3><p>{text(case['actual'])}</p>
<h3>Evidence</h3>{evidence}</article>""")
    limitations = "".join(f"<li>{text(item)}</li>" for item in data["limitations"])
    summary = " · ".join(f"{status}: {counts[status]}" for status in STATUSES)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{text(data['title'])}</title><style>
body{{font:16px/1.6 system-ui,sans-serif;color:#172b32;background:#f7f8f6;margin:0}}
main{{max-width:920px;margin:auto;padding:40px 24px}} h1{{line-height:1.15;font-size:2.4rem}}
article{{border-top:1px solid #bcc8c9;padding:24px 0}} h2,h3{{line-height:1.3}} h3{{font-size:1rem;margin-bottom:4px}}
p,li{{white-space:pre-wrap;overflow-wrap:anywhere}} img{{max-width:100%;height:auto}} a{{color:#006854}}
@media print{{body{{background:white}}main{{padding:0}}article{{break-inside:avoid}}}}
</style></head><body><main><header><p>QA observations</p><h1>{text(data['title'])}</h1>
<p>Build: {text(data['build'])}<br>Tested at: {text(data['tested_at'])}</p><p>{summary}</p></header>
<h2>Environment</h2><p>{text(environment['browser'])} · {text(environment['os'])}<br>{text(', '.join(environment['viewports']))}</p>
<h2>Scope</h2><p>{text(data['scope'])}</p><h2>Limitations</h2><ul>{limitations}</ul>
<p>This report presents supplied observations; the generator does not execute tests.</p>
{''.join(sections)}</main></body></html>
"""


def csv_safe(value):
    return "'" + value if value.startswith(("=", "+", "-", "@", "\t", "\r")) else value


def generate(input_path, output_path):
    input_path = input_path.resolve(strict=True)
    check_output(input_path, output_path)
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON: {error}") from error
    validate(data)
    assets = collect_evidence(data, input_path.parent)
    report = render(data)
    output_path.mkdir(parents=True, exist_ok=True)
    if assets:
        (output_path / "assets").mkdir()
    for name, content in assets.items():
        with (output_path / name).open("xb") as handle:
            handle.write(content)
    with (output_path / "report.html").open("x", encoding="utf-8") as handle:
        handle.write(report)
    with (output_path / "cases.csv").open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for case in data["cases"]:
            row = {field: case.get(field, "") for field in CSV_FIELDS}
            row["severity"] = case["severity"] if case["status"] == "fail" else ""
            row["steps"] = "\n".join(case["steps"])
            row["evidence"] = "\n".join(case["evidence"])
            writer.writerow({field: csv_safe(value) for field, value in row.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON observations file")
    parser.add_argument("--out", type=Path, required=True, help="New or empty output directory")
    args = parser.parse_args()
    try:
        generate(args.input, args.out)
    except (ValueError, OSError, UnicodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"Created {args.out / 'report.html'} and {args.out / 'cases.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
