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

## リリース

本プロダクトはSemantic Versioningを使い、タグ名を`vMAJOR.MINOR.PATCH`とします。互換性を判断する公開インターフェースには、ディレクトリと管理ファイルの役割、`rules.md`の運用契約、task・context・外部参照記述の形式、初期化・更新手順、付属ツールの文書化された入出力を含めます。

- MAJOR：既存プロジェクトに手動移行を要求する削除、改名、意味変更、既定の安全境界の非互換変更
- MINOR：既存運用を維持したまま利用できる機能、任意ガイド、後方互換な形式やツールの追加
- PATCH：意図する運用や文書化された入出力を変えない不具合修正、説明訂正、テスト修正

関連する変更は1つのReleaseへまとめられます。重大な不具合とsecurity fixは次のまとめを待たず、独立したPATCHまたは必要な互換性レベルで公開します。通常の個人運用ではrelease branchを作らず、承認済みPRを`main`へ取り込んだ後、その検証済みcommitにannotated tagを付けます。公開済みタグを付け替えません。

公開前に次を確認します。

1. Releaseへ含めるPRと利用者影響が確定している
2. `main`の対象commitと公開対象ファイルが一致している
3. 静的検証と`current/context-tools`の単体テストが成功している
4. 初期化、既存プロジェクト更新、保持対象、互換性への影響を確認している
5. Release notesに変更点、移行要否、検証結果、既知の制約、直前版を記載している
6. 人がtagとGitHub Releaseの公開を承認している

GitHub Releaseを公開変更履歴の正本とし、当面は別の`CHANGELOG.md`を作りません。不具合が判明した場合は公開済みタグを変更せず、影響をRelease notesへ明記し、修正版を新しい版として公開します。

## 秘密情報と個人情報

実在する認証情報、アクセストークン、署名付きURL、社内限定情報、不要な個人情報を、Issue、Pull Request、テスト、ログへ含めないでください。

## ライセンス

本リポジトリへ意図的に提出されたContributionは、別途明示しない限り、本リポジトリと同じMIT Licenseの条件で提供されるものとして扱います。
