#!/usr/bin/env python3
"""Create or compare a task-scoped SHA-256 snapshot without scanning the workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


CONTROL_FILES = (
    "_control/project.md",
    "_control/tasks.md",
    "_control/context.md",
    "_control/rules.md",
)
TASK_ID_PATTERN = re.compile(r"^T-\d+$")


def table_rows(path: Path, columns: int) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != columns or cells[0] == "Task ID":
            continue
        if all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        rows.append(cells)
    return rows


def select_task(root: Path, requested: str | None) -> tuple[str, str]:
    tasks = table_rows(root / "_control/tasks.md", 4)
    if requested:
        if not TASK_ID_PATTERN.match(requested):
            raise ValueError(f"invalid Task ID: {requested}")
        matches = [row for row in tasks if row[0] == requested]
    else:
        matches = [row for row in tasks if row[2] == "active"]
    if len(matches) != 1:
        raise ValueError(f"expected one task, found {len(matches)}")
    return matches[0][0], matches[0][3]


def safe_file(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"path must be relative and remain in workspace: {relative}")
    absolute = (root / candidate).resolve()
    try:
        absolute.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"path escapes workspace: {relative}") from error
    if not absolute.is_file() or absolute.is_symlink():
        raise ValueError(f"not a regular file: {relative}")
    return absolute


def task_scope(root: Path, task_id: str, detail: str) -> list[Path]:
    paths: dict[str, Path] = {}

    def add(relative: str) -> None:
        path = safe_file(root, relative)
        paths[path.relative_to(root.resolve()).as_posix()] = path

    for relative in CONTROL_FILES:
        add(relative)
    add(detail)

    for context_task, relative in table_rows(root / "_control/context.md", 2):
        if context_task == task_id:
            add(relative)

    output_directory = root / "wip" / task_id
    if output_directory.is_dir():
        for path in output_directory.rglob("*"):
            relative_parts = path.relative_to(output_directory).parts
            if ".tmp" in relative_parts or path.is_symlink() or not path.is_file():
                continue
            relative = path.relative_to(root).as_posix()
            add(relative)

    return [paths[key] for key in sorted(paths)]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_snapshot(root: Path, task_id: str, detail: str) -> dict[str, object]:
    files: dict[str, dict[str, object]] = {}
    for path in task_scope(root, task_id, detail):
        relative = path.relative_to(root.resolve()).as_posix()
        files[relative] = {"size": path.stat().st_size, "sha256": sha256(path)}

    aggregate = hashlib.sha256()
    for relative, metadata in files.items():
        aggregate.update(
            f"{relative}\0{metadata['size']}\0{metadata['sha256']}\n".encode("utf-8")
        )
    return {
        "version": 1,
        "task_id": task_id,
        "aggregate_sha256": aggregate.hexdigest(),
        "files": files,
    }


def compare(previous: dict[str, object], current: dict[str, object]) -> dict[str, object]:
    previous_files = previous["files"]
    current_files = current["files"]
    assert isinstance(previous_files, dict) and isinstance(current_files, dict)
    previous_paths = set(previous_files)
    current_paths = set(current_files)
    modified = sorted(
        path
        for path in previous_paths & current_paths
        if previous_files[path] != current_files[path]
    )
    return {
        "changed": previous.get("aggregate_sha256") != current.get("aggregate_sha256"),
        "added": sorted(current_paths - previous_paths),
        "modified": modified,
        "deleted": sorted(previous_paths - current_paths),
    }


def state_path(root: Path, task_id: str, requested: str | None) -> Path:
    if requested:
        path = Path(requested)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("state path must be relative to workspace")
        return root / path
    return root / "wip/.context-state" / f"{task_id}.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("snapshot", "check"))
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--task")
    parser.add_argument("--state")
    args = parser.parse_args()

    root = args.root.resolve()
    task_id, detail = select_task(root, args.task)
    snapshot = build_snapshot(root, task_id, detail)
    state = state_path(root, task_id, args.state)

    if args.command == "snapshot":
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({"saved": str(state), **snapshot}, ensure_ascii=False, indent=2))
        return 0

    if not state.is_file():
        raise ValueError(f"snapshot not found: {state}")
    previous = json.loads(state.read_text(encoding="utf-8"))
    result = compare(previous, snapshot)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["changed"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
