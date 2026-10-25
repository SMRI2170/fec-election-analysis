# レポート用エビデンス台帳と図表採否（Issue #67）

**このファイルは公開可能な証拠リンク・図表の採否記録。完成論文の本文ではない。**
対応する機械可読台帳：[data/sources/report_evidence.json](../data/sources/report_evidence.json)。
根拠資料：講義課題の要件[対応表（#56／PR #74）](https://github.com/SMRI2170/fec-election-analysis/pull/74)、研究論証図。
研究原稿v0.4は指定Word未適用の作業稿であり、本資料に自動的に置換したわけではない。

## 1. 主張→出典→再計算の検証可能性

| Evidence ID | 本文で可能な主張 | コホートと単位 | コード・証拠 | 状況 |
|---|---|---|---|---|
| **EV-001** | FEC下院報告1,756件→Primary列互換919件→最終916件（2016/2018/2020/2022の200/241/237/238） | FEC公刊年×州×区、**非投票権22グループを含む全報告1,756** | [固定FEC SHA・採否数](../data/sources/expected_analysis.json)、[時点別台帳](prediction-time-cohort.md)、[PR #55](https://github.com/SMRI2170/fec-election-analysis/pull/55) | **main検証済み**。選挙前公開時点は未証明 |
| **EV-002** | 2018/20/22のP持越しMAE **.0629/.0784/.0750** と線形MAE **.0442/.0549/.0502** | 予測テスト n=241/237/238、MAEは得票**比率**。本文では100倍して **pt** | [年度外評価](model-evaluation.md)、[残差研究ノート](error-structure-analysis.md)、[公式FEC CI](https://github.com/SMRI2170/fec-election-analysis/actions/runs/39004069145) | **main検証済み**。平均改善だけで一般化しない |
| **EV-003** | 2018/20/22の単純規則vsLogit二党票優勢のaccuracy、2022のMcNemar p=.09229 | 2018/20/22 n=241/237/238。同点除外ルールを原モデルと合わせる | [モデル評価](model-evaluation.md)、[paired検定](../scripts/paired_accuracy.py) | **main検証済み**。公式勝者予測・有意差の証明ではない |
| **EV-004** | 州内の**採用率とn、モデルMAEの地区等重みvs採用州等重み、年度間のG−P差** | 50州のFEC報告**1,734件**、別枠の非投票権22件。最終採用916件 | [PR #73（mainへマージ済）](https://github.com/SMRI2170/fec-election-analysis/pull/73)、[公式FEC専用CI](https://github.com/SMRI2170/fec-election-analysis/actions/runs/39086627384)、[研究ノート（main）](https://github.com/SMRI2170/fec-election-analysis/blob/main/docs/state-year-findings.md) | **公式FEC CI成功・PR #73は2026-10-25にmainへマージ**。`scripts/analyze_state_year.py --assert-baseline` でmain上から再計算できる |
| **EV-005** | 旧552/新678学習で**共通2022年186区**の線形/Logit評価が変わる | テストn=186に固定、学習nは違う | [標本感度](selection-bias.md)、[実装](../scripts/audit_selection_bias.py) | **main検証済み**。前処理だけの因果効果ではない |
| **EV-006** | 誤差上位5区で州公式・郡/町結果による外部票照合は**20党側中全区11、部分9** | 2022年・事後選択した5地区 | [事例研究](2022-error-case-studies.md) | **部分検証**。全地区一致・政治的原因同定と呼ばない |

**FEC原出典とSHA:** [FEC Election Results and Voting Information](https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/)。検証すべき元XLSX4本のSHA-256は [expected_analysis.json](../data/sources/expected_analysis.json) に固定しており、台帳の同じ値をCI/pytestで比較する。データソースの変更を無検査で認めない。

**予測入力と診断変数の境界:** Primary共和党二党得票率Pを予測入力に使用。General共和党二党得票率G、General二党票優勢Y、General得票差などは評価や事後分析だけに使用。選挙後に公刊されたFECのPrimary列を再構成しただけで選挙前の入手可能性を証明したことにはならない。

## 2. RQ別の本文図表予算（本文4ページを想定）

| RQ | 配置候補 | Evidence ID | 論証上の役割 | 採否 |
|---|---|---|---|---|
| **RQ1** 1変数Primary→General得票率 | **表T1**：2018/20/22のダミー/持越し/線形MAE・規則/Logit accuracy | EV-002, EV-003 | 目的関数を分けて単純モデルとの比較を成立させる | **採用** |
| **RQ1** 平均MAE差の直感的可視化 | **図F1**：3年度のP持越しと線形MAEを2系列 | EV-002 | 3年度すべてで平均絶対誤差が減る一方、毎年改善は保証しない | **採用候補**。図予算を超えたら削る |
| **RQ3** 州・年度・選択依存 | **表T2**：50州の報告/採用、2018/20/22採用州n、州等重みと地区等重みのMAE | EV-001, EV-004 | どの集合・集計法に対する誤差かを示す | **採用（PR #73はmainへマージ済）** |
| **RQ3** 州制度と欠損 | **図F2**：報告グループ数と採用率の州別散布図（計4年度） | EV-004 | 11州で採用0、州制度や無対立等の選択偏りを可視化 | **採用（PR #73はmainへマージ済）** |
| **RQ2** 分類の順位逆転と検定 | T1内accuracy・本文のMcNemar1文 | EV-003 | 「複雑なモデルが必ず改善する」は誤り | **採用** |
| **妥当性補足** | 固定186区比較、外部票照合20党側の範囲 | EV-005, EV-006 | 評価集合と元票の条件付け、外部検証の境界 | **本文1〜2文、詳細は付録** |

**原稿v0.4にあるが本文4頁の予算で優先度が低いもの:** 得票率帯5ビンの詳細表（2022年の事後観測）、誤差上位5区の全行表（事後選択）、検定の複数区間。これらは**結果が悪いから隠すのではなく、概要1文＋付録**へ。2020/22年度の符号付き残差方向の逆転は本文に含められる。

## 3. 生成コードと再現指示

レポート用図のために既存のモデルを別実装しない。モデルの唯一の基準は現行の [analyze_error_structure.py](../scripts/analyze_error_structure.py) と年度外バックテストである。

```bash
python -m pip install -r requirements.txt
python -m pytest -q tests/test_report_evidence.py
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022 --writein-policy attribute
python scripts/run_backtests.py --input data/processed/elections.csv --test-years 2018 2020 2022
python scripts/verify_reproducibility.py
python scripts/analyze_error_structure.py --assert-baseline --iterations 200
python scripts/build_report_figures.py
```

出力：`data/processed/report_figures/report_t1_yearly_mae.csv`、`report_f1_yearly_mae.png/.svg`、`report_figure_manifest.json`。**これらはFECデータ再取得と固定基準検査を通した上でのみ、実測図として扱う**。このツールは事後の図表再構成をするもので、選挙結果を新しい学習データに追加しない。

[#57 / PR #73](https://github.com/SMRI2170/fec-election-analysis/pull/73)は2026-10-25にmainへマージ済みで、`scripts/analyze_state_year.py` はmain上の手順として利用できる。出力は自動検出される（明示指定も可）。

```bash
python scripts/analyze_state_year.py --assert-baseline
python scripts/build_report_figures.py
```

で**原スクリプトが出力した採用州の表と州採用率図を**再利用する（複製して新しい州分析を作らない）。州のCSV/グラフが存在しない場合、build_report_figures.pyは**出典が存在しない州図を作成したように見せない**。

## 4. 不成立の主張と未完了の依存

- 「全米50州の予測に2018正解率90%」は不正確。採用州は限られ、50州Voting House全報告1,734のうち916しか採用していない。報告率と予測率を混同しない。
- 「2022年Logisticが単純規則より有意に悪い」は裏付け不足（McNemar p=.09229）。「差がない」も示していない。
- 「GeneralよりPrimaryの得票が低いので共和党の支持が増えた」は支持率・同一有権者の情報がなく因果誤認。
- 「高誤差5区の一次資料は完全に一致」は不正確。**20党側中全区照合11・一部照合9**。
- **未完成（2026-10-25時点）**：[#68](https://github.com/SMRI2170/fec-election-analysis/issues/68)正式Wordと[#69](https://github.com/SMRI2170/fec-election-analysis/issues/69)完全Python付録はprivate側で完成・機械検証済み（PR #97・#98で台帳化）、[#70](https://github.com/SMRI2170/fec-election-analysis/issues/70)本人の感想/AI範囲は本人執筆待ち。
- **解消済み**：[#56](https://github.com/SMRI2170/fec-election-analysis/issues/56)の講義要件対応PR #74と[#57](https://github.com/SMRI2170/fec-election-analysis/issues/57)の州別PR #73は2026-10-25にmainへマージ済み。
- **この台帳は公開してよい研究証拠のみ**。提出本文全文・本人の感想・氏名等はprivate保管し、GitHubへアップロードしない。

## 5. 完了の判定

**Issue #67は、#56と#57がmainへ反映され、ここで固定した全図表の元データが実FECから再計算でき、本人のレポート草稿に最終的な採否を反映した段階でCloseする。** #56（PR #74）と#57（PR #73）は2026-10-25にmainへマージされ、州別表・図も本PRで実データから再生成する。残る未完了は提出稿への最終反映と本人確認のみ。
