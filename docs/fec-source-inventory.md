# FEC公式選挙結果 — 出典台帳（Issue #2）

確認日: **2026-10-15**。本ファイルは公式ページとそのダウンロードリンクの所在を確認した記録。**Excelブックの全シート・列構造や全件票数の検証結果ではない**。実ダウンロード結果は別途監査する。

## 一次資料

- [FEC election results and voting information](https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/): FECは州が認証した連邦選挙結果を隔年で公表する（Primary、Runoff、General）。
- [Federal Elections 2022 — PDF](https://www.fec.gov/documents/5675/federalelections2022.pdf): 2022年の公式資料（2025年2月刊）のPreface・Explanatory Notesを確認。

## 年度別Excelの所在（リンク確認済）

| 年度 | 年度別ページ | Excelデータ | 形式 | 内部監査 |
|---|---|---|---|---|
| 2010 | [FEC 2010](https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/federal-elections-2010/) | [公式Excel](https://www.fec.gov/documents/1675/federalelections2010.xls) | xls | 未実施 |
| 2012 | [FEC 2012](https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/federal-elections-2012/) | [公式Excel](https://www.fec.gov/documents/1691/federalelections2012.xls) | xls | 未実施 |
| 2014 | [FEC 2014](https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/federal-elections-2014/) | [公式Excel](https://www.fec.gov/documents/1700/federalelections2014.xls) | xls | 未実施 |
| 2016 | [FEC 2016](https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/federal-elections-2016/) | [公式Excel](https://www.fec.gov/documents/1890/federalelections2016.xlsx) | xlsx | **実取得・SHA-256照合済** |
| 2018 | [FEC 2018](https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/federal-elections-2018/) | [公式Excel](https://www.fec.gov/documents/2706/federalelections2018.xlsx) | xlsx | **実取得・SHA-256照合済** |
| 2020 | [FEC 2020](https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/federal-elections-2020/) | [公式Excel](https://www.fec.gov/documents/4228/federalelections2020.xlsx) | xlsx | **実取得・SHA-256照合済** |
| 2022 | [FEC 2022](https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/federal-elections-2022/) | [公式Excel](https://www.fec.gov/documents/5676/federalelections2022.xlsx) | xlsx | **実取得・SHA-256照合済** |

2016/2018/2020/2022の4ファイルは実際にダウンロードし、バイト数とSHA-256が
`data/sources/expected_analysis.json` の固定値と一致することを確認済み。
数値とURLの対応は [report-citation-audit.md](report-citation-audit.md) に、
本文・付録の対応は [report-final-figure-selection.md](report-final-figure-selection.md) に記録する。

取得時のSHA256・容量は `scripts/download_fec.py` が `data/raw/download-manifest.json` に保存する。**リンク確認はダウンロード・中身の検証を意味しない**。

## 2022年の公式PDFで確認した分析上のリスク

1. Primary参加者とGeneral参加者は同一集合ではなく、候補者の得票率はそれぞれ異なる分母を使う。
2. CT/UT/VA等では党大会で候補者を指名する場合があり、Primary欄の欠損をゼロ票として扱ってはいけない。
3. 無対立の候補者が投票用紙に載らず、得票が0・空欄になる場合がある。
4. NY/CTのCombined Partiesでは複数政党の票が同じ候補者の票として集計される場合があり、二重計上に注意する。
5. Runoff、Regular、Special、General Runoffを区別する。2022年の巻頭集計表にはRunoff・Specialが合算された例もある。
6. 2020年と2022年は区割り変更があるため、同じdistrict番号を同一地域と仮定できない。
7. 書き込み候補・第三党票があるので、二大政党得票率は公式の総得票率と異なる。

根拠: Federal Elections 2022, Preface / Explanatory Notes / Notes on Charts。個々の州の制度には別途州別の検証が必要。

## 再現手順

```bash
python -m pip install -r requirements.txt
python scripts/download_fec.py --years 2020 2022
python scripts/audit_fec_workbook.py data/raw/federalelections2022.xlsx --max-sheets 8 --rows 6 --output data/raw/fec2022-audit.json
python scripts/audit_fec_workbook.py data/raw/federalelections2020.xlsx --max-sheets 8 --rows 6 --output data/raw/fec2020-audit.json
```

`FEC source audit` Actionsを手動実行するか、監査ファイルに変更のあるPRから実行する。GitHubには原票をコミットせず、Actions Artifactsにもアップロードせず、短い監査ログのみ保存する。

## 未完了事項

- 2020年・2022年の下院シート先頭18行の確認は完了。残る行・複雑な州の票数照合はIssue #3で実施する。
- Primary / General / House / Senateの正しいパース方法を実ファイルから確定する。
- 2010〜2014年の旧 `.xls` を実データで読み取れるか確認する。
- この手順では行頭しか検査しないため、票数や原票との一致はIssue #3で検証する。

## 実取得・実行結果（2026-10-15）

GitHub Actions [FEC source audit（検査ジョブ）](https://github.com/SMRI2170/fec-election-analysis/actions/runs/38686065875) において、2020・2022の**実Excelファイルをダウンロードし、シート名と下院結果シートの先頭18行を調査**した。ソースを推測で組み立てたものではない。

|年度|バイト数|SHA256|シート数|下院結果シート名|
|---|---:|---|---:|---|
|2020|6,251,110|`5073b6d2c76c86c941508dfb1a11cc497e8529b0068c5132aceb0f385c19352e`|19|`13. US House Results by State`|
|2022|3,179,722|`cdb258ea23803e50d752bcea19faa39b3c201eb960094bcb556c3a38c2350897`|11|`8. US House Results by State`|

下院結果表の先頭行の列名は両年度とも概ね共通で、`STATE ABBREVIATION`、`DISTRICT`、`FEC ID`、`PARTY`、`PRIMARY VOTES`、`RUNOFF VOTES`、`GENERAL VOTES `、`PE WINNER INDICATOR`、`GE WINNER INDICATOR`、`FOOTNOTES` を確認した。2020年の**24列**に対し、2022年はRCV（順位選択投票）のラウンド別得票/比率の列が追加されて**30列**。

列の位置は2020年・2022年の下院結果シートに限り以下のとおり（pandas `header=None` の0始まり列番号）。

|列番号|内容|
|---|---|
|1|STATE ABBREVIATION|
|3|DISTRICT|
|4|FEC ID（候補者識別に利用）|
|9|TOTAL VOTES（`Party Votes:` / `District Votes:` 等のラベルも入る）|
|10|PARTY|
|11|PRIMARY VOTES|
|13|RUNOFF VOTES|
|15|GENERAL VOTES|
|19|COMBINED GE PARTY TOTALS|
|21, 22|Primary/General winner indication|

注意: 2022年の最初の下院選挙区では、共和党Primary得票に文字列 `Unopposed` が記録される例がある。ここを0票として変換してはいけない。両年度とも `Party Votes:`・`District Votes:` の**小計行が候補者行に混在**し、二重計上防止が必須。2022年は州・区を見出し行でも記載しており、選挙区番号が数値でない見出し行を除外する必要がある。

この検査は下院先頭18行と全シート**名**の取得であり、すべての候補者・選挙区を検証したわけではない。次はIssue #3で全行に対する型判定・小計除外・除外理由を記録し、サンプリングした原票と照合する。
