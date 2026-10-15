# FEC公式当選者と二大政党票の優勢の区別（Issue #15）

検証日: **2026-10-15**。実データ根拠: [FEC source audit（修正前）](https://github.com/SMRI2170/fec-election-analysis/actions/runs/38701825993) / [FEC source audit（修正後）](https://github.com/SMRI2170/fec-election-analysis/actions/runs/38702180616)。

## なぜ検証が必要か

`src/fec_analysis/core.py`が使用していた`general_rep_win`は、**Generalの共和党得票数が民主党得票数を上回るか**（二党間優勢）を示す。FECの`GE WINNER INDICATOR`に記載された**公式の当選者**とは異なる概念である。通常の二党競争では一致しやすいが、順位選択投票・無効選挙・複数候補等では保証できない。

## 監査（修正前: 740件）

`scripts/audit_winners.py`が2016/2018/2020/2022年の公式Excelで、候補者ごとの`GE WINNER INDICATOR`（当選フラグのW）と、その年の二大政党の得票優勢を選挙区単位で比較した。

| 種類 | 件数 | 処理 |
|---|---:|---|
| 公式当選者の政党と二党票優勢が一致 | 738 | 原則維持 |
| 公式当選者と二党票優勢が異なる | 1 | 2018年ME-02を理由付きで除外 |
| 公式の当選者フラグがない | 1 | 2018年NC-09を理由付きで除外 |

- **ME-02（2018年）**: FEC公式ExcelのGeneral票は初回の順位選択投票の得票を示し、共和党のBruce Poliquinの票が民主党のJared Goldenの初回票を上回る。しかし順位選択投票の最終集計によりJared Goldenが当選。FECの`GE WINNER INDICATOR`は民主党候補を示すため、単純な「初回得票が多い政党が当選」という定義は誤り。
- **NC-09（2018年）**: 2018年の本選挙結果は認証されず、翌2019年に新たな選挙が実施された。2018年の結果を公式の当選実績として使えない。

それ以外の年は、今回の選別済みレコードで不一致を観察していない。

## 変更後: 738件

`scripts/normalize_fec.py`が、保守的な従来の除外条件に加え、公式の当選者フラグの検証を行う。修正後の出力は次のとおり。

| 年度 | 採用 | 除外 |
|---|---:|---:|
|2016|169|269|
|2018|195|243|
|2020|188|253|
|2022|186|253|
|**合計**|**738**|**1,018**|

新規除外理由:
- `official-ge-different_winner` : 2018 ME-02（順位選択投票の初回得票と当選者の違い）
- `official-ge-no_official_flag` : 2018 NC-09（当選表示のない未認証選挙）

修正後の全738件で、二大政党の得票優勢とFEC当選表示が一致し、独立に計算した候補者票および地区General票の不一致は0件だった。

## レポートで使う正確な言葉

- 変数`general_rep_win`は後方互換として維持するが、定義は**二大政党間の共和党得票優勢**。新しい明示的な列`general_two_party_rep_lead`も同値として提供する。
- 「米国の全下院当選者を予測できる」とは書かない。**制度差等を除外した標本について、二大政党得票の優勢を予測した**と記述する。
- 公式当選者情報を予測特徴量へ入れない。これは**分析対象の事後の選定基準**であり、予測性能が高く見える選択バイアスの可能性はIssue #16で分析する。

## 回帰・分類評価への影響

2018年の評価対象197→195、2020年の学習対象366→364、2022年の学習対象554→552に減少。2022年のロジスティック回帰正解率は**84.95%→85.48%**、Primary多数派規則は**90.86%**で変化なし。検定は新しい分類モデルの再学習に従い更新（McNemar正確検定**p=0.00635**）。

**2022年の数値が変わっていなくても、訓練集合の変化により性能評価が再計算されている。** 旧結果と新結果を混ぜて報告しない。

## 再現方法

```bash
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022
python scripts/audit_winners.py
python scripts/source_reconcile.py
python scripts/run_backtests.py --input data/processed/elections.csv --test-years 2018 2020 2022
python scripts/paired_accuracy.py
```

## 一次資料

- [FEC Federal Elections 2018 — PDF](https://www.fec.gov/documents/2705/federalelections2018.pdf) — 下院のME-02、NC-09と注記。
- [FECの2019年NC-09再選挙の説明](https://www.fec.gov/updates/north-carolina-special-election-reporting-9th-district-2019/)。
- [Maine州政府の順位選択投票の結果年表](https://www.maine.gov/sos/sites/maine.gov.sos/files/content/assets/RCVpowerpointtimeline.UpdateOCT2020.pdf)。

## 限界

ここでは**現行の選別済み集合に対して**当選表示と独自ラベルを検証した。元から除外した多数の州・無対立候補・書き込み票・Special Election等の制度全体に通用するラベルとは主張しない。Issue #14と#16の結果によって抽出条件を変えた場合は、監査と回帰評価を必ず再実行する。
