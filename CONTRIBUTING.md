# コントリビューションガイド

## 改善提案

`library/current/skills/product-feedback/SKILL.md`を指定して下書きを作成できます。独立した問題は分け、観測・期待・再現条件・未確認事項を記載してください。機密情報や脆弱性は公開Issueに記載せず、[セキュリティポリシー](SECURITY.md)に従ってください。

## Pull Request

変更目的と対象を明示し、無関係な変更を混ぜないでください。PR本文とリリース説明は日本語で記載します。作業領域版の検証入口は次のとおりです。

```text
python3 -B _control/tools/shared_operations/validate_workspace.py --root .
python3 -B -m unittest discover -s _control/tools/shared_operations -p 'test_workspace.py'
```

基本操作にPythonは必須ではありませんが、これらの機械検証にはPython 3.10以降とOSのロック機能が必要です。並行更新の実行条件は[管理操作の手順](_control/tools/shared_operations/README.md)で確認してください。機械検証を実行できない場合は、未実施と手動確認の範囲を報告してください。

管理表の検証だけでは、文章の意味、外部接続、各アプリの操作や並行更新の安全性は保証しません。変更した機能に関係する確認を追加し、未確認事項を明記してください。

## 公式スキルの更新

- 公式スキルの正本は、本リポジトリの`library/current/skills/`に置きます。取り込み元の個人版とは自動同期しません。
- 更新は通常の製品変更と同様に、WIPで修正案を作り、変更に応じた検証を行ってPRで確認します。
- 利用中の作業領域への配布は、既存の[テンプレート更新手順](reference/template_update_guide.md)を使います。利用者のカスタマイズを無断で上書きしません。

スキル単独の版番号や変更履歴は設けず、製品のGit履歴とリリースで管理します。

## リリース

Semantic Versioningを使い、タグは`vMAJOR.MINOR.PATCH`とします。公開インターフェースには配置、管理ファイルの役割と形式、規則、初期化・更新手順、付属プログラムの入出力を含めます。

- MAJOR：手動移行を要する削除・改名・意味変更・非互換変更
- MINOR：既存運用を維持できる追加
- PATCH：意図した運用や入出力を変えない修正

検証済みPRのmainへのマージ後、対象commitと配布ファイルを照合し、人の承認を得て注釈付きタグとGitHub Releaseを公開します。公開済みタグを付け替えません。GitHub Releaseを公開変更履歴の正本とし、変更点、移行要否、検証結果、既知の制約、直前版を記載します。重大な不具合・脆弱性は通常のまとめを待たず修正版を出します。

保守対象は[対応バージョン](_control/reference/operation_guide.md#対応バージョン)を参照してください。公開候補には開発project、試験データ、個人情報、秘密情報を含めないでください。

## ライセンス

本リポジトリへ意図的に提出されたContributionは、別途明示しない限り、本リポジトリと同じMIT Licenseの条件で提供されるものとして扱います。
