# 作業領域の導入と更新

保守対象は[対応バージョン](../_control/reference/operation_guide.md#対応バージョン)を参照してください。利用中の環境へ配布一式を上書きしないでください。

## 利用中の作業領域を更新する

現在の共通規則に従い、[更新スキル](../library/current/skills/template-update/SKILL.md)を指定して更新案を作ります。管理表・進行中タスク・固有資料を保持し、新規初期化をやり直しません。

別の作業領域内のprojectを追加する場合は、[既存projectの取込手順](../_control/reference/operation_guide.md#既存projectを取り込む)を使います。

## 新規作成時の手動初期化

これは未利用の新規コピーだけに適用します。GitHubの自動初期化が未実施なら、READMEが未編集であることを確認し、`.github/project-readme.md`の`{{PROJECT_NAME}}`を作業領域名へ置き換えてREADMEとします。`LICENSE`を`PROJECT_DIRECTORY_TEMPLATE_LICENSE`へ改名し、配布元専用の`.github/project-readme.md`、`.github/workflows/initialize-project-readme.yml`、`CONTRIBUTING.md`、`SECURITY.md`を削除します。削除できない環境では規則に従って隔離します。Gitへの記録には別途承認が必要です。

READMEを編集済み、既存の同名ライセンスがある、導入済みのタスク・成果物がある場合はこの初期化を実行せず、個別統合を依頼してください。
