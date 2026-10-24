# Issue #86 — 最終図表の番号・出典・研究問い台帳

**Issue:** [#86](https://github.com/SMRI2170/fec-election-analysis/issues/86)
**親Issue:** [#67](https://github.com/SMRI2170/fec-election-analysis/issues/67)

本文の manuscript（private DOCX）に載る図表について、番号・和文/英文キャプション・
対応節・出典・単位・分母・生成手順を一対一で記録する。公開可能な情報のみを載せ、
本文・著者名・感想・DOCXそのものはここには置かない。

> **前提:** 本台帳は private な DOCX（`private-work/report/fec_report_ieice.docx`）を
> 基準にしているため、ファイルそのものは公開リポジトリに存在しない。
> 表3（州と年度の差異）の元データは未マージの PR #73
> （[docs/state-year-findings.md](https://github.com/SMRI2170/fec-election-analysis/pull/73)）に
> ある。#86 の作業指示「未マージの分析PRの図表を先行して完成扱いしない」に従い、
> 表3 は **PR #73 の数値を本文に引用したものであり、同PRのマージとレビューを前提とする**。

## 1. 編集目標と実績

| 項目 | 指示 | 実績 | 判定 |
| --- | --- | --- | --- |
| 本文の図 | 最大2図 | 2図（図1・図2） | 適合 |
| 本文の表 | 2〜3表 | 3表（表1・表2・表3） | 適合 |
| 付録の表 | ページ上限外 | 2表（表A1・表A2） | 付録として分離済み |
| ページ上限 | 本文2〜4頁推奨・最大8頁 | 本文4頁・付録36頁（合計40頁） | 推奨範囲内 |

## 2. 図表台帳

### 図1

| 項目 | 内容 |
| --- | --- |
| 和文キャプション | 図1　判定率と条件付き誤り率の関係（破線は同数ランダム保留の期待値） |
| 英文キャプション | Figure 1　Answer rate against selective risk. |
| 対応節 | 3.2　判定保留のcoverageとrisk（本文2ページ目） |
| 出典 | 本研究の実測（閾値0/5/10/15/20は実測前に固定） |
| 証拠ID | `SEL-GRID`（`data/processed/selective-primary-grid.csv` / `.json`） |
| 生成スクリプト | `scripts/plot_selective_primary.py` |
| 図ファイル | `outputs/figures/selective_coverage_risk.png`（SVG併存） |
| PNG SHA-256 | `3527212e85e0201ac6e692d07bcaa74b91d93e961b3034ce340b4e4bfcfbf030` |
| x軸 | 回答率 coverage（%）＝ accepted / eligible |
| y軸 | 条件付き誤り率 selective risk（%）＝ wrong_accepted / accepted |
| 破線 | 同数ランダム保留の期待誤答率（K×E/N） |
| 母数 n | eligible 241（2018）／237（2020）／238（2022）、計716 |
| 対象年度 | 2018・2020・2022（2016は学習年としてのみ使用） |

### 図2

| 項目 | 内容 |
| --- | --- |
| 和文キャプション | 図2　観測した誤答数と同数ランダム保留の期待値の比較 |
| 英文キャプション | Figure 2　Observed errors against same-size random abstention. |
| 対応節 | 3.3　ランダム保留との比較（本文3ページ目） |
| 出典 | 本研究の実測（t＝0は全件判定の基準） |
| 証拠ID | `SEL-RANDOM`（`data/processed/selective-primary-random-baseline.csv` / `.json`） |
| 生成スクリプト | `scripts/plot_selective_primary.py` |
| 図ファイル | `outputs/figures/selective_random_abstention_comparison.png` |
| PNG SHA-256 | `e65fac4df8743c8587d66ff17ee94a573e64f643043f53a3f57fd373ba301ca2` |
| x軸 | 評価年・閾値 t（パーセンテージポイント） |
| y軸 | 誤答数（件） |
| 母数 n | eligible 241／237／238、閾値別15条件（t＝0は全件判定の基準線） |
| 注記 | t＝0の3点は基準線であり、比較対象は t>0 の12条件 |

### 表1

| 項目 | 内容 |
| --- | --- |
| 和文キャプション | 表1　母数の三段階（公式FEC報告グループから評価対象まで） |
| 英文キャプション | Table 1　Three stages of the denominator. |
| 対応節 | 2.1 データと対象母数／3.1 母数と基準性能 |
| 出典 | FEC Federal Elections 2018–2022 公式ワークブック |
| 証拠ID | `SEL-COHORT-AUDIT`（`data/processed/selective-cohort-audit.json`） |
| 生成スクリプト | `scripts/inspect_selective_cohort.py` |
| 単位 | 件（行数は報告グループ数）、採用率は % |
| 分母 | ①公式FEC報告グループ1,756 ②非投票権Delegate法域22を除いた50州Voting House 1,734 ③評価対象916 |
| 年度内訳 | 2018: 438/5/433/241、2020: 441/6/435/237、2022: 439/5/434/238（採用率55.66/54.48/54.84%、合計52.83%） |
| 丸め | 採用率小数2位、原文書の百分率表記は小数1位 |

### 表2

| 項目 | 内容 |
| --- | --- |
| 和文キャプション | 表2　年度外評価の基準性能（学習は前の年度のみ） |
| 英文キャプション | Table 2　Out-of-year baseline performance. |
| 対応節 | 3.1 母数と基準性能 |
| 出典 | FEC Federal Elections 2018–2022 公式ワークブック |
| 証拠ID | `BACKTEST-METRICS`（`data/processed/backtest_metrics.csv`）および `data/sources/expected_analysis.json` に固定値 |
| 生成スクリプト | `scripts/run_backtests.py` |
| 単位 | MAEはポイント（得票率の比×100、1ポイント＝0.01）、正解率は %、誤答数は 件 |
| 学習/検証境界 | 2018: 学習200(2016)・検証241、2020: 学習441・検証237、2022: 学習678・検証238 |
| 値 | 線形回帰MAE 4.42/5.49/5.02、多数派規則の正解率 90.04/89.87/89.92%、誤答数 24/24/24、Logistic回帰の正解率 84.23/91.56/86.97% |
| 注意 | 多数派規則の「正解」は本選挙の二党票多数派であり、公式当選者ではない |

### 表3

| 項目 | 内容 |
| --- | --- |
| 和文キャプション | 表3　州と年度の差異（同一の固定線形回帰，重み付け方の違い） |
| 英文キャプション | Table 3　State and year differences in the weighting of the same fixed model. |
| 対応節 | 3.4 州と年度の差異 |
| 出典 | FEC Federal Elections 2016–2022 公式ワークブック |
| 証拠ID | `STATE-YEAR-SUMMARY`（PR #73 の `data/processed/state_year/state_year_summary.json`） |
| 生成スクリプト | `scripts/analyze_state_year.py`（PR #73） |
| 単位 | MAEはポイント |
| **分母差** | 「地区等重み」は採用したテスト地区1件ずつのMAEの平均、「採用州等重み」は採用州ごとに州内MAEを等重み平均したもの。人口重みでも全州等重みでもない |
| 値 | 2018: 4.42 / 4.94（差+0.52、採用37州）、2020: 5.49 / 5.49（約0.00、37州）、2022: 5.02 / 5.27（差+0.25、36州） |
| 制約 | n<5の州は州別ランキングに使わない。採用0件の11州（AK, AR, CA, CT, DE, LA, MN, ND, NY, SD, WA）はMAEを定義できない |

### 表A1（付録A）

| 項目 | 内容 |
| --- | --- |
| 和文キャプション | 表A1　判定保留15条件のcoverage–risk（eligibleはGeneral二党票同点を除く固定評価母数） |
| 英文キャプション | Table A1　The fifteen year-by-threshold conditions. |
| 対応節 | 付録A 判定保留15条件とランダム保留比較 |
| 証拠ID | `SEL-GRID` |
| 単位 | 母数/回答/保留/誤答/放棄正答は 件、回答率・リスク・誤答/母数は % |
| 内容 | 3年×5閾値＝15条件の全文。t＝0は全件判定の基準 |
| 注記 | General二党票同点の地区は評価母数から除外（3年とも0件） |

### 表A2（付録A）

| 項目 | 内容 |
| --- | --- |
| 和文キャプション | 表A2　同数ランダム保留との比較（期待誤答数はK×E/N） |
| 英文キャプション | Table A2　Comparison with same-size random abstention. |
| 対応節 | 付録A／本文3.3 |
| 証拠ID | `SEL-RANDOM` |
| 単位 | 誤答数・回避件数・5%点はいずれも 件、p値は無次元 |
| 内容 | 15条件（t＝0は基準、t>0が12条件の比較） |
| 注意 | p値は探索的。12条件へのBonferroni補正（α=0.05→0.00417）でも全条件が有意。ランダム保留は参照点であり「保留した地区が無作為に選ばれた」ことを意味しない |

## 3. 単位・丸め・数値の相互突合

| 検査項目 | 結果 |
| --- | --- |
| 916 / 1,734 / 1,756 の混同 | 本文・表1・付録で3つの分母を明示的に区別（不一致0） |
| MAEの単位 | 本文・表2ともポイント表記に統一（原表は比表記、括弧で併記） |
| 正解率の単位 | 本文・表2とも % 表記に統一 |
| p値の表記 | 本文3.3は「全条件0.0002以下」、付録A2は科学计数表記。最大値は 1.21e-04（2020/t=5）で一致 |
| 図表番号 | 図1・図2・表1・表2・表3・表A1・表A2。本文中の参照（図1・図2・表1・表2・付録Aの表A1・表A2）と一対一 |
| 英語キャプション | 図1・図2・表1・表2・表3・表A1・表A2の7点すべてに英文キャプションあり |

## 4. 再現手順

```bash
python -m pip install -r requirements.txt
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022 --writein-policy attribute
python scripts/run_backtests.py --input data/processed/elections.csv --test-years 2018 2020 2022
python scripts/inspect_selective_cohort.py --output data/processed/selective-cohort-audit.json
python scripts/evaluate_selective_primary.py
python scripts/compare_random_abstention.py
python scripts/plot_selective_primary.py
```

図のPNGは上記手順で再生成でき、本文に埋め込んだPNGと
`3527212e…` / `e65fac4d…` のSHA-256が一致することを確認済み（private workspaceで照合）。

## 5. 未了・依存

1. 表3の証拠は **未マージのPR #73** にある。#73のマージとレビュー後に確定扱いとする。
2. 図1・図2はPR #82（[#96](https://github.com/SMRI2170/fec-election-analysis/pull/96)）で生成される。
   同PRが未マージのため、本文の数値も未マージ依存である。
3. 本文・付録の最終レンダリング目視確認は Microsoft Word で行う（開発環境では
   LibreOffice が日本語グリフを描画できず、段組の再現もQuick Lookでは不可）。
4. 表3の英文キャプション（"Table 3　State and year differences in the weighting of the
   same fixed model."）は本文幅の制約で2行に折り返す。表内の値とヘッダの折返しはない。
