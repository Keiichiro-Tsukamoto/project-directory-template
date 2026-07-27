# 外部リソース: <表示名>

- スキーマ版: 2
- サービス: <confluence | google-drive | sharepoint | other>
- ワークスペース: <安定したテナント、サイト、共有領域の識別子>
- リソース種別: <page | document | spreadsheet | file | bounded-collection>
- リソースID: <サービスが提供する安定した識別子>
- ロケーター: <任意の人向けURL。署名URLや認証情報を含めない>
- 変更性: <mutable | immutable>
- 取得モード: <live | pinned | snapshot>
- 期待するリビジョン: <pinnedでは必須。それ以外では空欄>
- 取得範囲: <セクション、ページ、シート、セル範囲など>
- 鮮度確認方法: <revision | updated-at | content-hash | refetch | not-applicable>
- キャッシュ再利用: <禁止 | 同一版確認時のみ | 固定スナップショットのみ>
- 検証不能時: <停止 | 登録スナップショットを旧版として使用>
- ローカルスナップショット: <snapshotまたはlocal-snapshotでは必須>
- 代替手段: <none | local-snapshot>
- ローカル保存: <許可 | 禁止 | 要承認>
- Git登録: <許可 | 禁止 | 要承認>
- アクセス上の注意: <任意。認証情報や秘密情報は記載しない>
