#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import shutil
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
        shutil.copytree(self.source, root)
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

    def test_duplicate_context_row_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            context = root / "_control/context.md"
            row = "| T-001 | _control/project.md |\n"
            context.write_text(context.read_text() + row + row, encoding="utf-8")
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn("context_rows_unique", failures)

    def test_done_task_context_and_detail_location_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_template(Path(directory))
            tasks = root / "_control/tasks.md"
            tasks.write_text(
                tasks.read_text().replace("| active |", "| done |"), encoding="utf-8"
            )
            context = root / "_control/context.md"
            context.write_text(
                context.read_text() + "| T-001 | _control/project.md |\n",
                encoding="utf-8",
            )
            failures = self.failed_checks(VALIDATOR.validate(root))
            self.assertIn("detail_location:T-001", failures)
            self.assertTrue(
                any(name.startswith("context_task_not_done:T-001:") for name in failures)
            )

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
