#!/usr/bin/env python3
"""Static consistency checks for a project directory template."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REQUIRED_DIRECTORIES = ("_control", "wip", "current", "reference", "archive")
REQUIRED_CONTROL_FILES = ("project.md", "tasks.md", "context.md", "rules.md")
ALLOWED_STATUSES = {"pending", "active", "blocked", "done"}
EXTERNAL_FIELDS = (
    "サービス",
    "ワークスペース",
    "リソース種別",
    "リソースID",
    "ロケーター",
    "取得モード",
    "期待するリビジョン",
    "取得範囲",
    "ローカルスナップショット",
    "代替手段",
    "ローカル保存",
    "Git登録",
    "アクセス上の注意",
)
NONEMPTY_EXTERNAL_FIELDS = (
    "サービス",
    "ワークスペース",
    "リソース種別",
    "リソースID",
    "取得モード",
    "取得範囲",
    "代替手段",
    "ローカル保存",
    "Git登録",
)
ALLOWED_RETRIEVAL_MODES = {"live", "pinned", "snapshot"}
ALLOWED_FALLBACKS = {"none", "local-snapshot"}
ALLOWED_STORAGE_VALUES = {"許可", "禁止", "要承認"}
SECRET_PATTERN = re.compile(
    r"(?i)(access[_-]?token|session[_-]?(?:id|token)|x-amz-signature|"
    r"[?&](?:token|sig|signature)=)[^\s<]*"
)


def table_rows(path: Path, columns: int) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != columns or cells[0] in {"Task ID", "---"}:
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        rows.append(cells)
    return rows


def descriptor_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^- ([^:：]+)[:：]\s*(.*)$", line)
        if match:
            fields[match.group(1).strip()] = match.group(2).strip()
    return fields


def is_external_descriptor(path: Path) -> bool:
    return (
        len(path.parts) >= 3
        and path.parts[0:2] == ("reference", "external")
        and path.suffix == ".md"
        and not path.name.startswith("_")
    )


def safe_relative_path(value: str) -> tuple[Path, bool]:
    path = Path(value)
    safe = bool(value) and not path.is_absolute() and ".." not in path.parts
    return path, safe


def validate(root: Path) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    warnings: list[dict[str, str]] = []

    def record(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "passed": passed, "detail": detail})

    def warn(name: str, detail: str) -> None:
        warnings.append({"warning": name, "detail": detail})

    for directory in REQUIRED_DIRECTORIES:
        record(
            f"directory:{directory}",
            (root / directory).is_dir(),
            f"{directory}/ exists",
        )
    for filename in REQUIRED_CONTROL_FILES:
        record(
            f"control_file:{filename}",
            (root / "_control" / filename).is_file(),
            f"_control/{filename} exists",
        )

    tasks = table_rows(root / "_control/tasks.md", 4)
    task_ids = [row[0] for row in tasks]
    task_statuses = {row[0]: row[2] for row in tasks}
    statuses = [row[2] for row in tasks]
    active_count = statuses.count("active")
    record("task_ids_unique", len(task_ids) == len(set(task_ids)), str(task_ids))
    record(
        "statuses_allowed",
        all(status in ALLOWED_STATUSES for status in statuses),
        str(statuses),
    )
    record("active_at_most_one", active_count <= 1, f"active={active_count}")

    for task_id, _name, status, detail in tasks:
        detail_path, detail_is_relative = safe_relative_path(detail)
        record(f"detail_path_relative:{task_id}", detail_is_relative, detail)
        record(
            f"detail_exists:{task_id}",
            detail_is_relative and (root / detail_path).is_file(),
            detail,
        )
        expected_directory = "archive" if status == "done" else "wip"
        record(
            f"detail_location:{task_id}",
            bool(detail_path.parts) and detail_path.parts[0] == expected_directory,
            f"expected {expected_directory}/, got {detail}",
        )

    contexts = table_rows(root / "_control/context.md", 2)
    context_pairs = [(task_id, file_path) for task_id, file_path in contexts]
    context_pair_set = set(context_pairs)
    record(
        "context_rows_unique",
        len(context_pairs) == len(context_pair_set),
        str(context_pairs),
    )

    descriptors: list[tuple[str, Path, dict[str, str]]] = []
    for task_id, file_path in contexts:
        context_path, context_is_relative = safe_relative_path(file_path)
        record(f"context_task_exists:{task_id}", task_id in task_ids, task_id)
        record(
            f"context_task_not_done:{task_id}:{file_path}",
            task_statuses.get(task_id) != "done",
            task_statuses.get(task_id, "missing task"),
        )
        record(
            f"context_path_relative:{task_id}:{file_path}",
            context_is_relative,
            file_path,
        )
        exists = context_is_relative and (root / context_path).is_file()
        record(f"context_file_exists:{task_id}:{file_path}", exists, file_path)
        if exists and is_external_descriptor(context_path):
            descriptors.append(
                (task_id, context_path, descriptor_fields(root / context_path))
            )

    identity_paths: dict[tuple[str, str, str, str], set[str]] = {}
    for task_id, descriptor_path, fields in descriptors:
        label = descriptor_path.as_posix()
        missing = [field for field in EXTERNAL_FIELDS if field not in fields]
        record(
            f"external_fields_present:{label}",
            not missing,
            f"missing={missing}",
        )
        empty = [field for field in NONEMPTY_EXTERNAL_FIELDS if not fields.get(field)]
        record(
            f"external_required_values:{label}",
            not empty,
            f"empty={empty}",
        )

        mode = fields.get("取得モード", "")
        fallback = fields.get("代替手段", "")
        local_storage = fields.get("ローカル保存", "")
        git_tracking = fields.get("Git登録", "")
        record(
            f"external_mode_allowed:{label}",
            mode in ALLOWED_RETRIEVAL_MODES,
            mode,
        )
        record(
            f"external_fallback_allowed:{label}",
            fallback in ALLOWED_FALLBACKS,
            fallback,
        )
        record(
            f"external_local_storage_allowed_value:{label}",
            local_storage in ALLOWED_STORAGE_VALUES,
            local_storage,
        )
        record(
            f"external_git_tracking_allowed_value:{label}",
            git_tracking in ALLOWED_STORAGE_VALUES,
            git_tracking,
        )
        record(
            f"external_pinned_revision:{label}",
            mode != "pinned" or bool(fields.get("期待するリビジョン")),
            fields.get("期待するリビジョン", ""),
        )

        content = (root / descriptor_path).read_text(encoding="utf-8")
        record(
            f"external_no_obvious_secret:{label}",
            SECRET_PATTERN.search(content) is None,
            "no token, session, or signed-URL pattern",
        )

        identity = tuple(
            fields.get(field, "")
            for field in ("サービス", "ワークスペース", "リソース種別", "リソースID")
        )
        if all(identity):
            identity_paths.setdefault(identity, set()).add(label)

        needs_snapshot = mode == "snapshot" or fallback == "local-snapshot"
        snapshot_value = fields.get("ローカルスナップショット", "")
        snapshot_path, snapshot_is_relative = safe_relative_path(snapshot_value)
        record(
            f"external_snapshot_path:{label}",
            not needs_snapshot or snapshot_is_relative,
            snapshot_value,
        )
        snapshot_exists = snapshot_is_relative and (root / snapshot_path).is_file()
        record(
            f"external_snapshot_exists:{label}",
            not needs_snapshot or snapshot_exists,
            snapshot_value,
        )
        record(
            f"external_snapshot_mapped:{label}",
            not needs_snapshot
            or (task_id, snapshot_path.as_posix()) in context_pair_set,
            f"{task_id}:{snapshot_value}",
        )
        record(
            f"external_snapshot_storage_not_forbidden:{label}",
            not needs_snapshot or local_storage != "禁止",
            local_storage,
        )
        if needs_snapshot and local_storage == "要承認":
            warn(
                f"external_snapshot_storage_requires_approval:{label}",
                "ローカルスナップショットの保存には人の明示承認が必要です。",
            )
        if snapshot_exists and git_tracking == "要承認":
            warn(
                f"external_snapshot_git_requires_approval:{label}",
                "スナップショットをGitへ登録する場合は人の明示承認が必要です。",
            )
        if snapshot_exists and git_tracking == "禁止":
            warn(
                f"external_snapshot_git_forbidden:{label}",
                "スナップショットをGitの追跡対象にしないでください。",
            )

    for identity, paths in identity_paths.items():
        record(
            "external_identity_unique:" + "/".join(identity),
            len(paths) == 1,
            str(sorted(paths)),
        )

    project = (root / "_control/project.md").read_text(encoding="utf-8")
    for heading in ("## Background", "## Purpose", "## Goal"):
        record(f"project_heading:{heading[3:]}", heading in project, heading)

    failures = [check for check in checks if not check["passed"]]
    return {
        "root": str(root),
        "passed": not failures,
        "checks": len(checks),
        "failures": len(failures),
        "warnings": len(warnings),
        "warning_details": warnings,
        "details": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = validate(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
