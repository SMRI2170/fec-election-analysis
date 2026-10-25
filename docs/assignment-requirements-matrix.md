# 第1回レポート課題：原資料に基づく要件対応と未達監査（Issue #56）

**確認した一次資料**：講義配布「Rep1v1015.pdf」pp. 2–5, 7–10。**提出先の指定様式は2026-11-03 17:00まで**（講義資料p.9。Manaba+R画面の最終確認は提出者が行う）。
**審査対象**：手元の編集用原稿 v0.4（2026-10-17版、指定Wordテンプレート未適用）と、公開研究リポジトリに確定した結果。**Issue #57の新分析はPR #73上でのみ確認済み、現時点ではmain未統合**。

## 1. どれが必須／推奨／例示か

| ID | 講義PDFページ | 区分 | 講義が求めるもの・課題の趣旨 | v0.4現状 | 根拠と対応する作業 |
|---|---:|---|---|---|---|
| R01 | 7 | **課題の中心** | [FEC公式サイト](https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/)の連邦選挙結果を実データ分析 | **実施済み**：2016/18/20/22下院選挙原票から916件を構築 | [#2](https://github.com/SMRI2170/fec-election-analysis/issues/2)、[#3](https://github.com/SMRI2170/fec-election-analysis/issues/3)、[再現性ノート](reproducibility.md) |
| R02 | 5,8 | **趣旨／分析例** | Primary↔General関係の分析。州差・上院/下院差・年度変化は**分析軸の例** | **一部**：3年度の予測誤差はあるが、州別観測の体系化をv0.4に未統合。上院比較は未実施でも「指示違反」とは断定不可 | [#57](https://github.com/SMRI2170/fec-election-analysis/issues/57)、[#58](https://github.com/SMRI2170/fec-election-analysis/issues/58)、任意[#66](https://github.com/SMRI2170/fec-election-analysis/issues/66) |
| R03 | 8 | **分析例** | 回帰・判別分析（“例えば”と明記）。この課題では両方を採用して多角的に比較 | **実施済み**：線形、ダミー、持越し、Logistic、二党票優勢の定義 | [#4](https://github.com/SMRI2170/fec-election-analysis/issues/4)、[モデル評価](model-evaluation.md) |
| R04 | 8,10 | **趣旨** | 各自の独自の工夫・何が分かったかを明確化 | **一部**：write-in監査、年度外比較、採否感度、外部票検証は記述あり。研究の問いと各図表の1:1対応、州差からの新しい知見を補強する必要 | [#67](https://github.com/SMRI2170/fec-election-analysis/issues/67) |
| R05 | 9,10 | **必須の記載** | 論文形式、冒頭あらましに成果・オリジナリティ、参考文献・考察 | **草稿あり**：あらまし、本文節、参考文献あり。引用元・論旨を最終査読していない | [#67](https://github.com/SMRI2170/fec-election-analysis/issues/67)、[#71](https://github.com/SMRI2170/fec-election-analysis/issues/71) |
| R06 | 9–10 | **強い評価対象** | 新規性／有効性／信頼性、詳細評価、他手法比較、手順・手法の妥当性、エビデンス | **部分対応**：ベースライン比較、符号付き誤差、州再標本化、州資料の照合済み範囲の記述あり。一方、既存の916件の**非代表性と公刊時刻未検証**、探索後の2022再利用を結論と合わせてさらに明示 | [#49](https://github.com/SMRI2170/fec-election-analysis/issues/49)、[#57](https://github.com/SMRI2170/fec-election-analysis/issues/57)、[#67](https://github.com/SMRI2170/fec-election-analysis/issues/67) |
| R07 | 8 | **必須の記載** | 自身と自身以外の成果を区別する | **未完了**：暫定AI使用説明のみ。本人の実施・確認範囲の事実確認なし | [#70](https://github.com/SMRI2170/fec-election-analysis/issues/70) |
| R08 | 9 | **必須の記載** | 「感想」 | **未完了**：本人確認の記入欄のみ。架空の体験を代筆しない | [#70](https://github.com/SMRI2170/fec-election-analysis/issues/70) |
| R09 | 9–10 | **必須の形式** | 講義指定のIEICE Wordテンプレート使用・**.docx**提出（違反は減点） | **未完了**：編集用v0.4のdocxはあるが**指定IEICE原本由来ではない** | [#68](https://github.com/SMRI2170/fec-election-analysis/issues/68) |
| R10 | 9–10 | **必須の付録** | **R/Python等のソースプログラムを付録に添付** | **未完了**：v0.4はコード抜粋＋実行コマンドのみで、完全プログラム付録ではない | [#69](https://github.com/SMRI2170/fec-election-analysis/issues/69) |
| R11 | 10 | **推奨／制限** | 本文**2–4頁推奨（最大8頁）**、付録別 | **要再検査**：v0.4は本文約5頁＋付録約1頁、しかも指定書式未適用 | [#68](https://github.com/SMRI2170/fec-election-analysis/issues/68)、[#71](https://github.com/SMRI2170/fec-election-analysis/issues/71) |
| R12 | 10 | **推奨／減点条件** | **500KB以下推奨**、**1.5MB以上は減点**、写真は避ける | **ファイル容量の再確認要**：指定Wordへ図を配置した時点で再計測が必要。写真を使わずグラフを利用 | [#68](https://github.com/SMRI2170/fec-election-analysis/issues/68) |
| R13 | 9 | **必須の操作** | Manaba+Rで**11月3日17:00**までに提出 | **未完了**：提出完了操作と画面確認は本人が行う | [#71](https://github.com/SMRI2170/fec-election-analysis/issues/71) |
| R14 | 2–4,6 | **講義上の背景** | 静的/動的予測、判別問題、データ収集・世論調査の意義と限界 | **要考察**：FEC選挙結果を世論調査と混同せず、Primary時点可用性・データ集積の妥当性に短く触れる | [#49](https://github.com/SMRI2170/fec-election-analysis/issues/49)、[#67](https://github.com/SMRI2170/fec-election-analysis/issues/67) |

**見落としやすい点**：講義資料の「例えば回帰分析・判別分析」や「Senate, House, State, and Year」は**例示**。一方「指定様式」「.docx」「ソース付録」「本人と他者の成果区分」「感想」は明確な指示。「2010〜2022が使いやすい」も**すべての年度の分析を要求していない**。

## 2. v0.4にある分析と不足している分析

| v0.4該当節 | 検証済みといえる結果 | 追加すると説得力が増す点 | 優先 |
|---|---|---|---|
| 2–3節 データと実験方法 | FEC元報告1,756件→採用916件、各年固定、候補者票と党小計の照合、時間順の学習 | [#49](https://github.com/SMRI2170/fec-election-analysis/issues/49)で得た**Primary側919→最終916**と、50州Voting House集団・非投票権法域との分母の違いを明記。FEC資料の刊行は選挙後 | **P0** |
| 4節 モデルの比較 | MAE改善が3年で観測、2022年Logisticが単純規則を明確に上回らない | MAEとaccuracyの目的の違い、2016学習のみ2018テストの限界を説明。分類Brier・校正は拡張実験でよい | P0／拡張P1 |
| 4.1–4.4節 残差分析 | 2020年−4.58pt・2022年+3.00ptの符号付き偏り、2022持越しに対して162/238区改善、得票率帯別の違い | 得票率帯・一部誤差事例を主要発見だと過大主張せず、**州×年度の採用率と平均誤差の構成依存**を新しい主表へ | **P0：#57→#67** |
| 5節 旧/新固定186区 | Logistic85.48→87.10%、線形MAE0.05178→0.05205 | 同時に学習標本も552→678へ変わったため「前処理だけの因果効果」と書かない | P0 |
| 6節 高誤差5区 | 事後選択した5区の符号付き残差、公式票20党側中11全地区／9部分照合 | 誤差上位5区の**事後選択**を前面に。全区外部照合できていないので「FEC全件と州票一致」は禁止 | P1 |
| 7–8節 考察・結論 | 結果・否定結果・限界を述べる | 3つのRQごとに図表と結果を対応させ、「何が分かり、何が不明か」を一文で答える | **P0** |
| 付録A–C | 再実行コマンド、解析スニペット、未完了記述あり | ソース全体／環境の固定／公式テンプレート／本人感想が未完了 | **P0** |

**課題に対する現段階の結論**：コード上の分析は相応に蓄積したが、講義が求める「多角的分析を根拠で論証する」「本人の考察と感想を完成させる」「指定形式で提出する」が未達。**2024年の未使用年度評価を追加しても、これらの未達は解消しない**。

## 3. 11月3日17時に向けた実行順

1. **P0** [#57](https://github.com/SMRI2170/fec-election-analysis/issues/57)の実FEC州×年度結果を確認し、採用率・欠損と予測誤差を評価（[PR #73](https://github.com/SMRI2170/fec-election-analysis/pull/73)はCI成功、ただしレビュー待ち）。
2. **P0** [#67](https://github.com/SMRI2170/fec-election-analysis/issues/67)でRQ/図/表/数値/根拠を縮約し、提出用の本文に載せる表・図の採否を決める。
3. **P0** [#68](https://github.com/SMRI2170/fec-election-analysis/issues/68)で指定IEICE Word原本を用意してページ・容量を検査（原本入手までは未完了）。
4. **P0** [#69](https://github.com/SMRI2170/fec-election-analysis/issues/69)で必要な完全ソース付録を整備、[#70](https://github.com/SMRI2170/fec-election-analysis/issues/70)で本人の実際の作業・AI使用範囲・感想を確認する。
5. **P0** [#71](https://github.com/SMRI2170/fec-election-analysis/issues/71)で参考文献と全図表を独立査読し、本人によるManaba+R提出を確認する。

**P1拡張**：[#58](https://github.com/SMRI2170/fec-election-analysis/issues/58)票規模、[#59](https://github.com/SMRI2170/fec-election-analysis/issues/59)→[#60](https://github.com/SMRI2170/fec-election-analysis/issues/60)候補者数/HHI、[#61](https://github.com/SMRI2170/fec-election-analysis/issues/61)→[#62](https://github.com/SMRI2170/fec-election-analysis/issues/62)非線形性、[#63](https://github.com/SMRI2170/fec-election-analysis/issues/63)/[#64](https://github.com/SMRI2170/fec-election-analysis/issues/64)州構成残差/校正。

**P2発展**：[#53](https://github.com/SMRI2170/fec-election-analysis/issues/53)→[#54](https://github.com/SMRI2170/fec-election-analysis/issues/54)の2024年研究、および上院比較[#66](https://github.com/SMRI2170/fec-election-analysis/issues/66)。提出本文に必須として組み込まない。

## 4. 完了条件と機密

- **#56ができた=レポート提出済みではない。** この監査は提出の不足箇所と出典・タスクを固定するだけ。
- レポート本文、氏名、学籍番号、本人感想、講義配布PDFはpublic GitHubへ公開しない。公開するのは**要件の要約、検証可能な研究値、Issue/スクリプト参照**のみ。
- 形式・本人の感想・提出状況が未確認のまま、[#71](https://github.com/SMRI2170/fec-election-analysis/issues/71)を閉じない。
