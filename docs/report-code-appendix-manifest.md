# Issue #87 — レポートのPythonソース付録収録範囲の確定

**状態:** 収録範囲を確定（#69-A）。私有DOCXへの貼込は[#88](https://github.com/SMRI2170/fec-election-analysis/issues/88)で行う。

**原則: 抜粋しない。** 実行に必要な自作ソースは**全文**を付録に収録する。分量が大きくても、勝手に数行へ縮めて「全ソース」と称しない。容量とページ数の影響は**先に算定**する。

## 1. レポート表・図 → ソース全文 → 実行コマンド → 出力

|レポート内の表・図|内容|生成スクリプト（全文収録）|実行コマンド|出力|
|---|---|---|---|---|
|**表1**|母数の3段階（1,756報告グループ→1,734 50州Voting House→916件）と年度別内訳|`scripts/inspect_selective_cohort.py`（`src/fec_analysis/selective.py`を使用）|307|11,736|
|**表2**|既存ベースラインの年度外評価（線形回帰MAE・多数派規則accuracy・Logistic accuracy）|`scripts/run_backtests.py`（`scripts/analyze.py`を使用）|81|4,124|
|**表3**|判定保留15条件のcoverage–risk（accepted/abstained/risk/放棄した正答）|`scripts/evaluate_selective_primary.py`（`src/fec_analysis/selective.py`, `scripts/selective_primary_rule.py`を使用）|307|11,736|
|**表4**|同数ランダム保留との比較（期待誤答・回避件数・探索的p値）|`scripts/compare_random_abstention.py`|364|13,169|
|**図1**|予備選挙比率と本選挙比率の散布（2022年）＋線形予測線|`scripts/plot_results.py`|108|4,423|
|**図2**|年度外MAE比較（2018/2020/2022）|`scripts/plot_results.py`|108|4,423|
|**図3**|判定率–誤答率図（2018/2020/2022＋同数ランダム保留の期待risk水平線）|`scripts/plot_selective_primary.py`|312|11,338|
|**図4**|観測誤答数と同数ランダム保留の期待値の比較|`scripts/plot_selective_primary.py`|312|11,338|

### 付録に収録する13ファイル（全文）

|#|ファイル|役割|行数|バイト|
|---:|---|---|---:|---:|
|1|`scripts/download_fec.py`|公式FECワークブック取得とSHA-256記録|82|3,618|
|2|`src/fec_analysis/core.py`|正規化レコードの検証と二党得票率|61|2,786|
|3|`scripts/normalize_fec.py`|保守的な選別（1,756→916）|209|11,786|
|4|`scripts/analyze.py`|ベースライン評価（回帰・分類・多数派規則）|81|4,124|
|5|`scripts/run_backtests.py`|年度外バックテスト実行|42|1,576|
|6|`scripts/verify_reproducibility.py`|再現マニフェスト作成と固定値照合|101|5,458|
|7|`src/fec_analysis/selective.py`|評価母数の凍結契約と監査|307|11,736|
|8|`scripts/inspect_selective_cohort.py`|母数監査CLI|137|4,856|
|9|`scripts/selective_primary_rule.py`|判定保留の純粋関数（General非参照）|154|6,047|
|10|`scripts/evaluate_selective_primary.py`|15条件のcoverage–risk評価|418|15,728|
|11|`scripts/compare_random_abstention.py`|同数ランダム保留との比較|364|13,169|
|12|`scripts/plot_results.py`|散布図・年度外MAE図|108|4,423|
|13|`scripts/plot_selective_primary.py`|判定率–誤答率図・ランダム保留比較図|312|11,338|
|**合計**||||**2,466**|**100,646**|

（バイト数は実測値。`python scripts/build_code_appendix.py` が毎回再計算する。）

### 収録**しない**もの（理由）

|対象|理由|
|---|---|
|ライブラリ内部ソース（numpy/scikit-learn/pandas等）|第三者のコードであり「本人のプログラム」ではない|
|`.github/workflows/*.yml`|CIの実行環境であり、報告された数値を生成する処理ではない。再実行手順は本文と本manifestに記述する|
|`tests/test_*.py`|品質保証のためのテストであり、報告値の生成には不要。**再検証には必要**なので、GitHub上のリポジトリを付録の参照先として明記する|
|公式FEC Excel原本|**無断で同梱しない**（URLとSHA-256のみ記載）|
|他者の既存コード|原著・出典を明記して引用し、自作部分と区別する|

## 2. 実行環境のmanifest

|項目|値|
|---|---|
|Python|`3.11`（CI）、`3.12.13`（開発時のローカル環境でも同一結果を確認）|
|依存|`numpy>=1.26,<3` / `pandas>=2.2,<3` / `scikit-learn>=1.5,<2` / `matplotlib>=3.8,<4` / `openpyxl>=3.1,<4` / `pytest>=8,<10` / `xlrd>=2.0.1,<3`（`requirements.txt`）|
|ランダムseed|本研究の集計は**すべて決定的**（学習なし・乱数なし）。`analyze.py`のLogistic回帰のみ`random_state=0`|
|公式FEC出典|https://www.fec.gov/documents/1890/federalelections2016.xlsx（SHA-256 `b4a1d138…9782eb6`）、https://www.fec.gov/documents/2706/federalelections2018.xlsx（`f2c42311…1e0e303`）、https://www.fec.gov/documents/4228/federalelections2020.xlsx（`5073b6d2…c19352e`）、https://www.fec.gov/documents/5676/federalelections2022.xlsx（`cdb258ea…c2350897`）|

### 実行順（連続した1本の再現手順）

```bash
python -m pip install -r requirements.txt
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022 --writein-policy attribute
python scripts/run_backtests.py --input data/processed/elections.csv --test-years 2018 2020 2022
python scripts/verify_reproducibility.py
python scripts/inspect_selective_cohort.py --output data/processed/selective-cohort-audit.json
python scripts/evaluate_selective_primary.py
python scripts/compare_random_abstention.py
python scripts/plot_results.py --input data/processed/elections.csv --metrics data/processed/backtest_metrics.csv
python scripts/plot_selective_primary.py
python -m pytest -q
```

### 各ファイルのcommit SHA（付録見出しに併記する）

|ファイル|commit SHA|
|---|---|
|`scripts/download_fec.py`|`1066b9d9e73a94db1fde19cccb65691d88f2ce73`|
|`src/fec_analysis/core.py`|`083681c8150d4dc028e9284fb628ffc0e2763917`|
|`scripts/normalize_fec.py`|`0de3b7c3bac82fb541fcfb3140c60736ff9e1d3c`|
|`scripts/analyze.py`|`1f6e05fb5ba8bed28a7c79945b791399d6583b5e`|
|`scripts/run_backtests.py`|`1f6e05fb5ba8bed28a7c79945b791399d6583b5e`|
|`scripts/verify_reproducibility.py`|`65b63d00b37b95dfc0e9609e893b53ca63b42ad7`|
|`src/fec_analysis/selective.py`|`3ba30f6e181b28c6da8ca9bacf78812fea293db2`|
|`scripts/inspect_selective_cohort.py`|`3ba30f6e181b28c6da8ca9bacf78812fea293db2`|
|`scripts/selective_primary_rule.py`|`5772283960e25cda3dc11fed1cd17524e6421adc`|
|`scripts/evaluate_selective_primary.py`|`b80971589f68e018d40aed9a5a1d96a81e172cfd`|
|`scripts/compare_random_abstention.py`|`9d996a1ff89aba6c885307ae80e6c97e4f58ff7c`|
|`scripts/plot_results.py`|`da1c8feaae88454349afa3f6819a317e7039b302`|
|`scripts/plot_selective_primary.py`|`da7a8d372361790f9b550564a0a60c34054bdd6c`|

（`scripts/build_code_appendix.py` が実行時に`git log`から自動取得するため、commitが変われば付録も更新される。）

## 3. 容量・ページ影響の算定（先に算出する）

|項目|値|判定|
|---|---|---|
|付録ソース全文|2,466行 / 100,646バイト|—|
|テンプレート原本|84,056バイト|—|
|付録に含める画像（図1・図3）|PNG 各60〜90KB程度|本文2〜4頁に収めるなら、画像は**本文の図として**2枚まで。付録には**画像を再掲しない**|
|**想定DOCX総サイズ**|**約350〜450KB**|**500KB以下推奨を満たす**（1.5MB以上減点には届かない）|
|付録のページ数（推定）|**約50〜55頁**（8.5pt・1段組・1行≈48行/頁）|**本文の頁数制限（2〜4頁、最大8頁、付録別）には含まれない**|

ページ数は**本文と別カウント**する（#88で実際にレンダリングして確定させる）。

## 4. 確認事項

- [x] 表・図 → ソース → コマンド → 出力が漏なく紐付いている（上記1）。
- [x] 13ファイルの全文を収録する（抜粋なし）。
- [x] 各ファイルにSHA-256とcommit SHAを付録見出しに付す。
- [x] Python版・pip依存・FEC出典SHA・seed・実行順・期待出力をmanifest化。
- [x] 容量とページ影響を事前に算定。
- [x] `scripts/build_code_appendix.py` で再生成でき、CIで`pytest`と公式FEC検証が通る。

## 5. 未達・要判断

- [ ] **本文の表・図の最終選択**は[#67](https://github.com/SMRI2170/fec-election-analysis/issues/67)で確定する。表4を図表枠削減のために表3へ列統合する案もある。
- [ ] **本人と生成AIの成果区分**（[#89](https://github.com/SMRI2170/fec-election-analysis/issues/89)）は本Issueの対象外。
- [ ] 付録を**1段組**で組むには、テンプレートの2セクション構成に1段セクションを追加する必要がある（#84で確定）。
