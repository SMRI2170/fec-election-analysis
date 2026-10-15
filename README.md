# FEC Election Analysis — データサイエンス特論レポート課題 #1

米国連邦選挙委員会（FEC）の公開選挙結果データを用い、**予備選挙（Primary）の投票構成から本選挙（General）をどこまで予測できるか**、また**データの選び方によって結論が変化するか**を検証する研究用リポジトリです。

> **研究準備中:** 現在含まれるデータは、テスト用の架空データのみです。FEC実データで得られた分析結果はまだありません。架空データの出力をレポートの分析結果として使用しないでください。

## 研究上の問い

1. 予備選挙の共和党・民主党の投票比率は、本選挙の政党別得票比率・勝敗と関係するか。
2. 過去年度のデータで構築したモデルは、未使用の年度にも通用するか。
3. 選挙制度・無対立選挙・欠損値などの扱いは、予測性能の解釈にどの程度影響するか。

一次資料: [FEC Election and voting information](https://www.fec.gov/introduction-campaign-finance/election-and-voting-information/)

## フォルダ構成

```text
.github/workflows/ci.yml       CI（テスト・Pythonチェック）
data/examples/                 架空のテスト用データ
data/raw/                      元データ（Git管理対象外）
data/processed/                正規化データ（Git管理対象外）
docs/research-plan.md          仮説・研究計画
docs/data-dictionary.md        正規化後データの仕様
docs/issue-backlog.md          実装の順序
docs/report-outline.md         論文の構成
scripts/inspect_fec.py         年度別Excel/CSVの構造調査
scripts/analyze.py             正規化済みCSVの簡易予測・評価
src/fec_analysis/core.py       検証・特徴量作成
tests/test_core.py             ユニットテスト
```

## セットアップ

Python 3.11+:

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

取得したFECの実ファイルの構造を確認:

```bash
python scripts/inspect_fec.py data/raw/2022.xlsx
```

**注意:** 2022.xlsxはファイル名の例です。ダウンロードした実ファイルを指定してください。年度ごとの構造を確認した後、`docs/data-dictionary.md`に従って`data/processed/elections.csv`に変換します（変換器は未実装）。

正規化データで年度外評価:

```bash
python scripts/analyze.py --input data/processed/elections.csv --test-year 2022
```

## 分析上の注意

- 上院（州単位）と下院（選挙区単位）は、原則として別々に分析する。
- 予備選挙は政党ごとに参加者と制度が異なり、二大政党の票数比率は有権者全体の支持率と一致するものではない。
- FECの年別Excel/PDFは表構造が異なり得る。候補者名・州・区・政党・選挙段階を確認し、原票との照合記録を残す。
- 無対立・特殊選挙・同日特別選挙・Top-two primaryなどを機械的に合算しない。
- テスト年度はモデル調整に使用しない。除外基準とその変更結果を公開できる形で記録する。

## レポート提出について

提出物は大学指定テンプレートを利用した`.docx`。本文2〜4ページ推奨（最大8ページ）、締切2026年11月3日17:00。コードは付録に添付し、参考資料と独自の成果を明確に区別します。最終レポート原稿はGit管理対象外とします。

## GitHub Actions

公開リポジトリの標準GitHub-hosted runner（`ubuntu-latest`）でテストを実施します。Actionsの実行時間は無料ですが、同時実行・単一ジョブの時間・成果物ストレージ等は制限されます。大量のバッチ分析をCIの代わりに連続実行する用途には使わないでください。

研究用の初期構成であり、ライセンスは未設定です。外部データや参照コードは各ファイル・レポートに出典を示します。
