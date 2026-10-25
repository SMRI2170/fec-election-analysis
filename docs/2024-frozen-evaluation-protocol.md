# Issue #53 — 2024年年度外検証の事前凍結

**Issue:** [#53](https://github.com/SMRI2170/fec-election-analysis/issues/53)（親 [#5](https://github.com/SMRI2170/fec-election-analysis/issues/5)）　**次工程:** [#54](https://github.com/SMRI2170/fec-election-analysis/issues/54)

**この文書は、2024年の 任何人も見ないうちに作成した事前登録である。** 計画固定日 2026-10-25。

## 1. なぜ凍結が必要か

2016～2022年を通して探索を重ねた結果、モデルと正規化条件を度々改訂してきた。したがって**2022年は独立した確認用の年としては呼べない**。2024年のFEC本選挙結果を**確認してから**モデルや採否規則を調整することは、方法論として許されない。

本Issueの作業は**評価計画の固定だけ**である。**2024年の本選挙得票・勝敗・誤差・地区別結果は、この文書の確定前に一切見ていない。** 実際、**2024年の公式資料は2026-10-25時点で未公開**であり、存在しない結果を見ることもできなかった。

**未公開であることはむしろ最強の事前登録である。** 結果がまだ存在しない段階で評価設計を固定したために、計画が結果に影響された可能性が構造的に排除される。

## 2. 出典の所在確認（資料所在と版のみ）

#53の指示どおり、**資料の所在と版だけ**を確認し、**党別票・勝敗・精度・地区別結果は見ていない**。

| 確認項目 | 2026-10-25 の結果 |
| --- | --- |
| FECの選挙結果カタログページ | https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/ を取得（37,667バイト）。双年刊「Federal Elections」の版のリンクは**2022年が最新**で、2024年の記載はない |
| 2024年版のページ | `…/election-results-and-voting-information/federal-elections-2024/` は **HTTP 404**。別slug（`election-and-voting-information` 配下、`federal-elections-2024-results`、`federalelections2024`）もすべて **HTTP 404** |
| 2022年版の構造（版の確認のみ） | `…/federal-elections-2022/` は HTTP 200。PDFは `/documents/5675/federalelections2022.pdf`、Excelは `/documents/5676/federalelections2022.xlsx` |
| 2024年Federal ElectionsのExcel（存在しないことの確認） | `https://www.fec.gov/documents/6900/federalelections2024.xlsx` は **HTTP 404** |
| 公式FEC 2024の代替公開物 | 2024年大統領一般選挙の公式結果（PDF・Excel）と上院選挙管理委員会の候補者一覧（`2024congressgecands.xlsx`）は存在するが、**PrimaryとGeneralの州別・地区別の下院結果が揃った形式ではない**。本評価の出典として使えため**確認できなかった** |

**結論: 2024年の一時編集の正確な出典は未公開である。** したがって本計画の出典は**未確定**であり、URL・SHA-256・シート名は**取得時に記録する**（手順は第7節）。

## 3. 固定した評価設計

### 3.1 学習と検証

| 項目 | 固定値 |
| --- | --- |
| 学習年 | 2016・2018・2020・2022年 |
| 学習件数 | 凍結母集団**916件**（200/241/237/238）。**母集団・除外理由・凍結基準値は変更しない** |
| 検証年 | 2024年 |
| 検証件数 | **未確定**。件数は事前に不明と宣言し、実際の件数と除外の内訳を報告する |
| 再学習 | **する**（同じモデルの形を、2016～2022年の916件で再適合する）。**2024年の行を適合に使わない** |
| ハイパーパラメータ探索 | **なし**。固定値のみ。内側の検証も格子探索も行わない |
| 予測の丸め | `clip(0,1)` |

**再学習することの理由:** モデルの形とハイパーパラメータは固定済みで、検証年より前の年をすべて使える。再学習は、検証年より前の年ごとに再適合していた凍結済みバックテストと同じ測定である。

### 3.2 評価するモデルの集合

| モデル | 形 | 役割 | 固定値 |
| --- | --- | --- | --- |
| `primary-carryover` | 恒等 | Primary→General関係の参照 | 適合なし（Pをそのまま予測） |
| `linear` | 線形 | **主評価候補**（凍結済みベースラインの形） | 通常の最小二乗 |
| `polynomial2-ridge` | 2次多項式＋Ridge | 事前登録済みの挑戦者 | 次数2・α=1.0・標準化あり |
| `cubic-spline-ridge` | 3次Bスプライン＋Ridge | 事前登録済みの挑戦者 | 次数3・節点[0, 0.25, 0.5, 0.75, 1]・α=1.0・標準化あり |

**除外したものと、その理由（2024年の結果を見る前の決定）**

- **`constant-mean`**: 床 参考としてのみ報告し、候補にはしない。
- **候補者レベルの特徴量**（候補者数・集中度・票規模）: **除外する。** 2016～2022年のアブレーションで安定した改善が出ず、原票の解析負荷も増えるため。**この除外は2024年の結果を見て決めたものではない。**
- **新しい分類器**: 作らない。分類は凍結済みの線形得票率1変数のまま評価する。

**挑戦者を残す理由:** 2016～2022年の比較では複雑モデルの改善が年ごとに符号を反転した（[#62](https://github.com/SMRI2170/fec-election-analysis/issues/62)）。それでも**結果を事前に登録したモデルなので、勝っても負けなくても報告する**。後から「複雑モデルを落とした」と没有关系に読める避免のため、**除外は2024年の結果を見てから行わない**。

### 3.3 予測の単位と対象

- 予測の単位は**下院選挙区1件**（州と地区の組）であり、**2022年と2024年の区割差は単位の同一性に影響しない**。地区番号の年をまたぐ同一性は仮定しない。
- 目的変数 `general_rep_share` は**同じ選挙区の一般選挙における共和党的二党得票率**（R票 ÷（R票＋D票））である。
- **分類ラベルは二党票の多数派であり、公式の当選者ではない。** `general_rep_win` という名称は二党票多数派を表すものとして扱い、認証された当選者とは区別する。
- 説明変数は `primary_rep_share` の1個だけ。

### 3.4 除外規則と欠損の扱い

除外カテゴリの**一覧は2024年の原票を読む前に固定する**。読み終えた後に記録できるのは、**すでに宣言済みのカテゴリへの帰属**だけである。**カテゴリの追加・改名・削除はしない。**

1. 無対立
2. 書き込み票のみ
3. 融合党・曖昧な党コード
4. 順位付選択・決選の選挙規則
5. 数値の票が欠損
6. 党小計の欠損
7. 特別選挙でPrimaryの対応がない

- **欠損値を0で補完しない。**
- **党小計を候補者の票に統合しない。**
- 各カテゴリに入る件数は**事前に不明**と宣言する。

### 3.5 指標

**主指標**

1. `mae_points`: 二党得票率のMAE（パーセントポイント）。
2. `mae_difference_against_primary_carryover_points`: Primary持越しとのMAE差。

**副指標**

3. `rmse_points`
4. `p95_abs_error_points`
5. `mean_signed_points`（年効果の確認用）
6. `two_party_lead_accuracy`（二党票多数派をラベルとする分類正解率）
7. `brier_score`
8. `per_state_n`（州別の件数）
9. `exclusion_rate`（除外率）

**不確実性:** 州を単位とするブートストラップ10000回（乱数シード 20261025）、95%パーセンタイル区間。**この区間は探索的である。** 同じ州の地区は選挙規則と候補者プールを共有するため独立ではなく、また評価対象は無作為抽出された標本ではないからである。

### 3.6 確認的か探索的か

- **主比較は2024年について確認的** である。**2024年は探索で観測したことがない最初の年**であり、計画は結果が公開される前に固定されている。
- **ただし次の条件下に限る。** 出典が計画どおりに取得・解析され、除外カテゴリが固定どおりに適用され、どのルールも変更されないこと。1つでも変更されれば、**2024年の結果は探索的**として報告し、確認的主張をしない。
- **ブートストラップ区間は主比較がどうであれ探索的**である（非無作為な標本に対する区間）。

## 4. 禁止操作

1. この設定の確定前に、2024年の下院得票・勝者・誤差を見ること。
2. 2024年の結果を見た後に、モデル集合・ハイパーパラメータ・前処理・指標を変えること。
3. 2024年の行、または2016年以降の年でハイパーパラメータを探索すること。
4. 2024年のラベルを見た後に、州や地区を追加・削除・重み付けすること。
5. 2024年の原票から書き込み票・融合党・無対立・欠損の規則を導出すること。
6. 2024年の結果を全米的性能として表現すること。評価対象は**選択された選挙区集合**である。
7. 得票率から政治的な因果効果を読むこと。

**設定を変更した場合はプロトコル版1.1（以降）とし、2024年の結果は探索的なもの**として扱う。

## 5. 固定文書と設定の一致をCIで検査する

- 機械可読な設定は `configs/frozen-2024-evaluation.json` に置く。
- 本書 第8節 には**同一内容**のJSONブロックを埋め込む。**両者が1項目でも違えばCIが失敗する**（`scripts/frozen_2024_protocol.py --check`）。
- **凍結コミット**（この設定を追加したコミット）を記録し、CIがそのコミットがリポジトリに存在し `HEAD` の祖先であることを確認する。記録は `freeze_commit_sha` にある。確定前は `PENDING` であり、確定後は `main` 上のコミット番号を記す。
- **設定内容のダイジェスト**（SHA-256）を `configs/frozen-2024-evaluation.sha256` に記録し、CIが照合する。**コミット番号は履歴の整理（rebase・squash）で変わるが、計画の*内容*は変えてはならない**ため、履歴に依存しない保証はダイジェストで担う。凍結後に設定を書き換えるとダイジェスト照合が失敗する。

## 6. 実行コマンド（将来の実評価）

```bash
python -m pip install -r requirements.txt
python -m pytest -q tests/test_frozen_2024_protocol.py
python scripts/frozen_2024_protocol.py --check
python scripts/download_fec_2024.py --output-dir data/raw
python scripts/normalize_fec_2024.py --writein-policy attribute
python scripts/evaluate_frozen_2024.py --assert-frozen-config
```

**`download_fec_2024.py` と `normalize_fec_2024.py`、`evaluate_frozen_2024.py` は#54で実装する。** 本Issueでは**計画だけ**を固定し、2024年の値は一切作らない。

## 7. 出典の取得手順（固定）

1. カタログページが存在することを確認し、URLと取得日を記録する。
2. ワークブックを取得し、**URL・バイト数・SHA-256**を記録する。**この時点でシートは解析しない。**
3. **シート名と列見出し行だけ**を記録する。
4. **その後で**得票表を解析する。
5. 記録を `data/sources/fec2024_publication.json` に保存する。

**2010～2022年の出典台帳 `data/sources/fec_publications.json` は変更しない。** 2024年の記録は別のファイルに置く。CIは、台帳に2024年が混ざっていないことを確認する。

## 8. 固定設定（機械可読）

このブロックは `configs/frozen-2024-evaluation.json` と**同一内容**でなければならない。CIが検査する。

```json
{
  "protocol_version": "1.0",
  "frozen_at": "2026-10-25",
  "issue": "#53",
  "parent_issue": "#5",
  "purpose": "Pre-registration of the 2024 out-of-year evaluation. The plan is fixed before the 2024 source is even published, so that no model, rule or metric can be chosen with knowledge of the 2024 outcome.",
  "status": {
    "confirmation_state": "the 2024 year is the first evaluation year that was never inspected during the 2016-2022 exploration",
    "no_2024_result_viewed": true,
    "source_published_at_freeze_time": false,
    "source_availability_check": "the FEC catalogue page https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/ lists the biennial Federal Elections editions only up to 2022 on 2026-10-25, and https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/federal-elections-2024/ returns HTTP 404",
    "consequence": "if the publication is still unavailable when the evaluation is attempted, the evaluation ends with a documented reason and no value is produced"
  },
  "data": {
    "cohort": "the frozen 916 House voting contests of 2016/2018/2020/2022 are the training material and are not modified",
    "training_years": [
      2016,
      2018,
      2020,
      2022
    ],
    "training_n": 916,
    "evaluation_year": 2024,
    "evaluation_n": "unknown; the count is declared unknown in advance and the actual count is reported with the exclusion breakdown",
    "chamber": "House",
    "prediction_unit": "one House contest, that is one state and one district; district numbers are not comparable across the 2022 and 2024 boundaries, and no cross-year district continuity is assumed",
    "feature_column": "primary_rep_share",
    "feature_definition": "the Republican two-party share of the Primary of the same contest",
    "target_column": "general_rep_share",
    "target_definition": "the Republican two-party share of the General election of the same contest; a two-party vote lead, NOT a certified winner",
    "label_definition": "the classification label is the two-party vote lead, not the certified election winner",
    "forbidden_columns_during_tuning": [
      "general_rep_share",
      "general_rep_votes",
      "general_dem_votes",
      "general_two_party_rep_lead",
      "general_rep_win",
      "general_tie",
      "general_rep_share_actual",
      "residual"
    ]
  },
  "models": [
    {
      "name": "primary-carryover",
      "family": "identity",
      "role": "pre-registered reference for the Primary-to-General relation",
      "hyperparameters": {},
      "fitted": false
    },
    {
      "name": "linear",
      "family": "linear",
      "role": "the primary evaluation candidate, the frozen baseline form",
      "hyperparameters": {},
      "fitted": true
    },
    {
      "name": "polynomial2-ridge",
      "family": "polynomial_ridge",
      "role": "pre-registered challenger, kept although the 2016-2022 comparison found no stable improvement",
      "hyperparameters": {
        "degree": 2,
        "alpha": 1.0,
        "standardize": true
      },
      "fitted": true
    },
    {
      "name": "cubic-spline-ridge",
      "family": "spline_ridge",
      "role": "pre-registered challenger, kept although the 2016-2022 comparison found no stable improvement",
      "hyperparameters": {
        "degree": 3,
        "n_knots": 5,
        "knots": [
          0.0,
          0.25,
          0.5,
          0.75,
          1.0
        ],
        "alpha": 1.0,
        "standardize": true,
        "include_bias": false
      },
      "fitted": true
    }
  ],
  "excluded_from_the_model_set": {
    "constant_mean": "reported as a floor reference only, never as a candidate",
    "candidate_level_features": "the Primary candidate counts, the concentration index and the vote volume are excluded from the 2024 model set, because the ablation of 2016-2022 found no stable improvement and the features add a parsing burden; the exclusion is decided before the 2024 result is known",
    "classification_models": "the classifier is evaluated with the frozen linear share as its single feature, and no new classifier is fitted"
  },
  "training": {
    "rule": "re-fit the same model form on all 916 frozen cohort rows of 2016/2018/2020/2022; the 2024 rows are never used for fitting",
    "refit_allowed": true,
    "refit_rationale": "the model form and the hyperparameters are fixed, and the whole pre-2024 cohort is available; re-fitting is the same measurement as the frozen backtests, which refit on every year before the test year",
    "hyperparameter_search": "none; the hyperparameters are fixed constants and no search, grid or inner validation is performed",
    "standardization": "the polynomial and the spline designs are centred and scaled with the training mean and standard deviation only",
    "prediction_clip": [
      0.0,
      1.0
    ]
  },
  "metrics": {
    "primary": [
      "mae_points",
      "mae_difference_against_primary_carryover_points"
    ],
    "secondary": [
      "rmse_points",
      "p95_abs_error_points",
      "mean_signed_points",
      "two_party_lead_accuracy",
      "brier_score",
      "per_state_n",
      "exclusion_rate"
    ],
    "metric_unit": "percentage points, that is the share multiplied by 100",
    "paired_comparison": "the per-contest absolute error difference against the linear reference model and against the Primary carry-over, bootstrapped over states",
    "bootstrap": {
      "repetitions": 10000,
      "seed": 20261025,
      "unit": "state",
      "interval": "percentile 95%",
      "status": "exploratory; the districts are not a random sample",
      "reason_for_state_unit": "the districts of one state share the electoral rules and the candidate pool, so they are not independent"
    }
  },
  "exclusion_rules": {
    "rule_set": "the rules of the frozen 2016-2022 cohort are applied unchanged",
    "categories": [
      "unopposed",
      "write-in only",
      "fusion or ambiguous party code",
      "rank-choice or runoff rule",
      "missing numeric votes",
      "missing party subtotal",
      "special election with no Primary counterpart"
    ],
    "blind_execution": "the category list is fixed before the 2024 data are read; only the assignment of a contest to an already declared category may be recorded afterwards, and no category may be added, renamed or removed afterwards",
    "no_zero_filling": "a missing numeric value is never replaced by zero",
    "no_subtotal_merging": "a party subtotal is never merged into the candidate votes",
    "unknown_in_advance": "the number of 2024 contests that fall into each category is unknown in advance and is reported as unknown in the plan"
  },
  "reporting_rules": [
    "the evaluation is executed from the frozen configuration only; the primary comparison is confirmatory for 2024 because the year was never inspected",
    "every metric is reported for every model and for the whole 2024 cohort, including results that are worse than the reference model",
    "the number of evaluated contests, the number of excluded contests and the reason of every exclusion are reported",
    "the 2022 results and the 2024 results are shown in separate tables",
    "a change to any rule of this configuration is a new protocol version and turns the 2024 result into an exploratory one",
    "no value is produced when the source or a rule is unavailable; the reason is recorded instead"
  ],
  "forbidden_operations": [
    "looking at any 2024 House vote total, winner or error before this configuration is committed",
    "changing the model set, the hyperparameters, the preprocessing or the metric after the 2024 result is seen",
    "searching hyperparameters on the 2024 rows or on any year after 2016",
    "adding, removing or re-weighting a state or a district after the 2024 label is seen",
    "re-deriving the write-in, fusion, unopposed or missing-value rules from the 2024 source",
    "reporting the 2024 result as the performance of the whole United States; the evaluated set is a selected set of contests",
    "reading a political causal effect out of a vote share"
  ],
  "planned_source": {
    "expected_publication": "the biennial FEC Federal Elections compilation, the PDF and the Excel workbook of the 2024 edition",
    "expected_url_pattern": "https://www.fec.gov/documents/<document-id>/federalelections2024.xlsx",
    "expected_catalogue_page": "https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/federal-elections-2024/",
    "document_id": "unknown; the identifier is assigned by the FEC when the edition is published",
    "sha256": "unknown; the checksum is recorded at retrieval time, before any sheet is parsed",
    "retrieval_order": [
      "1. confirm the catalogue page exists and record its URL and the retrieval date",
      "2. download the workbook and record the URL, the byte size and the SHA-256",
      "3. record the sheet names and the column header row only",
      "4. only then parse the vote tables",
      "5. write the record into data/sources/fec2024_publication.json"
    ],
    "separation_from_the_frozen_catalog": "the 2024 record goes into a separate 2024 catalogue file; data/sources/fec_publications.json keeps the 2010-2022 entries unchanged"
  },
  "evaluation_commands": [
    "python -m pip install -r requirements.txt",
    "python -m pytest -q tests/test_frozen_2024_protocol.py",
    "python scripts/frozen_2024_protocol.py --check",
    "python scripts/download_fec_2024.py --output-dir data/raw",
    "python scripts/normalize_fec_2024.py --writein-policy attribute",
    "python scripts/evaluate_frozen_2024.py --assert-frozen-config"
  ],
  "freeze_commit_sha": "4f5da467a5a37bec4cbfa8e2bea810007db65256"
}
```

## 9. 限界と未解決事項

1. **2024年の出典が未公開**であり、本計画は**実行可能性が未確認**である。#54の着手時に未公開なら、**理由を記録して終了し、値を作らない**。
2. **出典の仕様（シート構成）が未確認**である。2022年版との差異（シート名・列名・境界ラベル）は未検証であり、取得時に記録する。
3. **2024年の母集団規模が未知**である。区割変更・特别選挙・無対立の規模が2026-10-25の時点では分からない。
4. **除外規則は2016～2022年で開発した**ものであり、2024年の制度差に完全には対応していない可能性が残る（固定後に変更はしない）。
5. **州単位ブートストラップは探索的**である。
6. **「2024年で確認できる」ことと「全米で正しい」ことは別**である。評価対象は選択された選挙区集合であり、母集団は非無作為である。
7. **本Issueが固定するのは評価手順であって、2024年の性能ではない。** 実際の2024年性能はまだ確認していない。
