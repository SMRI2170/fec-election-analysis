# 2026 データサイエンス特論：原課題に沿った実装・Codex実行計画

**設計日:** 2026-10-17。根拠：講義資料 Rep1v1015.pdf（10ページ）。未公開レポート本文、講義PDF自体、個人情報をpublic GitHubへ転載しない。ここは作業計画であり、実験結果ではない。

## 1. 原課題の要求と研究の対応

| 講義資料 | 指示・意図 | 主要Issue |
|---|---|---|
| p.5 | 予備選挙と本選挙の関係を多角的に。州・年度・上下院は分析軸の例示 | #57 #58、任意 #66 |
| p.7–8 | FEC公式PDF/Excel、2010–2022が使いやすい、回帰・判別、独自の工夫、自他の成果の区別 | #56 #59–64 #70 |
| p.9 | 11/3 17:00、Manaba+R、指定Word DOCX、論文形式、新規性・有効性・信頼性、詳細結果・比較・手法妥当性・エビデンス・感想・Python等の付録 | #56 #67–71 |
| p.10 | IEICE指定テンプレート、本文2–4ページ推奨・最大8ページ（付録別）、500KB以下推奨／1.5MB以上減点、写真回避、計算だけで終わらない考察 | #67–71 |

**再評価:** 2024年の新規検証に時間をかけても、州×年度分析や指定DOCXの不足は埋まらない。**課題の提出要件をP0とし、2024とSenateはP2**。Senate/House比較は例示で、必須と断定しない。

## 2. 固定した実証の前提

- FEC 2016/2018/2020/2022 50州Voting House **916件**（200/241/237/238）。旧921/738/740件は古い抽出条件。固定値は data/sources/expected_analysis.json で検証。
- Primaryの共和党二党得票率PからGeneralの共和党二党得票率G、二党票優勢を評価。公式当選者フラグと二党優勢は常に同義でない。
- 年度外評価ではテスト年Generalを学習に混入させない。ただし2022年は既に探索に使用したので、完全独立な未使用検証とは書かない。
- [#49の完了結果](https://github.com/SMRI2170/fec-election-analysis/issues/49)：FEC報告1,756→事後FECのPrimary列互換919→General後採用916。837件がPrimary互換条件で除外。最終FEC公刊物が選挙前に実際に公表されていたことは未証明。
- 研究の新規性はこの課題内の組合せ・検査方法に限定。学術史上初のアルゴリズム発明とは主張しない。

## 3. 実行順序：1 Issue = 原則1 PR

### P0：11/3提出までのクリティカルパス

| 着手順 | Issue | 内容・依存 |
|---|---|---|
| 1 | [#56](https://github.com/SMRI2170/fec-election-analysis/issues/56) | 講義条件と本文のギャップを評価 |
| 1（並行） | [#57](https://github.com/SMRI2170/fec-election-analysis/issues/57) | 州×年度の採用・Primary/General得票率・誤差 |
| 1（並行） | [#68](https://github.com/SMRI2170/fec-election-analysis/issues/68) | IEICE公式Wordの入手・段組・サイズ・ページを検証。原本取得できない場合はユーザーへアップロードを依頼 |
| 1（並行） | [#69](https://github.com/SMRI2170/fec-election-analysis/issues/69) | 本文に使用したPython完全ソース付録・再実行環境 |
| 1（並行） | [#70](https://github.com/SMRI2170/fec-election-analysis/issues/70) | 新規性、本人とAI補助の成果区分、本人による実際の感想 |
| 2 | [#67](https://github.com/SMRI2170/fec-election-analysis/issues/67) | #56と#57の確定結果から図表・出典・考察を1対1照合 |
| 3 | [#71](https://github.com/SMRI2170/fec-election-analysis/issues/71) | #67〜#70の完了確認・Word最終検査・Manaba+R提出確認 |

**重要:** #56/#57/#67/#68/#69/#70/#71が満たされた時点で提出を進める。他の研究Issueの完了待ちによる遅延を避ける。

### P1：分析補強（並行しやすい独立タスク）

- [#58](https://github.com/SMRI2170/fec-election-analysis/issues/58)：Primary/Generalの二党票率・票規模・誤差の記述。
- [#59](https://github.com/SMRI2170/fec-election-analysis/issues/59) → [#60](https://github.com/SMRI2170/fec-election-analysis/issues/60)：FEC候補者数/HHI/票規模の抽出 → 同一916件で特徴量アブレーション。親[#50](https://github.com/SMRI2170/fec-election-analysis/issues/50)。
- [#61](https://github.com/SMRI2170/fec-election-analysis/issues/61) → [#62](https://github.com/SMRI2170/fec-election-analysis/issues/62)：非線形候補・パラメータ固定 → 同一年度外テストで線形と比較。親[#51](https://github.com/SMRI2170/fec-election-analysis/issues/51)。
- [#57](https://github.com/SMRI2170/fec-election-analysis/issues/57) → [#63](https://github.com/SMRI2170/fec-election-analysis/issues/63)：2020/22年の符号付き残差が州の採用構成に依存するか。親[#52](https://github.com/SMRI2170/fec-election-analysis/issues/52)。
- [#64](https://github.com/SMRI2170/fec-election-analysis/issues/64)：LogisticのBrier・校正図・ビン毎件数（#63とは並行可、親#52）。

確定・再現されたP1結果だけを本文へ統合し、**悪化や差なしも含める**。P1の未完了は課題提出のブロッカーではない。

### P2：発展研究。提出必須ではない

[#65](https://github.com/SMRI2170/fec-election-analysis/issues/65)州外挿、[#66](https://github.com/SMRI2170/fec-election-analysis/issues/66)Senate比較採否、[#53](https://github.com/SMRI2170/fec-election-analysis/issues/53)2024評価固定 → [#54](https://github.com/SMRI2170/fec-election-analysis/issues/54)2024年度外検証。長期継続の[#14](https://github.com/SMRI2170/fec-election-analysis/issues/14)複合政党票と[#17](https://github.com/SMRI2170/fec-election-analysis/issues/17)州選管個別票の独立照合も、未完了を限界として正しく報告する。

## 4. Codexに渡す実装契約

リポジトリ SMRI2170/fec-election-analysis の最新mainを確認し、この計画・docs/issue-backlog.md・指定Issue #NNを読んで、そのIssueだけを専用ブランチで実装する。既存916件・公式4年度のSHA-256・既存予測値を保持し、公式FEC再ダウンロードからpytest・実データCIまで再現する。テスト年のGeneralを特徴量やパラメータ選択に入れない。ソース・実測数値・解釈の限界・再現コマンドを記録する。**1件の独立PRを作り、ユーザーの承認なしにmainへマージしない。**実測が悪化しても消さない。個人情報、公式Excel原本、提出前のレポート本文全文はpublic GitHubに登録しない。

**安全な並行組:** #57/#59/#61/#64の別ブランチ開発は並行可能。#60は#59、#62は#61、#63は#57を待つ。同じREADMEや研究ノートを同時編集しない。#67は#56/#57の結果確定後に実施。

## 5. 提出ゲート

講義指定のIEICEテンプレート由来の.docx、本文2–4ページ推奨/最大8ページ、500KB以下推奨・1.5MB以上は減点、Pythonプログラム付録、本人の感想、自他の成果の区別、新規性・有効性・信頼性、FEC公式データと文中の数値の一致を全検査する。**Manaba+Rの提出完了表示はユーザー本人の確認が必要**。講義資料記載の期限は11月3日17:00。提出画面で再確認する。
