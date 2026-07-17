# Context Tools

コンテキスト管理テンプレートの任意ツールです。Python標準ライブラリだけで動作し、通常のタスク開始時に読み込む必要はありません。

## Validate Structure

タスク、detail file、context参照、必須ディレクトリ、`context.md`へ登録された外部リソース参照記述を検査します。

```text
python3 current/context-tools/validate_template.py . --output wip/T-XXX/validation.json
```

外部リソースについては、必須項目、取得モード、pinnedリビジョン、snapshotの存在とcontext登録、保存可否、識別情報の重複、明らかな署名URLやトークン形式を確認します。外部サービスへの接続、実際の権限、リモートリビジョンは実行時に確認してください。

`要承認`や`Git登録: 禁止`など、人の判断またはGit状態の確認が必要な項目はwarningとして出力します。warningは検証失敗を意味しません。

## Create Hash Snapshot

activeタスクの管理ファイル、detail file、context指定ファイル、タスク専用成果物をSHA-256で記録します。

```text
python3 current/context-tools/context_snapshot.py snapshot
```

## Check Hash Snapshot

前回のスナップショットと比較し、追加、変更、削除された対象ファイルを表示します。

```text
python3 current/context-tools/context_snapshot.py check
```

スナップショットは`wip/.context-state/`に保存され、通常のcontextとGit管理には含めません。外部リソースの一時的な取得状態は`wip/T-XXX/.tmp/external-state/`へ置きます。

## Tests

```text
python3 current/context-tools/test_validate_template.py
python3 current/context-tools/test_context_snapshot.py
```
