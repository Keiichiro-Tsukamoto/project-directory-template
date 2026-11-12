"""Existing v2/v3 descriptor checks shared by legacy and workspace validators.

Field lists and conditions are extracted unchanged from validate_template.py.
Only path resolution, registered snapshot matching and identity scope are
injected by the workspace adapter; this module never scans unregistered files.
"""
from pathlib import Path
import re

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


def validate_descriptors(root, descriptors, context_pair_set, record, warn, *,
                         resolve_snapshot=None, snapshot_mapped=None, identity_scope=None):
    identity_paths: dict[tuple[str, ...], set[str]] = {}
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
            identity_paths.setdefault((identity_scope(task_id, descriptor_path), *identity) if identity_scope else identity, set()).add(label)

        needs_snapshot = mode == "snapshot" or registered_snapshot_fallback
        snapshot_value = fields.get("ローカルスナップショット", "")
        if resolve_snapshot is None:
            snapshot_path, snapshot_is_relative = safe_relative_path(snapshot_value)
            snapshot_within_root = snapshot_is_relative and path_within_root(root, snapshot_path)
        else:
            snapshot_path, snapshot_within_root = resolve_snapshot(descriptor_path, snapshot_value)
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
            or (snapshot_mapped(task_id, snapshot_path) if snapshot_mapped else
                (task_id, snapshot_path.as_posix()) in context_pair_set),
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



def has_descriptor_heading(path):
    if path.suffix.lower() != '.md' or path.name.startswith('_'):
        return False
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            if line.strip():
                return line.startswith('# 外部リソース:')
    return False
