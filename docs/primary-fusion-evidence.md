# 複合政党コードのFEC一次資料に基づく検証（Issue #14）

確認: 2026-10-16。対象: 2016・2020・2022年のFEC `Federal Elections`公式PDF。

## 原票で確認できた事実

FECの下院選挙結果では、ひとつの候補者が複数政党の記号で記載される（例: `D/IP`、`R/IP`、`D/IP/WF`、`D/PRO/WF/IP`）。これらは単純な単独`D`・`R`行だけで候補者票を合計すると`Party Votes:`小計に差が生じる例を含む。

**FEC公式PDFに記載された個別の小計の算術的検証:**

|年度・選挙区|候補者とFEC政党コード|対応党のPrimary候補者票|他の同一党候補者票|対応党W票|FEC `Party Votes:`|
|---|---|---:|---:|---:|---:|
|2016 OR-01、民主党|Suzanne Bonamici（`D/IP`）|99,153|Shabba Woodley 10,961|376|110,490|
|2016 OR-02、共和党|Greg Walden（`R/IP`）|85,039|Paul Romero 21,099|238|106,376|
|2016 OR-04、民主党|Peter DeFazio（`D/PRO/WF/IP`）|113,816|Joseph McKinney 9,894|601|124,311|
|2016 OR-04、共和党|Art Robinson（`R/CON`）|55,557|Jo Rae Perkins 26,375|620|82,552|
|2020 OR-04、民主党|Peter DeFazio（`D/IP/WF`）|96,077|Doyle Canning 17,701|974|114,752|
|2022 OR-05、民主党|Jamie McLeod-Skinner（`D/IP/WF`）|47,148|Kurt Schrader 38,726|537|86,411|

すべて右側の小計と左の候補者票・帰属書き込み票の和が一致する。FEC公式表は複合政党表記の候補者を、対応する主要政党の`Primary`欄に票数を記載している。

一次資料：
- [FEC Federal Elections 2016, Oregon U.S. House pp.158–159](https://www.fec.gov/resources/cms-content/documents/federalelections2016.pdf)
- [FEC Federal Elections 2020, Oregon U.S. House（District 4）](https://www.fec.gov/resources/cms-content/documents/federalelections2020.pdf)
- [FEC Federal Elections 2022, Oregon U.S. House（District 5）](https://www.fec.gov/resources/cms-content/documents/federalelections2022.pdf)

州制度の一次資料：
- [Oregon Secretary of State: Voting in Oregon](https://sos.oregon.gov/elections/pages/voteinor.aspx) — 主要政党と少数政党はPrimaryでの候補者決定方法が異なる。
- [Oregon Secretary of State: State Candidate Manual](https://sos.oregon.gov/elections/Documents/statecandidates.pdf) — 少数政党候補者は主に党大会等で候補者を指名し、主要政党Primaryとは区別される。

## 21件の未解決問題との関係

[21選挙区の実データ監査](residual-party-audit.md)では、R/D政党側で非ゼロの残差が23件、そのうち**18件**が複合党コードの候補者Primary票数と一致した。

上記6つのFEC例は、`D/IP/WF`などの**候補者行全体のPrimary票が、対応する主要政党Primaryの小計に計上されている**ことの独立の裏付けとなる。ただし、18件すべてをひとつずつ州当局の結果と突合したわけではない。数値一致だけを理由に自動採用するべきではない。

### 将来的に採用条件を拡張する場合の必須条件

1. その候補者コードを`/`区切りで分割し、**主要政党R/Dの一方だけ**が現れること。`R/D`等の両主要党を含む場合は曖昧として除外。
2. FECが対応する党のPrimary候補者票として記録したことが確認できること。FEC`Party Votes:`が「単独党候補者票 + その主要党を含む複合党候補者票 + W(R)/W(D)」と**完全一致**すること。
3. 同じ候補者票を他党と二重計上しないこと。一般選挙の票数は候補者全体の票であり、複数党の支持票を自動的に分割したものではないこと。
4. `missing-party-candidates`や`no_single_party_subtotal`を推測で補正しないこと。公式当選者フラグも再監査すること。
5. 改訂後は出典別照合、全年度の採用件数、2022年ホールドアウト結果、McNemar検定を**再計算**し、当時の921件（現行50州Voting Houseは916件）を比較用ベースラインとして保持すること。

## 複合党コードとは別の5党側について（2026-10-17追記）

本ファイルの6つの複合政党コード実例とは別に、旧診断で説明できなかった**5党側**について後続のFEC原票監査が進んだ。

- **2018 WI-07(D) +11**: `W(D)/W`書き込み票11をFEC 2018 PDFで確認。
- **2022 UT-02(R) +75,586 / UT-04(R) +56,397**: `R*`候補者行75,586/56,397をFEC 2022 PDFで確認。
- **2020 WI-01(R) +131 / WI-02(R) −131**: 同一2020 FEC XLSXの**3941行目だけがWI-02ラベルの`W(R)`131票**であり、WI-01の候補者と小計に挟まれていることを確認。[行単位監査](residual-party-audit.md)を参照。

5党側すべてに原票上の**算術的な説明候補**が揃ったが、未採用21地区を推測で追加することはしない。党別小計欠損3党側、複合党18党側の個別の帰属・州制度の追跡が残る。

**結論:** 複合党コードのPrimary票を主要政党の小計に含める算術的根拠は具体例で確認できたが、現行の研究データ**916件**は変更せず、追加採用は別PRで厳格に検証する。
