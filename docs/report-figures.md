# データサイエンス特論 レポート図表の生成（Issue #6）

作成物は学習用研究の再現可能な分析図表であり、FEC公式の元データファイルや完成レポートそのものではない。

## 再現コマンド

```bash
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022
python scripts/run_backtests.py --input data/processed/elections.csv --test-years 2018 2020 2022
python scripts/plot_results.py --input data/processed/elections.csv --metrics data/processed/backtest_metrics.csv
```

実行後の図（リポジトリの追跡対象外）:
- `outputs/figures/primary_vs_general_2022.png`: 2022年の予備/本選挙の二大政党得票比率散布図。点は**選別した下院レコード**であり全国集計・国民支持率ではない。線形回帰線は2016〜2020年のレコードで学習したもの。
- `outputs/figures/chronological_share_mae.png`: 2018・2020・2022年を年度外テストとしたMAE比較。**小さいほど予測誤差が小さい**。

GitHub Actionsの`FEC source audit`が公式Excelから毎回生成し、PNGとメトリクスを短期間のArtifactとして公開する。

## レポートへの組込み

- 3章「分析結果」: 図1（予備選挙比率と本選挙比率）と図2（単純モデルと線形回帰の年度外評価）
- 4章「考察」: 選別済みレコードの母集団、欠損処理、2022年の制度差・誤予測、選択バイアスの限界
- 論文のあらましは、実際の数値が整合してから確定する
- レポート最終版のDOCXは**指定の大学テンプレート**を使う。これらのPNGを貼るときはファイルサイズや可読性を確認する。必要なら解像度を調整する。

## 未完了

- 元ファイルの記録・候補者・制度・除外理由の追加監査（Issue #3）
- 2022年の誤予測事例を実際の選挙データに戻って検証（Issue #5）
- レポート本文の執筆・独自研究の主張・参考文献と付録コードの整理
- Word指定書式、提出期限・サイズ等の確認とManaba+Rへの提出

**注意:** 図表は機械的に再生成できるが、それ自体は分析結果の信頼性を保証しない。条件変更や特殊ケースの除外について本文で開示する。
