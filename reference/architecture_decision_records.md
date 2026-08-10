# Architecture Decision Recordガイド

## 目的

ADRは、現在タスクの完了後も複数タスクへ影響し、将来その理由を再検討する必要がある重要な設計判断を残すための任意文書です。task detail、設計書、人の承認を置き換えません。

次のすべてに該当する場合だけ作成を検討します。

1. 決定が現在タスクの完了後も有効である
2. 選択肢、制約、trade-off、将来の見直し理由のいずれかを残す価値がある
3. 後続タスクが決定を参照する可能性が高い

軽微な実装選択、可逆的な試行、一回限りの承認、task detailだけで十分な判断には作成しません。

## 形式の選択

通常は小さいNygard形式を使います。複数案の比較、判断要因、確認方法まで必要な場合はMADR形式を使います。既存プロジェクトにADR形式がある場合は、その形式を優先します。

| 形式 | 適する判断 |
|---|---|
| Nygard | Context、Decision、Consequencesだけで理由を理解できる1つの判断 |
| MADR | 複数の選択肢やdecision driversを比較し、選択理由や確認方法を残す判断 |

## 配置と命名

- 草案：`wip/T-XXX/decisions/adr-T-XXX-short-title.md`
- 承認済みで有効：`current/decisions/adr-T-XXX-short-title.md`
- 却下された草案：必要なら`archive/T-XXX/decisions/`
- 置換済みの承認ADR：`archive/decisions/`

新しい連番管理ファイルは作らず、決定を作成したTask IDを識別子に使います。同じタスクで複数作る場合だけ`adr-T-XXX-01-...`のような枝番を付けます。

## statusと変更

使用できるstatusは`Proposed`、`Accepted`、`Rejected`、`Deprecated`、`Superseded by <path>`です。

草案は`Proposed`とし、人の承認後に`Accepted`へ変更して`current/`へ移します。Accepted後に決定の意味を変更する場合は上書きせず、新しいタスクとADRを作ります。旧ADRには置換先、新ADRには置換元の正確なパスを記載し、旧ADRを`archive/decisions/`へ移します。誤字やリンク修正など意味を変えない訂正は、通常の現行成果物修正手順で行えます。

## context登録

草案はactiveタスクの一次成果物としてcontextへ登録します。承認済みADRは常時読み込まず、その決定が入力として必要な後続タスクだけが正確な`current/decisions/...`を登録します。置換経緯が必要な場合だけ、特定のarchive ADRも登録します。

## Nygard形式（既定）

```markdown
# <短い決定名>

## Context

<判断が必要になった事実、制約、相反する力>

## Decision

<決定した内容を能動態で記載する>

## Status

Proposed

## Consequences

<良い結果、悪い結果、中立的な結果>
```

## MADR形式（比較が必要な場合）

```markdown
# <解決する問題と選んだ方針を表す短いタイトル>

## Status

Proposed

## Context and Problem Statement

<背景と解決する問い>

## Decision Drivers

- <判断要因。不要ならこの節を削除>

## Considered Options

- <選択肢1>
- <選択肢2>

## Decision Outcome

<選んだ案と理由>

## Consequences

- <良い、悪い、または中立的な結果>

## Confirmation

<決定が守られていることの確認方法。不要ならこの節を削除>
```

設計書に詳細な比較がある場合、ADRへ全文を複製せず、context登録可能な正確な参照先と最終判断だけを残します。

## 出典とライセンス

- Nygard形式：[Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)。原典は可能な範囲で著作権等が放棄されています。
- MADR形式：[MADR公式サイト](https://adr.github.io/madr/)。MADRはMITまたはCC0で利用できます。本ガイドのテンプレート要素はCC0の選択肢に基づき、ツール非依存の最小構成へ要約しています。
