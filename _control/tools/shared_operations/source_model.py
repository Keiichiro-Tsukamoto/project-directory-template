"""共有管理操作。利用者向け入口はmanage.py。"""
from dependency_model import (Stopped, model_root, local_path, parse,
                              check_pending, commit)
from locking import locks


def table(path, columns):
    if path.is_symlink():
        raise Stopped('管理表がリンク')
    return table_bytes(path.read_bytes(), columns)


def table_bytes(raw, columns):
    lines = raw.decode('utf-8').splitlines()
    # 管理データ以外は見出しと空行だけ。解釈できない行を読み飛ばさない。
    rows = [x for x in lines if x and not x.startswith('#')]
    if len(rows) < 2:
        raise Stopped('管理表欠落')
    def cells(line):
        parts = line.split('|')
        if len(parts) != len(columns) + 2 or parts[0] or parts[-1]:
            raise Stopped('管理表形式不正')
        return [x.strip() for x in parts[1:-1]]
    import re
    if cells(rows[0]) != columns or any(not re.fullmatch(r':?-{3,}:?', x) for x in cells(rows[1])):
        raise Stopped('管理表定義不一致')
    return [cells(x) for x in rows[2:]]


def overlaps(a, b):
    return a == b or a in b.parents or b in a.parents


def project_directories(root):
    projects = root / 'projects'
    if projects.is_symlink() or not projects.is_dir():
        raise Stopped('project一覧を確認不能')
    result = []
    for p in sorted(projects.iterdir()):
        if p.name == '.gitkeep' and not p.is_symlink() and p.is_file() and p.stat().st_size == 0:
            continue
        if p.is_symlink() or not p.is_dir():
            raise Stopped('project直下にディレクトリ以外またはリンクがある')
        result.append(p)
    return result


def protect_inputs(root, target):
    scopes = [root, *project_directories(root)]
    for scope in scopes:
        control = scope / '_control'
        if control.is_symlink():
            raise Stopped('管理領域がリンク')
        tasks = table(control / 'tasks.md', ['Task ID', 'Name', 'Status', 'Detail'])
        states = {}
        for task_id, name, status, detail in tasks:
            if not task_id or task_id in states or status not in ('pending', 'active', 'blocked', 'done'):
                raise Stopped('Task状態不正')
            if not name or not detail:
                raise Stopped('Task必須値不足')
            states[task_id] = status
        if list(states.values()).count('active') > 1:
            raise Stopped('active重複')
        for task_id, value in table(control / 'context.md', ['Task ID', 'File']):
            if task_id not in states or states[task_id] == 'done':
                raise Stopped('contextとtasksが不整合')
            if not value.startswith('workspace:'):
                prefix = '_control/' if scope == root else scope.relative_to(root).as_posix() + '/'
                value = 'workspace:' + prefix + value
            referenced = local_path(root, value)
            if overlaps(target, referenced):
                raise Stopped('未完了タスクの入力が参照中')


def change_source(root, source, expected, *, replacement=None, approved=False, checkpoint=None, guard=None):
    """replacement=Noneは削除。共有current内の単一通常ファイルだけが対象。"""
    root = model_root(root)
    with locks(root, [('0-gate', True)]):
        control = root / '_control'
        if control.is_symlink():
            raise Stopped('管理領域がリンク')
        check_pending(control)
        if guard:
            guard()
        if not approved:
            raise Stopped('対象操作の承認なし')
        target = local_path(root, source)
        allowed = root / 'library/current'
        if not target.is_relative_to(allowed) or not target.is_file():
            raise Stopped('共有ファイル変更の対象外')
        before = target.read_bytes()
        if before != expected:
            raise Stopped('確認後に対象が変化')
        dep = control / 'dependencies.md'
        if dep.is_symlink():
            raise Stopped('依存表がリンク')
        for consumer, origin in parse(root, dep.read_bytes()):
            if any(overlaps(target, local_path(root, x)) for x in (consumer, origin)):
                raise Stopped('永続依存あり')
        protect_inputs(root, target)
        pending = control / 'source-update'
        return commit(root, pending, target, before, replacement,
                      {'operation': 'delete' if replacement is None else 'replace', 'Source': source},
                      checkpoint, 'changed')
