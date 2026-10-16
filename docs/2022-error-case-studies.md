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
