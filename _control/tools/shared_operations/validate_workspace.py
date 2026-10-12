"""管理表・登録パスの読取専用検査。業務本文や未登録資料を走査しない。"""
import argparse
import json
from pathlib import Path

from dependency_model import Stopped, model_root, local_path, parse, check_pending
from source_model import table, project_directories


def validate(root):
    checked = 0
    try:
        root = model_root(root)
        check_pending(root / '_control')
        local_path(root, 'workspace:_control/rules.md')
        projects = project_directories(root)
        for project in [None, *projects]:
            scope = root / '_control' if project is None else project
            control = scope if project is None else scope / '_control'
            prefix = scope.relative_to(root).as_posix() + '/'
            def scoped(value, allow_workspace=True):
                if value.startswith('workspace:'):
                    if not allow_workspace:
                        raise Stopped('Detailは所有範囲内の相対パスが必要')
                    return local_path(root, value)
                return local_path(root, 'workspace:' + prefix + value)
            if project is not None:
                if not scoped('_control/project.md').is_file():
                    raise Stopped('project定義がファイルではない')
            tasks_path = local_path(root, 'workspace:' + (control / 'tasks.md').relative_to(root).as_posix())
            context_path = local_path(root, 'workspace:' + (control / 'context.md').relative_to(root).as_posix())
            tasks = table(tasks_path, ['Task ID', 'Name', 'Status', 'Detail'])
            states, details = {}, {}
            for tid, name, state, detail in tasks:
                if not tid or not name or tid in states or state not in ('pending', 'active', 'blocked', 'done'):
                    raise Stopped('Task ID・名称・状態が不正')
                path = scoped(detail, False)
                expected = scope / ('archive' if state == 'done' else 'wip')
                if not path.is_file() or not path.is_relative_to(expected):
                    raise Stopped('Task詳細の配置が状態と不整合')
                states[tid], details[tid] = state, path
                checked += 1
            if list(states.values()).count('active') > 1:
                raise Stopped('同一範囲にactiveが複数ある')
            seen = set()
            for tid, value in table(context_path, ['Task ID', 'File']):
                if tid not in states or states[tid] == 'done':
                    raise Stopped('contextとtasksが不整合')
                path = scoped(value)
                if not path.is_file() or path == details[tid] or (tid, path) in seen:
                    raise Stopped('入力がファイルでない、自タスク詳細の重複、または重複行')
                seen.add((tid, path))
                checked += 1
            checked += 1
        dependencies = local_path(root, 'workspace:_control/dependencies.md')
        rows = parse(root, dependencies.read_bytes())
        for consumer, source in rows:
            if consumer == source:
                raise Stopped('自己依存')
        checked += len(rows) + 1
        return {'passed': True, 'checked': checked, 'projects': len(projects),
                'scope': '管理表の形式・状態・配置・登録先の実在。内容の妥当性、外部参照のschema、未登録資料、承認、並行更新中の一貫性は対象外。'}
    except (Stopped, OSError, UnicodeError, ValueError) as exc:
        return {'passed': False, 'checked': checked, 'reason': str(exc)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    args = parser.parse_args()
    report = validate(args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['passed'] else 2)
