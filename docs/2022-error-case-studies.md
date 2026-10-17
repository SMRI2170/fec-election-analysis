# 2022年の下院選挙予測で誤差が大きい5選挙区 — FEC候補者票の事例調査

検証日: **2026-10-16**。分析対象は50州の投票権を持つ下院議員選挙916件（2022年238件）。[公式FEC結果を再取得して年度外学習・予測したActions](https://github.com/SMRI2170/fec-election-analysis/actions/runs/38850507154)。

## 研究目的

予備選挙のR/D票構成比から本選挙の二大政党票構成比を予測する線形回帰について、2022年の**絶対誤差上位5件**の候補者構成を原票で確認する。予備選挙と本選挙は参加者・候補者・投票の意味が異なるため、数値差から候補者の人気・因果効果を推定しない。

## 1. 線形回帰の誤差上位5区

|選挙区|PrimaryのR票比率|GeneralのR票比率|線形回帰の予測|絶対誤差|
|---|---:|---:|---:|---:|
|RI-02|17.76%|48.09%|28.81%|**19.28ポイント**|
|OH-15|84.40%|56.96%|75.62%|**18.66ポイント**|
|OH-09|64.95%|43.37%|61.96%|**18.59ポイント**|
|MI-03|63.67%|43.33%|61.06%|**17.73ポイント**|
|NH-01|64.02%|45.94%|61.31%|**15.37ポイント**|

学習は2016・2018・2020年の678件、テストは2022年の238件。順位は2022年の誤差を見て選択した**探索的なケーススタディ**であり、独立検証による事前に選んだ事例ではない。

## 2. FEC候補者行・党別小計の照合

|区|Primary共和党票|Primary民主党票|General共和党票|General民主党票|PrimaryのR/D候補者行数|
|---|---:|---:|---:|---:|---:|
|RI-02|12,113|56,102|93,969|101,432|1 / 6|
|OH-15|48,938|9,047|143,112|108,139|1 / 1|
|OH-09|61,090|32,968|115,362|150,655|4 / 1|
|MI-03|104,576|59,661|142,229|185,989|2 / 1|
|NH-01|75,401|42,368|142,229|167,391|10 / 1|

2022年のFEC公式下院Excelから、候補者名・FEC ID・政党・Primary/General得票・脚注を再抽出した`case-evidence.json`で、各区の候補者票合計と地区General総票の整合を確認している。上のPrimary党別小計には`W(R)`/`W(D)`の書き込み票が含まれることがあるため、**候補者個人票の和と必ずしも一致しない**。

独立した候補者行の事実：
- **RI-02**: 共和党候補者はAllan Fungの1人、民主党はSeth Magazinerほか計6人。PrimaryではDの票が多いがGeneralの差は約7,463票。
- **OH-15**: PrimaryのR/D候補者行は各1人（Mike Carey、Gary Josephson）。共和党Primary票が約5.4倍でも、GeneralのR/D票差は予備選挙ほど極端ではない。
- **OH-09**: 共和党Primary候補者行4人（J. R. Majewski、Craig Riedel、Theresa Gavarone、Beth Deck）、民主党はMarcy Kapturの1人。PrimaryのR/D比率はR優勢だがGeneralではD優勢。
- **MI-03**: 共和党Primary候補者行2人（John Gibbs、Peter Meijer）、民主党はHillary Scholtenの1人。PrimaryでR優勢、GeneralはD優勢。
- **NH-01**: 共和党Primary候補者行10人（Karoline Leavittほか）、民主党はChris Pappasの1人。PrimaryでR優勢、GeneralはD優勢。

## 3. 予測失敗の特徴と未検証の要因

**原票で確認できること:**
- RI-02とOH-15はPrimaryのR/D構成比が非常に偏っているのに、Generalの二党構成比がそれより50%に近い。
- OH-09・MI-03・NH-01はPrimaryの共和党構成比が50%を上回る一方、Generalでは民主党票が共和党票より多い。両モデル（単純多数派規則・ロジスティック回帰）は3区で勝敗優勢を誤判定した。
- 党内候補者の数に差があり、同じPrimary構成比でも党内競争の度合いが異なる。**ただし候補者数と誤差の因果関係は未検証。**

**あり得るが、現時点で検証していない仮説:** Primaryへの投票参加層や関心の違い、候補者間の競争、候補者の個別要因、州・区の政治的背景など。これらを事実として決めつけない。FECの票数と候補者一覧だけでは区別できない。

**対象範囲の重要な修正:** 旧921件基準の最大誤差はGU-00だったが、グアムは非投票権Delegateの選挙であることが[Guam Election Commission](https://gec.guam.gov/2022-election-information/)および[米国下院](https://www.house.gov/the-house-explained)で確認できる。Issue #27で50州の投票権を持つ下院選挙へ研究対象を絞った後の5区が本表である。この変更を確認的な性能改善と解釈しない。

## 4. 再現と出典

```bash
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022
python scripts/error_cases.py --input data/processed/elections.csv --test-year 2022
python scripts/source_reconcile.py
python scripts/build_error_case_studies.py --top-n 5
```

生成物 `data/processed/2022-top-error-cases.csv` は、順位・比率・候補者行数・Primaryの最多候補者票の比率・General候補者名・脚注有無・公式票数との一致フラグを持つ。GitHub ActionsはCSVを短期Artifactへ保存する。

一次資料: [FEC Federal Elections 2022（PDF、下院各州の候補者別結果）](https://www.fec.gov/resources/cms-content/documents/federalelections2022.pdf) / [FEC公式Excelソース台帳](../data/sources/fec_publications.json)。

## 5. 今後の検証

- [ ] それぞれの州選管の2022年Primary/General公式報告と、党内候補者行・得票小計を照合する。
- [ ] 候補者交代・再選区割り・投票参加者構成・特別選挙など、候補者票だけで説明できない要因を一次資料で調査する。
- [ ] 誤差の大きい5区と、それ以外の選挙区の候補者数・党内競争度を比較する。ただし事後選択バイアスと、因果解釈の制限を明示する。

ここまでの**事実記録・原票照合**は完成したが、政治制度・候補者背景の外部裏付けが未完了のため、Issue #17はOpenのままとする。

## 6. 州選管一次資料との独立照合（2026-10-16、追跡中）

以下はFECから独立した**州当局の公式結果サイト**の所在と確認状況を記録する。サイトを発見したことと、候補者票を独立に照合できたことは区別する。

|選挙区|公式州資料|検証状況|残作業|
|---|---|---|---|
|RI-02|[RI 2022 statewide primary](https://www.ri.gov/election/results/2022/statewide_primary/) / [RI 2022 general election](https://www.ri.gov/election/results/2022/general_election/)|**一次資料の票数照合済み**（下記）|候補者選択・党派参加層について因果説明はしない|
|OH-15|[Ohio Secretary of State公式結果ポータル](https://www.ohiosos.gov/data) / [2022年本選挙の認証公表](https://www.ohiosos.gov/office/media-center/categories/press-releases/2022-12-09) / [Clark County BOE](https://liveresults.boe.ohio.gov/ENR/clarkohenr/11/en/Index_11.html)|**Clark郡のPrimary/General票を部分照合（PR #37）**|州当局の全選挙区公式Primary/General票をまだ独立照合していない|
|OH-09|[8郡の認証済みGeneral票（Lucas County BOE、Defiance郡保管）](https://www.boe.ohio.gov/defiance/c/elecres/20221108overlap.pdf)|**Generalの全8郡・全地区票をFECと照合済み（PR #38）**|2022年5月Primaryの州公式候補者票との独立照合が残る|
|MI-03|[Michigan州議会公式公刊物](https://www.legislature.mi.gov/documents/2023-2024/michiganmanual/2023-MM-Chapter9.pdf)|**Primary/Generalの3郡合計でFECと独立一致（PR #36）**|予測誤差の要因は因果検証していない|
|NH-01|[NH州2022年共和党Primary](https://www.sos.nh.gov/elections/elections/election-results/2022-state-primary-election-results/2022-republican-state) / [民主党Primary](https://www.sos.nh.gov/elections/elections/election-results/2022-state-primary-election-results/2022-democratic-state) / [General結果](https://www.sos.nh.gov/elections/2022-election-results/2022-general-election-results)|**民主党Primaryの党小計のみFECと一致（§10）**|共和党Primary票とGeneral票の州公式独立照合は未完了|

### RI-02：州政府資料とFECの照合が成立した事実

- 公式Statewide PrimaryにおけるRI-02共和党Allan W. Fungは**12,113票**。民主党はSeth M. Magaziner **30,309票**を含む**6候補**で、合計は **56,102票**（30,309 + 9,067 + 6,696 + 6,112 + 2,600 + 1,318）。
- 公式General ElectionでFungは**93,969票**、Magazinerは**101,432票**、第三党William H. Gilbertは**5,489票**、write-inは**199票**。二大政党票率の計算には後二者を混入させない。
- このR/D票数は上記のFEC起源の値と一致する。予備選挙の共和党候補は1人、民主党は6人。予備選挙の共和党比率17.76%と本選挙48.09%の違いは**観測事実**。
- **未検証の仮説:** 民主党予備選の競争による参加人数増、候補者個人の吸引力、参加者の党派構成や投票率の違い。これらの因果効果を票数だけから断定できない。

### 解釈上のゲート

- 「州の公式ポータルを発見」は「FEC票数と州票数が一致」ではない。照合完了のフラグを地区ごとに更新する。
- 2022年の誤差上位5件を**事後的に選んだ**ため、これらの例を代表性のある因果分析や独立の汎化テストとして扱わない。
- 高誤差の候補者構成と他の2022年選挙区との対照分析は別の探索的検証とする。資料を確認できない政治的背景は「未検証」と明記する。

## 7. MI-03：Michigan州議会公刊資料に基づく郡別票の独立照合（2026-10-17）

**一次資料:** [Michigan Legislature, *Michigan Manual 2023–2024*, Chapter IX: Elections（公式PDF）](https://www.legislature.mi.gov/documents/2023-2024/michiganmanual/2023-MM-Chapter9.pdf)、2022年予備選の第3選挙区表は**印刷上の729ページ**、本選挙の第3選挙区表は**印刷上の767ページ**。別ソースとして[Kent County Clerk公式2022年共和党Primary District 3](https://electionstats.kentcountymi.gov/eng/contests/view/2881)、[Kent County Clerk公式2022年General District 3](https://electionstats.kentcountymi.gov/eng/contests/view/5950)を参照。州は[2022年8月Primaryの認証](https://www.michigan.gov/sos/resources/news/2022/08/19/board-of-state-canvassers-certifies-primary-elections)も公表している。

### 州刊行物に記録された郡別Primary票（8月2日）

| MI-03 | Kent County | Muskegon County | Ottawa County | 3郡計 |
|---|---:|---:|---:|---:|
| John Gibbs（R） | 36,597 | 5,866 | 11,673 | **54,136** |
| Peter Meijer（R） | 35,623 | 5,118 | 9,699 | **50,440** |
| Hillary Scholten（D） | 45,600 | 8,803 | 5,258 | **59,661** |

- 共和党Primaryの候補者票合計は54,136＋50,440＝**104,576**、民主党は**59,661**。FEC起源のケーススタディに固定した**R=104,576、D=59,661**と一致。
- **Kent郡**の一次資料にはGibbs=36,597、Meijer=35,623と記録されており、州刊行物のKent郡列と一致。これは州刊行物の単なる複写ではない郡集計の追加確認となる。

### 州刊行物に記録された郡別General票（11月8日）

| MI-03 | Kent County | Muskegon County | Ottawa County | 3郡計 |
|---|---:|---:|---:|---:|
| John Gibbs（R） | 98,016 | 16,420 | 27,793 | **142,229** |
| Hillary Scholten（D） | 139,812 | 24,013 | 22,164 | **185,989** |
| Jamie Lewis（Libertarian） | 4,726 | 856 | 1,052 | **6,634** |
| Louis Palus（Working Class） | 2,733 | 793 | 610 | **4,136** |

- 全候補者のGeneral合計は**338,988票**。R/D二大政党票を比較する研究では第三党10,770票をRまたはDへ配分しない。
- FEC起源のGeneral R=142,229、D=185,989とも一致。したがって、2022 MI-03で**PrimaryはR優勢、GeneralはD優勢**だったことは州刊行物とFECの独立した集計が裏付ける。
- Kent郡の一次資料にはGibbs=98,016、Scholten=139,812、Lewis=4,726、Palus=2,733と記録され、州刊行物の郡列と一致。

### 証拠を再計算するコード

- [州刊行物から転記した候補者・郡別の票数と出典](../data/sources/mi03_2022_state_canvass.json)
- [郡別→州全体の再集計とFEC正規化結果の照合](../scripts/verify_mi03_state_canvass.py)
- [転記間違い・未知の郡・FECとの不一致を検出するテスト](../tests/test_mi03_state_canvass.py)

\`\`\`bash
python scripts/download_fec.py --years 2022
python scripts/normalize_fec.py --years 2022
python scripts/verify_mi03_state_canvass.py
\`\`\`

**検証範囲の明示:** 公式Michigan Manualの郡別表は人手で構造化JSONへ転記したもので、CIはその転記値の総和、刊行物の州合計、および別に取得したFECの正規化数値を突合する。**CIがMichigan州公式PDFを毎回再ダウンロード・パースしているわけではない**。候補者交代、支持者層、地域要因の因果効果はこの票の一致からは断定できない。

**#17の残件:** OH-09、OH-15、NH-01の州公式票数との独立した票数照合、ならびに背景に関する仮説の一次資料調査。

## 8. OH-15：Ohio Clark郡公式結果による部分照合（2026-10-17）

**資料の範囲に注意。** オハイオ州の第15選挙区全体ではなく、そのうち **Clark Countyで投じられた票数** を、Clark County Board of Electionsの公式結果から確認した。これだけで「OH-15のFEC得票が州選管結果と全件一致」とは言えない。

一次資料：
- [Clark County BOE: May 3, 2022 Primary Election（Official Election Results、5月25日更新）](https://liveresults.boe.ohio.gov/clarkoh/LiveResults/en/Index_9.html)
- [Clark County BOE: November 8, 2022 General Election（11月30日更新）](https://liveresults.boe.ohio.gov/ENR/clarkohenr/11/en/Index_11.html)
- [Ohio Secretary of State: 2022年11月8日のGeneral選挙結果を12月9日に認証](https://www.ohiosos.gov/office/media-center/categories/press-releases/2022-12-09)。**認証の公表それ自体ではOH-15の候補者別地区全体票を独立照合したことにはならない。**

| 投票と候補者 | Clark郡の公式候補者得票（第15区内） | 研究用FEC第15区全体票 | 差額（まだ独立照合していない票） |
|---|---:|---:|---:|
| Primary Mike Carey（共和党） | **3,398** | 48,938 | 45,540 |
| Primary Gary Josephson（民主党） | **365** | 9,047 | 8,682 |
| General Mike Carey（共和党） | **15,671** | 143,112 | 127,441 |
| General Gary Josephson（民主党） | **5,407** | 108,139 | 102,732 |

- PrimaryのClark郡集計では第15区に**21投票区**、Generalでは**33投票区**が報告されている。投票区範囲が同一だと仮定してPrimaryとGeneralの単純な投票率差を解釈しない。
- 単独の郡で観測された票数が、FECで集計した選挙区全体の対応する票数以下であるという最低限の整合性を検証した。ただし、その差額の内訳を確定するには州当局の全郡集計を取得して突合する必要がある。
- OH-15 Primary R比率84.40%、General R比率56.96%、回帰の誤差18.66ポイントは引き続きFECの選挙区全体票から計算する。Clark郡の票を混ぜたり、因果推論をしたりしない。

### 再現可能な部分照合

- [原票出典URLとClark郡公式公開値を記録したJSON](../data/sources/oh15_clark_2022_official_votes.json)
- [Clark郡公式値とFEC OH-15全体票の不等式・固定値照合](../scripts/audit_oh15_county.py)
- [部分照合を全件照合と誤認しない回帰テスト](../tests/test_oh15_county.py)

再現コマンド：

    python scripts/download_fec.py --years 2022
    python scripts/normalize_fec.py --years 2022
    python scripts/audit_oh15_county.py

**結果の判定は county_only_not_district_complete とし、complete_district_reconciliation_verified=false を明示。** OH-15の州公認地区全体の候補者得票を独立照合するには、Ohio Secretary of Stateの認証済み全地区結果、または区域内各郡選管の認証済み公式票を足し合わせる必要がある。

**Issue #17の進捗**：RI-02とMI-03は州公式全地区値との照合済み。OH-15はClark郡の部分照合段階。OH-09とNH-01およびOH-15全地区は未完了。

## 9. 2026-10-17 時点の外部照合ステータス（研究論文引用時の基準）

この表はFEC内部の候補者票照合（5選挙区とも実施済み）と、州公式資料を**別個に用いた独立照合**の範囲を分ける。州公式資料の入口だけを見つけた地区と、実際に全地区の票数を確認した地区を混同しない。

| 地区 | 州公式Primary | 州公式General | 独立監査の証拠 | 研究上の扱い |
|---|---|---|---|---|
| RI-02 | **地区全体のR/D票照合済み** | **地区全体のR/D票照合済み** | 上記§6 | 完了（背景の因果説明は未検証） |
| MI-03 | **地区全体の郡別R/D票照合済み** | **地区全体の郡別R/D票照合済み** | [§7と再現コード](../scripts/verify_mi03_state_canvass.py) | 完了（州原典の転記JSONとFECを比較） |
| OH-09 | **未完了** | **全8郡の認証済み地区票とFECが完全一致** | [Ohio州認証canvassの8郡表](oh09-general-canvass.md)、[自動照合コード](../scripts/verify_oh09_general_canvass.py) | **Generalだけ完了**。Primary候補4対1の州公式票を未検証 |
| OH-15 | **Clark郡のみ照合** | **Clark郡のみ照合** | [§8と再現コード](../scripts/audit_oh15_county.py) | **両選挙とも部分照合**。全選挙区の州公式結果は未完了 |
| NH-01 | **民主党側42,368票のみ照合済み**・共和党側75,401票は未完了 | **未完了** | [NH州公式民主党Primary PDF](https://www.sos.nh.gov/sites/g/files/ehbemt561/files/inline-documents/sonh/2022-sp-congressional-district-1-democratic-remediated.pdf) / [§10](#10-nh-01民主党primary票の州公式集計との独立照合2026-10-17) | **Primary Dだけの部分照合**。R PrimaryとGeneralの公式票数は未検証 |

**公開リポジトリの現行916件・2022年の238件・モデル精度・McNemar統計検定は、今回の外部照合の追加では変更しない。** 州公式Primaryとの独立照合が未完了なOH-09、地区全体の照合が未完了なOH-15、NH-01について、完了率を5/5と表記してはならない。

## 10. NH-01：民主党Primary票の州公式集計との独立照合（2026-10-17）

2022年9月13日の[NH州Secretary of State公式報告「Congressional District 1 - Democratic」](https://www.sos.nh.gov/sites/g/files/ehbemt561/files/inline-documents/sonh/2022-sp-congressional-district-1-democratic-remediated.pdf) の**Totals行**には、Chris Pappas 41,990票、候補者名つき書き込み票226票、その他Scattered 152票が記録される。

|民主党Primaryの内訳|公式州集計|R/Dの研究用FEC|
|---|---:|---:|
|Chris Pappas（D）|41,990|FEC候補者票の内訳に対応|
|他候補者名による書き込み票（10候補、合計）|226|党側の書き込み票へ算入される|
|その他Scattered書き込み票|152|党側の書き込み票へ算入される|
|**民主党Primary全票**|**42,368**|**42,368**|

書き込み票の公式内訳: Tom Alciere 1、Tim Baxter 19、Gail Huff Brown 42、Mark Kilbane 0、Karoline Leavitt 72、Mary Maxwell 2、Matt Mowers 72、Russell Prescott 15、Kevin Rondeau 2、Gilead R. Towne 1、Scattered 152。**共和党候補者名のwrite-inが民主党Primaryに登場しても、この226票は共和党Primary票へ振り替えない。**

**証拠範囲の制限:** 確認したのは**NH-01の民主党Primary総票だけ**。別の共和党Primary公式票との照合や、本選挙のPappas/Leavitt票の州公式原票照合はまだ行っていない。研究用FECにおける共和党Primary75,401票／本選挙D167,391票・R142,229票は、今回の州一次資料で検証できた値と混同しない。

コードとテスト：
- [州政府資料から転記したTotals行と出典](../data/sources/nh01_2022_democratic_primary.json)
- [候補別write-inの合算、党小計、FEC正規化票との照合](../scripts/verify_nh01_democratic_primary.py)
- [票の変化、R/Generalの照合完了誤認を防ぐテスト](../tests/test_nh01_democratic_primary.py)

再現:

    python scripts/download_fec.py --years 2022
    python scripts/normalize_fec.py --years 2022
    python scripts/verify_nh01_democratic_primary.py

**再現性の限界:** NH州PDFはソースから手作業で固定JSONへ転記したもので、CIは州PDFを毎回自動取得・再パースしない。FEC公式2022 Excelは毎回再取得する。**予測値・現行916件・標本選択には変更なし。**

## 11. 2022年の誤差上位5区と、それ以外233区の探索的比較（2026-10-17）

5区の事例を他の地区と比較するために、[FEC2022公式Excel候補者行を238地区すべてで再集計](../scripts/compare_error_case_candidates.py)した。[CIの元FEC再取得・評価・比較ログ](https://github.com/SMRI2170/fec-election-analysis/actions/runs/38992357153)で、同じテスト年2022の現行238区全体の中から**線形回帰の絶対誤差上位5区**と**残り233区**を分けた。数値は4年度のFEC公式Excelを再取得し、既存の年度外予測を再生成して得た。

**候補者数の定義:** FEC原票で`PARTY=R`または`PARTY=D`に分類され、Primary票が**正の数値**として記録された候補者行の数。`W(R)`/`W(D)`等の書き込み票や無効・欠損値は「名前のある正式Primary候補者」の人数として数えない。各党で2候補者以上が正の票を得た場合に「党内に競争あり」とする。この指標は実際の候補者の活動や選挙運動の強度を測ったものではない。

| 指標 | 誤差上位5地区（事後選択） | 残り233地区 |
|---|---:|---:|
| 共和党Primaryの正票候補者行数（地区平均） | **3.60** | **3.14** |
| 民主党Primaryの正票候補者行数（地区平均） | **2.00** | **2.25** |
| RまたはDのどちらかで2候補以上が得票した地区 | **4/5（80.0%）** | **186/233（79.8%）** |
| Primary多数派で予測したGeneralのR/D優勢を誤判定 | **3/5** | **21/233** |
| 線形回帰絶対誤差の中央値 | **0.185896** | **0.042876** |

**観測事実として記述可能な結論:** 5区の共和党Primary候補者数の平均は残り233区よりやや多いが、「少なくとも一方の党に2人以上の候補者がいた」地区の割合は**80.0%対79.8%**と近い。したがって、候補者数が2以上という粗いフラグだけでは誤予測上位5区の特徴を十分に区別できない。

**不可とする結論:** 誤差に着目して上位5区を選別したため、誤差の中央値が高いのは**選択の定義上必然**であり、独立した検証ではない。単純規則の誤判定率の違いも含め、これらの観測結果から候補者数の因果効果・有意差・外挿可能性を推定しない。p値は計算していない。州の政治環境、投票率、候補者交代などは追加共変量として検証していない。

成果物：`data/processed/error-case-feature-comparison.csv`（各地区の特徴）、`data/processed/error-case-feature-summary.json`（上表の機械可読統計）。GitHub ActionsのArtifactは一時保存であり、実行手順は以下。

    python scripts/download_fec.py --years 2016 2018 2020 2022
    python scripts/normalize_fec.py --years 2016 2018 2020 2022
    python scripts/error_cases.py --input data/processed/elections.csv --test-year 2022
    python scripts/compare_error_case_candidates.py --assert-baseline

**リポジトリの現行916件、モデルの学習内容と主要予測指標は変更しない。**

