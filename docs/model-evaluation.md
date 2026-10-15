# FEC下院データの年度外予測 — 検証済みの結果（Issue #4 / #15）

> **現行の基準: 2016〜2022年の738選挙区レコード。** 2026-10-15のIssue #15更新で2018年ME-02（順位選択投票の初回集計値と最終当選者が異なる）とNC-09（2018年結果が非認証）を通常の分析対象から除いた。以前の740件での値は[旧検証ログ](https://github.com/SMRI2170/fec-election-analysis/actions/runs/38687520194)に残るが、**提出用には今回の再計算値を使用する**。

## 目的と定義

予備選挙の共和党/民主党投票数比率 `P=primary_R/(primary_R+primary_D)` から、本選挙の二大政党得票数比率 `G=general_R/(general_R+general_D)` を予測する。

分類の旧変数 `general_rep_win` は、正しくは **二大政党の票数における共和党優勢フラグ**（`G>0.5`）であって、いかなる選挙制度でも公式当選者を保証するものではない。新たに明示名 `general_two_party_rep_lead` も提供する。FECの`GE WINNER INDICATOR`を用いた一致検証は、データ採用判定だけで行い、**説明変数には用いない**。

## 検証基準

- 使用: FEC Federal Elections 2016/2018/2020/2022、各年下院`US House Results by State`シート。
- 対象: 2016年169、2018年195、2020年188、2022年186、**合計738**。
- 学習: テスト年より過去の年に限定。2018を2016で、2020を2016+2018で、2022を2016+2018+2020で評価。
- 回帰: mean-share baseline、Primary比率持越し、線形回帰。尺度はMAE（低いほど良い）。
- 分類: majority-class baseline、Primary多数派規則、ロジスティック回帰。尺度はaccuracyと確率出力モデルのBrier。
- FEC元データとの得票集計照合: 現在の738件で候補者R/D票と地区総票の不一致0。

## 現行の年度外実測結果

再実行ログ: [GitHub Actions（正規化・モデル比較・票数監査）](https://github.com/SMRI2170/fec-election-analysis/actions/runs/38702180616)

|評価年|学習件数|評価件数|平均値MAE|Primary持越しMAE|線形回帰MAE|
|---|---:|---:|---:|---:|---:|
|2018|169|195|0.1331|0.0648|**0.0416**|
|2020|364|188|0.1453|0.0757|**0.0541**|
|2022|552|186|0.1457|0.0786|**0.0518**|

|評価年|多数派ダミー正解率|Primary多数派規則正解率|ロジスティック正解率|
|---|---:|---:|---:|
|2018|57.95%|**89.23%**|84.10%|
|2020|56.38%|89.36%|**92.55%**|
|2022|51.61%|**90.86%**|85.48%|

線形回帰は3年とも平均値ダミーより小さい誤差。分類では単純なPrimary多数派規則が**2018・2022年では**ロジスティック回帰より高精度だったが、2020年では逆転した。2022年の差の検定結果は[感度分析](sensitivity-analysis.md)を参照。

## 必須の限界

- 全国の全選挙区ではなく、Primary票の欠損・無対立・制度差・小計不一致などを除外した選別サンプル。除外条件の妥当性はIssue #14と#16で検証中。
- PrimaryとGeneralの参加者は同一ではない。党別Primary投票比率は全国の政党支持率とは解釈できない。
- 分析は相関・予測であり因果関係ではない。
- 2018年ME-02は初回得票の二党優勢と順位選択投票による当選者が異なり、NC-09の2018年結果は認証されなかった。通常の二大政党優勢ラベルによる比較から除外した。
- ホールドアウト2022年を後から見たモデル改良は探索的分析として明記し、追加データなしで性能を一般化しない。

## 再現

```bash
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022
python scripts/audit_winners.py
python scripts/run_backtests.py --input data/processed/elections.csv --test-years 2018 2020 2022
python scripts/source_reconcile.py
```

一次資料:
- [FEC Federal Elections 2018](https://www.fec.gov/documents/2705/federalelections2018.pdf)
- [FEC 2019 NC/09 special election reporting](https://www.fec.gov/updates/north-carolina-special-election-reporting-9th-district-2019/)
- [Maine state government, ranked-choice voting timeline](https://www.maine.gov/sos/sites/maine.gov.sos/files/content/assets/RCVpowerpointtimeline.UpdateOCT2020.pdf)
