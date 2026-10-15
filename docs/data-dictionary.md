# 正規化CSV仕様

`data/processed/elections.csv` は原則として **年×州×議院×選挙区×選挙イベント** に1行。

|列|型|意味|
|---|---|---|
|year|integer|選挙年度|
|state|string|州略号|
|chamber|string|House または Senate|
|district|string|下院区番号、上院は STATEWIDE|
|primary_rep_votes|integer|共和党候補のPrimary票数合計|
|primary_dem_votes|integer|民主党候補のPrimary票数合計|
|general_rep_votes|integer|共和党候補のGeneral票数合計|
|general_dem_votes|integer|民主党候補のGeneral票数合計|

追加推奨: `election_id`（特別選挙との識別）、`election_rule`（top-two等）、`source_file`、`exclude_reason`。

**この列構成は研究用独自スキーマであり、FECの原ファイルに同名列があるとは限らない。**

確認事項:
- 候補者の重複・政党の違い・cross-filingの扱い
- 通常選挙と特別選挙の重複キー
- 負数、欠損、未報告、小数票、投票数が0のイベント
- 無対立選挙、Top-two形式、特殊な選挙制度
- 元ファイルとの票数照合、除外理由と除外件数の保存
