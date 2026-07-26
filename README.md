<!-- project-directory-template:source-readme -->
# Project Directory Template

## 本プロダクトが解決する課題

LLMと長期間プロジェクトを進めると、過去資料や無関係なファイルの読み込みによるトークン消費、古い方針の混入、成果物の現行版が分からないといった問題が起こりやすくなります。

このテンプレートは、タスクごとに必要なファイルだけをLLMへ渡し、作業中・現行・旧版を明確に分けます。人による承認を保ちながら、コンテキスト量、モデル利用コスト、確認時間を抑えたい個人のプロジェクト作業に利用できます。

## 本プロダクトの仕組み

以下の仕組みにより、人とLLMの両方がファイルの役割と状態を理解しやすい形で、コンテキスト量と管理コストを抑えます。

1. `_control/context.md`に、進行中のタスクで参照すべきファイルの一覧を管理し、LLMはその一覧にあるファイルだけを読みます。
2. 成果物を`wip/`（作業中）、`current/`（現行）、`archive/`（旧版）へ分け、参照すべき版をディレクトリ上でも判別できるようにします。
3. Git差分またはハッシュ比較を使い、人が管理ファイル、入力資料、成果物を変更した場合にも早期に検出できるようにします。
4. ファイル確認や定型作業には、決定的なツールまたは必要条件を満たす低コストモデルを優先し、モデル利用コストを抑えます。

## 本プロダクトの導入方法

### 0. 導入方法を選ぶ

次のいずれかへ進みます。

- 新規プロジェクトでGitを使わない：1-A → 2
- 新規プロジェクトでGitを使う：1-B → 2
- 既存プロジェクトへ追加する：1-C → 2
- 旧版テンプレートを利用中のプロジェクトを更新する：1-D

Python 3がなくても基本運用は可能です。付属の静的検証とハッシュ比較を使う場合はPython 3が必要です。外部リソース連携とモデル分業は任意です。

このREADMEではPythonの実行コマンドを`python3`と表記しています。利用環境に応じて`python`または`py`へ読み替えてください。

### 1-A. 新規プロジェクトへ導入する（Gitを使わない場合）

隠しファイルの`.gitignore`を含め、テンプレートの内容を新しいプロジェクトルートへコピーします。

コピー後、プロジェクト固有の初期状態へ切り替えます。

1. `LICENSE`を`PROJECT_DIRECTORY_TEMPLATE_LICENSE`へ改名します。
2. `.github/project-readme.md`を基に、プロジェクト名を反映したルートREADMEを作ります。
3. `.github/project-readme.md`、`.github/workflows/initialize-project-readme.yml`、`CONTRIBUTING.md`、`SECURITY.md`を削除します。

`PROJECT_DIRECTORY_TEMPLATE_LICENSE`はテンプレート由来部分のMIT License表示です。派生プロジェクト全体のライセンスは、必要に応じて別のルート`LICENSE`として設定します。準備後、「2. プロジェクトを初期化する」へ進みます。

変更検出には、付属のハッシュツールを利用できます。

```text
python3 current/context-tools/context_snapshot.py snapshot
python3 current/context-tools/context_snapshot.py check
```

### 1-B. 新規プロジェクトへ導入する（Gitを使う場合）

GitHub上でこのリポジトリの「Use this template」から作成した場合、作成直後に`Initialize project README` workflowが1回だけ動作します。workflowは新しいリポジトリ名を見出しにしたプロジェクト用READMEへ切り替え、元テンプレートの`LICENSE`を`PROJECT_DIRECTORY_TEMPLATE_LICENSE`へ改名し、配布元専用のCONTRIBUTING、SECURITY、初期化workflow、READMEひな型を削除してコミットします。完了後は「2. プロジェクトを初期化する」へ進みます。

READMEが`Project Directory Template`のままの場合は、新しいリポジトリのActions画面で`Initialize project README`の実行結果を確認してください。作成時にGitHub Actionsが無効だった場合は、有効化後にこのworkflowを手動実行できます。書き込み権限またはデフォルトブランチへの直接pushがポリシーで禁止されている場合、自動初期化は失敗します。その場合はREADMEをプロジェクト用の内容へ手動で置き換え、`LICENSE`を`PROJECT_DIRECTORY_TEMPLATE_LICENSE`へ改名し、`.github/project-readme.md`、`.github/workflows/initialize-project-readme.yml`、`CONTRIBUTING.md`、`SECURITY.md`を削除してコミットします。既にREADMEを編集した場合や追加コミットがある場合、workflowは誤上書きを避けるため何も変更しません。

GitHubのテンプレート機能を使わずローカルへコピーする場合は、テンプレートを新しいプロジェクトルートへコピーし、ルートREADMEをプロジェクト用に置き換え、`LICENSE`を`PROJECT_DIRECTORY_TEMPLATE_LICENSE`へ改名し、`.github/project-readme.md`、`.github/workflows/initialize-project-readme.yml`、`CONTRIBUTING.md`、`SECURITY.md`を削除してから、その場所でGitを初期化します。

```text
git init
git status --short
```

初回はファイルが`??`と表示されます。秘密情報や不要な生成物がないことと、`.gitignore`の内容を確認してから初期baselineを作ります。

```text
git add .
git diff --cached --stat
git commit -m "Initialize project"
```

stageとcommitは人が実行するか、LLMへ対象と操作を明示的に許可します。Gitはローカルの差分検出だけでも利用でき、リモートやpush権限は必須ではありません。完了後は「2. プロジェクトを初期化する」へ進みます。

### 1-C. 既存プロジェクトへ導入する

既存のソースコード、設定、テスト、アセットの構成は変更せず、テンプレートの管理用ディレクトリとファイルを追加します。同名の管理ファイルやディレクトリが既にある場合は上書きせず、内容と運用方針を確認してから統合します。既存リポジトリでは`git init`を実行しません。

既存のルートREADME、`LICENSE`、CONTRIBUTING、SECURITYを上書きしません。テンプレート共通ファイルを取り込む場合は、元テンプレートの`LICENSE`を`PROJECT_DIRECTORY_TEMPLATE_LICENSE`という名前で追加し、テンプレート由来部分の表示として保持します。既存プロジェクト全体のライセンスは変更しません。

```text
git status --short
git branch --show-current
```

既存の`.gitignore`、CONTRIBUTING、開発ガイド、ブランチ方針を優先します。既存の`.gitignore`を上書きせず、必要に応じて次の2行だけを統合します。

```gitignore
/wip/.context-state/
/wip/T-*/.tmp/
```

追加後は「2. プロジェクトを初期化する」へ進みます。

### 1-D. 旧版テンプレートを利用中のプロジェクトを更新する

既存プロジェクトのルートREADME、ルート`LICENSE`、`_control/project.md`、`tasks.md`、`context.md`、進行中タスク、成果物を保持したまま、テンプレート共通ファイルだけの更新候補をWIPへ作ります。MIT公開版へ更新する場合は、元テンプレートの`LICENSE`を既存プロジェクトの`PROJECT_DIRECTORY_TEMPLATE_LICENSE`として追加または更新します。最新版テンプレート一式を既存プロジェクトへ上書きしないでください。

最新版テンプレートをローカルへ用意し、その正確な場所を指定してLLMへ次の指示を渡します。

> この既存プロジェクトのルート位置とディレクトリ構造は変更せず、`<最新版テンプレートの場所>`を更新元として、必要なテンプレート共通ファイルだけを取り込む更新案を作成してください。最初にこのプロジェクトの`_control/rules.md`を読み、既存のactiveタスクがある場合は勝手に置き換えず、更新タスクの開始方法を提案してください。更新タスク開始後、指定場所と参照する更新元ファイルをWIP参照記録にしてcontextへ登録し、更新元の`reference/template_update_guide.md`に従ってください。プロジェクト固有ファイルとルートREADMEを保持し、現行ファイルを直接変更せず、最初にWIPへ更新候補、変更対象、保持対象、競合、検証方法、ロールバック方法を作成してください。最新版テンプレートへ移動したり、最新版テンプレート一式をこのプロジェクト内へコピーしたりしないでください。承認を受けるまで対応パスへの反映、削除、Git変更を行わないでください。

LLMは指定場所を更新元として記録し、変更対象と保持対象を提示します。競合がある場合はそこで停止します。WIPの候補と検証結果を確認してから、反映するファイルを承認してください。

詳しい分類、検証、ロールバックは`reference/template_update_guide.md`を参照してください。この更新手順は既存プロジェクトの初期化をやり直すものではないため、「2. プロジェクトを初期化する」には進みません。

### 2. プロジェクトを初期化する

LLMへ次の指示を渡します。

> このフォルダを作業ディレクトリとして扱ってください。最初に `_control/rules.md` を読み、その後はルールに従い、必要なファイルだけを読んでください。プロジェクト全体を勝手にスキャンせず、`tasks.md` の `active` タスクに従ってください。

初期状態では`T-001: Initialize project`が用意されています。LLMから確認を受けながら、プロジェクトの背景、目的、達成目標を伝えます。作成された`_control/project.md`を確認し、問題がなければ承認します。

付属ツールを利用できる場合は、初期化後にテンプレートの整合性を確認します。

```text
python3 current/context-tools/validate_template.py . --output wip/T-001/validation.json
```

## 本プロダクトの使い方

### 1. ディレクトリの役割を確認する

```text
workspace/
├── _control/   プロジェクト、タスク、参照ファイル、ルールの管理
├── wip/        作業中・承認待ちの成果物
├── current/    現在有効な成果物と任意ツール
├── reference/  必要な場合だけ読む参考資料
└── archive/    旧版・完了済み・置換済み資料
```

通常、人が主に確認するのは、作業依頼の内容を記したtask detail fileと、LLMが作成した`wip/`の成果物です。`_control/rules.md`は運用上の正本であり、READMEと内容が食い違う場合は`rules.md`を優先します。

### 2. LLMへ作業を依頼する

作業の目的、完了条件、参照してほしいファイルを伝え、LLMへ新しいタスクの登録を依頼します。既にタスクが進行中の場合は、完了または中断の扱いを決めてから次のタスクを開始します。

参照してほしいファイルが後から増えた場合は、そのファイルを現在タスクの`context.md`へ追加するよう依頼します。`context.md`は、LLMが今回のタスクで正式な入力として扱う既存ファイルを示します。ディレクトリに置かれているだけの未登録ファイルを、LLMが勝手に探索または採用することはありません。

登録済み入力だけではGoalを正確に達成できない場合、LLMは不足している情報、必要な理由、受入可能な形式をまとめて提言します。

- 既存ファイルがある場合：正確なパスを示し、現在タスクのcontextへ登録してから作業を続けます。
- 必要な入力をまだ持っていない場合：入力を作成する別タスクを追加できます。元タスクを`blocked`、入力作成タスクを`active`として進め、入力完成後に元タスクへ戻ります。
- 入力を作らない場合：Goal、前提、受入条件を見直します。

登録済み入力を使った解決方法、ツール選択、WIPでの可逆的な試行はLLMへ任せられます。contextによる入力管理は、解決手順を細かく固定するためのものではありません。

### 3. 成果物を確認する

LLMが作成した`wip/`の成果物を確認します。

- 問題がある場合：同じタスクのまま修正を依頼します。
- 問題がない場合：成果物の確定とタスク完了を明示的に承認します。

承認すると、LLMは継続利用する成果物を`current/`へ移し、旧版や完了資料を`archive/`へ整理します。承認前の成果物が自動的に現行版になることはありません。

### 4. 現行成果物の修正を依頼する

修正対象となる`current/`のファイルを指定し、新しいタスクとして修正を依頼します。LLMは現行版を直接変更せず、修正版を`wip/`へ作成します。

修正版を承認すると、旧現行版が`archive/`へ移り、修正版が`current/`になります。過去タスクの成果物を再利用したい場合も、対象ファイルを新しいタスクの入力として指定します。

### 5. 必要に応じて変更を確認する

Gitを使う場合は、現在タスクの管理ファイル、入力、成果物に対象を限定して差分を確認します。

```text
git status --short -- _control wip/T-XXX_name.md wip/T-XXX path/from/context.md
git diff --name-status -- _control wip/T-XXX_name.md wip/T-XXX path/from/context.md
```

Gitを使わない場合、またはGitと独立して確認したい場合はハッシュ比較を利用します。

```text
python3 current/context-tools/context_snapshot.py snapshot
python3 current/context-tools/context_snapshot.py check
```

理由が分からない変更が検出された場合は、作業を続ける前にLLMへ変更理由の確認を依頼します。

### 6. 必要に応じて外部資料を指定する

ConfluenceやGoogle Driveなどの外部資料を使う場合は、対象、取得範囲、使用する版をLLMへ伝え、`reference/external/`の参照記述を作成するよう依頼します。外部のドライブ、サイト、フォルダ全体を探索させないでください。

外部リソースの閲覧権限は、変更やローカル保存の許可を意味しません。外部への書き込みは、更新先と操作を確認したうえで明示的に承認します。アクセストークンや認証情報をプロジェクトファイルへ記録しないでください。

### 7. 必要に応じてモデル分業を指定する

モデルを選べる環境では、ファイル確認、形式修正、既知仕様の検査など、範囲と合否が明確な作業を低コストモデルへ委譲できます。新規設計、規則の矛盾、高影響で検証困難な判断には上位モデルを使います。

人が個別のモデルを指定しなくても、`rules.md`に従って適切な方法を選ぶようLLMへ依頼できます。品質に不安がある場合は、使用モデル、検証結果、再作業の有無を確認してください。

### 8. 問題が発生した場合

- 必要な資料が読み込まれていない：対象ファイルを明示し、現在タスクの`context.md`へ追加するよう依頼します。
- 必要な入力がまだ存在しない：入力作成タスクを追加するか、Goalや受入条件を見直します。
- 古い成果物が使われている可能性がある：正とするファイルを推測させず、人が対象を指定します。
- 無関係なGit差分がある：破棄や退避をさせず、対象と変更理由の説明を求めます。
- 外部資料へアクセスできない：未登録の代替情報源を使わせず、必要な権限やスナップショットを確認します。
- 委譲した作業を検証できない：推測で続けさせず、上位モデルまたは人へ判断を戻します。

LLMの具体的な読み込み順、タスクのライフサイクル、context登録基準、検証方法は`reference/operation_guide.md`に分離しています。通常は読む必要がなく、運用確認や問題調査が必要な場合だけ参照します。

## コントリビューション

不具合、改善提案、Pull Requestを受け付けています。公開Issueや変更を作成する前に`CONTRIBUTING.md`を確認してください。

## セキュリティ

脆弱性や秘密情報を公開Issueへ投稿しないでください。非公開の報告方法は`SECURITY.md`を確認してください。

## ライセンス

本成果物はMIT Licenseで公開します。詳細は`LICENSE`を確認してください。

Copyright (c) 2026 塚本 圭一郎 (Keiichiro Tsukamoto)

## 本プロダクトの問い合わせ先

- 作成者：塚本 圭一郎 (Keiichiro Tsukamoto)
- 問い合わせ先：本リポジトリのGitHub Issues

問い合わせ時は、利用環境、現在のTask ID、発生した事象、実行した検証とその結果を添えてください。秘密情報や認証情報は含めないでください。

## 補足事項

Git、Pythonツール、外部コネクタ、モデル選択・並列実行は任意です。利用できない機能があっても、対象限定の`context.md`、成果物の状態分離、人による承認を使った基本運用は可能です。

詳細が必要な場合だけ、対象ファイルを`context.md`へ登録して参照します。

- 日常運用、タスクライフサイクル、context登録、検証：`reference/operation_guide.md`
- 旧版テンプレート利用プロジェクトの更新：`reference/template_update_guide.md`
- Git、成果物分類、権限、ハッシュ方式：`reference/git_artifact_management.md`
- 外部リソースの取得、変更検出、エラー処理：`reference/external_resource_context.md`
- モデル階層、作業票、並列化、エスカレーション、評価：`reference/model_routing_and_delegation.md`

テンプレートの`.gitignore`は、言語、フレームワーク、IDE、ビルドツールに合わせて拡張できます。ただし、`_control/`、`current/`、`archive/`、`wip/`全体を一括で除外しないでください。
