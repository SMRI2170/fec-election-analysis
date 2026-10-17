# Issue #49 — Primary時点の採否条件とGeneral事後情報の選択を分離する

**状態:** 新規検証。公式FEC 2016/2018/2020/2022の50州Voting House下院報告**1,756グループ**を対象に、最終採用**916件（200/241/237/238）**および除外**840件**と1対1で突合する。現行の916件のデータ・予測指標は**更新しない**。

## 何を検証するか

現在の\`scripts/normalize_fec.py\`では、\`PRIMARY VOTES\`・候補者・党別小計などPrimary側の採用条件を検査した後、\`GENERAL VOTES\`の欠損・ゼロ票・非数値表記、\`GE RUNOFF ELECTION VOTES\`／RCVの追加段階、公式当選者表示との整合を使って最終採否を決める。したがって研究の916件は**General後の観測・採否を条件とする選別標本**であり、「選挙前に予測可能だった地区の無作為標本」ではない。

本Issueでは**予測モデル自体は再学習・修正せず**、FECの同じ原票を使って各グループについて次の3つの異なる概念を記録する。

|分類|定義|General結果に依存するか|
|---|---|---|
|\`primary_report_compatible\`|**事後公刊FEC**のPrimary候補票と党小計のみで、既存制度・欠損規則を満たすと判定できる|いいえ（General列を一切読まない）|
|\`post_general_rd_numeric_observable\`|General候補R/D票の双方が有効な数値で、二党得票の評価指標を定義できる|**はい**|
|\`final_916_selected\`|現在の正規化器と公式勝者監査も通過したか|**はい**|

各行で\`primary_snapshot_timestamp_verified=False\`と\`operational_pre_election_eligibility_proven=False\`を記録する。FEC最終ワークブックのPrimary行は**同じ数値が選挙前に実際に利用できたことを証明しない**。時点別の評価可能性は**事後再構成**である。

## 公式FEC再取得で得られた実測結果（2026-10-17）

初回[公式FEC4年度ダウンロード＋916件固定評価＋Primary/General独立監査](https://github.com/SMRI2170/fec-election-analysis/actions/runs/39014867519)の成功結果。下記は**本選挙後公刊のFEC元Excelから事後的に再構成した数値**であり、当時Primary直後に公表・入手できた件数ではない。

|テスト対象年|元FECグループ|Primary列と党小計・候補者列だけで互換|Primary条件からの除外|Primary互換かつGeneral二党票が数値|General後の追加除外|最終選別916件の内訳|
|---|---:|---:|---:|---:|---:|---:|
|2016|438|200|238|200|0|200|
|2018|438|243|195|243|**2**|241|
|2020|441|237|204|237|0|237|
|2022|439|239|200|239|**1**|238|
|**合計**|**1,756**|**919**|**837**|**919**|**3**|**916**|

- **差の内訳：** 2018年の2地区は公式当選者表示と二党票多数派の判定が不整合／公式当選者表示欠損となった既存の例外（ME-02・NC-09）。2022年の1地区はFECの決選投票・RCV関連の値を持つとして既存正規化器が除外した例。別の3地区と混ぜていないか\`final_exclusion_reason\`でトレースできる。
- Primary側の837件のうち、**406件は州の制度を保守的に除外**、22件は非投票権Delegate等の法域、212件はUnopposed、135件はR/D候補者行の不足、37件はPrimary得票0等、21件は党小計不一致、4件は未分類政党行。これらは「最初に該当した理由」の**単一分類**であり、複数の欠損理由が共存する可能性がある。
- 今回Primary側で互換と判定できた919件はGeneral二党候補者票も数値で観測でき、**追加のGeneral得票欠損を理由とした減少は0件**。ただし**これは後日FEC workbookで対象を条件付けした結果**であり、後日公刊物にある情報を選挙前に取得できたと証明しない。
- FEC公式1,756件のうち約47.7%（837件）がPrimary側基準で除外されることは、州制度・無対立・党行の欠損などから**原データ全体に強い選択がある**ことを示す。General後の追加除外3件という小ささから、全米代表性や選挙前運用性能の問題が解消したと結論付けてはならない。
- 選挙前に取得可能な一次アーカイブのタイムスタンプを独立に確認していないため、\`primary_snapshot_timestamp_verified\`も\`operational_pre_election_eligibility_proven\`も1,756件で**false**。それらを今後確認するまでは、「事後再構成されたPrimary互換集合919件」と呼ぶ。

**結論の修正案（レポート用）：** 本研究の年度外予測では、モデルに未来のGeneral票を入力する情報漏洩は防止した一方、採用集合916件は**Primaryだけで一定程度再構成できる919件の内、General後の適格条件を通過した選択標本**である。General事後判定で落ちたのは3件だったが、Primary段階の保守的な除外は837件に達し、FECデータの出版時刻も未検証である。したがって主張できるのは**条件付きの過去再現可能性**であり、全米の実運用選挙前予測精度ではない。

## 重要な境界と比較手順

- FEC内部の「Primary行」検証では所属州の選挙制度保守除外、R/D候補者の正得票・無対立、Party Votes小計、W(R)/W(D)の取り扱いを既存正規化器に揃える。全報告グループが選挙前に入手できたとは決して書かない。
- \`GENERAL VOTES\`の空白、二党の得票欠損、RCV／決選投票や公式当選者表示の相違は**General後の情報**として独立記録。これをPrimary側の採否に持ち込まない。
- **Primaryから条件判定可能なグループ数 → General R/D票数が観測されたグループ数 → 最終916件**という包含関係（2番目は1番目に限定）を年別集計する。General後の選択で欠損・数値観測可否が影響したグループの理由も原本と突合。
- Generalの欠測値・無対立・州別制度は勝手に補完しない。**全米の予測精度の外挿やサンプル選択バイアスが消えたと主張しない**。

## 再実行

\`\`\`bash
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022 --writein-policy attribute
python scripts/run_backtests.py --input data/processed/elections.csv --test-years 2018 2020 2022
python scripts/verify_reproducibility.py
python scripts/audit_prediction_time_eligibility.py --assert-baseline
\`\`\`

最終分析台帳：\`data/processed/prediction-time-cohort.csv\`（1,756行：各年・州・区・Primary互換性／事後General票数観測／最終916件採否／理由）。集計：\`data/processed/prediction-time-cohort-summary.json\`。これらは実際のFECデータを再取得するGitHub Actionsで作成し、短期Artifactとして保存する。テストの合成fixtureは実測数値と混ぜない。

## 注意と既存研究の関係

**結果を選んでから標本を選んでいるわけではないと断定できるわけではない。** 研究用にはGeneral後に確認できる結果を使った条件付き評価として説明可能だが、2024年の追加評価を確認的な実験にするには、さらに**選挙前に確定できる対象集合と公開日時の独立証明**、検証手順の凍結（[#53](https://github.com/SMRI2170/fec-election-analysis/issues/53)）が必要。これは[#16](https://github.com/SMRI2170/fec-election-analysis/issues/16)の「旧・新の採否比較」と違い、**採否時点による評価対象の循環を明示する**もの。

**参照:** [#49](https://github.com/SMRI2170/fec-election-analysis/issues/49)、[親分析 #5](https://github.com/SMRI2170/fec-election-analysis/issues/5)、[提出レポート #6](https://github.com/SMRI2170/fec-election-analysis/issues/6)。
