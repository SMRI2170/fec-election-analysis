# Issue #57 — FEC下院 Primary/Generalの州×年度比較

**研究の問い:** 「Primaryの二党得票率とGeneralの二党得票率は州・年度でどう異なるか」「年度外予測が外れる州/年に共通の性質はあるか」。講義資料Rep1v1015.pdf p.5の「州による差異・特徴」「年度による変化」、p.9–10のモデル妥当性・エビデンスの要求に対応する。

> **対象の境界:** FEC公式2016/18/20/22の50州Voting House **916選別レコード**。FECの報告グループは州・年・地区ごとのデータであり、非投票権Delegateの管轄は「50州Voting House」の分母へ含めない。特定の州の選挙を代表すると仮定せず、州制度による保守的除外・Primary無対立や欠損を除外理由つきで示す。実運用の選挙前予測に利用できたデータとは主張しない。

## 実装した比較

- **採用の州間差:** \`exclusions.csv\`と\`elections.csv\`を同一の年×州×地区で結合。各年×州のFEC報告グループ数、現行採用/除外数、採用割合、除外理由を保存。Delegates/Resident Commissionerを別法域として記録。
- **Primary→Generalの観測差:** R二党得票率の両段階での選択区平均と \`G-P\`（**同じ有権者の支持率変化や得票率全体ではない**）を年×州で記述。
- **年度外の予測誤差:** 既存 \`analyze_error_structure.heldout()\` を変更せず、2018は2016、2020は2016/2018、2022は2016/2018/2020で線形回帰をfit。州×年別に選択区数n、線形回帰MAE、Primary持越しMAE、符号付き残差\`linear_pred − actual_G\`（正=R過大予測）を算出。
- **州の等重み平均と選択区の等重み平均:** 選択された州それぞれのMAE/残差平均を平均した値と、選択区すべてを同じ重みで平均した値を**両方**報告。どちらも全米人口/有権者票で重みづけした「全国得票率」ではない。
- **小標本対策:** 各州×年で\`n<5\`の行はCSVに残すが、州残差の図では**n>=5のみ**表示。n=1,2から州ランキングを作らない。
- **2図:** 全4年度の50州の選択率・報告件数を示す散布図と、テスト3年度の州平均Primary共和党二党票率と**符号付き予測残差**の散布図を保存。後者の点の大きさは採用地区数を反映する。

## 実FECデータによる結果

**この節はGitHub Actionsの公式FEC再実行成功後に、実際の数値のみを追記する。** テスト用の合成fixtureを実選挙の結果として報告しない。

## 図表と再実行手順

\`\`\`bash
python -m pip install -r requirements.txt
python -m pytest -q tests/test_state_year.py
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022 --writein-policy attribute
python scripts/run_backtests.py --input data/processed/elections.csv --test-years 2018 2020 2022
python scripts/verify_reproducibility.py
python scripts/analyze_state_year.py --assert-baseline
\`\`\`

出力はgit管理外の\`data/processed/state_year/\`配下：\`state_year_coverage.csv\`、\`state_year_exclusion_reasons.csv\`、\`state_year_error_metrics.csv\`、\`state_year_summary.json\`、\`fig_state_coverage.png/.svg\`、\`fig_state_year_bias.png/.svg\`。GitHub Actionsは7日保持のArtifact。グラフは写真ではなく計算値から生成したベクター/PNG。

## 解釈の留意点

1. PrimaryとGeneralは投票者が同じとは限らず、R/Dの二党票分母も異なる。\`G-P\`は投票率・党派支持率の因果変化ではない。
2. 極端な州差が出ても、州制度差と非無作為な採用の違いを除外できないため、特定州が「本質的に予測しやすい」とは断定しない。
3. 2010年代と2020年代の区割りは変更されている。同じ district 番号を同一領域と仮定して固定効果等を推定しない。
4. 使用したFEC Excelは選挙**後**の刊行資料であり、Primary終了時点の利用可能性は独立に証明していない（[#49](https://github.com/SMRI2170/fec-election-analysis/issues/49)）。
5. 2022年の分析条件は既に探索されているため、今回の州別結果を新しい独立検証とは扱わない。

関連：[課題に沿ったロードマップ](assignment-aligned-roadmap.md)、[従来の誤差構造分析](error-structure-analysis.md)、[Issue #57](https://github.com/SMRI2170/fec-election-analysis/issues/57)。
