> **現行データ基準（2026-10-15）:** FECの党帰属付きPrimary書き込み票`W(R)`/`W(D)`を修正して抽出した**921件**を使用します。過去の740/738件は履歴値。最新の再計算結果は[モデル評価](docs/model-evaluation.md)をご覧ください。

# FEC Election Analysis — データサイエンス特論レポート課題 #1

米国連邦選挙委員会（FEC）の公開選挙結果データを用い、**予備選挙（Primary）の投票構成から本選挙（General）をどこまで予測できるか**、また**データの選び方によって結論が変化するか**を検証する研究用リポジトリです。

> **実データによる実験は実施済み:** 公式FECの2016/2018/2020/2022年のデータから、厳格な採用条件で**921選挙区**を抽出して年度外評価を実施しています。公式Excelと生成CSVはGit管理外ですが、取得コード・監査コード・再現手順と実測値を公開しています。`data/examples/` のデータは架空のテスト専用です。

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

## 公式FECデータの出典・形式監査

取得元一覧と検査方法は [出典台帳](docs/fec-source-inventory.md) を参照。`python scripts/download_fec.py --years 2020 2022` で公式Excelを取得し、`python scripts/audit_fec_workbook.py data/raw/federalelections2022.xlsx` で原ファイルの表構造を確認できます。データの正規化はIssue #3で行います。

## 年度外予測の再現

FEC公式XLSXの2016〜2022年をダウンロード・正規化した後、時間順にモデルを学習して評価します。

```bash
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022
python scripts/run_backtests.py --input data/processed/elections.csv --test-years 2018 2020 2022
```

[分析方法・実測結果と限界](docs/model-evaluation.md) / [データの除外条件](docs/normalization-audit.md)

## データの信頼性と統計的な不確実性

抽出した740件について、公式Excelの候補者票と選挙区別総票の内部整合を再確認しました。[原票照合と限界](docs/source-reconciliation.md) / [2022年の勝敗モデル比較と統計的検定](docs/sensitivity-analysis.md)。

## 公式当選者の検証と研究上のラベル

FEC`GE WINNER INDICATOR`と二大政党の得票優勢を比較する[監査と理由付き除外](docs/target-label-audit.md)を追加しました。2018年ME-02（順位選択投票で結果が逆転）およびNC-09（2018年結果が非認証）を除外した結果、**当初の標本は738件でしたが、党帰属付き書き込み票を追加検証した現行の標本は921件**です。

[現行のモデル評価・MAE・正解率](docs/model-evaluation.md) / [Primary小計不一致224件の監査](docs/primary-subtotal-audit.md)。現行の`general_rep_win`は後方互換名で、定義は「共和党の二大政党得票数での優勢」です（すべての選挙における実際の当選とは限りません）。
