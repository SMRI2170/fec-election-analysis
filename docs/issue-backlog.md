# Issue台帳 — FEC Election Analysis

**基準日: 2026-10-16。** 分析対象は米国50州Voting U.S. House **916件（2016=200、2018=241、2020=237、2022=238）**。旧921/738/740件は以前の採用条件での履歴値。数値・統計検定は[現行モデル評価](model-evaluation.md)、固定値は[`expected_analysis.json`](../data/sources/expected_analysis.json)を優先して参照する。

## 研究の問い
Primary共和党二大政党票率を用い、未知年度のGeneralの二大政党得票率・二大政党票優勢を予測できるか。入力の正規化と標本選択で結論は変わるか。

## 実タスクの最新状態

| Issue | 状態 | 成果と残作業 |
|---|---|---|
| [#2 出典監査](https://github.com/SMRI2170/fec-election-analysis/issues/2) | 完了 | 公式ファイル・年度構造調査 |
| [#4 年度外予測](https://github.com/SMRI2170/fec-election-analysis/issues/4) | 完了 | 2018/2020/2022の年度外評価と単純規則比較 |
| [#15 勝敗ターゲット](https://github.com/SMRI2170/fec-election-analysis/issues/15) | 完了 | 二大政党の得票優勢とFEC公式当選者の差を分離 |
| [#16 標本選択](https://github.com/SMRI2170/fec-election-analysis/issues/16) | 完了 | 年・州別採否、共通テスト集合の比較、除外群の観測可能性 |
| [#18 再現性](https://github.com/SMRI2170/fec-election-analysis/issues/18) | 完了（PR #30） | 4年度元XLSXのSHA-256・916件の採用数・9指標をCIで固定 |
| [#14 Primary小計差](https://github.com/SMRI2170/fec-election-analysis/issues/14) | **進行中・P0** | 過去224地区の不一致を監査し、W(R)/W(D)を修正。残る21区・42党側のうち複合党表記18党側、小計差未説明5党側、小計欠損3党側を安全に調査 |
| [#17 誤予測5事例](https://github.com/SMRI2170/fec-election-analysis/issues/17) | **進行中・P1** | PR #29でFEC照合済み。RI-02は州公式結果でも一致。OH-15、OH-09、MI-03、NH-01の州選管票数照合と背景検証が残る（PR #31参照） |
| [#3 データ品質 親Issue](https://github.com/SMRI2170/fec-election-analysis/issues/3) | Open | #14の結論を引き継ぎ、採用/除外基準と照合の最新基準を統合 |
| [#5 頑健性 親Issue](https://github.com/SMRI2170/fec-election-analysis/issues/5) | Open | 完了済み#16、進行中#17を統合。未検証の政治的因果関係を断定しない |
| [#6 最終レポート](https://github.com/SMRI2170/fec-election-analysis/issues/6) | **進行中・P0** | 指定Wordテンプレート、論文構成・図表・再現手順・参考文献、提出確認 |

## 推奨実施順序

1. **#14**: 残差5党側（2018 WI-07、2020 WI-01/02、2022 UT-02/04）を原票・州選管の制度資料で確認する。複合党コードの18党側についても個別の票の帰属を確認する。未確認なら現行916件を変えず除外理由を残す。
2. **#17**: OH/MI/NH公式Primary/Generalファイルを確認し候補者票を突合。個別観測事実・制度・未検証仮説・予測上の失敗特性を比較表にまとめる。
3. **#3/#5**: 子Issueの完了状態と現行916件基準を反映して親Issueを終了できるか判定。
4. **#6**: **調査と並行**して論文の構成・結果節・図表を確定。11月3日17:00までに指定DOCX提出（締切の公式画面を最終確認）。

## AI開発エージェント向けルール

- 原則**1 Issue=1 PR**。既存のPR・Issue・コードの有無を調べ、完了済み作業を重複実装しない。
- **現行採用916件**を無断で変更しない。旧921/738/740件と現行結果は別基準の比較であり、学習集合とテスト集合の変化を区別する。
- 複合党の票を推定配分しない。Primary党票とGeneral党票を合算しない。欠損・無対立をゼロ埋めしない。原票と合致しない票数は採用しない。
- `general_rep_win`は二大政党優勢であって全選挙の公式当選者ではない。
- 結論は**選別された標本での探索的・予測的関連**のみ。2022年の誤予測を観測後に行った対象修正や選別は確認的検定の成果と呼ばない。
- 結果を動かす変更には`Python CI`と`FEC source audit`の成功、公式出典、採用数/除外数、年度外評価値、固定値の更新理由が必要。
- 生のFEC Excel・処理CSV、個人情報、未公開レポートは公開Gitに追加しない。CIアーティファクトのみを唯一の再現性根拠にしない。
- データ範囲の拡張（上院、2010–2014、追加モデル）は**レポート提出後**に検討する。
