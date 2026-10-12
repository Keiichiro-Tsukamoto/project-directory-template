"""共有管理操作。利用者向け入口はmanage.py。"""
import json
import os
import stat
from pathlib import Path
from locking import locks

HEADER = '# Dependencies\n\n| Consumer | Source |\n|---|---|\n'


class Stopped(RuntimeError):
    pass


def model_root(root):
    root = Path(root).resolve(strict=True)
    if not (root / '_control').is_dir() or (root / '_control').is_symlink():
        raise Stopped('作業領域の管理ディレクトリがない')
    return root


def local_path(root, logical):
    if not isinstance(logical, str) or not logical.startswith('workspace:'):
        raise Stopped('論理パスが必要')
    value = logical[len('workspace:'):]
    parts = value.split('/')
    if any(p in ('', '.', '..') for p in parts) or any(c in value for c in '\\|\r\n\x00'):
        raise Stopped('不正なパス')
    p = root
    for part in parts:
        p = p / part
        if p.is_symlink():
            raise Stopped('リンクは対象外')
    if p.is_file() and p.stat().st_nlink != 1:
        raise Stopped('複数の実体名を持つファイルは対象外')
    if not p.exists():
        raise Stopped('参照先がない')
    if not p.is_file() and not p.is_dir():
        raise Stopped('通常のファイルまたはディレクトリではない')
    return p


def parse(root, raw):
    from source_model import table_bytes
    rows = []
    for cells in table_bytes(raw, ['Consumer', 'Source']):
        row = tuple(cells)
        for value in row:
            local_path(root, value)
        if row in rows:
            raise Stopped('重複行')
        rows.append(row)
    return rows


def synced_write(path, data):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def check_pending(control):
    for name in ('dependency-update', 'source-update', 'context-update'):
        p = control / name
        if p.exists() or p.is_symlink():
            raise Stopped('未完了変更あり。実体と旧版を確認して人へ返す')


def commit(root, pending, target, before, after, operation, checkpoint, changed_stage):
    """旧内容と予定内容を保持し、変更後に記録を保管する。呼出元がロックを保持。"""
    import uuid
    archive = root / '_control/archive'
    if archive.is_symlink() or (archive.exists() and not archive.is_dir()):
        raise Stopped('保管先不正')
    archive.mkdir(exist_ok=True)
    suffix = 'bin' if pending.name == 'source-update' else 'md'
    pending.mkdir()
    synced_write(pending / ('before.' + suffix), before)
    if after is not None:
        synced_write(pending / 'after.expected', after)
    operation.update(target='workspace:' + target.relative_to(root).as_posix(),
                     delete=after is None, backup='before.' + suffix,
                     mode=stat.S_IMODE(target.stat().st_mode))
    synced_write(pending / 'operation.json', json.dumps(operation, ensure_ascii=False).encode())
    if checkpoint:
        checkpoint('prepared')
    if after is None:
        target.unlink()
    else:
        synced_write(pending / 'staged', after)
        os.chmod(pending / 'staged', operation['mode'])
        os.replace(pending / 'staged', target)
    if checkpoint:
        checkpoint(changed_stage)
    if (target.read_bytes() if target.exists() else None) != after:
        raise Stopped('反映後照合が不一致')
    os.rename(pending, archive / (pending.name + '-' + uuid.uuid4().hex))
    return 'applied'


def add_dependency(root, consumer, source, expected, *, approved=False, checkpoint=None, guard=None):
    """取得から結果確認まで一回で行う。checkpointは障害注入専用。"""
    root = model_root(root)
    # 異なるprojectからも管理表は同じロックで直列化する。
    with locks(root, [('0-gate', False), ('2-meta', True)]):
        control = root / '_control'
        target = control / 'dependencies.md'
        pending = control / 'dependency-update'
        if control.is_symlink() or target.is_symlink():
            raise Stopped('管理パスのリンク')
        check_pending(control)
        if guard:
            guard()
        if not approved:
            raise Stopped('対象操作の承認なし')
        before = target.read_bytes()
        if before != expected:
            raise Stopped('確認後に管理表が変化。再読込が必要')
        rows = parse(root, before)
        for value in (consumer, source):
            local_path(root, value)
        row = (consumer, source)
        if row in rows:
            return 'unchanged'
        after = before + f'| {consumer} | {source} |\n'.encode()
        parse(root, after)
        return commit(root, pending, target, before, after,
                      {'operation': 'add_dependency', 'Consumer': consumer, 'Source': source},
                      checkpoint, 'replaced')
