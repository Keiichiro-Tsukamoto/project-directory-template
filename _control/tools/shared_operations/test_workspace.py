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
        values = [value] if isinstance(value, str) else value
        self.put(f'projects/{name}/_control/context.md', '# Context\n\n| Task ID | File |\n|---|---|\n' +
                 ''.join('| T-001 | ' + item + ' |\n' for item in values))

    @staticmethod
    def descriptor(**overrides):
        values = {'スキーマ版': '3', 'サービス': 'test-service',
                  'ワークスペース': 'test-workspace', 'リソースID': 'report-1',
                  'ロケーター': '', '対象オブジェクト': '指定document全体',
                  '構造': 'atomic', '構成単位': 'なし', '構成規則': 'なし',
                  '変更性': 'mutable', '取得モード': 'live',
                  '期待するリビジョン': '', '鮮度確認方法': 'revision',
                  'キャッシュ再利用': '同一版確認時のみ', '検証不能時': '停止',
                  'ローカルスナップショット': '', 'ローカル保存': '許可',
                  'Git登録': '禁止', 'アクセス上の注意': ''}
        values.update(overrides)
        return '# 外部リソース: Test\n\n' + ''.join(
            f'- {key}: {value}\n' for key, value in values.items())

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

    def test_20_registered_current_descriptor_valid_and_invalid(self):
        self.project()
        self.put('projects/P-001/current/report.remote.md', self.descriptor())
        self.input('current/report.remote.md')
        self.assertTrue(validate(self.root)['passed'])
        self.put('projects/P-001/current/report.remote.md', self.descriptor(**{'取得モード': 'invalid'}))
        self.assertFalse(validate(self.root)['passed'])
        self.put('projects/P-001/reference/external/broken.md', '# Broken heading\n')
        self.input('reference/external/broken.md')
        self.assertFalse(validate(self.root)['passed'])

    def test_21_snapshot_uses_descriptor_owner_not_consumer(self):
        self.project(); self.project('P-002')
        for owner in ('projects/P-002', 'library', 'profiles/test-user', '_control'):
            with self.subTest(owner=owner):
                self.put(owner + '/reference/snapshot.txt', 'snapshot')
                self.put(owner + '/current/report.remote.md', self.descriptor(**{
                    '取得モード': 'snapshot', '鮮度確認方法': 'not-applicable',
                    'キャッシュ再利用': '固定スナップショットのみ',
                    'ローカルスナップショット': 'reference/snapshot.txt'}))
                descriptor = 'workspace:' + owner + '/current/report.remote.md'
                self.input([descriptor, 'workspace:' + owner + '/reference/snapshot.txt'])
                self.assertTrue(validate(self.root)['passed'])
                self.put('projects/P-001/reference/snapshot.txt', 'consumer-local copy')
                self.input([descriptor, 'reference/snapshot.txt'])
                self.assertFalse(validate(self.root)['passed'])
        self.put('projects/P-001/current/report.remote.md', self.descriptor(**{
            '取得モード': 'snapshot', '鮮度確認方法': 'not-applicable',
            'キャッシュ再利用': '固定スナップショットのみ',
            'ローカルスナップショット': 'workspace:library/reference/snapshot.txt'}))
        self.input(['current/report.remote.md', 'workspace:library/reference/snapshot.txt'])
        self.assertTrue(validate(self.root)['passed'])

    def test_22_identity_is_scoped_to_consuming_task(self):
        self.project(); self.project('P-002')
        for project in ('P-001', 'P-002'):
            self.put(f'projects/{project}/current/report.remote.md', self.descriptor())
            self.input('current/report.remote.md', name=project)
        self.assertTrue(validate(self.root)['passed'])
        self.input(['current/report.remote.md', 'workspace:projects/P-002/current/report.remote.md'])
        self.assertFalse(validate(self.root)['passed'])

    def test_23_nonresources_and_unregistered_descriptors_are_excluded(self):
        self.project()
        self.put('projects/P-001/current/report.md', '# Report\n\n# 外部リソース: example only\n')
        self.put('projects/P-001/_control/reference/external/_template.md', '# 外部リソース: template\n')
        self.put('projects/P-001/current/unregistered.remote.md', '# 外部リソース: broken\n')
        self.input(['current/report.md', '_control/reference/external/_template.md'])
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.assertTrue(validate(self.root)['passed'])
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})


    @staticmethod
    def descriptor_v2(**overrides):
        # 外部参照のスキーマ版2は、製品の旧v1構造とは別に維持する。
        body = DistributionTests.descriptor(**{'スキーマ版': '2', **overrides})
        body = '\n'.join(line for line in body.splitlines()
                         if not line.startswith(('- 対象オブジェクト:', '- 構造:', '- 構成単位:', '- 構成規則:')))
        return body + '\n- リソース種別: document\n- 取得範囲: 本文全体\n- 代替手段: none\n'

    def check_descriptor(self, body, expected=(), passed=False):
        self.put('projects/P-001/current/report.remote.md', body)
        self.input('current/report.remote.md')
        result = validate(self.root)
        self.assertEqual(result['passed'], passed, result)
        names = {item['check'].split(':', 1)[0]
                 for item in result.get('descriptor_failures', [])}
        self.assertTrue(set(expected) <= names, result)
        return result

    def test_24_v2_live_and_snapshot_fallback_remain_supported(self):
        self.project()
        self.check_descriptor(self.descriptor_v2(), passed=True)
        self.put('projects/P-001/reference/snapshot.txt', 'snapshot')
        body = self.descriptor_v2(**{
            '検証不能時': '登録スナップショットを旧版として使用',
            'ローカルスナップショット': 'reference/snapshot.txt'})
        self.check_descriptor(body, ['external_fallback_unverifiable_consistency'])
        body = body.replace('- 代替手段: none', '- 代替手段: local-snapshot')
        self.put('projects/P-001/current/report.remote.md', body)
        self.input(['current/report.remote.md', 'reference/snapshot.txt'])
        self.assertTrue(validate(self.root)['passed'])

    def test_25_v3_structure_contract(self):
        self.project()
        for structure in ('atomic', 'composite', 'fixed-collection', 'dynamic-collection'):
            with self.subTest(structure=structure):
                fields = {} if structure == 'atomic' else {
                    '構成単位': 'item', '構成規則': '明示した集合のitem'}
                self.check_descriptor(self.descriptor(**{'構造': structure, **fields}), passed=True)
        self.check_descriptor(self.descriptor(**{'構成単位': 'page'}),
                              ['external_structure_components'])
        self.check_descriptor(self.descriptor() + '- 取得範囲: 本文全体\n',
                              ['external_v3_legacy_fields_absent'])

    def test_26_schema_metadata_and_single_resource_contract(self):
        self.project()
        cases = (
            (self.descriptor_v2().replace('- スキーマ版: 2\n', ''),
             ['external_schema_version', 'external_fields_present']),
            (self.descriptor().replace('- ワークスペース: test-workspace\n', ''),
             ['external_fields_present']),
            (self.descriptor() + self.descriptor(),
             ['external_single_resource_heading', 'external_fields_unique']),
        )
        for body, expected in cases:
            with self.subTest(expected=expected):
                self.check_descriptor(body, expected)

    def test_27_pinned_and_cache_policies(self):
        self.project()
        for fields, expected in (
            ({'取得モード': 'pinned'}, 'external_pinned_revision'),
            ({'鮮度確認方法': 'refetch'}, 'external_refetch_cache_policy'),
            ({'取得モード': 'snapshot'}, 'external_snapshot_freshness'),
            ({'キャッシュ再利用': '固定スナップショットのみ'}, 'external_snapshot_cache_policy'),
        ):
            with self.subTest(expected=expected):
                self.check_descriptor(self.descriptor(**fields), [expected])
        self.check_descriptor(self.descriptor(**{
            '鮮度確認方法': 'refetch', 'キャッシュ再利用': '禁止'}), passed=True)
        self.check_descriptor(self.descriptor(**{
            '取得モード': 'pinned', '期待するリビジョン': 'revision-1'}), passed=True)

    def test_28_snapshot_storage_mapping_and_approval_warnings(self):
        self.project()
        fields = {'取得モード': 'snapshot', '鮮度確認方法': 'not-applicable',
                  'キャッシュ再利用': '固定スナップショットのみ',
                  'ローカルスナップショット': 'reference/snapshot.txt'}
        self.check_descriptor(self.descriptor(**fields),
                              ['external_snapshot_exists', 'external_snapshot_mapped'])
        self.put('projects/P-001/reference/snapshot.txt', 'snapshot')
        for storage, git, passed in (('禁止', '禁止', False), ('許可', '禁止', True),
                                     ('要承認', '要承認', True)):
            with self.subTest(storage=storage, git=git):
                self.put('projects/P-001/current/report.remote.md',
                         self.descriptor(**{**fields, 'ローカル保存': storage, 'Git登録': git}))
                self.input(['current/report.remote.md', 'reference/snapshot.txt'])
                result = validate(self.root)
                self.assertEqual(result['passed'], passed, result)
                if not passed:
                    self.assertTrue(any(item['check'].startswith('external_snapshot_storage_not_forbidden:')
                                        for item in result['descriptor_failures']), result)
                else:
                    warnings = {item['warning'].split(':', 1)[0]
                                for item in result['warning_details']}
                    expected = {'external_snapshot_storage_requires_approval',
                                'external_snapshot_git_requires_approval'} if storage == '要承認' else set()
                    self.assertEqual(warnings, expected)

    def test_29_cross_schema_identity_and_obvious_secrets(self):
        self.project()
        self.put('projects/P-001/current/v2.remote.md', self.descriptor_v2())
        self.put('projects/P-001/current/v3.remote.md', self.descriptor())
        self.input(['current/v2.remote.md', 'current/v3.remote.md'])
        result = validate(self.root)
        self.assertTrue(any(item['check'].startswith('external_identity_unique:')
                            for item in result['descriptor_failures']), result)
        self.check_descriptor(self.descriptor(**{
            # 拒否動作の試験だけに使う架空のURLと値。
            'ロケーター': 'https://example.invalid/doc?X-Amz-Signature=test-signature'}),
            ['external_no_obvious_secret'])


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(DistributionTests))
    report = {'tests': result.testsRun, 'passed': result.wasSuccessful(),
              'failures': len(result.failures), 'errors': len(result.errors),
              'details': [str(t) + '\n' + message for t, message in result.failures + result.errors]}
    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0 if report['passed'] else 1)
