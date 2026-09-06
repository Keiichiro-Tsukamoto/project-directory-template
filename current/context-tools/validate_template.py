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
EXTERNAL_FIELDS_V2 = (
    "スキーマ版",
    "サービス",
    "ワークスペース",
    "リソース種別",
    "リソースID",
    "ロケーター",
    "変更性",
    "取得モード",
    "期待するリビジョン",
    "取得範囲",
    "鮮度確認方法",
    "キャッシュ再利用",
    "検証不能時",
    "ローカルスナップショット",
    "代替手段",
    "ローカル保存",
    "Git登録",
    "アクセス上の注意",
)
NONEMPTY_EXTERNAL_FIELDS_V2 = (
    "スキーマ版",
    "サービス",
    "ワークスペース",
    "リソース種別",
    "リソースID",
    "変更性",
    "取得モード",
    "取得範囲",
    "鮮度確認方法",
    "キャッシュ再利用",
    "検証不能時",
    "代替手段",
    "ローカル保存",
    "Git登録",
)
EXTERNAL_FIELDS_V3 = (
    "スキーマ版",
    "サービス",
    "ワークスペース",
    "リソースID",
    "ロケーター",
    "対象オブジェクト",
    "構造",
    "構成単位",
    "構成規則",
    "変更性",
    "取得モード",
    "期待するリビジョン",
    "鮮度確認方法",
    "キャッシュ再利用",
    "検証不能時",
    "ローカルスナップショット",
    "ローカル保存",
    "Git登録",
    "アクセス上の注意",
)
NONEMPTY_EXTERNAL_FIELDS_V3 = tuple(
    field
    for field in EXTERNAL_FIELDS_V3
    if field
    not in {
        "ロケーター",
        "期待するリビジョン",
        "ローカルスナップショット",
        "アクセス上の注意",
    }
)
V3_LEGACY_FIELDS = {"リソース種別", "取得範囲", "代替手段"}
ALLOWED_EXTERNAL_STRUCTURES = {
    "atomic",
    "composite",
    "fixed-collection",
    "dynamic-collection",
}
ALLOWED_RETRIEVAL_MODES = {"live", "pinned", "snapshot"}
ALLOWED_MUTABILITY = {"mutable", "immutable"}
ALLOWED_FRESHNESS_METHODS = {
    "revision",
    "updated-at",
    "content-hash",
    "refetch",
    "not-applicable",
}
ALLOWED_CACHE_REUSE = {"禁止", "同一版確認時のみ", "固定スナップショットのみ"}
ALLOWED_UNVERIFIABLE_ACTIONS = {"停止", "登録スナップショットを旧版として使用"}
ALLOWED_FALLBACKS = {"none", "local-snapshot"}
ALLOWED_STORAGE_VALUES = {"許可", "禁止", "要承認"}
SECRET_PATTERN = re.compile(
    r"(?i)(access[_-]?token|session[_-]?(?:id|token)|x-amz-signature|"
    r"[?&](?:token|sig|signature)=)[^\s<]*"
)


def table_rows(path: Path, columns: int) -> list[list[str]]:
    rows: list[list[str]] = []
    if not path.is_file():
        return rows
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


def descriptor_field_names(path: Path) -> list[str]:
    names: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^- ([^:：]+)[:：]\s*(.*)$", line)
        if match:
            names.append(match.group(1).strip())
    return names


def is_external_descriptor(path: Path, task_id: str) -> bool:
    approved_location = (
        len(path.parts) >= 3
        and path.parts[0:2] == ("reference", "external")
    ) or (
        len(path.parts) >= 5
        and path.parts[0:2] == ("wip", task_id)
        and path.parts[2:4] == ("reference", "external")
    )
    return approved_location and path.suffix == ".md" and not path.name.startswith("_")


def safe_relative_path(value: str) -> tuple[Path, bool]:
    path = Path(value)
    safe = bool(value) and not path.is_absolute() and ".." not in path.parts
    return path, safe


def path_within_root(root: Path, path: Path) -> bool:
    try:
        (root / path).resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


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
        detail_within_root = detail_is_relative and path_within_root(root, detail_path)
        record(f"detail_path_relative:{task_id}", detail_is_relative, detail)
        record(f"detail_path_within_root:{task_id}", detail_within_root, detail)
        detail_exists = detail_within_root and (root / detail_path).is_file()
        record(
            f"detail_exists:{task_id}",
            detail_exists,
            detail,
        )
        expected_directory = "archive" if status == "done" else "wip"
        record(
            f"detail_location:{task_id}",
            bool(detail_path.parts) and detail_path.parts[0] == expected_directory,
            f"expected {expected_directory}/, got {detail}",
        )
        if status in {"active", "pending", "blocked"} and detail_exists:
            detail_content = (root / detail_path).read_text(encoding="utf-8")
            for heading in ("## Background", "## Purpose", "## Goal", "## Notes"):
                record(
                    f"detail_heading:{task_id}:{heading[3:]}",
                    heading in detail_content,
                    heading,
                )
    discarded_root = root / "archive/discarded"
    discarded_entries = list(discarded_root.iterdir()) if discarded_root.is_dir() else []
    invalid_discarded = sorted(
        path.name
        for path in discarded_entries
        if path.is_symlink() or not path.is_dir() or path.name not in task_ids
    )
    record(
        "discarded_entries_valid",
        not invalid_discarded,
        str(invalid_discarded),
    )

    contexts = table_rows(root / "_control/context.md", 2)
    context_pairs = [(task_id, file_path) for task_id, file_path in contexts]
    context_pair_set = set(context_pairs)
    record(
        "context_rows_unique",
        len(context_pairs) == len(context_pair_set),
        str(context_pairs),
    )
    discarded_contexts = sorted(
        file_path
        for _task_id, file_path in contexts
        if Path(file_path).parts[:2] == ("archive", "discarded")
    )
    record(
        "context_excludes_discarded",
        not discarded_contexts,
        str(discarded_contexts),
    )

    for task_id in sorted({task_id for task_id, _file_path in contexts}):
        record(f"context_task_exists:{task_id}", task_id in task_ids, task_id)
        record(
            f"context_task_not_done:{task_id}",
            task_id in task_statuses and task_statuses[task_id] != "done",
            task_statuses.get(task_id, "missing task"),
        )

    descriptors: list[tuple[str, Path, dict[str, str]]] = []
    for task_id, file_path in contexts:
        context_path, context_is_relative = safe_relative_path(file_path)
        context_within_root = context_is_relative and path_within_root(root, context_path)
        record(
            f"context_path_relative:{task_id}:{file_path}",
            context_is_relative,
            file_path,
        )
        record(
            f"context_path_within_root:{task_id}:{file_path}",
            context_within_root,
            file_path,
        )
        exists = context_within_root and (root / context_path).is_file()
        record(f"context_file_exists:{task_id}:{file_path}", exists, file_path)
        if exists and is_external_descriptor(context_path, task_id):
            descriptors.append(
                (task_id, context_path, descriptor_fields(root / context_path))
            )

    identity_paths: dict[tuple[str, str, str, str], set[str]] = {}
    for task_id, descriptor_path, fields in descriptors:
        label = descriptor_path.as_posix()
        descriptor = root / descriptor_path
        field_names = descriptor_field_names(descriptor)
        duplicate_fields = sorted(
            {name for name in field_names if field_names.count(name) > 1}
        )
        content = descriptor.read_text(encoding="utf-8")
        resource_heading_count = len(
            re.findall(r"^# 外部リソース:", content, flags=re.MULTILINE)
        )
        record(
            f"external_single_resource_heading:{label}",
            resource_heading_count == 1,
            f"count={resource_heading_count}",
        )
        record(
            f"external_fields_unique:{label}",
            not duplicate_fields,
            f"duplicates={duplicate_fields}",
        )
        schema_version = fields.get("スキーマ版", "")
        expected_fields = (
            EXTERNAL_FIELDS_V3 if schema_version == "3" else EXTERNAL_FIELDS_V2
        )
        required_fields = (
            NONEMPTY_EXTERNAL_FIELDS_V3
            if schema_version == "3"
            else NONEMPTY_EXTERNAL_FIELDS_V2
        )
        missing = [field for field in expected_fields if field not in fields]
        record(
            f"external_fields_present:{label}",
            not missing,
            f"missing={missing}",
        )
        empty = [field for field in required_fields if not fields.get(field)]
        record(
            f"external_required_values:{label}",
            not empty,
            f"empty={empty}",
        )

        mutability = fields.get("変更性", "")
        mode = fields.get("取得モード", "")
        freshness_method = fields.get("鮮度確認方法", "")
        cache_reuse = fields.get("キャッシュ再利用", "")
        unverifiable_action = fields.get("検証不能時", "")
        fallback = fields.get("代替手段", "")
        structure = fields.get("構造", "")
        component_unit = fields.get("構成単位", "")
        component_rule = fields.get("構成規則", "")
        local_storage = fields.get("ローカル保存", "")
        git_tracking = fields.get("Git登録", "")
        record(
            f"external_schema_version:{label}",
            schema_version in {"2", "3"},
            schema_version,
        )
        if schema_version == "3":
            legacy_fields = sorted(V3_LEGACY_FIELDS.intersection(fields))
            record(
                f"external_v3_legacy_fields_absent:{label}",
                not legacy_fields,
                f"legacy_fields={legacy_fields}",
            )
            record(
                f"external_structure_allowed:{label}",
                structure in ALLOWED_EXTERNAL_STRUCTURES,
                structure,
            )
            atomic_shape = component_unit == "なし" and component_rule == "なし"
            record(
                f"external_structure_components:{label}",
                atomic_shape
                if structure == "atomic"
                else component_unit not in {"", "なし"}
                and component_rule not in {"", "なし"},
                f"structure={structure}, unit={component_unit}, rule={component_rule}",
            )
        record(
            f"external_mutability_allowed:{label}",
            mutability in ALLOWED_MUTABILITY,
            mutability,
        )
        record(
            f"external_mode_allowed:{label}",
            mode in ALLOWED_RETRIEVAL_MODES,
            mode,
        )
        record(
            f"external_freshness_method_allowed:{label}",
            freshness_method in ALLOWED_FRESHNESS_METHODS,
            freshness_method,
        )
        record(
            f"external_cache_reuse_allowed:{label}",
            cache_reuse in ALLOWED_CACHE_REUSE,
            cache_reuse,
        )
        record(
            f"external_unverifiable_action_allowed:{label}",
            unverifiable_action in ALLOWED_UNVERIFIABLE_ACTIONS,
            unverifiable_action,
        )
        if schema_version != "3":
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
        record(
            f"external_snapshot_freshness:{label}",
            (mode == "snapshot") == (freshness_method == "not-applicable"),
            f"mode={mode}, freshness={freshness_method}",
        )
        record(
            f"external_snapshot_cache_policy:{label}",
            (mode == "snapshot") == (cache_reuse == "固定スナップショットのみ"),
            f"mode={mode}, cache={cache_reuse}",
        )
        record(
            f"external_refetch_cache_policy:{label}",
            freshness_method != "refetch" or cache_reuse == "禁止",
            f"freshness={freshness_method}, cache={cache_reuse}",
        )
        record(
            f"external_live_or_pinned_cache_policy:{label}",
            mode not in {"live", "pinned"}
            or cache_reuse in {"禁止", "同一版確認時のみ"},
            f"mode={mode}, cache={cache_reuse}",
        )
        registered_snapshot_fallback = (
            unverifiable_action == "登録スナップショットを旧版として使用"
        )
        if schema_version != "3":
            record(
                f"external_fallback_unverifiable_consistency:{label}",
                (fallback == "local-snapshot") == registered_snapshot_fallback,
                f"fallback={fallback}, unverifiable={unverifiable_action}",
            )
        record(
            f"external_snapshot_fallback_not_redundant:{label}",
            mode != "snapshot" or not registered_snapshot_fallback,
            f"mode={mode}, unverifiable={unverifiable_action}",
        )

        record(
            f"external_no_obvious_secret:{label}",
            SECRET_PATTERN.search(content) is None,
            "no token, session, or signed-URL pattern",
        )

        identity_fields = ["サービス", "ワークスペース", "リソースID"]
        identity = tuple(fields.get(field, "") for field in identity_fields)
        if all(identity):
            identity_paths.setdefault(identity, set()).add(label)

        needs_snapshot = mode == "snapshot" or registered_snapshot_fallback
        snapshot_value = fields.get("ローカルスナップショット", "")
        snapshot_path, snapshot_is_relative = safe_relative_path(snapshot_value)
        snapshot_within_root = snapshot_is_relative and path_within_root(
            root, snapshot_path
        )
        record(
            f"external_snapshot_path:{label}",
            not needs_snapshot or snapshot_within_root,
            snapshot_value,
        )
        snapshot_exists = snapshot_within_root and (root / snapshot_path).is_file()
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
    for identity, paths in identity_paths.items():
        record(
            "external_identity_unique:" + "/".join(identity),
            len(paths) == 1,
            str(sorted(paths)),
        )

    project_path = root / "_control/project.md"
    project = project_path.read_text(encoding="utf-8") if project_path.is_file() else ""
    for heading in ("## Background", "## Purpose", "## Goal"):
        record(f"project_heading:{heading[3:]}", heading in project, heading)

    failures = [check for check in checks if not check["passed"]]
    return {
        "root": str(root),
        "passed": not failures,
        "checks": len(checks),
        "check_types": len({str(check["check"]).split(":", 1)[0] for check in checks}),
        "failures": len(failures),
        "warnings": len(warnings),
        "warning_details": warnings,
        "details": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="全検査詳細を標準出力へ表示する",
    )
    args = parser.parse_args()

    result = validate(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if args.verbose:
        console_result = result
    else:
        console_result = {
            key: result[key]
            for key in (
                "root",
                "passed",
                "checks",
                "check_types",
                "failures",
                "warnings",
            )
        }
        console_result["output"] = str(args.output)
    print(json.dumps(console_result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
