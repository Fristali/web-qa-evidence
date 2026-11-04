import csv
import copy
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CLI = Path(__file__).resolve().parents[1] / "qa_report.py"
# Real 1x1 PNG, used only to exercise copying and signatures; never sold as QA evidence.
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jVJkAAAAASUVORK5CYII=")


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "input"
        self.source.mkdir()
        self.input = self.source / "observations.json"
        self.output = self.root / "report"
        self.data = {
            "title": "Checkout review", "build": "local v1",
            "tested_at": "Not executed — template",
            "environment": {"browser": "Unspecified", "os": "Unspecified",
                            "viewports": ["390 × 844", "1280 × 800"]},
            "scope": "Quote preview only", "limitations": ["No backend"],
            "cases": [{"id": "Q01", "title": "Preview quote", "status": "not_run",
                       "steps": ["Enter a valid quote", "Preview"],
                       "expected": "Quote appears", "actual": "Not executed", "evidence": []}],
        }

    def run_cli(self):
        self.input.write_text(json.dumps(self.data), encoding="utf-8")
        return subprocess.run([sys.executable, str(CLI), str(self.input), "--out", str(self.output)],
                              text=True, capture_output=True)

    def assert_rejected(self, result, message):
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertFalse(self.output.exists(), "Invalid input must not create output")

    def test_valid_report_contains_observations_counts_and_csv(self):
        for status in ("pass", "fail", "blocked"):
            case = dict(self.data["cases"][0], id=status, status=status)
            if status == "fail":
                case["severity"] = "high"
            self.data["cases"].append(case)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = (self.output / "report.html").read_text()
        for text in ("Checkout review", "local v1", "390 × 844", "Quote preview only",
                     "No backend", "Quote appears", "Not executed", "high", "pass: 1",
                     "fail: 1", "blocked: 1", "not_run: 1"):
            self.assertIn(text, report)
        self.assertNotIn("<script", report)
        with (self.output / "cases.csv").open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual([row["id"] for row in rows], ["Q01", "pass", "fail", "blocked"])
        self.assertEqual(rows[0]["steps"], "Enter a valid quote\nPreview")
        self.assertEqual(rows[2]["severity"], "high")

    def test_html_escapes_all_observation_text(self):
        payload = '<script>alert("x")</script>&'
        self.data.update(title=payload, build=payload, tested_at=payload, scope=payload,
                         limitations=[payload])
        self.data["environment"] = dict(browser=payload, os=payload, viewports=[payload])
        self.data["cases"][0].update(id=payload, title=payload, steps=[payload],
                                     expected=payload, actual=payload)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        report = (self.output / "report.html").read_text()
        self.assertNotIn(payload, report)
        self.assertNotIn("<script", report)
        self.assertGreaterEqual(report.count("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;&amp;"), 12)

    def test_csv_neutralizes_formula_prefixes_and_preserves_other_text(self):
        for index, (raw, expected) in enumerate([
            ("=1+1", "'=1+1"), ("+SUM(A1)", "'+SUM(A1)"), ("-2", "'-2"),
            ("@cmd", "'@cmd"), ("\tformula", "'\tformula"), ("\rformula", "'\rformula"),
            ("ordinary, \"text\"\nsecond line", "ordinary, \"text\"\nsecond line"),
        ]):
            with self.subTest(raw=raw):
                self.output = self.root / f"report{index}"
                self.data["cases"][0].update(id=raw, title=raw, steps=[raw], expected=raw, actual=raw)
                result = self.run_cli()
                self.assertEqual(result.returncode, 0, result.stderr)
                with (self.output / "cases.csv").open(newline="") as handle:
                    row = next(csv.DictReader(handle))
                for field in ("id", "title", "steps", "expected", "actual"):
                    self.assertEqual(row[field], expected)

    def test_rejects_invalid_schema_before_writing(self):
        valid = copy.deepcopy(self.data)
        mutations = [
            (lambda d: d.pop("title"), "title"),
            (lambda d: d.update(title="  "), "title"),
            (lambda d: d.update(build=42), "build"),
            (lambda d: d.update(tested_at=None), "tested_at"),
            (lambda d: d.update(scope=[]), "scope"),
            (lambda d: d.update(environment=[]), "environment"),
            (lambda d: d["environment"].pop("browser"), "browser"),
            (lambda d: d["environment"].update(os=""), "os"),
            (lambda d: d["environment"].update(viewports=[12]), "viewports"),
            (lambda d: d.update(limitations="none"), "limitations"),
            (lambda d: d.update(limitations=[""]), "limitations"),
            (lambda d: d.update(cases=[]), "cases"),
            (lambda d: d.update(cases=[False]), "cases"),
            (lambda d: d["cases"][0].update(id=""), "id"),
            (lambda d: d["cases"][0].update(title=""), "title"),
            (lambda d: d["cases"][0].update(status="unknown"), "status"),
            (lambda d: d["cases"][0].update(status=[]), "status"),
            (lambda d: d["cases"][0].update(steps=[]), "steps"),
            (lambda d: d["cases"][0].update(steps=[""]), "steps"),
            (lambda d: d["cases"][0].update(expected=""), "expected"),
            (lambda d: d["cases"][0].update(actual=None), "actual"),
            (lambda d: d["cases"][0].pop("evidence"), "evidence"),
            (lambda d: d["cases"][0].update(evidence="shot.png"), "evidence"),
            (lambda d: d["cases"][0].update(evidence=[42]), "evidence"),
            (lambda d: d["cases"][0].update(status="fail"), "severity"),
            (lambda d: d["cases"][0].update(status="fail", severity="critical"), "severity"),
        ]
        for mutate, message in mutations:
            with self.subTest(field=message, mutation=mutations.index((mutate, message))):
                self.data = copy.deepcopy(valid)
                mutate(self.data)
                self.assert_rejected(self.run_cli(), message)

    def test_rejects_duplicate_case_ids(self):
        self.data["cases"].append(copy.deepcopy(self.data["cases"][0]))
        self.assert_rejected(self.run_cli(), "duplicate")

    def test_rejects_non_object_input_without_tracebacks(self):
        self.data = []
        self.assert_rejected(self.run_cli(), "object")

    def test_rejects_invalid_json_without_tracebacks(self):
        self.input.write_text('{"title":', encoding="utf-8")
        result = subprocess.run([sys.executable, str(CLI), str(self.input), "--out", str(self.output)],
                                text=True, capture_output=True)
        self.assert_rejected(result, "JSON")

    def test_copies_images_to_stable_assets_and_links_report_and_csv(self):
        (self.source / "screens").mkdir()
        image = self.source / 'screens' / 'proof "<&.PNG'
        image.write_bytes(PNG)
        self.data["cases"][0]["evidence"] = ['screens/proof "<&.PNG']
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        assets = list((self.output / "assets").glob("*.png"))
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].read_bytes(), PNG)
        asset = assets[0].relative_to(self.output).as_posix()
        report = (self.output / "report.html").read_text()
        self.assertIn(f'src="{asset}"', report)
        self.assertIn('alt="Evidence 1 for Q01"', report)
        with (self.output / "cases.csv").open(newline="") as handle:
            self.assertEqual(next(csv.DictReader(handle))["evidence"], asset)
        self.output = self.root / "second-report"
        self.assertEqual(self.run_cli().returncode, 0)
        self.assertTrue((self.output / asset).exists(), "Asset names must be stable across runs")

    def test_rejects_unsafe_evidence_paths_before_writing(self):
        outside = self.root / "outside.png"
        outside.write_bytes(PNG)
        (self.source / "escape.png").symlink_to(outside)
        (self.source / "linked-dir").symlink_to(self.root, target_is_directory=True)
        paths = [str(outside), "../outside.png", "screens/../../outside.png",
                 "https://example.com/a.png", "file:///etc/passwd", "//example.com/a.png",
                 "C:\\outside.png", "..\\outside.png", "escape.png", "linked-dir/outside.png",
                 "missing.png"]
        for path in paths:
            with self.subTest(path=path):
                self.data["cases"][0]["evidence"] = [path]
                self.assert_rejected(self.run_cli(), "evidence")

    def test_rejects_non_image_and_mismatched_signatures(self):
        for name, content in [
            ("fake.png", b"<html>not an image</html>"),
            ("fake.jpg", PNG), ("fake.webp", b"RIFFxxxxWAVEhello"),
            ("wrong.svg", b"<svg></svg>"),
        ]:
            with self.subTest(name=name):
                (self.source / name).write_bytes(content)
                self.data["cases"][0]["evidence"] = [name]
                self.assert_rejected(self.run_cli(), "evidence")

    def test_rejects_overwrite_of_existing_nonempty_directory(self):
        self.output.mkdir()
        sentinel = self.output / "report.html"
        sentinel.write_text("Existing report")
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("nonempty", result.stderr)
        self.assertEqual(sentinel.read_text(), "Existing report")
        self.assertEqual(list(self.output.iterdir()), [sentinel])

    def test_rejects_input_directory_alias_and_output_symlinks(self):
        alias = self.root / "alias"
        alias.symlink_to(self.source, target_is_directory=True)
        for output in (self.source, alias, self.input):
            with self.subTest(output=str(output)):
                self.output = output
                result = self.run_cli()
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse((self.source / "report.html").exists())
                self.assertTrue(self.input.exists())

    def test_accepts_existing_empty_output_directory(self):
        self.output.mkdir()
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.output / "report.html").exists())

    def test_output_symlink_loop_is_a_clear_error(self):
        self.output.symlink_to(self.output)
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_unknown_fields_do_not_change_valid_output(self):
        self.data["ignored"] = {"nested": [1, False, None]}
        self.data["cases"][0]["severity"] = {"ignored": True}
        self.data["cases"][0]["ignored"] = [False]
        self.assertEqual(self.run_cli().returncode, 0)
        with (self.output / "cases.csv").open(newline="") as handle:
            self.assertEqual(next(csv.DictReader(handle))["severity"], "")

    def test_later_invalid_evidence_prevents_all_writes(self):
        image = self.source / "valid.png"
        image.write_bytes(PNG)
        self.data["cases"][0]["evidence"] = ["valid.png", "missing.png"]
        self.assert_rejected(self.run_cli(), "missing.png")
        self.assertEqual(image.read_bytes(), PNG)

    def test_accepts_empty_optional_context_arrays(self):
        self.data["environment"]["viewports"] = []
        self.data["limitations"] = []
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Unspecified", (self.output / "report.html").read_text())

    def test_rejects_non_utf8_text_before_creating_output(self):
        valid = copy.deepcopy(self.data)
        (self.source / "valid.png").write_bytes(PNG)
        for index, (mutate, field) in enumerate([
            (lambda d: d.update(title="\ud800"), "title"),
            (lambda d: d["cases"][0].update(actual="\udfff"), "actual"),
            (lambda d: d["environment"].update(viewports=["\ud800"]), "viewports"),
            (lambda d: d["cases"][0].update(steps=["\ud800"]), "steps"),
            (lambda d: d.update(limitations=["\ud800"]), "limitations"),
        ]):
            with self.subTest(field=field):
                self.data = copy.deepcopy(valid)
                self.data["cases"][0]["evidence"] = ["valid.png"]
                self.output = self.root / f"invalid-text-{index}"
                mutate(self.data)
                result = self.run_cli()
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(self.output.exists(), "Invalid text must not create partial reports or assets")
                self.assertIn(field, result.stderr)
                self.assertIn("UTF-8", result.stderr)


if __name__ == "__main__":
    unittest.main()
