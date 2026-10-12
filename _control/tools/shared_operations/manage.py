"""共有管理操作の入口。標準ライブラリのみ。直接編集を禁止する機能ではない。"""
import argparse
import base64
import json
import os
from pathlib import Path
import sys
import uuid

from dependency_model import (Stopped, model_root, local_path, check_pending,
                              synced_write, add_dependency)
from source_model import table, change_source
from context_model import add_context
from locking import locks


def logical(root, path):
    return 'workspace:' + path.relative_to(root).as_posix()


def scope_paths(root, project):
    if project is None:
        scope = local_path(root, 'workspace:_control')
        return scope, scope
    if not isinstance(project, str) or not project or any(c in project for c in '/\\|\r\n\x00') or project in ('.', '..'):
        raise Stopped('Project ID不正')
    scope = local_path(root, f'workspace:projects/{project}')
    return scope, local_path(root, logical(root, scope / '_control'))


def owner(root, project, task):
    scope, control = scope_paths(root, project)
    tasks = local_path(root, logical(root, control / 'tasks.md'))
    states = table(tasks, ['Task ID', 'Name', 'Status', 'Detail'])
    if len({r[0] for r in states}) != len(states) or any(
            not tid or not name or not detail or state not in ('pending', 'active', 'blocked', 'done')
            for tid, name, state, detail in states):
        raise Stopped('タスク表不正')
    active = [r for r in states if r[2] == 'active']
    if len(active) != 1 or active[0][0] != task:
        raise Stopped('指定タスクが唯一のactiveではない')
    detail = active[0][3]
    if detail.startswith(('workspace:', '/')):
        raise Stopped('タスク詳細は所有範囲内の相対パスが必要')
    detail_path = local_path(root, logical(root, scope) + '/' + detail)
    if not detail_path.is_file():
        raise Stopped('タスク詳細がファイルではない')
    context = local_path(root, logical(root, control / 'context.md'))
    return scope, tasks, context, detail_path


def capture(root, paths):
    return {logical(root, p): base64.b64encode(p.read_bytes()).decode('ascii')
            for p in paths if p.is_file()}


def decoded(value):
    return base64.b64decode(value, validate=True)


def required(root, operation, project, task, source, consumer=None, replacement=None):
    scope, tasks, context, detail = owner(root, project, task)
    origin = local_path(root, source)
    paths = [tasks, context, detail, origin]
    if operation == 'context-add':
        if project is None or not origin.is_file():
            raise Stopped('入力追加はprojectと単一ファイルを指定してください')
    elif operation == 'dependency-add':
        destination = local_path(root, consumer)
        if destination == origin:
            raise Stopped('同じ対象への自己依存は登録しない')
        owned = [scope] if project is not None else [scope, root / 'library', root / 'profiles']
        if not any(destination.is_relative_to(p) and destination != p for p in owned):
            raise Stopped('利用側は所有範囲内の成果物を指定してください')
        if origin.is_relative_to(scope):
            raise Stopped('同じ所有範囲内の依存は登録対象外')
        paths += [destination, local_path(root, 'workspace:_control/dependencies.md')]
    elif operation in ('source-delete', 'source-replace'):
        if project is not None or not origin.is_file() or not origin.is_relative_to(root / 'library/current'):
            raise Stopped('参照元変更は管理タスクからlibrary/currentの単一ファイルを指定してください')
        paths.append(local_path(root, 'workspace:_control/dependencies.md'))
        if operation == 'source-replace':
            candidate = local_path(root, replacement)
            if not candidate.is_file() or not candidate.is_relative_to(scope / 'wip'):
                raise Stopped('置換候補は管理WIPのファイルを指定してください')
            paths.append(candidate)
    else:
        raise Stopped('未対応操作')
    return scope, paths


def prepare(root, operation, project, task, source, output, consumer=None, replacement=None):
    root = model_root(root)
    with locks(root, [('0-gate', True)]):
        check_pending(root / '_control')
        scope, paths = required(root, operation, project, task, source, consumer, replacement)
        # 保存先は既存WIP内。親を勝手に作らず、既存案を上書きしない。
        relative = output.removeprefix('workspace:')
        if not output.startswith('workspace:') or not relative or relative.endswith('/'):
            raise Stopped('保存先の論理パスが必要')
        parent, _, name = relative.rpartition('/')
        directory = local_path(root, 'workspace:' + parent)
        if not directory.is_relative_to(scope / 'wip') or name in ('', '.', '..') or any(c in name for c in '\\|\r\n\x00'):
            raise Stopped('案の保存先は所有範囲のWIP内にしてください')
        request = dict(format=1, root=str(root), operation=operation, project=project,
                       task=task, source=source, consumer=consumer, replacement=replacement,
                       expected=capture(root, paths))
        synced_write(directory / name, (json.dumps(request, ensure_ascii=False, indent=2) + '\n').encode())
    return {'status': 'prepared', 'request': output, 'operation': operation,
            'source': source, 'consumer': consumer, 'replacement': replacement,
            'changed': '作業案のみ。対象ファイルは未変更'}


def apply(root, request_path, approved=False, checkpoint=None):
    root = model_root(root)
    request_file = local_path(root, request_path)
    r = json.loads(request_file.read_bytes())
    if not isinstance(r, dict) or r.get('format') != 1 or r.get('root') != str(root):
        raise Stopped('案の形式または作業領域が一致しない')
    if not approved:
        raise Stopped('依頼・承認の範囲を確認してから--approvedを指定してください')
    op, project, task, source = (r[k] for k in ('operation', 'project', 'task', 'source'))
    expected = r['expected']
    if not isinstance(expected, dict):
        raise Stopped('案の比較対象が不正')
    scope, control = scope_paths(root, project)
    if not request_file.is_relative_to(scope / 'wip'):
        raise Stopped('案が所有範囲のWIPにない')

    def guard():
        _, paths = required(root, op, project, task, source, r.get('consumer'), r.get('replacement'))
        needed = {logical(root, p) for p in paths if p.is_file()}
        if set(expected) != needed:
            raise Stopped('案の比較対象が不足または過剰')
        for p in paths:
            if p.is_file() and p.read_bytes() != decoded(expected[logical(root, p)]):
                raise Stopped('案作成後に資料・管理表が変化。再読込して案を作り直してください')

    if op == 'context-add':
        status = add_context(root, project, task, source,
                             decoded(expected[logical(root, control / 'tasks.md')]),
                             decoded(expected[logical(root, control / 'context.md')]),
                             decoded(expected[source]), authorized=True, guard=guard, checkpoint=checkpoint)
    elif op == 'dependency-add':
        status = add_dependency(root, r['consumer'], source,
                                decoded(expected['workspace:_control/dependencies.md']),
                                approved=True, guard=guard, checkpoint=checkpoint)
    elif op in ('source-delete', 'source-replace'):
        after = decoded(expected[r['replacement']]) if op == 'source-replace' else None
        status = change_source(root, source, decoded(expected[source]), replacement=after,
                               approved=True, guard=guard, checkpoint=checkpoint)
    else:
        raise Stopped('未対応操作')
    return {'status': status, 'operation': op,
            'changed': status == 'applied', 'request': request_path}


def recover(root, task, approved=False):
    """人が旧内容への復元を選んだ時だけ実行。成功済み操作の巻戻しは対象外。"""
    root = model_root(root)
    with locks(root, [('0-gate', True)]):
        owner(root, None, task)
        if not approved:
            raise Stopped('旧内容への復元承認が必要')
        control = root / '_control'
        pending = [control / n for n in ('dependency-update', 'source-update', 'context-update')
                   if (control / n).exists() or (control / n).is_symlink()]
        if len(pending) != 1:
            raise Stopped('未完了記録が一件に特定できない。変更せず人へ返す')
        journal = local_path(root, logical(root, pending[0]))
        meta = json.loads(local_path(root, logical(root, journal / 'operation.json')).read_bytes())
        name = meta['backup']
        if name not in ('before.md', 'before.bin'):
            raise Stopped('旧版記録が不正')
        before = local_path(root, logical(root, journal / name)).read_bytes()
        target_value = meta['target']
        if not isinstance(target_value, str):
            raise Stopped('復元対象のパスが不正')
        # 未完了記録の対象を、実装が書き込む場所に限定する。
        parts = target_value.removeprefix('workspace:').split('/')
        allowed = ((journal.name == 'dependency-update' and target_value == 'workspace:_control/dependencies.md')
                   or (journal.name == 'context-update' and len(parts) == 4 and parts[0] == 'projects'
                       and parts[2:] == ['_control', 'context.md'])
                   or (journal.name == 'source-update' and parts[:2] == ['library', 'current']))
        if not allowed or not target_value.startswith('workspace:'):
            raise Stopped('復元対象が範囲外')
        parent = local_path(root, 'workspace:' + '/'.join(parts[:-1]))
        if parts[-1] in ('', '.', '..') or any(c in parts[-1] for c in '\\|\r\n\x00'):
            raise Stopped('復元先不正')
        target = parent / parts[-1]
        current = local_path(root, target_value).read_bytes() if target.exists() or target.is_symlink() else None
        after = None if meta['delete'] else local_path(root, logical(root, journal / 'after.expected')).read_bytes()
        if current not in (before, after):
            raise Stopped('記録と異なる変更があるため復元しない')
        archive = local_path(root, 'workspace:_control/archive')
        if current != before:
            stage = journal / ('restore-' + uuid.uuid4().hex)
            synced_write(stage, before)
            mode = meta['mode']
            if not isinstance(mode, int) or mode < 0 or mode > 0o7777:
                raise Stopped('復元する権限情報が不正')
            os.chmod(stage, mode)
            os.replace(stage, target)
        if target.read_bytes() != before:
            raise Stopped('復元後照合失敗')
        destination = archive / (journal.name + '-restored-' + uuid.uuid4().hex)
        os.rename(journal, destination)
        return {'status': 'restored', 'changed': current != before, 'target': target_value,
                'record': logical(root, destination)}


def main():
    p = argparse.ArgumentParser(description='共有管理操作。基本の単独作業には不要です。')
    p.add_argument('--root', required=True, help='作業領域のルート')
    sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('prepare', help='対象を変更せずWIPへ案を保存')
    q.add_argument('operation', choices=['dependency-add', 'context-add', 'source-delete', 'source-replace'])
    for key in ('task', 'source', 'output'):
        q.add_argument('--' + key, required=True)
    for key in ('project', 'consumer', 'replacement'):
        q.add_argument('--' + key)
    q = sub.add_parser('apply', help='保存した案をロック内で照合して適用')
    q.add_argument('--request', required=True)
    q.add_argument('--approved', action='store_true')
    q = sub.add_parser('recover', help='承認された未完了変更を旧内容へ戻す')
    q.add_argument('--task', required=True)
    q.add_argument('--approved', action='store_true')
    args = vars(p.parse_args())
    command = args.pop('command')
    if command == 'apply':
        args['request_path'] = args.pop('request')
    try:
        result = {'prepare': prepare, 'apply': apply, 'recover': recover}[command](**args)
        code = 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        root = Path(args['root'])
        pending = [n for n in ('dependency-update', 'source-update', 'context-update')
                   if (root / '_control' / n).exists() or (root / '_control' / n).is_symlink()]
        result = {'status': 'stopped', 'reason': str(exc), 'pending': pending,
                  'changed': '未完了記録と実体を照合してください' if pending else '対象変更は未実施',
                  'next': '競合は終了後に再確認。前提変更は案を作り直す。未完了なら他の書込みを止めて復元判断。'}
        code = 2
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == '__main__':
    sys.exit(main())
