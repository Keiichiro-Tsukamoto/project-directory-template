#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("context_snapshot.py")
SPEC = importlib.util.spec_from_file_location("context_snapshot", MODULE_PATH)
assert SPEC and SPEC.loader
SNAPSHOT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SNAPSHOT)


class ContextSnapshotTest(unittest.TestCase):
    def make_workspace(self, root: Path) -> None:
        for directory in ("_control", "wip/T-001/.tmp", "current"):
            (root / directory).mkdir(parents=True, exist_ok=True)
        (root / "_control/project.md").write_text("# Project\n", encoding="utf-8")
        (root / "_control/rules.md").write_text("# Rules\n", encoding="utf-8")
        (root / "_control/tasks.md").write_text(
            "# Tasks\n\n| Task ID | Name | Status | Detail |\n"
            "|---|---|---|---|\n"
            "| T-001 | Test | active | wip/T-001_test.md |\n",
            encoding="utf-8",
        )
        (root / "_control/context.md").write_text(
            "# Context\n\n| Task ID | File |\n|---|---|\n"
            "| T-001 | current/input.md |\n",
            encoding="utf-8",
        )
        (root / "wip/T-001_test.md").write_text("# Task\n", encoding="utf-8")
        (root / "current/input.md").write_text("input v1\n", encoding="utf-8")
        (root / "wip/T-001/output.md").write_text("output v1\n", encoding="utf-8")
        (root / "wip/T-001/.tmp/cache.bin").write_bytes(b"cache")
        (root / "unrelated.md").write_text("not in scope\n", encoding="utf-8")

    def test_scope_excludes_transient_and_unrelated_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self.make_workspace(root)
            task_id, detail = SNAPSHOT.select_task(root, None)
            result = SNAPSHOT.build_snapshot(root, task_id, detail)
            files = result["files"]
            self.assertIn("wip/T-001/output.md", files)
            self.assertNotIn("wip/T-001/.tmp/cache.bin", files)
            self.assertNotIn("unrelated.md", files)

    def test_compare_detects_added_modified_and_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self.make_workspace(root)
            task_id, detail = SNAPSHOT.select_task(root, None)
            before = SNAPSHOT.build_snapshot(root, task_id, detail)
            (root / "current/input.md").write_text("input v2\n", encoding="utf-8")
            (root / "wip/T-001/output.md").unlink()
            (root / "wip/T-001/new.md").write_text("new\n", encoding="utf-8")
            after = SNAPSHOT.build_snapshot(root, task_id, detail)
            changes = SNAPSHOT.compare(before, after)
            self.assertTrue(changes["changed"])
            self.assertEqual(changes["added"], ["wip/T-001/new.md"])
            self.assertIn("current/input.md", changes["modified"])
            self.assertEqual(changes["deleted"], ["wip/T-001/output.md"])

    def test_unchanged_snapshot_matches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            self.make_workspace(root)
            task_id, detail = SNAPSHOT.select_task(root, None)
            before = SNAPSHOT.build_snapshot(root, task_id, detail)
            after = SNAPSHOT.build_snapshot(root, task_id, detail)
            self.assertFalse(SNAPSHOT.compare(before, after)["changed"])


if __name__ == "__main__":
    unittest.main()
