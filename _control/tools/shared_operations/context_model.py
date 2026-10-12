"""共有管理操作。利用者向け入口はmanage.py。"""
from dependency_model import Stopped, model_root, local_path, check_pending, commit
from source_model import table
from locking import locks


def add_context(root, project, task_id, source, expected_tasks, expected_context,
                expected_source, *, authorized=False, checkpoint=None, guard=None):
    root = model_root(root)
    if not project or any(c in project for c in '/\\\\|\r\n') or project in ('.', '..'):
        raise Stopped('Project ID不正')
    with locks(root, [('0-gate', False), ('1-project-' + project, True), ('2-meta', True)]):
        common = local_path(root, 'workspace:_control')
        control = local_path(root, f'workspace:projects/{project}/_control')
        check_pending(common)
        if guard:
            guard()
        if not authorized:
            raise Stopped('入力登録の指示・権限が未確認')
        tasks = local_path(root, f'workspace:projects/{project}/_control/tasks.md')
        target = local_path(root, f'workspace:projects/{project}/_control/context.md')
        before = target.read_bytes()
        if tasks.read_bytes() != expected_tasks or before != expected_context:
            raise Stopped('管理表が変化。再読込が必要')
        states = {}
        for tid, name, status, detail in table(tasks, ['Task ID', 'Name', 'Status', 'Detail']):
            if not tid or tid in states or status not in ('pending', 'active', 'blocked', 'done') or not name or not detail:
                raise Stopped('タスク表不正')
            states[tid] = status
        if list(states.values()).count('active') != 1 or states.get(task_id) != 'active':
            raise Stopped('指定タスクが唯一のactiveではない')
        rows = table(target, ['Task ID', 'File'])
        seen = set()
        for tid, path in rows:
            if tid not in states or states[tid] == 'done' or (tid, path) in seen:
                raise Stopped('context不整合')
            seen.add((tid, path))
            logical = path if path.startswith('workspace:') else f'workspace:projects/{project}/{path}'
            local_path(root, logical)
        origin = local_path(root, source)
        if not origin.is_file() or origin.read_bytes() != expected_source:
            raise Stopped('入力資料の版が変化')
        project_root = root / 'projects' / project
        stored = origin.relative_to(project_root).as_posix() if origin.is_relative_to(project_root) else source
        if (task_id, source) in seen or (task_id, stored) in seen:
            return 'unchanged'
        if not before.endswith(b'\n'):
            raise Stopped('未対応のcontext書式')
        after = before + f'| {task_id} | {stored} |\n'.encode()
        pending = common / 'context-update'
        return commit(root, pending, target, before, after,
                      {'operation': 'add_context', 'project': project, 'Task ID': task_id, 'File': source},
                      checkpoint, 'changed')
