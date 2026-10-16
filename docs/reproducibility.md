# 実験の再現性と固定した評価基準（Issue #18）

現行の実験対象は**50州の投票権を持つ米国下院選挙（選別済み916レコード）**。FECの2016・2018・2020・2022年公式Excelを再取得して同じ結果が得られることを検査する。

## 入力データ

- 公式URL一覧: [FEC Publications](../data/sources/fec_publications.json)。
- `scripts/download_fec.py`で、公式URLから取得したファイルの年・URL・ファイルサイズ・SHA-256を`data/raw/download-manifest.json`に記録。
- `scripts/verify_reproducibility.py`で実際のXLSXバイトを**独立に再計算**し、ダウンロード記録のSHA-256と一致を照合。
- GitHub Actionsの実行ごとに、出典とSHA-256、年度別抽出件数、評価指標を`reproducibility-manifest.json`へまとめる。元ExcelはGitHubリポジトリへコミットしない。

## 固定した結果

`data/sources/expected_analysis.json`に、2016年200件、2018年241件、2020年237件、2022年238件（計916件）を明記し、年度外の線形回帰MAE・単純分類精度・ロジスティック回帰精度をチェックする。

- 論文に掲載する指標の実数値は[現行916件の実験報告](model-evaluation.md)と合わせる。
- 固定値は表示用に丸めた精度をもとにしているため許容誤差は`0.0001`。年・モデル名・評価件数が変わる場合は許容しない。
- 公式ファイルの**恒久的SHA-256固定は、成功した公式データ監査からハッシュを確認してから**`official_source_sha256`へ追加する。追加前は、取得後ファイルとダウンロード時の記録の相互照合であり、将来の公式ファイル差し替えを検出する恒久的基準にはならない。

## 再実行方法

Python 3.11でリポジトリのルートから次の順に実行（Windows PowerShell、macOS、Linuxのいずれも同じコマンド、実行環境により`python`を`python3`に置換）。

```bash
python -m pip install -r requirements.txt
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022
python scripts/run_backtests.py --input data/processed/elections.csv --test-years 2018 2020 2022
python scripts/verify_reproducibility.py
```

同時に原票・選挙区総票照合、除外群診断、誤予測の事例一覧もGitHub Actionsの`FEC source audit`で実行する。マージしたコードのGit commit SHAと、公式ファイルのSHA-256・年・実験結果をレポートの再現性節に記載する。

## 結果が違った場合の対応

CIは結果を**自動更新せず失敗**する。公式ファイルの改訂、データ変換ロジックの変更、モデルの依存ライブラリ差分、機械精度などを確認し、研究上の意味を記録してから別PRで基準値を更新する。

## 制約

現行916件は米国下院全体の無作為抽出ではない。2022年のデータを確認後に対象条件も修正しており探索的解析である。GitHub Actionsの3日保存のArtifactは補助証跡で、提出用の説明・コード・基準値はリポジトリに残す。公開リポジトリに学生番号・個人情報・非公開の論文原稿はコミットしない。
