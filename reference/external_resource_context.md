# 外部リソース・コンテキストガイド

## 基本方針

外部リソース1件につき、原則として`reference/external/`へ参照記述を1件置き、`context.md`にはURLや取得した本文ではなく参照記述を登録します。clone、download、cache等の作業用実体は同ディレクトリへ置きません。

`reference/external/`配下の`_`で始まらないMarkdownは、context登録時に外部リソース参照記述として静的検証されます。新規参照記述は`reference/external/_template.md`のschema v3で作成します。既存schema v2は次回利用時まで変更せず、v3の意味へ読み替えません。

リソースは、サービス、ワークスペース、リソースIDの組み合わせで識別します。表示名とURLは補助情報です。参照記述を作成または更新したら、本文取得やcache利用より前にcontextへ登録して`validate_template.py`を実行します。

## 参照記述、Task、実行時状態の分離

| 場所 | 記録するもの | 変わる時 |
|---|---|---|
| 参照記述 | IDやlocatorが表す対象オブジェクトの外側の境界 | 参照先またはresource構造が変わった時 |
| active Task | Goalに必要なsheet、列、slide、page、論点 | Taskが変わった時 |
| 実行時状態 | connector能力、実取得範囲・量、実際のLLM入力 | 取得を実行した時 |

Task T-003がA sheet、T-004がB・C sheetを必要としても、同じworkbookの参照記述は変更しません。context登録はresourceを正規入力として利用できる境界であり、resource全体を毎回LLMへ入力する指示ではありません。

## 対象オブジェクトの構造

形式名、拡張子、Task必要範囲、connector能力ではなく、resource IDとrevision・lifecycleの境界で分類します。

| 構造 | 判定 | 例 |
|---|---|---|
| `atomic` | 一つのresourceで、別に選択する安定した内部単位を持たない | 単一Webページ、単一API record |
| `composite` | 一つのIDを持ち、親とrevision・lifecycleを共有する内部単位を持つ | spreadsheetのsheet、Slidesのslide、PDFのpage |
| `fixed-collection` | 独立resourceのmemberをIDまたはlocatorの一覧で固定する | 明示した複数file、Issue #8と#9 |
| `dynamic-collection` | memberがquery、path規則、status、`latest`等で決まる | open Issues、latest release、検索結果 |

次の順で判定します。

1. 最上位の独立resource IDが一つで、安定した内部単位がなければ`atomic`、あれば`composite`とする。
2. 独立resourceが複数で、memberを列挙できれば`fixed-collection`、決定規則で変われば`dynamic-collection`とする。
3. member一覧も決定規則も示せなければ分類せず、本文取得前に停止する。

repository本体、Issues、releasesのようにrevisionやlifecycleが異なる対象を一つの`composite`へ混在させません。未知の形式もまず4類型へ分類し、形式名だけを理由にschemaを拡張しません。既存類型で表せない構造差分がある場合は、active TaskのWIPへ境界、構造候補、取得能力、不明点を記録し、人の判断後に実例fixtureと4類型の回帰testを伴ってschema拡張を検討します。

## 取得モードと鮮度

- `live`: 鮮度境界で最新版を確認する。mutableでは現在の更新指標とcache側の値が一致した場合だけcacheを再利用する。
- `pinned`: `期待するリビジョン`と一致する版だけを取得する。検証できなければ最新版へ置き換えず停止する。
- `snapshot`: context登録済みの固定スナップショットを使い、リモート現在版とは主張しない。

mutableなリソースは、タスク開始・再開後の初回利用、別環境への引継ぎ後、重要判断や成果物確定の直前、更新通知後、外部書込み直前に現在版との一致を確認します。

本文と独立して確認できる最小の更新指標を、revision・version・ETag、updated-at、安定したcontent-hash、refetchの順で優先します。上位の方法を使える場合、安全上の理由なく下位を既定にしません。

## 内容取得とLLM入力

本文取得前に、connectorがTask必要範囲を指定できるか、対象オブジェクト全体しか取得できないか、結果全体がLLMへ直接入力されるかを確認します。`対象オブジェクト`の外を探索しません。

1. Task必要範囲だけを取得できる場合は、その機能を使う。
2. 広い単位しか取得できないがLLM入力前に決定論的に抽出できる場合は、実取得単位、概算量、ローカル保存の有無を示し、必要な許可を得て1回取得し、必要範囲だけを入力する。
3. 広い結果全体がLLMへ直接入力される場合は、実入力範囲と概算量を取得前に示し、人の承認、狭いexport、ローカル処理のいずれかを求める。
4. 取得能力を確認できない、またはいずれも選べない場合は、必要範囲を満たしたとみなさず停止する。

同じ内容を再入力しません。現在版と確認済みのcacheはGoalに必要な部分だけを入力し、変更がある場合も変更箇所と必要な周辺に限定します。差分だけでは意味が確定しない場合は、Task必要範囲全体を入力します。

## cache

- `禁止`: cacheを正規入力に使わない。
- `同一版確認時のみ`: 現在のリモート更新指標とcache側の指標が一致した場合だけ再利用する。
- `固定スナップショットのみ`: `snapshot`としてcontext登録済みの固定版だけを使う。

cacheの存在、過去のアクセス、表示名、同じfile IDだけでは現在版とみなしません。`鮮度確認方法: refetch`では`キャッシュ再利用: 禁止`とします。異なるexport形式、列順、文字コード、改行、数式と表示値を同じ条件のhashとして比較しません。

## 実行時状態

`reference/external/_state_template.md`を基に、`wip/T-XXX/.tmp/external-state/`へ次の6項目だけを記録します。この場所はGitとcontextの対象外です。

- 参照記述
- 確認日時
- 鮮度確認：方法、比較元、今回値、判定
- 内容取得：取得能力、実取得範囲、量、対象外内容の扱い
- LLM入力：Task必要範囲、実入力範囲、量
- 結果：判断、例外理由、必要な承認

静的な参照記述へ実行日時、更新指標、Task必要範囲を書き戻しません。検収や再現に必要な情報だけをWIP evidenceへ移してcontext登録します。

## エラー、保存、外部更新

アクセス不能またはrevision検証不能の場合、Web検索、類似文書、未登録cacheへ暗黙に置き換えません。`検証不能時: 登録スナップショットを旧版として使用`で、指定snapshotがcontext登録済みの場合だけ旧版利用できます。現在版との一致がGoalの合否に必要なら停止します。

閲覧権限はローカル保存、Git登録、外部変更の権限を含みません。`要承認`または不明なら実行前に確認します。アクセストークン、セッション情報、認証情報、有効期限付き署名URLを参照記述、snapshot、成果物、ログ、Gitへ保存しません。

外部アクセスは読み取り専用を標準とします。変更案はWIPで作り、対象と操作の承認を得て、書込み直前にrevisionを再確認します。

## 静的検証と移行

validatorはschema v2とv3を別々に検証します。v3では4構造類型と構成単位・構成規則の整合を確認します。外部サービスへの接続、実際の権限、更新指標、取得能力、実取得範囲、LLM入力範囲は実行時または人による確認が必要です。

既存v2または旧形式を利用する時は、次の順で扱います。

1. `取得範囲`を`対象オブジェクト`へ自動変換しない。
2. resource ID、revision・lifecycle、member一覧または決定規則からv3の境界と構造を人が確定する。
3. Task固有の論点や利用範囲はdescriptorへ移さない。
4. 不足する鮮度、保存、Git方針を推測しない。
5. 新しいdescriptorをcontext登録してvalidator合格後に外部内容を利用する。

既存の実行時状態記録は一時物のため移行しません。
