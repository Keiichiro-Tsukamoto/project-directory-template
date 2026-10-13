"""配布固有の差分と管理表検査の代表確認。実環境は変更しない。"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent
DIST = BASE.parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(DIST / '_control/tools/shared_operations'))
from validate_workspace import validate
from source_model import protect_inputs, Stopped


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='workspace-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'workspace'
        self.root.mkdir()
        for name in ('rules.md', 'tasks.md', 'context.md', 'dependencies.md'):
            self.put('_control/' + name, (DIST / '_control' / name).read_text())
        self.put('projects/.gitkeep', '')
        self.put('library/current/shared.md', '共有資料')

    def put(self, name, body):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding='utf-8')

    def project(self, name='P-001', state='active'):
        prefix = 'projects/' + name + '/'
        self.put(prefix + '_control/project.md', '# Project\n\n## Background\n背景\n## Purpose\n目的\n## Goal\n目標\n')
        location = 'archive' if state == 'done' else 'wip'
        self.put(prefix + '_control/tasks.md', f'# Tasks\n\n| Task ID | Name | Status | Detail |\n|---|---|---|---|\n| T-001 | 作業 | {state} | {location}/T-001.md |\n')
        self.put(prefix + location + '/T-001.md', '# Task\n')
        self.put(prefix + '_control/context.md', '# Context\n\n| Task ID | File |\n|---|---|\n')

    def input(self, value, name='P-001'):
        self.put(f'projects/{name}/_control/context.md', '# Context\n\n| Task ID | File |\n|---|---|\n| T-001 | ' + value + ' |\n')

    def test_01_empty_distribution(self):
        self.assertTrue(validate(DIST)['passed'])

    def test_02_two_projects_can_have_same_active_id(self):
        self.project(); self.project('P-002')
        self.assertTrue(validate(self.root)['passed'])

    def test_03_duplicate_active_stops(self):
        self.project()
        path = self.root / 'projects/P-001/_control/tasks.md'
        path.write_text(path.read_text() + '| T-002 | 別作業 | active | wip/T-002.md |\n')
        self.put('projects/P-001/wip/T-002.md', '# Task\n')
        self.assertFalse(validate(self.root)['passed'])

    def test_04_missing_input_stops(self):
        self.project(); self.input('reference/missing.md')
        self.assertFalse(validate(self.root)['passed'])

    def test_05_done_input_stops(self):
        self.project(state='done'); self.input('workspace:library/current/shared.md')
        self.assertFalse(validate(self.root)['passed'])

    def test_06_pending_input_allowed(self):
        self.project(state='pending'); self.input('workspace:library/current/shared.md')
        self.assertTrue(validate(self.root)['passed'])

    def test_07_unsafe_path_stops(self):
        self.project(); self.input('../P-002/current/data.md')
        self.assertFalse(validate(self.root)['passed'])

    def test_08_missing_dependency_stops(self):
        self.put('_control/dependencies.md', '# Dependencies\n\n| Consumer | Source |\n|---|---|\n| workspace:library/current/shared.md | workspace:library/current/missing.md |\n')
        self.assertFalse(validate(self.root)['passed'])

    def test_09_placeholder_allows_protection(self):
        protect_inputs(self.root, self.root / 'library/current/shared.md')

    def test_10_nonempty_placeholder_stops(self):
        self.put('projects/.gitkeep', '未知の情報')
        self.assertFalse(validate(self.root)['passed'])
        with self.assertRaises(Stopped):
            protect_inputs(self.root, self.root / 'library/current/shared.md')

    def test_11_symlink_placeholder_stops(self):
        path = self.root / 'projects/.gitkeep'
        path.unlink()  # このテストだけが作った一時物
        path.symlink_to('../library/current/shared.md')
        self.assertFalse(validate(self.root)['passed'])

    def test_12_context_still_protects_source(self):
        self.project(); self.input('workspace:library/current/shared.md')
        with self.assertRaises(Stopped):
            protect_inputs(self.root, self.root / 'library/current/shared.md')

    def test_13_incomplete_operation_stops(self):
        self.put('_control/context-update/operation.json', '{}')
        self.assertFalse(validate(self.root)['passed'])

    def test_14_export_import_reference_closure(self):
        self.project(); self.input('workspace:library/current/shared.md')
        exported = Path(self.tmp.name) / 'exported'
        # 明示した共通規則・管理表、project、必要な共有資料だけを収録。
        shutil.copytree(self.root / '_control', exported / '_control')
        shutil.copytree(self.root / 'projects/P-001', exported / 'projects/P-001')
        self.assertFalse(validate(exported)['passed'])
        shutil.copytree(self.root / 'library', exported / 'library')
        self.assertTrue(validate(exported)['passed'])
        imported = Path(self.tmp.name) / 'imported'
        shutil.copytree(exported, imported)
        self.assertTrue(validate(imported)['passed'])
        # 同名取込を上書きせず停止する。
        with self.assertRaises(FileExistsError):
            shutil.copytree(exported / 'projects/P-001', imported / 'projects/P-001')

    def test_16_os_metadata_is_ignored_without_change(self):
        self.project()
        self.put('projects/.DS_Store', 'OS metadata')
        path = self.root / 'projects/.DS_Store'
        before = path.read_bytes()
        result = validate(self.root)
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['projects'], 1)
        protect_inputs(self.root, self.root / 'library/current/shared.md')
        self.assertEqual(path.read_bytes(), before)
        self.input('workspace:library/current/shared.md')
        with self.assertRaises(Stopped):
            protect_inputs(self.root, self.root / 'library/current/shared.md')

    def test_17_unknown_files_still_stop(self):
        for name in ('unknown.md', '.unknown', '.DS_Store.backup'):
            with self.subTest(name=name):
                self.put('projects/' + name, 'unknown')
                self.assertFalse(validate(self.root)['passed'])
                with self.assertRaises(Stopped):
                    protect_inputs(self.root, self.root / 'library/current/shared.md')
                (self.root / 'projects' / name).unlink()  # 本試験で生成した一時物だけ。

    def test_18_os_metadata_symlink_still_stops(self):
        path = self.root / 'projects/.DS_Store'
        for target in ('../library/current/shared.md', '../missing'):
            with self.subTest(target=target):
                path.symlink_to(target)
                self.assertFalse(validate(self.root)['passed'])
                with self.assertRaises(Stopped):
                    protect_inputs(self.root, self.root / 'library/current/shared.md')
                path.unlink()  # 本試験で生成したリンクだけ。

    def test_19_os_metadata_directory_is_not_hidden(self):
        (self.root / 'projects/.DS_Store').mkdir()
        self.assertFalse(validate(self.root)['passed'])
        with self.assertRaises((Stopped, OSError)):
            protect_inputs(self.root, self.root / 'library/current/shared.md')

    def test_15_validation_is_read_only(self):
        self.project(); self.input('workspace:library/current/shared.md')
        def snapshot():
            return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        before = snapshot()
        self.assertTrue(validate(self.root)['passed'])
        self.assertEqual(before, snapshot())


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DistributionTests))
    report = {'tests': result.testsRun, 'passed': result.wasSuccessful(),
              'failures': len(result.failures), 'errors': len(result.errors),
              'details': [str(t) + '\n' + message for t, message in result.failures + result.errors]}
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0 if report['passed'] else 1)
