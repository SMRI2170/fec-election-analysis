> **更新（Issue #15）:** 本文の740件照合は2026-10-15の初回実験の履歴。2018年の2件を除いた**現在の738件**について、候補者別票・地区総票の不一致がともに0件であることを [最新Actions](https://github.com/SMRI2170/fec-election-analysis/actions/runs/38702180616) で再確認している。本文の過去件数と混同しない。

# FEC元Excelとの二重照合（2026-10-15）

## 検証データと目的
2016・2018・2020・2022年のFEC連邦選挙結果Excel（下院の\`US House Results by State\`）を、\`scripts/normalize_fec.py\`で保守的に抽出した**740レコード**と直接突合した。

**照合は、分析対象が正しく数値として集計されているかの検査である。分析対象の選定・投票率の比較可能性・因果関係・全国代表性を保証するものではない。**

## 独立した照合の手順

1. 公式Excelの候補者行を \`STATE ABBREVIATION\` × \`DISTRICT\` × \`FEC ID\` × \`PARTY\` から検索。
2. 各政党（R/D）のPrimary・Generalの候補者票合計を、正規化済みの4得票列と一致照合。
3. FECが示す \`District Votes:\` のGeneral合計を、**候補者IDのない少数政党候補・Scattered書き込み票を含む全政党候補行**から算出した総票数と一致照合。
4. 予測誤差が大きい2022年の上位5選挙区、および既知の2020年AL-01について、候補者名・FEC ID・政党・票数・脚注を別ファイルに保存。
5. 除外されている\`primary-subtotal-mismatch\`の事例について、候補者票合計と政党別小計の差を保存。未確認の原因を推測で修正しない。

再実行:

\`\`\`bash
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022
python scripts/error_cases.py --input data/processed/elections.csv --test-year 2022
python scripts/source_reconcile.py
\`\`\`

## 公式データでの実測結果

[成功したFEC source audit実行ログ](https://github.com/SMRI2170/fec-election-analysis/actions/runs/38690181698)より。

|検証対象|件数|
|---|---:|
|抽出済みレコード（2016〜2022年）|740|
|Primary/General候補者票と正規化票の不一致|0|
|FEC District Votes（General）と総候補者票の不一致|0|
|2022年の誤差上位5件での得票照合|全件一致|

最初の総得票照合では書き込み票・少数政党の候補者行にFEC IDがない場合を数えず、97件の差が発生した。**元データに誤りがあったのではなく、監査実装側の集計範囲の不備**だった。これらを含めた後にゼロとなった。監査ルールはGitHubで履歴管理する。

## 未解決のデータ選択上の問題

2016〜2022年のPrimaryの党別小計不整合による**224件の除外**は、候補者票合計がFEC記載の政党別小計に一致しないものであり、今回の740件の総得票検証とは別問題である。

2020年AZ-03（共和党候補票合計29,272・FEC政党別小計29,316）など、小差でも自動修正せずに除外した。2016年AZ-04（民主党24,097 vs 24,146）、CO-02（民主党43,660 vs 45,017）も同様である。書き込み票等との関係は個別検証が必要。

さらに、制度差が未検証の州、無対立選挙、2010〜2014年の旧XLSは未対応。これらを含めて「全米の選挙全体」を一般化しない。

## 再現可能な成果物

GitHub ActionsのArtifact（保存期間3日）:
- \`data/processed/source-reconciliation.csv\`: 740件すべての候補者票・選挙区総票の照合ステータス
- \`data/processed/case-evidence.json\`: 2022年誤差上位5件・2020年AL-01の候補者行、除外されたPrimary小計不整合の例

生のExcelをGitに登録せず、取得URLとファイルSHA256は別の台帳に残す。

研究上の評価: 票数集計の**内部整合性**は確認できた一方、選挙制度の共通性とサンプル選択のバイアスについては引き続き検証が必要。
