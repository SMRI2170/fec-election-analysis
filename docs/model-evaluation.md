# FEC下院選挙の年度外予測 — 現行916件（2026-10-16）

> 対象は**米国50州の投票権を持つ下院議員選挙のうち、前処理の全条件を満たした916グループ**。FECの`US House Results by State`に含まれる非投票権Delegate・Resident Commissioner選挙を別の理由で除外した。旧921件は履歴であり、最新値と混ぜない。

## 研究の問いと範囲

2016・2018・2020・2022年のFEC公式下院結果を用い、予備選挙の二大政党共和党票比率 `P=R_primary/(R_primary+D_primary)` から、General共和党二大政党得票率 `G=R_general/(R_general+D_general)` と二大政党得票での共和党優勢を予測する。`general_rep_win`は後方互換名であり**公式当選者と常に同じ概念ではない**。FEC当選者情報はラベルの事後照合と選定にのみ使い、モデルの説明変数には含めない。

### 現行の採用数

|年|採用件数|
|---|---:|
|2016|200|
|2018|241|
|2020|237|
|2022|238|
|**合計**|**916**|

FEC元シートの1,756個の年×州・地域×選挙区グループは、**全米の435投票区の無作為標本や全区×年度の厳密な母数ではない**。現行916件の票数集計とFECの候補者/選挙区票を独立に照合し、得票数不一致0件。米州の制度差・無対立選挙・小計の不一致21区などは理由付きで除外。非投票権の`AS/DC/GU/MP/PR/VI`は別の除外理由`nonvoting-delegate-jurisdiction`とする。`WY-00`のような通常の州at-large区はこの理由では除外しない。

## 年度外評価（実FEC公式Excel）

[GitHub Actions検証ログ](https://github.com/SMRI2170/fec-election-analysis/actions/runs/38850507154)。必ず**テスト年より前の年のみ**で学習。

|テスト年|学習件数|テスト件数|平均値予測 MAE|Primary持越し MAE|線形回帰 MAE|
|---|---:|---:|---:|---:|---:|
|2018|200|241|0.1327|0.0629|**0.0442**|
|2020|441|237|0.1398|0.0784|**0.0549**|
|2022|678|238|0.1409|0.0750|**0.0502**|

|テスト年|Primary多数派規則 正解率|ロジスティック回帰 正解率|
|---|---:|---:|
|2018|**90.04%**|84.23%|
|2020|89.87%|**91.56%**|
|2022|**89.92%**|86.97%|

2022年の分類モデル間の正解率差は約**+2.94ポイント**（単純規則−ロジスティック）。McNemar正確両側検定は**p=0.09229**で、通常の5%有意水準の差とは言えない。ブートストラップ95%区間（選挙区再標本化）は**0〜+5.88ポイント**、州単位クラスター再標本化の区間は約**−0.46〜+6.72ポイント**。すべて探索的解析であり、複数回のデータ選別・モデル選択の影響を受ける。

## データ選別の影響

初期の738件は政党帰属付き`W(R)/W(D)`票を十分に扱えていなかった。これを修正して921件に増えたが、2022年の誤差上位を追跡した結果、通常の50州下院議員ではないGU-00等のDelegate/Resident Commissioner選挙が含まれていることを確認した。**916件への再選別は2022年の結果を観察後の妥当性修正**であるため、精度の微小改善を確認的性能改善と説明しない。

旧/現行の比較: 旧738件／現行916件。2022年の共通186区を固定し、旧学習552件 vs 現行学習678件を比較すると、線形回帰MAEは0.05178→0.05205、ロジスティック正解率は85.48%→87.10%。全238区で評価する場合とは母集団が異なる。詳細は[選別バイアスの検証](selection-bias.md)。

最新の2022年の絶対誤差上位: **RI-02、OH-15、OH-09、MI-03、NH-01**。旧921件基準ではGU-00が最大だったが、GU-00は非投票権Delegateのため現行の研究対象外。個別事例の背景は、票数整合だけでは因果的に説明できない。

## 制約

- 50州に限定しても、州制度の除外（例: CA/WA等）、無対立選挙、欠損・候補者構成の違いがあるため、全国の代表性は保証できない。
- PrimaryとGeneralは投票参加者が異なる。`P`を世論支持率とは扱えない。
- 二大政党得票率は第三党候補に投じた票を除く指標である。
- 2022年を観察した後の前処理変更・モデル比較は探索的として扱い、2024年以降の成績を保証しない。

## 再現

```bash
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022 --writein-policy attribute
python scripts/run_backtests.py --input data/processed/elections.csv --test-years 2018 2020 2022
python scripts/error_cases.py --input data/processed/elections.csv --test-year 2022
python scripts/paired_accuracy.py
python scripts/source_reconcile.py
python scripts/audit_selection_observability.py
```

一次資料: [FEC公式選挙結果](https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/) / [U.S. House — 代表とDelegateの区別](https://www.house.gov/the-house-explained) / [Guam Election Commission 2022](https://gec.guam.gov/2022-election-information/)。
