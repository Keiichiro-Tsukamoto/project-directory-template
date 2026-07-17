# Git・ローカル成果物管理ガイド

## 基本方針

Gitを必須にせず、利用能力と権限に応じて3段階の運用プロファイルを使う。

既定は、ローカルGitリポジトリで現在タスクの範囲だけを読取専用で差分検出する方式とする。branch、commit、pushは自動的に許可せず、既存プロジェクトの方針またはユーザーの明示的な指示がある場合だけ行う。

`wip/`全体はGit管理から除外しない。一次成果物、再現用スクリプト、検証結果を追跡できるようにし、一時物と機械状態だけを決められた場所へ隔離する。

## Operating Profiles

### Profile 0: Tool-independent

Gitもハッシュ計算も利用しない。`rules.md`のイベントチェックポイント、`context.md`、Human-in-the-loopだけで運用する。

すべての対応環境で利用できる最低ラインとする。

### Profile 1: Local detection

次を満たす場合に利用できる。

- Gitコマンドを実行できる
- 対象フォルダがローカルGitワークツリーである
- Gitメタデータと対象パスを読み取れる

リモート、認証情報、push権限は不要。現在タスクの対象パスへ限定して、`status`と`diff`による変更検出だけを行う。

これをGit利用時の既定プロファイルとする。

### Profile 2: Managed Git workflow

Gitを変更管理にも使う。既存のリポジトリ方針、またはユーザーが明示的に採用した方針がある場合だけ利用する。

branch作成、stage、commit、pushはそれぞれ別の権限として扱う。Profile 2が選択されただけでは、pushまで自動的に許可されたことにはならない。

## Task Scope

差分検出やハッシュ計算の対象は次に限定する。

- `_control/`の管理ファイル
- active task detail
- activeタスクとして`context.md`に記載されたローカルファイル
- activeタスク専用の成果物ディレクトリ

Gitリポジトリ全体の変更パスを無条件に列挙しない。可能ならGitのpathspecを使い、現在タスクの対象パスだけを確認する。

## Artifact Layout

task detailは従来どおり `wip/T-XXX_name.md` に置く。

複数ファイルからなるタスク成果物は、原則として次にまとめる。

```text
wip/T-XXX/
├── primary artifact
├── reproducibility asset
├── evidence
└── .tmp/
```

単一の成果物は `wip/` 直下に置いてもよい。

### Primary artifact

人がレビューし、承認後に`current/`へ移す候補。Git追跡対象かつ`context.md`対象とする。

### Reproducibility asset

成果物を再生成・検証するためのスクリプト、設定、入力定義。必要なものはGit追跡対象かつ`context.md`対象とする。

### Evidence

判断根拠として保持する集計結果や検査結果。レビュー・再検証に必要なものはGit追跡対象かつ`context.md`対象とする。

### Transient artifact

キャッシュ、一時ダウンロード、デバッグログ、作業用コピー、再生成可能でレビュー不要な中間生成物。`context.md`に追加せず、原則としてGit管理から除外する。

## Artifact Promotion and Reuse

タスク完了時にPrimary artifactだけを機械的に`current/`へ移さない。次の基準で分ける。

- 成果物の利用、保守、再編集、再現に継続して必要なファイル: Primary artifactと一緒に`current/`の成果物バンドルへ移す
- 承認判断の記録として残す一回限りのEvidence: `archive/T-XXX/`へ移す
- Transient artifact: 保存要件がなければ削除する

複数ファイルの成果物バンドルは、主ファイル、保守用アセット、関連Evidenceの保存先を短いREADMEで示す。最低限、`Primary`、`Maintenance`、`Related evidence`だけを記載する。

過去の成果物を別タスクで使う場合は、過去タスクのcontext行を復活させない。新しいTask IDとして、`current/`の成果物バンドルから必要なファイルを登録する。過去Evidenceも必要な場合だけ、`archive/T-XXX/`の特定ファイルを明示的に登録する。

再編集するときは、`current/`の成果物バンドルを入力として参照し、修正版と必要な保守アセットを新しいタスクの`wip/T-YYY/`へ作る。

## Ignore Policy

新規プロジェクト用テンプレートには、この仕組み固有の最小`.gitignore`を実ファイルとして含める。

この仕組み固有の最小推奨パターンは次だけとする。

```gitignore
wip/.context-state/
wip/T-*/.tmp/
```

言語・フレームワーク固有のキャッシュや生成物は、対象プロジェクトの規則に従う。`*.log`や`*.json`のような広すぎるパターンは、証拠データまで除外する可能性があるため標準には含めない。

テンプレートから新規プロジェクトを作成した後は、言語、フレームワーク、ビルドツールに合わせて`.gitignore`を拡張してよい。ただし、標準の2パターンを維持し、`_control/`、`current/`、`archive/`、`wip/`全体を除外しない。

既存プロジェクトへテンプレートを追加する場合は、既存`.gitignore`を上書きしない。標準の2パターンが必要なら、追加候補として提示して人の承認を受ける。

## Read-only Change Detection

次のイベントで現在タスクの対象パスだけを確認する。

- タスク開始・再開時
- レビュー依頼前
- タスク完了処理前

確認対象:

- 追跡済みファイルの変更・削除
- stage済み変更
- タスク専用成果物ディレクトリの未追跡ファイル

activeタスク内で予定どおり行った変更は確認不要とする。セッション外で発生した変更、理由不明の変更、入力や一次成果物への競合変更だけをユーザーへ確認する。

## Hash Fallback

Gitを利用できない場合は、現在タスクの対象ファイルごとにSHA-256を計算する。

スナップショットには次だけを保存する。

- 相対パス
- ファイルサイズ
- SHA-256

相対パスとハッシュを並べた一覧から集約ハッシュを作ってもよい。保存先は `wip/.context-state/T-XXX.json` とし、通常のLLM読込とGit管理の対象外にする。

ワークスペース全体や無関係な既存ソースコードはハッシュしない。

## Branch Strategy

### Existing repositories

既存のCONTRIBUTING、開発ガイド、保護ルール、既存branchを優先する。方針が不明な場合、LLMはbranchを作成・切替しない。

作業ツリーに既存変更がある場合、それを破棄、退避、stageしない。現在タスクと競合する場合だけユーザーへ確認する。

### New repositories with explicit opt-in

変更管理をLLMへ明示的に委任し、タスクが1つのまとまった変更単位に収まる場合は、短命branchの候補名を次とする。

```text
task/T-XXX-short-name
```

Task IDとbranchを常に1対1にすることは要求しない。大きなタスク、複数の独立した変更を含むタスク、既存のリリース運用がある場合は、プロジェクト方針または人の判断でbranch境界を決める。

branch作成自体もユーザーまたはプロジェクト方針による許可を必要とする。

## Authority Matrix

| Operation | Default |
|---|---|
| Gitリポジトリか確認 | LLMが実行可 |
| 対象パス限定のstatus・diff | LLMが実行可 |
| hash計算 | 対象範囲内でLLMが実行可 |
| `.gitignore`変更 | 候補提示後に承認 |
| stage | 明示的な許可が必要 |
| commit | 明示的な許可が必要 |
| branch作成・切替 | 明示的な許可が必要 |
| push・remote変更 | 明示的な許可が必要 |
| reset、clean、履歴改変 | 明示的な指示がない限り禁止 |

既存のプロジェクト方針が、より厳しい場合はそちらを優先する。

## Relationship to Directory Lifecycle

Git履歴は`wip/ → current/ → archive/`の状態表現を置き換えない。Gitを利用できないLLMや人も、ディレクトリだけで文書状態を判断できる状態を維持する。

Git commitの有無にかかわらず、承認前の成果物は`wip/`、承認済み成果物は`current/`、置換済み成果物は`archive/`に置く。
