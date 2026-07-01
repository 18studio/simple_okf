from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from okf_mcp.okf import OKFBundle, OKFError


class OKFContractTests(unittest.TestCase):
    def _bundle(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name) / "okf"
        root.mkdir()
        return tmp, root

    def _write(self, root: Path, name: str, frontmatter: str) -> None:
        (root / name).write_text(f"---\n{frontmatter}---\n\nBody.\n", encoding="utf-8")

    def test_validate_rejects_missing_status(self) -> None:
        tmp, root = self._bundle()
        with tmp:
            self._write(root, "missing.md", "type: Function Requirement\n")
            result = OKFBundle(root).validate()
        self.assertFalse(result["ok"])
        self.assertTrue(any("missing required frontmatter key `status`" in item for item in result["errors"]))

    def test_validate_rejects_missing_type(self) -> None:
        tmp, root = self._bundle()
        with tmp:
            self._write(root, "missing-type.md", "status: draft\n")
            result = OKFBundle(root).validate()
        self.assertFalse(result["ok"])
        self.assertTrue(any("missing required frontmatter key `type`" in item for item in result["errors"]))

    def test_validate_rejects_invalid_status(self) -> None:
        tmp, root = self._bundle()
        with tmp:
            self._write(root, "invalid.md", "type: Function Requirement\nstatus: done\n")
            result = OKFBundle(root).validate()
        self.assertFalse(result["ok"])
        self.assertTrue(any("invalid status `done`" in item for item in result["errors"]))

    def test_validate_rejects_unmapped_type(self) -> None:
        tmp, root = self._bundle()
        with tmp:
            self._write(root, "unknown.md", "type: Unknown Artifact\nstatus: draft\n")
            result = OKFBundle(root).validate()
        self.assertFalse(result["ok"])
        self.assertTrue(any("unmapped concept type `Unknown Artifact`" in item for item in result["errors"]))

    def test_write_concept_rejects_invalid_merged_frontmatter(self) -> None:
        tmp, root = self._bundle()
        with tmp:
            bundle = OKFBundle(root)
            bundle.write_concept(
                "reqs/valid",
                {"type": "Function Requirement", "status": "draft", "x-extra": "preserved"},
                "Body.",
            )
            with self.assertRaises(OKFError):
                bundle.write_concept("reqs/valid", {"status": "done"}, "Body.", merge_frontmatter=True)
            raw = (root / "reqs" / "valid.md").read_text(encoding="utf-8")
            self.assertIn("x-extra: preserved", raw)
            self.assertIn("status: draft", raw)

    def test_validate_7d_reuses_frontmatter_validation(self) -> None:
        tmp, root = self._bundle()
        with tmp:
            self._write(root, "missing.md", "type: Function Requirement\n")
            result = OKFBundle(root).validate_7d()
        self.assertFalse(result["ok"])
        self.assertTrue(any("missing required frontmatter key `status`" in item for item in result["errors"]))

    def test_validate_7d_rejects_missing_type(self) -> None:
        tmp, root = self._bundle()
        with tmp:
            self._write(root, "missing-type.md", "status: draft\n")
            result = OKFBundle(root).validate_7d()
        self.assertFalse(result["ok"])
        self.assertTrue(any("missing required frontmatter key `type`" in item for item in result["errors"]))

    def test_cli_help_lists_multi_app_commands(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "okf_mcp", "--help"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        for command in ("server", "validate", "indexes", "graph", "rag", "7d"):
            self.assertIn(command, output)

    def test_cli_option_first_invocation_keeps_legacy_server_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "okf_mcp", "--bundle", "okf", "--help"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        output = result.stdout + result.stderr
        self.assertIn("--transport", output)
        self.assertIn("--bundle", output)
        self.assertNotIn("validate", output)
        self.assertNotIn("indexes", output)

    def test_cli_invalid_usage_reports_click_error_without_traceback(self) -> None:
        cases = [
            [sys.executable, "-m", "okf_mcp", "validate", "--unknown"],
            [sys.executable, "-m", "okf_mcp", "rag", "retrieve"],
            [sys.executable, "-m", "okf_mcp", "rag", "refresh", "--mode", "bad"],
        ]
        for command in cases:
            with self.subTest(command=command):
                result = subprocess.run(command, text=True, capture_output=True, check=False)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("Traceback", result.stderr + result.stdout)

    def test_cli_validate_reports_temp_bundle_failure(self) -> None:
        tmp, root = self._bundle()
        with tmp:
            self._write(root, "missing-type.md", "status: draft\n")
            result = subprocess.run(
                [sys.executable, "-m", "okf_mcp", "validate", str(root)],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing required frontmatter key `type`", result.stderr)

    def test_cli_validate_reports_temp_bundle_success(self) -> None:
        tmp, root = self._bundle()
        with tmp:
            self._write(root, "valid.md", "type: Function Requirement\nstatus: draft\n")
            result = subprocess.run(
                [sys.executable, "-m", "okf_mcp", "validate", str(root)],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Validated 1 concept file", result.stdout)
        self.assertIn("OK: 0 error", result.stdout)

    def test_legacy_validate_entrypoint_wrapper_returns_status_code(self) -> None:
        from okf_mcp import cli

        import contextlib
        import io

        tmp, root = self._bundle()
        with tmp, contextlib.redirect_stdout(io.StringIO()):
            self._write(root, "valid.md", "type: Function Requirement\nstatus: draft\n")
            self.assertEqual(cli.validate_main([str(root)]), 0)

    def test_cli_graph_writes_json_and_html(self) -> None:
        tmp, root = self._bundle()
        with tmp:
            self._write(root, "valid.md", "type: Function Requirement\nstatus: draft\n")
            out = Path(tmp.name) / "artifacts" / "graph.json"
            html_out = Path(tmp.name) / "artifacts" / "graph.html"
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "okf_mcp",
                    "graph",
                    str(root),
                    "--out",
                    str(out),
                    "--html-out",
                    str(html_out),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.exists())
            self.assertTrue(html_out.exists())


if __name__ == "__main__":
    unittest.main()
