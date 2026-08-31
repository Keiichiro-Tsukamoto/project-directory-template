#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("validate_template.py")
SPEC = importlib.util.spec_from_file_location("validate_template", MODULE_PATH)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class TemplateValidationTest(unittest.TestCase):
    development_template = Path.cwd() / "current/project_directory_template"
    installed_project = Path(__file__).resolve().parents[2]
    source = (
        development_template
        if development_template.is_dir()
        else installed_project
    )

    def copy_template(self, target: Path) -> Path:
        root = target / "template"
        for directory in ("_control", "wip", "current", "reference", "archive"):
            (root / directory).mkdir(parents=True, exist_ok=True)
        (root / "_control/project.md").write_text(
            "# Project\n\n## Background\n\nTest.\n\n"
            "## Purpose\n\nTest.\n\n## Goal\n\nTest.\n",
            encoding="utf-8",
        )
        (root / "_control/tasks.md").write_text(
            "# Tasks\n\n## Task List\n\n"
            "| Task ID | Name | Status | Detail |\n"
            "|---|---|---|---|\n"
            "| T-001 | Test | active | wip/T-001_initialize_project.md |\n",
            encoding="utf-8",
        )
        (root / "_control/context.md").write_text(
            "# Context\n\n| Task ID | File |\n|---|---|\n",
            encoding="utf-8",
        )
        (root / "_control/rules.md").write_text("# Rules\n", encoding="utf-8")
        (root / "wip/T-001_initialize_project.md").write_text(
            "# Task\n\n## Background\n\nTest.\n\n"
            "## Purpose\n\nTest.\n\n## Goal\n\nTest.\n\n"
            "## Notes\n\nTest.\n",
            encoding="utf-8",
        )
        return root

    @staticmethod
    def failed_checks(result: dict[str, object]) -> set[str]:
        return {
            str(item["check"])
            for item in result["details"]
            if not item["passed"]
        }

    @staticmethod
    def descriptor(**overrides: str) -> str:
        values = {
            "スキーマ版": "2",
            "サービス": "example-service",
            "ワークスペース": "workspace-1",
            "リソース種別": "document",
            "リソースID": "document-1",
            "ロケーター": "https://example.invalid/document-1",
            "変更性": "mutable",
            "取得モード": "live",
            "期待するリビジョン": "",
            "取得範囲": "本文全体",
            "鮮度確認方法": "revision",
            "キャッシュ再利用": "同一版確認時のみ",
            "検証不能時": "停止",
            "ローカルスナップショット": "",
            "代替手段": "none",
            "ローカル保存": "要承認",
            "Git登録": "要承認",
            "アクセス上の注意": "",
        }
        values.update(overrides)
        body = "\n".join(f"- {key}: {value}" for key, value in values.items())
        return f"# 外部リソース: テスト資料\n\n{body}\n"

    def add_descriptor(
        self,
        root: Path,
        content: str,
        name: str = "test-resource.md",
        extra_context: str = "",
    ) -> Path:
        relative = Path("reference/external") / name
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        context = root / "_control/context.md"
        context.write_text(
            context.read_text(encoding="utf-8")
            + f"| T-001 | {relative.as_posix()} |\n"
            + extra_context,
            encoding="utf-8",
        )
        return path

    def test_current_template_passes(self) -> None:
        result = VALIDATOR.validate(self.source)
        self.assertTrue(result["passed"])

    def test_synthetic_fixture_passes_without_source_task_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            result = VALIDATOR.validate(root)
            self.assertTrue(result["passed"], self.failed_checks(result))
            tasks = (root / "_control/tasks.md").read_text(encoding="utf-8")
            self.assertIn("| T-001 | Test | active |", tasks)

    def test_duplicate_context_row_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            context = root / "_control/context.md"
            row = "| T-001 | _control/project.md |\n"
            context.write_text(context.read_text() + row + row, encoding="utf-8")
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn("context_rows_unique", failures)

    def test_duplicate_task_id_and_invalid_status_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            tasks = root / "_control/tasks.md"
            original = tasks.read_text(encoding="utf-8")
            duplicate = "| T-001 | Duplicate | pending | wip/T-001_initialize_project.md |\n"
            tasks.write_text(
                original.replace("| active |", "| invalid |") + duplicate,
                encoding="utf-8",
            )
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn("task_ids_unique", failures)
            self.assertIn("statuses_allowed", failures)

    def test_multiple_active_tasks_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            detail = root / "wip/T-002_test.md"
            detail.write_text(
                "# Task\n\n## Background\n\n## Purpose\n\n## Goal\n\n## Notes\n",
                encoding="utf-8",
            )
            tasks = root / "_control/tasks.md"
            tasks.write_text(
                tasks.read_text(encoding="utf-8")
                + "| T-002 | Test | active | wip/T-002_test.md |\n",
                encoding="utf-8",
            )
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn("active_at_most_one", failures)

    def test_unknown_task_and_missing_context_file_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            context = root / "_control/context.md"
            context.write_text(
                context.read_text(encoding="utf-8")
                + "| T-999 | current/missing.md |\n",
                encoding="utf-8",
            )
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn("context_task_exists:T-999", failures)
            self.assertIn("context_task_not_done:T-999", failures)
            self.assertIn(
                "context_file_exists:T-999:current/missing.md", failures
            )

    def test_missing_required_directory_and_control_file_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            shutil.rmtree(root / "archive")
            (root / "_control/project.md").unlink()
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn("directory:archive", failures)
            self.assertIn("control_file:project.md", failures)
            self.assertIn("project_heading:Background", failures)

    def test_done_task_detail_context_and_discarded_state_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            tasks = root / "_control/tasks.md"
            tasks.write_text(
                tasks.read_text().replace("| active |", "| done |"), encoding="utf-8"
            )
            context = root / "_control/context.md"
            discarded = root / "archive/discarded/T-999"
            discarded.mkdir(parents=True)
            (discarded / "cache.bin").write_bytes(b"cache")
            context.write_text(
                context.read_text()
                + "| T-001 | archive/discarded/T-999/cache.bin |\n",
                encoding="utf-8",
            )
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn("detail_location:T-001", failures)
            self.assertIn("context_task_not_done:T-001", failures)
            self.assertIn("context_excludes_discarded", failures)
            self.assertIn("discarded_entries_valid", failures)

    def test_absolute_context_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            context = root / "_control/context.md"
            context.write_text(
                context.read_text() + "| T-001 | /tmp/example.md |\n",
                encoding="utf-8",
            )
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn("context_path_relative:T-001:/tmp/example.md", failures)

    def test_parent_traversal_fails_for_context_and_detail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            tasks = root / "_control/tasks.md"
            tasks.write_text(
                tasks.read_text(encoding="utf-8").replace(
                    "wip/T-001_initialize_project.md", "../outside-detail.md"
                ),
                encoding="utf-8",
            )
            context = root / "_control/context.md"
            context.write_text(
                context.read_text(encoding="utf-8")
                + "| T-001 | ../outside-context.md |\n",
                encoding="utf-8",
            )
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn("detail_path_relative:T-001", failures)
            self.assertIn(
                "context_path_relative:T-001:../outside-context.md", failures
            )

    def test_symlink_escape_fails_for_context_and_detail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = self.copy_template(base)
            outside = base / "outside.md"
            outside.write_text(
                "# outside\n\n## Background\n\n## Purpose\n\n## Goal\n\n## Notes\n",
                encoding="utf-8",
            )

            context_link = root / "wip/context-link.md"
            context_link.symlink_to(outside)
            context = root / "_control/context.md"
            context.write_text(
                context.read_text(encoding="utf-8")
                + "| T-001 | wip/context-link.md |\n",
                encoding="utf-8",
            )

            detail_link = root / "wip/detail-link.md"
            detail_link.symlink_to(outside)
            tasks = root / "_control/tasks.md"
            original_detail = "wip/T-001_initialize_project.md"
            tasks.write_text(
                tasks.read_text(encoding="utf-8").replace(
                    original_detail, "wip/detail-link.md"
                ),
                encoding="utf-8",
            )

            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn(
                "context_path_within_root:T-001:wip/context-link.md", failures
            )
            self.assertIn("detail_path_within_root:T-001", failures)

    def test_active_task_detail_requires_four_headings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            detail = root / "wip/T-001_initialize_project.md"
            detail.write_text(
                detail.read_text(encoding="utf-8").replace("## Notes", "## Memo"),
                encoding="utf-8",
            )
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn("detail_heading:T-001:Notes", failures)

    def test_wip_external_descriptor_is_schema_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            relative = Path("wip/T-001/reference/external/test-resource.md")
            descriptor = root / relative
            descriptor.parent.mkdir(parents=True, exist_ok=True)
            descriptor.write_text(
                self.descriptor().replace("- スキーマ版: 2\n", ""),
                encoding="utf-8",
            )
            context = root / "_control/context.md"
            context.write_text(
                context.read_text(encoding="utf-8")
                + f"| T-001 | {relative.as_posix()} |\n",
                encoding="utf-8",
            )
            failures = self.failed_checks(VALIDATOR.validate(root))
            label = relative.as_posix()
            self.assertIn(f"external_fields_present:{label}", failures)
            self.assertIn(f"external_schema_version:{label}", failures)

    def test_context_task_checks_are_aggregated_by_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            context = root / "_control/context.md"
            context.write_text(
                context.read_text(encoding="utf-8")
                + "| T-001 | _control/project.md |\n"
                + "| T-001 | _control/rules.md |\n",
                encoding="utf-8",
            )
            checks = [
                str(item["check"])
                for item in VALIDATOR.validate(root)["details"]
            ]
            self.assertEqual(checks.count("context_task_exists:T-001"), 1)
            self.assertEqual(checks.count("context_task_not_done:T-001"), 1)

    def test_cli_is_concise_unless_verbose(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "validation.json"
            command = [
                sys.executable,
                str(MODULE_PATH),
                str(self.source),
                "--output",
                str(output),
            ]
            concise = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
            concise_result = json.loads(concise.stdout)
            full_result = json.loads(output.read_text(encoding="utf-8"))
            self.assertNotIn("details", concise_result)
            self.assertIn("details", full_result)
            self.assertEqual(concise_result["checks"], full_result["checks"])

            verbose = subprocess.run(
                command + ["--verbose"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("details", json.loads(verbose.stdout))

    def test_live_descriptor_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            self.add_descriptor(root, self.descriptor())
            result = VALIDATOR.validate(root)
            self.assertTrue(result["passed"], self.failed_checks(result))

    def test_missing_external_metadata_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            content = self.descriptor().replace("- ワークスペース: workspace-1\n", "")
            self.add_descriptor(root, content)
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn("external_fields_present:reference/external/test-resource.md", failures)

    def test_legacy_descriptor_without_schema_v2_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            content = self.descriptor().replace("- スキーマ版: 2\n", "")
            self.add_descriptor(root, content)
            failures = self.failed_checks(VALIDATOR.validate(root))
            label = "reference/external/test-resource.md"
            self.assertIn(f"external_fields_present:{label}", failures)
            self.assertIn(f"external_schema_version:{label}", failures)

    def test_multiple_resources_in_one_descriptor_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            first = self.descriptor()
            second = self.descriptor(
                **{"リソースID": "document-2"}
            ).replace("テスト資料", "テスト資料2", 1)
            self.add_descriptor(root, first + "\n" + second)
            failures = self.failed_checks(VALIDATOR.validate(root))
            label = "reference/external/test-resource.md"
            self.assertIn(f"external_single_resource_heading:{label}", failures)
            self.assertIn(f"external_fields_unique:{label}", failures)

    def test_pinned_without_revision_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            self.add_descriptor(root, self.descriptor(**{"取得モード": "pinned"}))
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn("external_pinned_revision:reference/external/test-resource.md", failures)

    def test_snapshot_must_exist_and_be_mapped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            self.add_descriptor(
                root,
                self.descriptor(
                    **{
                        "取得モード": "snapshot",
                        "鮮度確認方法": "not-applicable",
                        "キャッシュ再利用": "固定スナップショットのみ",
                        "ローカルスナップショット": "reference/snapshots/source.md",
                        "ローカル保存": "許可",
                    }
                ),
            )
            failures = self.failed_checks(VALIDATOR.validate(root))
            label = "reference/external/test-resource.md"
            self.assertIn(f"external_snapshot_exists:{label}", failures)
            self.assertIn(f"external_snapshot_mapped:{label}", failures)

    def test_snapshot_with_forbidden_local_storage_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            snapshot = root / "reference/snapshots/source.md"
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_text("snapshot\n", encoding="utf-8")
            self.add_descriptor(
                root,
                self.descriptor(
                    **{
                        "取得モード": "snapshot",
                        "鮮度確認方法": "not-applicable",
                        "キャッシュ再利用": "固定スナップショットのみ",
                        "ローカルスナップショット": "reference/snapshots/source.md",
                        "ローカル保存": "禁止",
                    }
                ),
                extra_context="| T-001 | reference/snapshots/source.md |\n",
            )
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn(
                "external_snapshot_storage_not_forbidden:reference/external/test-resource.md",
                failures,
            )

    def test_valid_snapshot_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            snapshot = root / "reference/snapshots/source.md"
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_text("snapshot\n", encoding="utf-8")
            self.add_descriptor(
                root,
                self.descriptor(
                    **{
                        "取得モード": "snapshot",
                        "鮮度確認方法": "not-applicable",
                        "キャッシュ再利用": "固定スナップショットのみ",
                        "ローカルスナップショット": "reference/snapshots/source.md",
                        "ローカル保存": "許可",
                    }
                ),
                extra_context="| T-001 | reference/snapshots/source.md |\n",
            )
            result = VALIDATOR.validate(root)
            self.assertTrue(result["passed"], self.failed_checks(result))

    def test_git_forbidden_snapshot_does_not_warn(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            snapshot = root / "reference/snapshots/source.md"
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_text("snapshot\n", encoding="utf-8")
            self.add_descriptor(
                root,
                self.descriptor(
                    **{
                        "取得モード": "snapshot",
                        "鮮度確認方法": "not-applicable",
                        "キャッシュ再利用": "固定スナップショットのみ",
                        "ローカルスナップショット": "reference/snapshots/source.md",
                        "ローカル保存": "許可",
                        "Git登録": "禁止",
                    }
                ),
                extra_context="| T-001 | reference/snapshots/source.md |\n",
            )
            result = VALIDATOR.validate(root)
            warning_names = {
                str(item["warning"]) for item in result["warning_details"]
            }
            self.assertTrue(result["passed"], self.failed_checks(result))
            self.assertFalse(
                any(name.startswith("external_snapshot_git_forbidden:") for name in warning_names)
            )

    def test_git_approval_snapshot_still_warns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            snapshot = root / "reference/snapshots/source.md"
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_text("snapshot\n", encoding="utf-8")
            self.add_descriptor(
                root,
                self.descriptor(
                    **{
                        "取得モード": "snapshot",
                        "鮮度確認方法": "not-applicable",
                        "キャッシュ再利用": "固定スナップショットのみ",
                        "ローカルスナップショット": "reference/snapshots/source.md",
                        "ローカル保存": "許可",
                        "Git登録": "要承認",
                    }
                ),
                extra_context="| T-001 | reference/snapshots/source.md |\n",
            )
            result = VALIDATOR.validate(root)
            warning_names = {
                str(item["warning"]) for item in result["warning_details"]
            }
            self.assertIn(
                "external_snapshot_git_requires_approval:reference/external/test-resource.md",
                warning_names,
            )

    def test_refetch_requires_cache_reuse_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            self.add_descriptor(
                root,
                self.descriptor(**{"鮮度確認方法": "refetch"}),
            )
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn(
                "external_refetch_cache_policy:reference/external/test-resource.md",
                failures,
            )

    def test_valid_refetch_without_cache_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            self.add_descriptor(
                root,
                self.descriptor(
                    **{
                        "鮮度確認方法": "refetch",
                        "キャッシュ再利用": "禁止",
                    }
                ),
            )
            result = VALIDATOR.validate(root)
            self.assertTrue(result["passed"], self.failed_checks(result))

    def test_local_snapshot_fallback_requires_matching_failure_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            snapshot = root / "reference/snapshots/source.md"
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_text("snapshot\n", encoding="utf-8")
            self.add_descriptor(
                root,
                self.descriptor(
                    **{
                        "代替手段": "local-snapshot",
                        "ローカルスナップショット": "reference/snapshots/source.md",
                        "ローカル保存": "許可",
                    }
                ),
                extra_context="| T-001 | reference/snapshots/source.md |\n",
            )
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn(
                "external_fallback_unverifiable_consistency:"
                "reference/external/test-resource.md",
                failures,
            )

    def test_valid_local_snapshot_fallback_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            snapshot = root / "reference/snapshots/source.md"
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_text("snapshot\n", encoding="utf-8")
            self.add_descriptor(
                root,
                self.descriptor(
                    **{
                        "検証不能時": "登録スナップショットを旧版として使用",
                        "代替手段": "local-snapshot",
                        "ローカルスナップショット": "reference/snapshots/source.md",
                        "ローカル保存": "許可",
                    }
                ),
                extra_context="| T-001 | reference/snapshots/source.md |\n",
            )
            result = VALIDATOR.validate(root)
            self.assertTrue(result["passed"], self.failed_checks(result))

    def test_duplicate_external_identity_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            self.add_descriptor(root, self.descriptor(), name="first.md")
            self.add_descriptor(root, self.descriptor(), name="second.md")
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertTrue(
                any(name.startswith("external_identity_unique:") for name in failures)
            )

    def test_signed_url_pattern_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            self.add_descriptor(
                root,
                self.descriptor(
                    # Deliberately fake signed URL used only to verify rejection;
                    # it contains no real endpoint or credential.
                    **{
                        "ロケーター":
                            "https://example.invalid/doc?X-Amz-Signature=test-signature"
                    }
                ),
            )
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn("external_no_obvious_secret:reference/external/test-resource.md", failures)


if __name__ == "__main__":
    unittest.main()
