# Issue #86 — 最終図表の番号・出典・研究問い台帳

**Issue:** [#86](https://github.com/SMRI2170/fec-election-analysis/issues/86)
**親Issue:** [#67](https://github.com/SMRI2170/fec-election-analysis/issues/67)

本文の manuscript（private DOCX）に載る図表について、番号・和文/英文キャプション・
対応節・出典・単位・分母・生成手順を一対一で記録する。公開可能な情報のみを載せ、
本文・著者名・感想・DOCXそのものはここには置かない。

> **前提:** 本台帳は private な DOCX（`private-work/report/fec_report_ieice.docx`）を
> 基準にしているため、ファイルそのものは公開リポジトリに存在しない。
> 表3 の元データは PR #73（[docs/state-year-findings.md](https://github.com/SMRI2170/fec-election-analysis/pull/73)）に
> あり、**PR #73 は main へマージ済み**（[#75](https://github.com/SMRI2170/fec-election-analysis/pull/75)）。
> 表A3・表A4・表A5・図3 は PR #103（#63）と PR #105（#64）で追加され、
> いずれも main へマージ済み。

## 1. 編集目標と実績

| 項目 | 指示 | 実績 | 判定 |
| --- | --- | --- | --- |
| 本文の図 | 最大2図 | 2図（図1・図2） | 適合 |
| 本文の表 | 2〜3表 | 3表（表1・表2・表3） | 適合 |
| 付録の表 | ページ上限外 | 5表（表A1・表A2・表A3・表A4・表A5） | 付録として分離済み |
| 付録の図 | ページ上限外 | 1図（図3） | 付録として分離済み |
| ページ上限 | 本文2〜4頁推奨・最大8頁 | **本文5頁・付録55頁（合計60頁）** | 最大8頁の枠内。推奨（2〜4頁）を1頁超過 |
| 本文の頁数超過の理由 | — | ①日本語グリフが未描画の状態で頁数を測っていたため過小評価していた ②本文の全角組版は実測5頁 ③本文の行間をテンプレートの行グリッド（266 twips = 13.3 pt）に固定し、Word と LibreOffice の差異を解消した | 推奨超過は**記録して残す**。圧縮は§5のとおり著者の判断事項 |

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

### 図3（付録D）

| 項目 | 内容 |
| --- | --- |
| 和文キャプション | 図3　予備選挙得票率の確率出力の校正図（破線は完全校正） |
| 英文キャプション | Figure 3　Reliability diagram of the probability output. |
| 対応節 | 付録D　予備選挙得票率の確率出力の校正 |
| 出典 | 本研究の実測（Logistic回帰，検証年のGeneral得票は採点のみに使用） |
| 証拠ID | `CAL-BINS`（`data/processed/calibration/calibration_bins.csv`） |
| 生成スクリプト | `scripts/analyze_probability_calibration.py` |
| 図ファイル | `outputs/figures/calibration_reliability.png`（SVG併存） |
| PNG SHA-256 | `db746a51f945f3eedcbb29226d27cf9b8278199a0eab46411a154fb5ec5295bf` |
| x軸 | 予備選挙共和党二党得票率から出力した二党票多数派の予測確率（0〜1） |
| y軸 | 観測した正答率（0〜1） |
| 破線 | 完全校正の対角線（predicted = observed） |
| 母数 n | 241（2018）／237（2020）／238（2022）、各年10ビン |
| 読み取り | 両端（特に0.9以上）は観測とよく合い，中央から外れる。校正が不良であることと整合する |

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

### 表A3（付録C）

| 項目 | 内容 |
| --- | --- |
| 和文キャプション | 表A3　州×年度の符号付き残差の構成効果（n≥5の比較可能群とn<5の比較不能群） |
| 英文キャプション | Table A3　Composition of the signed residual by state sample size. |
| 対応節 | 付録C 州×年度の符号付き残差の構成効果／本文3.4 |
| 出典 | FEC Federal Elections 2016–2022 公式ワークブック |
| 証拠ID | `STATE-RESIDUAL-COMPOSITION`（`data/processed/state_year/state_residual_composition.csv` / `.json`） |
| 生成スクリプト | `scripts/audit_state_residual_composition.py`（PR #103） |
| 単位 | 州数・地区数は 件、地区割合・偏りの割合は %、符号付き残差と年度値はポイント |
| 行数 | 3年×3群（n≥5／1≤n<5／n=0）＝9行 |
| 値（年度値） | 2018 +0.77ポイント、2020 −4.58ポイント、2022 +3.00ポイント |
| 値（偏りの割合） | 2018: n≥5が+150.96%、1≤n<5が−50.96%／2020: +81.14%・+18.86%／2022: +96.08%・+3.92% |
| 注意 | 年度値は群の符号付き寄与の**相殺**であり，年度値と逆符号の比較可能州が2018年2/16州・2020年1/16州・2022年1/17州ある。n=0群は実測値が無いため「—」表示（0補完はしない） |

### 表A4（付録D）

| 項目 | 内容 |
| --- | --- |
| 和文キャプション | 表A4　確率出力の校正指標（検証年別） |
| 英文キャプション | Table A4　Calibration metrics of the probability output. |
| 対応節 | 付録D 予備選挙得票率の確率出力の校正／本文3.1・4.2 |
| 出典 | 本研究の実測（Logistic回帰，検証年のGeneral得票は採点のみに使用） |
| 証拠ID | `CAL-METRICS`（`data/processed/calibration/calibration_metrics.json`） |
| 生成スクリプト | `scripts/analyze_probability_calibration.py`（PR #105） |
| 単位 | Brier・log loss・ECE・最大校正誤差・校正の項は無次元、母数は 件 |
| 値 | Brier 0.1110/0.0829/0.0910、ECE 0.1867/0.1441/0.1360、最大校正誤差 0.2970/0.3458/0.4498、校正の項 +0.0443/−0.0454/+0.1044 |
| 注意 | Brierは `backtest_metrics.csv` の固定値と一致（独立実装の相互検証）。**ECEと最大校正誤差の小ささから、確率を信頼度として読めない** |

### 表A5（付録D）

| 項目 | 内容 |
| --- | --- |
| 和文キャプション | 表A5　確率ビンごとの予測平均確率と観測率 |
| 英文キャプション | Table A5　Predicted mean probability against observed rate per bin. |
| 対応節 | 付録D |
| 証拠ID | `CAL-BINS`（`data/processed/calibration/calibration_bins.csv`） |
| 生成スクリプト | `scripts/analyze_probability_calibration.py`（PR #105） |
| 単位 | 母数 n は 件、確率と観測率と差は 0〜1の無次元 |
| 行数 | 3年×10ビン＝30行（確率幅0.1の固定ビン） |
| 注意 | 5件未満のビン（thin）は★で明示し，観測率の推定不確実性が大きいことを示す。最大誤差は2022年の0.4–0.5ビン（n=9，予測0.4498・観測0.0000） |

## 3. 単位・丸め・数値の相互突合

| 検査項目 | 結果 |
| --- | --- |
| 916 / 1,734 / 1,756 の混同 | 本文・表1・付録で3つの分母を明示的に区別（不一致0） |
| MAEの単位 | 本文・表2ともポイント表記に統一（原表は比表記、括弧で併記） |
| 正解率の単位 | 本文・表2とも % 表記に統一 |
| 符号付き残差の単位 | 本文3.4・表A3ともポイント表記に統一（原表は比表記）。表A3の年度値 +0.77／−4.58／+3.00 と本文が一致 |
| 校正指標の単位 | 表A4・表A5とも無次元（0〜1）。ECE・最大校正誤差の値が本文（0.136〜0.187／0.297〜0.450）と一致 |
| p値の表記 | 本文3.3は「全条件0.0002以下」、付録A2は科学计数表記。最大値は 1.21e-04（2020/t=5）で一致 |
| 図表番号 | 図1・図2・図3・表1・表2・表3・表A1〜表A5。本文中の参照（図1・図2・表1・表2・表3・付録Aの表A1・表A2・付録Cの表A3・付録Dの表A4・図3）と一対一 |
| 英語キャプション | 図1・図2・図3・表1・表2・表3・表A1〜表A5の10点すべてに英文キャプションあり |

## 4. 再現手順

```bash
python -m pip install -r requirements.txt
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022 --writein-policy attribute
python scripts/run_backtests.py --input data/processed/elections.csv --test-years 2018 2020 2022
python scripts/inspect_selective_cohort.py --output data/processed/selective-cohort-audit.json
python scripts/evaluate_selective_primary.py
python scripts/compare_random_abstention.py
python scripts/analyze_state_year.py --assert-baseline
python scripts/audit_state_residual_composition.py
python scripts/analyze_probability_calibration.py --input data/processed/elections.csv --test-years 2018 2020 2022
python scripts/plot_selective_primary.py
```

図のPNGは上記手順で再生成でき、本文に埋め込んだPNGと
`3527212e…` / `e65fac4d…` / `db746a51…` のSHA-256が一致することを確認済み（private workspaceで照合）。

## 5. 未了・依存

1. **本文5頁は推奨（2〜4頁）を1頁超過する。** 圧縮すれば約2,100字
   （2.3の評価指標の列挙，4.2の限界の一部，1．序論と5．むすびの精簡）を削れば
   4頁に収まるが，論証の厚みが落ちる。**著者の判断事項**として未決。
2. 図1・図2・図3は本文（図1・図2）と付録D（図3）に分けて再掲し，番号の重複はない。
3. 本文・付録の最終レンダリング目視確認は Microsoft Word で行う（開発環境では
   日本語グリフを代替フォントで描画しているため，目視は代替環境）。
   行間はテンプレートの行グリッド（266 twips）に固定済みで，Word 
   LibreOffice の組版差が生じないようにしてある。
4. 表3の英文キャプション（"Table 3　State and year differences in the weighting of the
   same fixed model."）は本文幅の制約で2行に折り返す。表内の値とヘッダの折返しはない。
