# {{PROJECT_NAME}}

複数のprojectを管理する作業領域です。同じ利用者・LLM・プログラムに見せてよい情報だけを置き、アクセス権限の異なる案件は別の作業領域へ分けてください。

## 作業を始める

このディレクトリ全体をLLMの作業対象として指定し、次の指示を渡してください。

> 最初に`_control/rules.md`を読み、その規則に従って、新規projectの作成と初期化を進めてください。

既存projectを再開する場合は、次のように指定します。

> 最初に`_control/rules.md`を読み、Project ID「対象のID」の作業を再開してください。

案件の背景・目的・目標は各projectで管理します。基本操作にPythonやGitは必須ではありません。共有管理情報の並行更新を行う場合は、[管理操作の手順](_control/tools/shared_operations/README.md)に従ってください。

## 別の既存projectを取り込む

複数の既存projectをこの作業領域へ集める場合は、次の指示を渡してください。先に`projects/`へコピーする必要はありません。

> 最初に`_control/rules.md`を読んでください。別の既存projectをこの作業領域へ取り込みたいので、作業領域管理タスクで取込案を作成してください。`_control/reference/operation_guide.md`の「既存projectを取り込む」に従い、まずコピーを置く受入場所と、私が用意するものを案内してください。元資料は保持し、反映・削除・Git変更は承認まで行わないでください。

人が案内された管理WIPへ取込元のコピーを置き、その場所と希望するProject IDを伝えます。タスクと成果物はprojectごとに保持し、既定ではGit履歴を統合しません。詳しくは[取込手順](_control/reference/operation_guide.md#既存projectを取り込む)を参照してください。

## 更新とフィードバック

> `_control/rules.md`に従い、`library/current/skills/template-update/SKILL.md`を使って既定更新元から更新案を作成してください。反映は承認まで行わないでください。

フィードバックは`library/current/skills/product-feedback/SKILL.md`を指定して下書きを依頼できます。外部投稿は別途承認します。v1系から移行する場合は[移行案内](reference/template_update_guide.md)に従い、一式を上書きしないでください。

## ライセンス

`PROJECT_DIRECTORY_TEMPLATE_LICENSE`はテンプレート由来部分のMIT Licenseです。この作業領域内の独自資料・各project全体を自動的にMITへ変更するものではありません。
