"""Assemble the Python source appendix of the report (Issues #87 and #88).

The assignment asks for the **complete** source of the programs used to
produce the reported results. This script assembles that appendix from the
repository itself so that:

* the appendix is byte-identical to the committed sources,
* every file carries its SHA-256 and the Git commit that introduced it, and
* the size and page impact can be measured *before* the appendix is put into
  a Word document.

Nothing is excerpted. If a file is too large to include, that is a finding to
report, not a reason to silently trim it.

The appendix text is written to a private directory; it is not part of the
public repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class AppendixFile:
    """One source file that belongs in the appendix."""

    path: str
    role: str
    produces: str

    @property
    def absolute(self) -> Path:
        return ROOT / self.path


#: The complete set of self-written programs needed to reproduce the report.
#:
#: Order is the reproduction order: official data, normalisation, evaluation,
#: then the figures. Library internals and CI workflow files are deliberately
#: excluded -- they are not "the author's programs" and they do not reproduce
#: a single reported number.
APPENDIX_FILES: tuple[AppendixFile, ...] = (
    AppendixFile(
        "scripts/download_fec.py",
        "公式FECワークブックの取得とSHA-256記録",
        "data/raw/federalelections{2016,2018,2020,2022}.xlsx と download-manifest.json",
    ),
    AppendixFile(
        "src/fec_analysis/core.py",
        "正規化レコードの検証と二党得票率の計算",
        "primary_rep_share / general_rep_share / general_tie",
    ),
    AppendixFile(
        "scripts/normalize_fec.py",
        "保守的な選別（1,756報告グループ→916件）",
        "data/processed/elections.csv, exclusions.csv, normalization-summary.json",
    ),
    AppendixFile(
        "scripts/analyze.py",
        "ベースライン評価（回帰・分類・多数派規則）",
        "scripts/analyze.py の evaluate() が出力する指標表",
    ),
    AppendixFile(
        "scripts/run_backtests.py",
        "年度外バックテストの実行",
        "data/processed/backtest_metrics.csv（2018/2020/2022のMAE・accuracy）",
    ),
    AppendixFile(
        "scripts/verify_reproducibility.py",
        "再現マニフェストの作成と固定値の照合",
        "data/processed/reproducibility-manifest.json",
    ),
    AppendixFile(
        "src/fec_analysis/selective.py",
        "評価母数の凍結契約と監査",
        "母数241/237/238、基準誤答24/24/24、包含関係1,756/1,734/916",
    ),
    AppendixFile(
        "scripts/inspect_selective_cohort.py",
        "母数監査CLI",
        "data/processed/selective-cohort-audit.json",
    ),
    AppendixFile(
        "scripts/selective_primary_rule.py",
        "判定保留の純粋関数（General非参照）",
        "採否と回答の判定（整数演算）",
    ),
    AppendixFile(
        "scripts/evaluate_selective_primary.py",
        "15条件のcoverage–risk評価",
        "data/processed/selective-primary-grid.csv / .json",
    ),
    AppendixFile(
        "scripts/compare_random_abstention.py",
        "同数ランダム保留との比較（超幾何分布）",
        "data/processed/selective-primary-random-baseline.csv / .json",
    ),
    AppendixFile(
        "scripts/plot_results.py",
        "予備選挙比率と本選挙比率の散布図・年度外MAE図",
        "outputs/figures/primary_vs_general_2022.png, chronological_share_mae.png",
    ),
    AppendixFile(
        "scripts/plot_selective_primary.py",
        "判定率–誤答率図とランダム保留比較図",
        "outputs/figures/selective_coverage_risk.png/.svg, selective_random_abstention_comparison.png",
    ),
    AppendixFile(
        "scripts/analyze_state_year.py",
        "州×年度の採用数・年度外残差・重み付け別のMAE",
        "data/processed/state_year/state_year_summary.json, state_year_error_metrics.csv, "
        "state_year_coverage.csv, fig_state_coverage.png/.svg",
    ),
    AppendixFile(
        "scripts/analyze_error_structure.py",
        "誤答構造の分析（analyze_state_year.pyが依存する補助スクリプト）",
        "data/processed/error_structure_summary.json",
    ),
    AppendixFile(
        "scripts/source_reconcile.py",
        "FEC党別小計と候補者票の突合（normalize_fec.pyが使う）",
        "data/processed/source-reconciliation.json",
    ),
    AppendixFile(
        "scripts/audit_winners.py",
        "勝者例外の監査（normalize_fec.pyが使う）",
        "data/processed/winner-exceptions.json",
    ),
    AppendixFile(
        "scripts/audit_state_residual_composition.py",
        "符号付き残差の構成効果と標本数の監査",
        "data/processed/state_year/state_residual_composition.csv / .json",
    ),
    AppendixFile(
        "scripts/analyze_probability_calibration.py",
        "予備選挙得票率の確率出力の校正評価",
        "data/processed/calibration/calibration_bins.csv / calibration_metrics.json, "
        "outputs/figures/calibration_reliability.png/.svg",
    ),
)


def git_commit_for(path: str) -> str | None:
    """Return the commit that last touched ``path``, or None."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", path],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    value = result.stdout.strip()
    return value or None


def collect() -> list[dict]:
    """Describe every appendix file with its checksum and commit."""
    entries: list[dict] = []
    for item in APPENDIX_FILES:
        if not item.absolute.exists():
            raise FileNotFoundError(f"missing appendix source: {item.path}")
        payload = item.absolute.read_bytes()
        entries.append(
            {
                "path": item.path,
                "role": item.role,
                "produces": item.produces,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
                "lines": payload.decode("utf-8").count("\n"),
                "git_commit": git_commit_for(item.path),
            }
        )
    return entries


def render_appendix(entries: list[dict]) -> str:
    """Render the appendix text with one complete file after another."""
    parts: list[str] = []
    for index, entry in enumerate(entries, start=1):
        source = (ROOT / entry["path"]).read_text(encoding="utf-8")
        parts.append(
            "\n".join(
                [
                    f"--- リスト{index} {entry['path']} ---",
                    f"役割: {entry['role']}",
                    f"生成物: {entry['produces']}",
                    f"SHA-256: {entry['sha256']}",
                    f"commit: {entry['git_commit']}",
                    "---",
                    source.rstrip("\n"),
                    "",
                ]
            )
        )
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble the complete Python source appendix of the report"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("report-appendix/code-appendix.txt"),
        help="where to write the assembled source text",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("report-appendix/code-appendix-manifest.json"),
        help="where to write the machine-readable manifest",
    )
    args = parser.parse_args()

    entries = collect()
    text = render_appendix(entries)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    args.manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "files": entries,
                "total_bytes": len(text.encode("utf-8")),
                "total_lines": text.count("\n"),
                "file_count": len(entries),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"files      : {len(entries)}")
    print(f"lines      : {text.count(chr(10))}")
    print(f"bytes      : {len(text.encode('utf-8')):,}")
    for entry in entries:
        print(f"  {entry['path']:<42} {entry['lines']:>4} lines  {entry['sha256'][:12]}")
    print(f"Saved: {args.output}")
    print(f"Saved: {args.manifest}")


if __name__ == "__main__":
    main()
