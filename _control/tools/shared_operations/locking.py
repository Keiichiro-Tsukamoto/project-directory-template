"""同じ作業領域を使う協調的な管理操作の、短時間のOSロック。"""
import contextlib
import os
import re
import stat


@contextlib.contextmanager
def locks(root, requests):
    try:
        import fcntl
    except ImportError as exc:
        raise RuntimeError('この環境はOSロックに未対応。単独運用を使用してください') from exc
    directory = root / '_control' / '.locks'
    if directory.parent.is_symlink() or directory.is_symlink():
        raise ValueError('ロック保存先がリンク')
    directory.mkdir(exist_ok=True)
    handles = []
    try:
        for name, exclusive in sorted(requests):
            if name not in ('0-gate', '2-meta') and not re.fullmatch(r'1-project-[^/\\\x00-\x1f|]+', name):
                raise ValueError('ロック名不正')
            fd = os.open(directory / name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            handles.append(fd)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ValueError('ロック実体不正')
            fcntl.flock(fd, (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
        yield
    finally:
        for fd in reversed(handles):
            os.close(fd)

    # ロックファイルは解放時に削除・置換しない。
