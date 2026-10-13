# 共有管理操作

同じPC・同じアプリから、一つの作業領域の管理情報を同時に更新するための補助機能。通常の単独作業は従来どおりMarkdownの読み書きで行える。この機能を使用する操作だけPython 3.10以降と`fcntl.flock`が必要で、追加パッケージは不要。

配布先は`workspace:_control/tools/shared_operations/`。実行に必要な6個の`.py`と本書を一緒に配置する。配布物には保守用の`test_workspace.py`も同梱するが、通常操作では実行不要である。変更操作の入口は`manage.py`、読取専用検査の入口は`validate_workspace.py`とし、内部関数を直接呼び出さない。

## 管理表の検査

関係する管理表への書込みを止めてから、作業領域ルートで`python3 -B _control/tools/shared_operations/validate_workspace.py --root .`を実行する。作業領域管理と各projectの管理表、および登録されたパスの実在を確認する。業務本文は読まない。成功時は終了コード0、停止時は2。外部参照の記述形式、承認の有無、内容の妥当性はこの検査では確認しない。プログラムが使えない場合は運用ガイドの手動確認を使う。

`projects/.gitkeep`は空ディレクトリの配布用で、空の通常ファイルだけをproject一覧から除外する。`projects/.DS_Store`も通常ファイルの場合だけOS補助ファイルとして除外し、本文の読込・削除は行わない。同名のディレクトリを除外せず、未知のファイルやリンクは従来どおり停止する。管理表に明示された参照は、この一覧除外とは別に検査する。

## 対応する操作

| 操作名 | 所有するタスク | 変更するもの |
|---|---|---|
| `dependency-add` | 利用側の成果物を所有するactiveタスク | ルートの`dependencies.md`に一組追加 |
| `context-add` | 指定projectのactiveタスク | 当該`context.md`に一つの既存ファイルを追加 |
| `source-delete` | 作業領域管理のactiveタスク | 参照されていない`library/current/`の単一ファイルを削除 |
| `source-replace` | 作業領域管理のactiveタスク | 同上のファイルを管理WIPの候補で置換 |

依存表は`Consumer / Source`、入力表は`Task ID / File`、タスク表は`Task ID / Name / Status / Detail`。見出し・空行と管理表を受け付け、解釈できない本文を勝手に読み飛ばさない。リンク、複数の実体名を持つファイル、未解消の参照切れは停止する。予約入力がまだ実在しない管理表もこの版では停止対象とする。

利用側・参照元は既存の正確な論理パスを指定する。`workspace:`の後は作業領域ルートからの相対パスで、`..`は使わない。Project IDは既存ディレクトリ名と一致させる。

## 更新案の作成と適用

次の例のルート、Project ID、Task ID、資料名は対象に合わせて置き換える。作業領域ルートで実行する場合の例である。

```sh
python3 _control/tools/shared_operations/manage.py --root . prepare context-add \
  --project P-017 --task T-001 \
  --source workspace:library/current/source.md \
  --output workspace:projects/P-017/wip/input_request.json
```

`prepare`は指定したWIPに操作案を保存し、対象は変更しない。対象・所有タスクの管理表・タスク詳細・関係資料の比較用内容を案に含める。周辺の業務本文は取得しない。既存案を上書きしない。保存先の親ディレクトリは既に存在するものを使う。

JSON内の`operation / project / task / source / consumer / replacement`が依頼と一致すること、置換の場合は候補内容も確認する。`expected`はプログラム用の比較データであり、LLMへ全体を入力する必要はない。案を手修正せず、変更が必要なら別名で作り直す。

依頼または既存方針によりその操作が許可されていることを確認してから実行する。承認不要の入力登録について、追加の承認を一律に要求するものではない。

```sh
python3 _control/tools/shared_operations/manage.py --root . apply \
  --request workspace:projects/P-017/wip/input_request.json --approved
```

`--approved`は操作権限を確認した呼出側の申告であり、人の意思を認証する仕組みではない。案にない別操作の権限を付与しない。

適用処理はロック取得から再確認・変更・結果照合・解放まで一度に行う。案作成後に所有タスク、管理表、関係資料が変わっていれば適用しない。人の検討・承認待ちにはロックを保持しない。

他の操作の追加引数は次のとおり。

- `dependency-add`：`--consumer workspace:projects/P-017/current/result.md`を追加する。project所有なら`--project`を指定する。所有範囲外の実体への継続依存だけを登録する。
- `source-delete`：`--project`を付けず、管理タスクを指定する。案の保存先は`workspace:_control/wip/`内にする。
- `source-replace`：削除と同じ指定に`--replacement workspace:_control/wip/replacement.md`を追加する。

削除・置換では、ルートと各projectの管理表、依存表を横断確認する。対象を含むディレクトリへの参照も停止対象。同じタスク自身の参照も無視しない。参照切替が必要ならその所有タスクで先に扱う。

## 結果と停止

結果はJSON、正常終了は終了コード0、停止は2。`applied`は変更と照合の成功、`unchanged`は既に同じ行がある状態、`stopped`は理由と再開方法を表す。

- 競合：他の処理が終了してから現在の状態を確認する。無条件の再試行を繰り返さない。
- 前提変更：必要な資料を読み直し、依頼の有効性を確認して別名で案を作り直す。
- 未完了：以下の復元手順へ進む。ロックを再取得できても完了・復元済みとは判断しない。
- 未対応環境：対象操作を単独運用で行う。同時実行してよいことにはならない。

## 未完了変更を旧内容へ戻す

未完了記録は`workspace:_control/dependency-update/`、`source-update/`、`context-update/`のいずれかにある。成功時には旧内容と操作記録が`workspace:_control/archive/<操作名>-<一意な値>/`へ移り、未完了状態が解消する。ロックは`workspace:_control/.locks/`に置く。**ロックファイルを削除・置換して解放しない。**

1. 関係する書込みを止める。直接編集で記録を消したり、単独運用への切替だけで停止を迂回したりしない。
2. 指定された未完了ディレクトリの`operation.json`、`before.md`または`before.bin`、削除以外では`after.expected`と対象実体を確認する。これらが不足する場合は、完全な復元記録があると推測しない。
3. 人が旧内容への復元を選んだら、管理タスクを指定して次を実行する。正常完了した操作を後から巻き戻すコマンドではない。

```sh
python3 _control/tools/shared_operations/manage.py --root . recover \
  --task T-001 --approved
```

4. 一つに特定できた記録について、実体が旧内容または予定内容に一致する場合だけ旧内容へ復元する。別の内容になっていれば上書きしない。復元成功時は記録を管理archiveへ移し、保存先を返す。復元も途中で止まったら記録を保持して再確認する。
5. 記録が欠ける場合は、対象・実施済み変更・残存旧版を人へ提示して個別の修復案を作る。未完了印だけを消して進めない。

旧版、操作案、記録は管理タスクの完了時に通常の配置・不要物整理手順で扱う。毎回自動削除はしない。削除権限がない環境では削除は成功しないが、停止と復元判断は同じ手順で行う。

## 同時実行の対象外

タスク状態変更、入力解除、依存解消、複数ファイルの変更、共通規則更新は、影響する書込みを止めて行う。共通規則更新後は関係するチャットで規則とタスク状態を読み直す。

別PC、別アプリ、同期サービスの介入、直接編集による迂回、意図的なロック破壊、電源断は保護の保証対象外。別projectの独立した本文作業まで全てこのプログラム経由にする必要はないが、管理操作と競合する対象を直接編集しない。
