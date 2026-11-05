# Web QA Evidence

Turn explicit QA observations into a portable HTML report and CSV case ledger using Python's standard library.

```sh
python3 qa_report.py examples/template.json --out reports/template
```

Open `reports/template/report.html` in a browser. Keep `report.html`, `cases.csv` and the generated `assets/` directory together when sharing. The bundled template contains **not_run** cases, with no executed results or screenshots. Use Python 3.9 or later; no packages, API keys, network access or accounts are required.

This CLI formats observations a tester supplies. It does not run browser tests or discover defects. Reports contain all cases, status counts, environment, scope, limitations, failure severity and supplied evidence images. Generated reports have no JavaScript or external assets.

## Input contract

Supply a UTF-8 JSON object; see [the complete editable template](examples/template.json).

| Field | Required value |
| --- | --- |
| `title`, `build`, `tested_at`, `scope` | Nonempty strings. For executed work, use the exact build and actual execution time. The generator does not invent or verify them. |
| `environment` | Object with nonempty `browser`, `os` strings and a `viewports` array of nonempty strings; the array may be empty. |
| `limitations` | Array of nonempty strings; an empty array is allowed. State the practical coverage limits. |
| `cases` | Nonempty array of case objects. |

Each case requires:

| Field | Required value |
| --- | --- |
| `id` | Nonempty string, unique within the report. |
| `title`, `expected`, `actual` | Nonempty strings. Preserve the distinction between expectation and observed result. |
| `status` | `pass`, `fail`, `blocked` or `not_run`. |
| `steps` | Nonempty array of nonempty strings, in execution order. |
| `evidence` | Array of relative PNG/JPG/JPEG/WebP image paths; may be empty. |
| `severity` | For `fail` cases: `high`, `medium` or `low`. Otherwise ignored. |

Unknown fields are ignored. Schema errors print a clear message to stderr and exit nonzero before creating output. Empty strings and whitespace-only strings are rejected. `tested_at` is recorded as supplied, allowing honest unexecuted templates rather than fictional timestamps.

## Evidence and output

Evidence paths are relative to the input JSON's directory. For example, if `review/observations.json` names `screens/quote.png`, the source is `review/screens/quote.png`.

- Only regular files inside the input directory are accepted. Absolute paths, URLs, `..` traversal, backslashes, colon-containing paths and symlinks are rejected. Copy linked evidence into the input tree as a regular file first.
- Extension and PNG/JPEG/WebP signatures must match. This checks file signatures, not complete image decoding or whether a screenshot proves a finding.
- Safe images are copied into `assets/` with stable SHA-256 names. HTML and CSV reference those copied assets; original names are not exposed. Identical content with the same normalized extension shares an asset.
- All observation text is escaped in HTML. CSV uses standard quoting, with steps and evidence separated by newlines within their cells. Cells starting with `=`, `+`, `-`, `@`, tab or carriage return receive a leading apostrophe to neutralize spreadsheet formulas; other text is preserved.
- Choose a new or empty output directory. The input file/directory, a symlink output directory, and existing nonempty output directories are rejected. Existing reports and source evidence are not overwritten.

Input validation and evidence reads finish before writing begins. A disk or permission error during output may leave a partial report; choose a fresh output directory after resolving it. Run locally against a stable input tree: this is not a sandbox for concurrently modified hostile files. Large images are held in memory during validation. Review screenshots and observations for private data before sharing.

## Synthetic browser fixture

Open `demo/index.html` locally, or serve the repository:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Visit `http://127.0.0.1:8000/demo/` for the explicitly seeded build and `http://127.0.0.1:8000/demo/?build=fixed` for the reference. Both display **Synthetic QA fixture — no booking or payment is sent**. The fixture makes no service requests and stores no information.

The default build has exactly two intentional defects: Express does not receive SAVE20, and a validation error resets parcel count to 1. The fixed build corrects both. [Demo requirements](docs/demo-requirements.md) document rules, expected behavior and coverage suggestions. A documented defect is not proof that a test was executed; record actual observations and capture actual evidence separately.

## Observed sample

[See the measured synthetic sample](docs/sample-results.md): 48 recorded browser observations, with two known defect types reproduced at both tested widths and 24 passing checks in the corrected reference. Includes actual screenshots, a CSV ledger, raw observations and a short flow guide. This is a calibration exercise, not client work or proof of paid demand.

## Optional scoped service

A scoped C$149 QA/documentation pilot uses this kit for one agreed journey, twelve cases at two viewport widths, an evidence report and flow guide. Inquiries are open. Checkout is issued privately after written scope, access checks and an accepted preview. [Scope, eligibility and contact](docs/pilot.md).

## Development

```sh
python3 -m unittest discover -s tests -v
```

The CLI tests exercise real subprocess runs, schema errors, output protection, HTML escaping, CSV formula protection, evidence copying and unsafe paths. Browser execution against the disposable fixture is a separate activity.

MIT licensed; see [LICENSE](LICENSE).
