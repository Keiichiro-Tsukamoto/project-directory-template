# コントリビューションガイド

Project Directory Templateへの改善提案を歓迎します。

## Issue

不具合や改善案はGitHub Issuesへ投稿してください。利用環境、対象ファイル、再現手順、期待する結果、実際の結果を含めると確認しやすくなります。

脆弱性や秘密情報を含む報告は公開Issueへ投稿せず、`SECURITY.md`に従ってください。

## Pull Request

1. 変更の目的と対象範囲を明確にします。
2. 無関係な整形や別目的の変更を混ぜません。
3. テンプレートのルールとガイドに矛盾がないことを確認します。
4. 次の検証を実行します。

```text
python3 current/context-tools/validate_template.py .
python3 -m unittest discover -s current/context-tools -p 'test_*.py'
```

Pythonのコマンド名は環境に応じて`python`または`py`へ読み替えてください。

## 秘密情報と個人情報

実在する認証情報、アクセストークン、署名付きURL、社内限定情報、不要な個人情報を、Issue、Pull Request、テスト、ログへ含めないでください。

## ライセンス

本リポジトリへ意図的に提出されたContributionは、別途明示しない限り、本リポジトリと同じMIT Licenseの条件で提供されるものとして扱います。
