# AI coding agent instructions — FEC Election Analysis

This is a public repository for a Japanese graduate data-science assignment. Read [the assignment-aligned roadmap](docs/assignment-aligned-roadmap.md), [the live issue backlog](docs/issue-backlog.md), the user-assigned GitHub Issue, and existing files before making changes. Follow its **P0/P1/P2 priority**; do not expand the scope just to pursue model complexity.

## Every task

1. Work on a dedicated issue branch and create **one focused pull request per GitHub Issue**, normally. Do not merge into main without explicit user approval.
2. Before editing, inspect existing scripts, CI workflows, tests, and documentation so that completed work is not repeated or overwritten.
3. Implement exactly the stated acceptance criteria. Add or update Python tests (synthetic fixtures only for unit tests), reproduce with the actual official FEC data when numerical research claims are made, and write real results in a traceable research note.
4. In the PR description, include: purpose; exact files; results for all tested conditions (including failed or worsened ones); FEC source URL and checksum; train/test sizes and temporal boundaries; local/CI commands and status; documented limitations; dependencies left open. Never claim CI ran if it did not.
5. Avoid simultaneous changes to shared files when other Codex tasks run in parallel; wait for dependent Issue merges (e.g. #59 before #60, #61 before #62, #57 before #63).
6. If the required source or template is unavailable, report the blocker and do not substitute fabricated results.

## Research integrity

- Frozen 2016/2018/2020/2022 voting U.S. House **916 election records** (200, 241, 237, 238). Older 921/738/740 counts belong to historical normalization revisions. Maintain expected_analysis.json, original FEC Excel SHA-256 hashes, and original backtest metrics unless a separate explicitly reviewed migration justifies changing them.
- The predictor is Republican Primary share among Republican+Democratic Primary candidate votes, and the regression outcome is Republican General share among the two parties. The classification label is **two-party vote lead, NOT necessarily certified election winner**.
- Never use test year's General votes, winner labels, residuals, or state selections determined by General results as forecasting-time inputs or parameters. Clear retrospective diagnostics are allowed only when explicitly labelled.
- The FEC Excel workbooks are post-election publications. Reconstructing Primary vote columns retrospectively does **not** prove the same data was available before the General election. Issue #49 established raw 1,756 groups → retrospectively Primary-compatible 919 → ultimately selected 916. Neither 916-row performance nor 2022 exploratory tests are representative or confirmatory nationwide forecasts.
- Exclusions for unopposed candidates, write-ins, fusion parties, rank-choice/runoff election rules, and missing numeric votes are real selection restrictions. Never fill missing numbers with zero or merge vote subtotals into candidates.
- Provide the unit of every statistic, sample count, missing/excluded categories, and uncertainty limitation. Report negative findings. Do not infer political causal effects from vote ratios.

## Running research code

From repository root with Python 3.11:

    python -m pip install -r requirements.txt
    python -m pytest -q
    python scripts/download_fec.py --years 2016 2018 2020 2022
    python scripts/normalize_fec.py --years 2016 2018 2020 2022 --writein-policy attribute
    python scripts/run_backtests.py --input data/processed/elections.csv --test-years 2018 2020 2022
    python scripts/verify_reproducibility.py

Then run this Issue's script, dedicated pytest tests, and its dedicated GitHub Actions workflow. Download the official inputs with source checksums; keep large source/processed data under gitignored data/raw and data/processed. Do not add source Excel workbooks or per-district private outputs to Git. A synthetic test dataset is not evidence of a real-world numerical result.

## Assignment and confidentiality

- The original handout Rep1v1015.pdf (pp. 5, 7–10) values **multiple perspectives on Primary→General, differences by State and Year, regression/classification comparisons, validity, independent innovation, reliability, and evidence**, plus author attribution and reflection. A Senate/House comparison is an example, not a mandatory task. See Issues #56, #57, #67–#71.
- The assignment asks for a specified IEICE Word .docx, 2–4 body pages recommended (max 8, excluding appendix), Python source appendix, and a personal reflection; recommends a file at most 500KB, with a penalty over 1.5MB. Submission deadline stated as **November 3, 17:00**, and the submission portal must be confirmed.
- Keep the user's name, student number, unreleased report manuscript, private Word submission, and the assignment PDF itself **OUT of public GitHub**. Only checklists, code, aggregates, anonymized evidence registers and reproducibility instructions should be committed.
- Personal impressions, the user's actual use of AI, and submission status require the user's verification. Never invent those facts or claim Manaba submission is complete.

## Work order

Prioritize #56 requirements, #57 state/year study, #67 evidence and #68–#71 report delivery. #58–#64 improve the research; #65/#66 and the 2024 #53/#54 extension are **optional**, must not block the November 3 deadline.
