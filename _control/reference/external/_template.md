# 外部リソース: <表示名>

このファイルには1件の外部リソースだけを記述します。別のリソースは別ファイルへ分けます。

- スキーマ版: 3
- サービス: <confluence | google-drive | sharepoint | other>
- ワークスペース: <安定したテナント、サイト、共有領域の識別子>
- リソースID: <サービスが提供する安定した識別子>
- ロケーター: <任意の人向けURL。署名URLや認証情報を含めない>
- 対象オブジェクト: <IDとlocatorが表す外側の境界。含むものと含まないものを明記>
- 構造: <atomic | composite | fixed-collection | dynamic-collection>
- 構成単位: <atomicは「なし」。それ以外はsection、sheet、slide、page、file、record、issueなど>
- 構成規則: <atomicは「なし」。compositeの内部単位、fixedのmember一覧、dynamicの決定規則>
- 変更性: <mutable | immutable>
- 取得モード: <live | pinned | snapshot>
- 期待するリビジョン: <pinnedでは必須。それ以外では空欄>
- 鮮度確認方法: <revision | updated-at | content-hash | refetch | not-applicable>
- キャッシュ再利用: <禁止 | 同一版確認時のみ | 固定スナップショットのみ>
- 検証不能時: <停止 | 登録スナップショットを旧版として使用>
- ローカルスナップショット: <snapshotまたは旧版利用では必須>
- ローカル保存: <許可 | 禁止 | 要承認>
- Git登録: <許可 | 禁止 | 要承認>
- アクセス上の注意: <任意。認証情報や秘密情報は記載しない>
