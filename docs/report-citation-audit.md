# Issue #90 — 引用監査台帳（一次資料・学術論文）

**Issue:** [#90](https://github.com/SMRI2170/fec-election-analysis/issues/90)
**親Issue:** [#67](https://github.com/SMRI2170/fec-election-analysis/issues/67)

private な manuscript（IEICE形式のDOCX）が参照する一次資料・学術論文について、
書誌情報・URL・取得日・検証方法・本文中の引用位置を一対一で記録する。
公開可能なメタデータのみを載せ、著者名・学生番号・感想・DOCXそのものは含めない。

## 1. 結論

| 検査項目 | 結果 |
| --- | --- |
| 参考文献番号と本文の引用の対応 | **3件すべて1対1**（本文で引用され、参考文献に実在する） |
| 参考文献のうち本文から引用されていないもの | **0件** |
| 検証できた書誌情報 | 3件（公式データ1件・学術論文2件） |
| 検証できず削除した引用 | 2件（下記5章） |
| 出典URLの到達性 | 引用したURLは全7件HTTP 200（2026-10-24確認） |
| FEC原文ExcelのSHA-256照合 | 4件すべて `data/sources/expected_analysis.json` の固定値と一致 |

## 2. 参考文献台帳（private DOCXの番号と一致）

| 番号 | 引用先 | 種別 | URL | 検証方法 | 本文での引用位置 |
| --- | --- | --- | --- | --- | --- |
| [1] | Federal Election Commission, “Federal Elections” ワークブック2016・2018・2020・2022（公式投票結果） | 公的一次資料（統計） | https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/ | 実ダウンロード→SHA-256照合（3章） | 1．はじめに、2.1 データと対象母数 |
| [2] | R. El-Yaniv and S. Wiener, “On the foundations of noise-free selective classification,” *J. Mach. Learn. Res.*, vol.11, no.53, pp.1605-1641, 2010. | 学術論文（査読誌） | https://jmlr.org/papers/v11/el-yaniv10a.html | JMLR掲載ページで巻号・頁・年を照合 | 1．はじめに、4.2 限界 |
| [3] | Y. Geifman and R. El-Yaniv, “Selective classification for deep neural networks,” arXiv:1705.08500, 2017. | 学術論文（プレプリント） | https://arxiv.org/abs/1705.08500 | arXiv APIで題名・著者・投稿日を確認。抄録に “selective classification techniques (also known as reject option)” の記述があり本文の用法と一致 | 1．はじめに、4.2 限界 |

参照日: 2026年10月（ワークブックは2026年10月に取得）。

## 3. FEC公式ワークブック（本文の全数値の唯一の出所）

| 年度 | URL | バイト数 | SHA-256 | 固定値の所在 |
| --- | --- | ---: | --- | --- |
| 2016 | https://www.fec.gov/documents/1890/federalelections2016.xlsx | 1,549,194 | `b4a1d1383602bc388cfbdf1fbea2476476d32e0b44b44236d3a3910fa9782eb6` | `data/sources/expected_analysis.json` |
| 2018 | https://www.fec.gov/documents/2706/federalelections2018.xlsx | 602,712 | `f2c42311862b4927df2ca5908c5f9c8f8da6221a8db88fd00434a22ec1e0e303` | 同上 |
| 2020 | https://www.fec.gov/documents/4228/federalelections2020.xlsx | 6,251,110 | `5073b6d2c76c86c941508dfb1a11cc497e8529b0068c5132aceb0f385c19352e` | 同上 |
| 2022 | https://www.fec.gov/documents/5676/federalelections2022.xlsx | 3,179,722 | `cdb258ea23803e50d752bcea19faa39b3c201eb960094bcb556c3a38c2350897` | 同上 |

- 検証: `python scripts/download_fec.py --years 2016 2018 2020 2022` で実際に取得し、
  上表のSHA-256が `expected_analysis.json` の固定値と一致することを確認済み。
  GitHub Actions（`official-fec-cohort-audit`）でも同じ照合が毎回走る。
- private DOCXの **付録B** に同じ4行（年・URL・バイト数・SHA-256）を掲載している。
- 出典URLの内訳は [docs/fec-source-inventory.md](fec-source-inventory.md) も参照。

## 4. 出典の種別区分（#90の要求）

| 種別 | 具体例 | 本稿での扱い |
| --- | --- | --- |
| 公的一次資料 | FEC Federal Elections ワークブック | 数値の唯一の一次出所として引用[1]。ダウンロードとSHA-256照合を行う |
| 既存の学術論文 | El-Yaniv & Wiener 2010[2]、Geifman & El-Yaniv 2017[3] | 手法（reject option / coverage-risk）の先行研究として引用 |
| 単著の学術論文・学位論文 | — | 採用しない（検証できる形で書誌情報を確定できないため） |
| リポジトリ内の再現ノート・PR | `docs/state-year-findings.md`、PR #73/#92〜#98 | **学術論文の代替にはしない。** 数値の算出手順と根拠の追跡にのみ用い、本文の引用番号は付けない |
| GitHub Actions の実行記録 | 各PRのCI | 数値の再現性の証拠として台帳に記録する（引用ではなく） |

## 5. 削除した引用とその理由

| 削除した引用 | 理由 | 代替 |
| --- | --- | --- |
| N. Vovk, “The necessary condition for a probability of error less than one half,” ECML-95, pp.189-194, 1995. | 書誌情報を検証できる一次ソース（Crossref / OpenAlex / Google Books / Springer / DBLP / arXiv）をいずれも確認できず、**特定できなかったため削除**。著者自身の出版一覧（vovk.net/publications.html）にも該当論文は掲載がない | [2] El-Yaniv & Wiener 2010、[3] Geifman & El-Yaniv 2017（いずれも reject option と coverage-risk を扱う） |
| P. J. Bickel and R. J. Tibshirani, “Statistical prediction: the problem of shrinkage,” *Ann. Statist.*, vol.17, no.2, pp.519-533, 1989. | **本文のどこからも引用されていなかった**（参考文献表だけの掲載）。また書誌情報を検証できる一次ソースを確認できなかった | 引用自体を削除 |

未検証の引用を「要確認」として残すより削除する判断をした（第90Issueの
「不明な出典は『要確認』、特定できない引用は削除」に従う）。

## 6. 本文の主張と引用の対応（変更点）

| 箇所 | 修正前 | 修正後 | 理由 |
| --- | --- | --- | --- |
| 1．はじめに 第1段落 | 「予備選挙結果から本選挙の勝者を予測する試みは…広く行われてきた[1]」 | 「予備選挙と本選挙の得票がFECの公式ワークブックに年ごとに記録されている[1]」 | 前半は[1]（FEC）で裏づけられない文献主張だったため、検証可能な一次資料の記述に改めた。後半の本論文の位置づけはそのまま |
| 1．はじめに 第2段落 | 「判定保留（reject option）がある[2]」 | 「判定保留（reject option）がある[2][3]」 | 判定保留の枠組みを裏づける2件を割り当てた |
| 1．はじめに 第2段落 | 「入力の分布に関する仮定には依存せず」 | 「coverage（回答率）とrisk（回答中の誤り率）のトレードオフとして表す」 | 引用した論文の範囲を超える「分布非依存」の主張を削った |
| 4.2 限界 | （なし） | 「第五に，判定保留自体は既存の枠組みであり[2][3]．本研究の寄与は新しい予測アルゴリズムではなく，FECの標本選択と判定保留を組み合わせた二段階の評価設計にある．」 | #89の要求（先行研究を引用して独自性を限定する）を本文側で担保 |

## 7. 因果解釈の禁止（#90の要求）

- 本文3.4は「採用地区のPrimary共和党二党得票率とGeneral二党得票率の平均差が
  年度で符号が異なる（2018年−0.28ポイント，2020年+6.14ポイント，2022年−2.26ポイント）」
  と**観測値のみ**を述べ、その直後に「PrimaryとGeneralの投票者集団は同一ではなく，
  年度外学習の学習年も年度ごとに異なるため，この差を政治的要因として説明することは
  できない．ここで述べられるのは，1変数の写像のずれが年度を通じて一定ではないことまで
  である．」と明記している。
- 州制度・投票者心理・因果効果の根拠になる出典は本文に置いていない。
  「特定の州で予測しやすい／しにくい」という主張は、
  採用0件の11州（AK, AR, CA, CT, DE, LA, MN, ND, NY, SD, WA）とn<5の州に
  順位付けしない方針として取り扱っている。

## 8. 未了・依存

1. #90のDoDにある `docs/report-citation-audit.md` は本書である。
   private DOCXの番号と本文の対応は本書2章の表で照合できる。
2. FECワークブックのリンク先ページは授業終了後に差し替わる可能性があるため、
   取得日とSHA-256を必ず併記する運用を維持する。
3. 表3（州と年度の差異）の元データは未マージの PR #73 にある。
   引用番号は本文の[1]〜[3]の3件だけであり、PR由来の数値に新たな文献引用は付けていない。
4. 学術論文の追加が必要になった場合は、検証済みの一次ソースで確認できるものだけを
   追加し、検証できないものは追加しない。
