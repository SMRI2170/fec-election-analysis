# FEC Election Analysis — データサイエンス特論レポート課題 #1

> **現行基準（2026-10-16）**: FEC公式2016・2018・2020・2022年結果から、**米国50州の投票権を持つ下院議員選挙916レコード**を厳格な規則で抽出（2016=200、2018=241、2020=237、2022=238）。非投票権Delegate/Resident Commissionerを含む旧921件、旧738/740件は**履歴上の異なる抽出基準**。本文の現行指標と混ぜない。

## 研究課題

**予備選挙（Primary）の二大政党別投票構成は、本選挙（General）の二大政党得票比率・多数派をどこまで予測できるか。前処理・標本の選び方によって結論は変わるか。**

- 入力: `P = R_primary / (R_primary + D_primary)`
- 回帰ターゲット: `G = R_general / (R_general + D_general)`
- 分類ターゲット: **Generalの二大政党票における共和党優勢**（`G > 0.5`）。`general_rep_win`という後方互換名は**FEC公式当選者と同義ではない**。
- 年度外評価: 2018年は2016年、2020年は2016–2018年、2022年は2016–2020年のみで学習。テスト年の結果を説明変数に含めない。

## 現行の実験結果

| テスト年 | テスト件数 | 線形回帰MAE | Primary多数派規則 正解率 | ロジスティック回帰 正解率 |
|---|---:|---:|---:|---:|
| 2018 | 241 | 0.0442 | 90.04% | 84.23% |
| 2020 | 237 | 0.0549 | 89.87% | 91.56% |
| 2022 | 238 | 0.0502 | 89.92% | 86.97% |

2022年の単純規則−ロジスティック回帰の差は**約+2.94ポイント**だが、McNemar正確両側検定は **p=0.09229**。5%有意水準で両モデルに明確な差があるとは主張できない。異なる抽出基準で出た旧738件のp=0.00635と混ぜない。

- [現行のモデル評価・限界](docs/model-evaluation.md)
- [標本選択の影響](docs/selection-bias.md)
- [2022年の誤予測上位5例](docs/2022-error-case-studies.md)
- [FEC原票との照合・正規化方針](docs/normalization-audit.md)
- [再現性、データSHA-256、固定した実験指標](docs/reproducibility.md)

**重要な限界:** 916件は50州すべての選挙の無作為標本ではない。無対立選挙、特殊な州制度、小計の不一致、欠損などを理由付きで除外している。予備選挙と本選挙では投票者が異なり、Primaryの比率を世論調査・支持率や因果効果と同一視できない。2022年の予測誤差を確認した後に研究対象を修正した経緯もあり、以後の比較は探索的として扱う。

## 再現手順

Python 3.11以降。以下はリポジトリのルートから実行する。

```bash
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/download_fec.py --years 2016 2018 2020 2022
python scripts/normalize_fec.py --years 2016 2018 2020 2022 --writein-policy attribute
python scripts/run_backtests.py --input data/processed/elections.csv --test-years 2018 2020 2022
python scripts/verify_reproducibility.py
```

- Windows PowerShellでは必要に応じて`python`を`py`に、macOS/Linuxでは`python3`に置換する。
- 入力元は[FEC公式選挙結果](https://www.fec.gov/introduction-campaign-finance/election-results-and-voting-information/)に掲載される4年度のExcel。取得URLとファイルSHA-256は`data/sources/fec_publications.json`および`data/sources/expected_analysis.json`で管理。
- `data/raw/`と`data/processed/`の大きな公式Excel・正規化CSVはGit管理外。コードと小容量の固定基準・説明文書はGitで公開。
- `Python CI`は単体テスト、`FEC source audit`は実公式ファイルを用いた票数照合・予測評価・再現性チェックを行う。後日公式ファイルや分析結果が変化した場合は自動で基準値を上書きせずエラーとする。

## ディレクトリの主要ファイル

| パス | 用途 |
|---|---|
| `scripts/download_fec.py` | 公式FEC Excel取得・出典とSHA-256記録 |
| `scripts/normalize_fec.py` | 候補者票・政党小計の変換と除外理由記録 |
| `scripts/run_backtests.py` | 年度外予測と基準モデル比較 |
| `scripts/source_reconcile.py` | FEC候補者行・地区票の独立照合 |
| `scripts/error_cases.py` / `scripts/build_error_case_studies.py` | 誤差上位例・候補者行の照合 |
| `scripts/verify_reproducibility.py` | 固定した年別件数・指標・公式データSHA-256との比較 |
| `data/sources/expected_analysis.json` | **現行916件**の再現性基準 |
| `docs/issue-backlog.md` | 現行Issue進捗・依存関係・AI開発ルール |

## 進捗・次の作業

現状: #15（当選者ターゲット監査）、#16（標本選択分析）、#18（再現性固定）は完了。**#14（残り21区のPrimary小計差）、#17（高誤差5区の州選管一次資料）、#6（指定Word提出）**が主要な未完了事項。研究Issue一覧は[Issue台帳](docs/issue-backlog.md)を参照。

## 提出形式と公開範囲

提出予定: **2026年11月3日17:00**、Manaba+R、大学指定Wordテンプレートの`.docx`。本文2–4ページ推奨（最大8ページ）・ソースコード付録。**締切日時・容量・正式な書式は講義資料と提出画面で最終確認すること。** 個人情報・学生番号・提出前の未公開レポート原稿を公開GitHubへコミットしない。

本リポジトリは研究・課題提出用であり、ライセンスは未設定。
