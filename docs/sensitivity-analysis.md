# 感度分析と誤予測の検証 — 計画・初回評価（Issue #5）

## 研究上の目的

Issue #4では2016〜2022年の選別済み740レコードから高い正解率を得た。しかし、含まれる選挙区が変わると数値が変わる可能性がある。本実験は**標本選択への感度**と**予測誤差が大きい選挙区**を調べる。

## 実験A: Primaryの党別投票数に関する感度

元の正規化条件は変更せず、両党のPrimary投票数がそれぞれ 0 / 1,000 / 5,000 / 10,000 票以上という4つの下限を追加する。

- 学習はテスト年度より前の選挙のみ。
- 各条件で学習・テスト件数、MAE、accuracy、Brierを記録する。
- 条件を厳しくしたとき精度が変わっても、それは**異なる標本での比較**であり、モデル改善とは限らない。
- 2022年で最適な閾値を選んでから「事前に設定した」とは主張しない。探索的分析として区別する。

## 実験B: 予測失敗事例

2016・2018・2020年のデータで線形回帰/ロジスティック回帰を学習し、2022年の選別済み選挙区で予測を行う。

- 線形回帰の共和党得票比率の絶対誤差で降順に並べる。
- Primary多数派の単純規則とロジスティック回帰の勝敗予測ミスも併記する。
- 候補者の所属・無対立・州制度・Special Election・票数の転記等が原因とは**原票の検証前には判断しない**。

## 再現方法

\`\`\`bash
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022
python scripts/run_sensitivity.py --input data/processed/elections.csv --test-year 2022
python scripts/error_cases.py --input data/processed/elections.csv --test-year 2022
\`\`\`

\`data/processed/sensitivity_metrics.csv\` と \`data/processed/errors_2022.csv\` はGit管理対象外。Actions実行時には短期保存のArtifactsへ集計値のみ保存する。

**未完了:** 個別誤予測の原票照合、欠損値・特殊な選挙制度の選択条件の比較、州ごとの代表性の検討、信頼区間/統計的差の評価。
