<!-- project-directory-template:source-readme -->
# 複数プロジェクトの作業領域

必要な資料だけを読み、作業途中の資料と確定した成果物を分けて管理するための構成です。一つの作業領域に複数のprojectを置き、共通規則を一か所で管理します。

## はじめに

これはv2.0.0の作業領域版です。v1系を利用中の場合は、[旧版からの移行](reference/template_update_guide.md)を読み、既存環境へ一式を上書きしないでください。

新規作成ではGitHubの「Use this template」を利用できます。初回の自動処理はREADMEを作業領域用に変更し、配布元のLICENSEを`PROJECT_DIRECTORY_TEMPLATE_LICENSE`へ改名します。処理を利用できない場合は[手動初期化](reference/template_update_guide.md#新規作成時の手動初期化)に従ってください。既存環境の移行でこの初期化処理を実行しません。

このディレクトリ全体を、利用するLLMの作業対象として指定してください。同じ利用者・LLM・プログラムに見せてよい情報だけを入れます。閲覧権限の異なる案件は別の作業領域に分け、アクセス権限は利用環境で設定してください。Markdownの規則は、技術的なアクセス制限にはなりません。

新規利用時は、次の指示から始めます。

> 最初に`_control/rules.md`を読み、その規則に従って、新規projectの作成と初期化を進めてください。

Project IDを決め、背景・目的・目標を初期化タスクで整理します。既存projectを再開する場合は、次のように対象を指定します。

> 最初に`_control/rules.md`を読み、Project ID「対象のID」の作業を再開してください。

## 配置

| 場所 | 内容 |
|---|---|
| `_control/` | 共通規則・管理表・ガイド・管理プログラム。管理作業の途中資料は`wip/`、完了記録は`archive/` |
| `projects/<project-id>/` | 案件ごとの定義・タスク・成果物・参照資料 |
| `library/` | 全projectで共通利用する資料・スキル |
| `profiles/<profile-id>/` | 利用者固有の手順・素材・スキル。必要時に作成 |

各projectは`_control/`、`wip/`、`current/`、`reference/external/`、`archive/discarded/`を持ちます。project用の`rules.md`は作らず、共通規則を使います。既存ソースコード等の配置を一律に変更する仕組みではありません。

通常の作業で全project・全資料を読み込ませる必要はありません。開始時の選択と、対象タスクの入力一覧に従って必要な資料を読みます。

## 必要な機能

基本操作はMarkdownの読み書きで行え、PythonやGitは必須ではありません。成果物の確定・反映・完了等は、規則に従って人の承認を得ます。

同じPC・同じアプリの複数チャットで管理情報を並行更新する場合は、[共有管理操作の手順](_control/tools/shared_operations/README.md)に従ってください。対応する操作だけPython 3.10以降とOSのロック機能を使います。未対応の操作は、関係する書込みを止めて行います。別PC・別アプリ・同期サービスをまたぐ同時更新の安全性は保証しません。

## 既存環境への導入

共通機構の更新案を作る場合は、次のように指示できます。

> `_control/rules.md`に従い、`library/current/skills/template-update/SKILL.md`を使って既定更新元から更新案を作成してください。反映は承認まで行わないでください。

利用中の問題を報告する場合は、`library/current/skills/product-feedback/SKILL.md`を指定して下書きを依頼できます。どちらも正確なファイルを読ませる入口であり、この配置だけで各アプリへ自動登録されるとは限りません。

この一式を既存環境へ上書きコピーしないでください。ルート・既存コード・README・固有資料を保持する配置対応と復元手順を用意し、承認後に切り替えます。作業環境の移行と、公開する製品の更新は別の操作です。

## 確認範囲と版の選択

ChatGPT Workの単一チャットで、project作成、承認後の初期化、パスで指定したフィードバックスキルの利用、成果物配置とタスク完了を1回確認しています。全モデル・全アプリ、自動スキル発見、実コネクタ、同時更新を確認した結果ではありません。実消費トークンや料金の削減は測定していません。

安定版は[GitHub Releases](https://github.com/Keiichiro-Tsukamoto/project-directory-template/releases)のタグで固定します。「Use this template」はmainを参照するため、同じ版の再現にはReleaseのSource codeを使用してください。v1系の公開済みタグは保持し、v2への自動移行は行いません。
