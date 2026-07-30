# 外部リソース実行時状態

- 参照記述: <reference/external/...md>
- 確認日時: <ISO 8601、タイムゾーン付き>
- 取得モード: <live | pinned | snapshot>
- 鮮度確認方法: <revision | updated-at | content-hash | refetch | not-applicable>
- 取得範囲: <実際に確認、取得、利用した範囲>
- 前回リモート更新指標: <revision、version、ETag、更新日時、hash。なければ空欄>
- 今回リモート更新指標: <revision、version、ETag、更新日時、hash。取得不能なら理由>
- 更新指標一致: <一致 | 不一致 | 対象外 | 確認不能>
- 本文取得: <未実施 | 登録範囲を取得 | 必要部分を取得 | snapshot利用 | 取得不能>
- 前回対象範囲hash: <同じ正規化方法によるhash。なければ空欄>
- 今回対象範囲hash: <同じ正規化方法によるhash。未取得なら空欄>
- 対象範囲一致: <一致 | 不一致 | 対象外 | 確認不能>
- 利用元: <remote取得 | cache再利用 | snapshot利用 | なし>
- cache更新指標: <cache再利用時のrevision、更新日時、hash。それ以外は空欄>
- 現在版として利用: <可 | 不可 | 対象外>
- LLM入力: <再入力なし | 必要部分のみ | 登録範囲全体 | 旧版利用 | 入力せず停止>
- 結果と判断理由: <取得、再利用、再入力範囲、停止、旧版利用を選んだ理由>
- エラーと代替判断: <なければ空欄。秘密情報を記載しない>
