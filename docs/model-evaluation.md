# FEC下院データの年度外予測 — 現行（2026-10-15）の再現結果

> **現行の研究対象921選挙区レコード。** 以前の740件（初期）・738件（公式当選者確認後）の実験結果は過去バージョンとして保存されているが、**本文中で新旧の数値を混ぜない**。

## 研究の問い

米国FECの下院結果（2016・2018・2020・2022年）を使い、Primaryの共和党票比率 `P=R_primary/(R_primary+D_primary)` から、Generalの二大政党共和党票比率 `G=R_general/(R_general+D_general)` と、**二大政党間の得票優勢**を予測する。後者は当選者の公式認定と概念上異なるため、FECの`GE WINNER INDICATOR`で照合し、特殊選挙等は採用対象から除外している。

## 前処理（#14・#15）

- FECが`W(R)`・`W(D)`と表示する政党帰属付きPrimary書き込み票を、対応する党の`Party Votes:`と**完全一致する場合だけ加算**。
- 無対立、候補者の不足、未検証の州・制度、票数の不整合、実際の公式当選者と二党得票優勢の不一致・非認証選挙を除外。
- 2016:201件、2018:243件、2020:237件、2022:240件、合計**921件**。
- 抽出した921件のPrimary/General得票数の再計算は元Excelと一致。District General総票の原票小計が取得できる920件でも不一致0件（2016年WY-00の小計は独立した集計確認が必要）。
- **選定は完全に代表的ではない。** 初期基準738件との比較を同じ標本での再学習の純粋な効果と混同しない。

## 年度外テスト

[2026-10-15 GitHub Actions 実測](https://github.com/SMRI2170/fec-election-analysis/actions/runs/38703687765) 。各テスト年より**前の年度だけ**を学習に使った。

|テスト年|学習|評価|平均値MAE|Primary比率持越しMAE|線形回帰MAE|
|---|---:|---:|---:|---:|---:|
|2018|201|243|0.1339|0.0639|**0.0452**|
|2020|444|237|0.1399|0.0784|**0.0547**|
|2022|681|240|0.1416|0.0762|**0.0514**|

|テスト年|最頻クラス正解率|Primary多数派規則正解率|ロジスティック回帰正解率|
|---|---:|---:|---:|
|2018|54.32%|**90.12%**|84.36%|
|2020|53.59%|89.87%|**91.56%**|
|2022|50.42%|**89.58%**|86.67%|

2022年の分類正解率の差は+2.92ポイント。**McNemar両側正確検定 p=0.09229**で、一般的な5%有意水準の有意差は認められない。前回の738件基準のp=0.00635とは結論が変わる。詳細は[感度分析](sensitivity-analysis.md)。

## 解釈

- 線形回帰は3年度で平均値ダミーよりMAEが小さい。
- 単純勝敗規則とロジスティック回帰は年度・採用サンプルによって評価が逆転し得る。
- 票数小計の意味を正しく解釈しただけで、予測精度と統計的な推測が変わった。これ自体が**前処理条件が研究結論に与える影響**を示す事例となる。
- 全米の政治的因果関係や、すべての州・年の選挙への外挿はできない。

## 再実行

```bash
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022
python scripts/audit_primary_subtotals.py
python scripts/audit_winners.py
python scripts/run_backtests.py --input data/processed/elections.csv --test-years 2018 2020 2022
python scripts/source_reconcile.py
python scripts/error_cases.py --input data/processed/elections.csv --test-year 2022
python scripts/paired_accuracy.py
```

一次資料: [FEC公式結果一覧](https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/) / [2022年公式PDF](https://www.fec.gov/documents/5675/federalelections2022.pdf)。コードと取得した公式原票を混同しないこと。
