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


if __name__ == "__main__":
    unittest.main()
