# Issue台帳 — FEC Election Analysis（2026-10-17）

**原課題からの優先度**: 講義資料 Rep1v1015.pdf p.5/7–10。PrimaryとGeneralの多角的分析、回帰・判別とベースライン比較、モデルの妥当性・エビデンス・独自性、指定DOCX/コード付録/感想/本人と他者の区分が必要。**2024年追加検証や上院追加は必須ではない。**

詳細な講義要件、依存順、Codex作業契約は [課題整合ロードマップ](assignment-aligned-roadmap.md)。原資料は私有ファイルであり、公開リポジトリへアップロードしない。

## 研究の固定基準

- FEC公式2016, 2018, 2020, 2022年50州Voting House、**916件（200/241/237/238）**。歴史値921/738/740は旧採用条件であり比較時は区別する。
- 2018/2020/2022の時間順の検証で、Generalの票と当選者ラベルを説明変数に混入しない。2022年は既に探索に使用したため完全独立な未使用テストと呼ばない。
- [#49](https://github.com/SMRI2170/fec-election-analysis/issues/49)の公式FEC再分析で、報告**1,756→Primary互換919→最終916**を再現。primary側の採否も最終Excelからの事後再構成であり、選挙前の可用性は証明していない。
- 生のFECデータ、本人情報、提出前レポート本文はpublic GitHubへコミットしない。

## 既存の完了事項

| Issue/PR | 確認済みの結果 |
|---|---|
| #2, #4 | FEC原典調査、単純規則・線形回帰・Logisticの年度外評価 |
| #15, #16, #18 | 二党票多数派と当選者の分離、採用選択感度、4年度Excelハッシュ＋基準件数/指標の自動再現 |
| [PR #48](https://github.com/SMRI2170/fec-election-analysis/pull/48) | 年度別の誤差分布、Primary得票率の条件別性能、州単位探索的再標本化 |
| [#49](https://github.com/SMRI2170/fec-election-analysis/issues/49) / [PR #55](https://github.com/SMRI2170/fec-election-analysis/pull/55) | Primary列互換性とGeneral後採否を1,756行台帳で分離（919→916） |

## P0：11月3日17時提出までに必要

| 作業 | Issue | 先行 |
|---|---|---|
| 元課題の採点/提出条件とv0.4との欠落比較 | [#56](https://github.com/SMRI2170/fec-election-analysis/issues/56) | なし |
| 州×年度の実測特徴/採否/予測誤差分析 | [#57](https://github.com/SMRI2170/fec-election-analysis/issues/57) | 現行916件 |
| 研究の問いと図表・一次データの証拠突合 | [#67](https://github.com/SMRI2170/fec-election-analysis/issues/67) | #56, #57 |
| 指定IEICE Wordの本文化・容量/ページ/図表確認 | [#68](https://github.com/SMRI2170/fec-election-analysis/issues/68) | 正式テンプレート取得（ユーザーからの原本提供が必要な可能性） |
| 全Pythonプログラム付録と再実行環境 | [#69](https://github.com/SMRI2170/fec-election-analysis/issues/69) | 実際に本文へ使ったコードの特定 |
| 独自性・本人/他者/AIの区別・本人感想 | [#70](https://github.com/SMRI2170/fec-election-analysis/issues/70) | 本人の事実確認 |
| 最終独立査読・Manaba提出確認 | [#71](https://github.com/SMRI2170/fec-election-analysis/issues/71) | #67–70完了 |

## P1：レポートの分析を厚くする（P0と並行して可能）

- [#58](https://github.com/SMRI2170/fec-election-analysis/issues/58): Primary↔Generalの票比率・規模の記述。
- [#50](https://github.com/SMRI2170/fec-election-analysis/issues/50)親: [#59](https://github.com/SMRI2170/fec-election-analysis/issues/59)候補者数・HHI等の原票特徴抽出 → [#60](https://github.com/SMRI2170/fec-election-analysis/issues/60)アブレーション比較。
- [#51](https://github.com/SMRI2170/fec-election-analysis/issues/51)親: [#61](https://github.com/SMRI2170/fec-election-analysis/issues/61)非線形モデル固定 → [#62](https://github.com/SMRI2170/fec-election-analysis/issues/62)比較実行。
- [#52](https://github.com/SMRI2170/fec-election-analysis/issues/52)親: [#63](https://github.com/SMRI2170/fec-election-analysis/issues/63)州構成を固定した残差分析（先行#57）、[#64](https://github.com/SMRI2170/fec-election-analysis/issues/64)Brier/校正。
- [#76](https://github.com/SMRI2170/fec-election-analysis/issues/76)親: [#78](https://github.com/SMRI2170/fec-election-analysis/issues/78)評価母数と基準24誤答の凍結 → [#79](https://github.com/SMRI2170/fec-election-analysis/issues/79)General非参照の判定保留純粋関数 → [#80](https://github.com/SMRI2170/fec-election-analysis/issues/80)3年×5閾値15条件 → [#81](https://github.com/SMRI2170/fec-election-analysis/issues/81)同数ランダム保留比較 → [#82](https://github.com/SMRI2170/fec-election-analysis/issues/82)図表と研究解釈。**#80/#81/#82は#78/#79のPRに積み重なるため、マージ承認後にmainへ取り込む。**

## P2：発展研究（未完了でもレポート提出を止めない）

[#65](https://github.com/SMRI2170/fec-election-analysis/issues/65)州外挿、[#66](https://github.com/SMRI2170/fec-election-analysis/issues/66)Senate/House比較の採否、[#53](https://github.com/SMRI2170/fec-election-analysis/issues/53)2024凍結→[#54](https://github.com/SMRI2170/fec-election-analysis/issues/54)2024評価、継続中の[#14](https://github.com/SMRI2170/fec-election-analysis/issues/14)複合政党票と[#17](https://github.com/SMRI2170/fec-election-analysis/issues/17)州選管の独立照合。

## AI/Codex開発エージェントの操作規則

1. 指定Issueとその依存Issue、最新main、[課題整合ロードマップ](assignment-aligned-roadmap.md)、既存実装を読む。**1 Issue = 原則1 PR**。別ブランチで作業し、ユーザー承認なしにmainにマージしない。
2. 公式FEC元Excelの取得／SHA-256／既存916件と基準指標を検証、必要な実験のみ変更。pytestと実データCI、再現コマンドと限界をPRに記載。
3. 未来年のGeneral情報を特徴・学習・モデル選択に混入させない。二党票優勢と公式勝者を混同しない。欠損や無対立をゼロ補完しない。
4. **結果が改善しなくても正直に報告**する。州間の制度差・選別された標本・事後探索の限界を明記する。
5. 並行可能：#57/#59/#61/#64。依存必須：#59→#60、#61→#62、#57→#63、#56/#57→#67、#67〜#70→#71。同じファイルを2つのPRで同時に編集しない。
