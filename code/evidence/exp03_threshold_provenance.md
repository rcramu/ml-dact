# EXP-03 — Threshold Provenance Audit

**Experiment ID:** `EXP-03`
**Git commit (baseline anchor):** `df2ad389fccb3fcc41d8c51b030d4f42202f55a2`
**Method:** every threshold below was located by reading the actual source files
listed in the Evidence column — none were taken from memory or from the manuscript.
No git history predates this project's `df2ad38` baseline commit (the project had no
version control before this audit), so "fixed before primary run" is assessed instead
from filesystem modification timestamps on the defining files vs. the earliest
result-artifact timestamps in `k8s/metrics/`. File mtimes are **not** cryptographic
proof and can be altered; they are reported as the best verifiable signal available,
and are explicitly flagged as weaker than git history.

## Table

| Parameter | Actual value | Source/rationale | Fixed before primary run? | Evidence |
|---|---:|---|---|---|
| PSI warning | 0.10 | Default arg of `drift_level()`; docstring cites "paper Section 8 threshold table: PSI < 0.10 Normal" | Yes (mtime-based signal only — see note) | `backend/app/ml/drift.py:36-37`; file mtime 2026-09-06 16:16, earliest result artifact `k8s/metrics/electricity-natural.json` mtime 2026-09-08 13:56 |
| PSI significant | 0.25 | Default arg of `drift_level()`; docstring cites "0.10-0.25 Warning, > 0.25 Significant" | Yes (mtime-based signal only — see note) | `backend/app/ml/drift.py:36,38-39`; same file/mtime evidence as above |
| F1 floor | 0.70 | `Settings.minimum_f1` default; also exposed as override `CTP_MINIMUM_F1` | Yes (mtime-based signal only — see note) | `backend/app/config.py:24-25` (comment: "req.md Sec. 16, 21-23"); `.env.example:3`; file mtimes 2026-09-06 16:16 / 14:51 |
| Precision floor | 0.60 | `Settings.minimum_precision` default | Yes (mtime-based signal only — see note) | `backend/app/config.py:27`; mtime 2026-09-06 16:16 |
| Recall floor | 0.60 | `Settings.minimum_recall` default | Yes (mtime-based signal only — see note) | `backend/app/config.py:26`; mtime 2026-09-06 16:16 |
| Regression budget | 10.0% | `Settings.max_regression_pct` default; also exposed as override `CTP_MAX_REGRESSION_PCT` | Yes (mtime-based signal only — see note) | `backend/app/config.py:28`; `.env.example:4`; mtimes 2026-09-06 16:16 / 14:51 |

## Rationale-citation caveat

`config.py` and `gates.py` comments attribute these values to a document named
`req.md` ("req.md Sec. 16, 21-23" etc.). That document is **not present anywhere in
this project directory** — it could not be located by search, so its contents cannot
be independently checked and its existence/dating cannot be verified from this audit.
The section-number citations are recorded as-is in the code but are **not** treated as
independent provenance evidence.

## Disclosed limitation (per PRD fallback rule)

Because there is no git history, issue tracker, or dated experiment manifest
predating this audit's baseline commit, these six values are labeled **engineering
configuration defaults** rather than thresholds with an auditable pre-registration
trail. The mtime evidence above is suggestive (every defining file is older than
every stored result artifact) but is not proof against retrospective tuning — mtimes
can be changed without altering content, and no cryptographic/commit-based timestamp
exists for anything before `df2ad38`. From this commit forward, any threshold change
is independently verifiable via `git log -p -- backend/app/config.py backend/app/ml/drift.py`.

## Acceptance criteria check

- [x] Rule followed: provenance not inferred from memory — every row cites a concrete file:line read during this audit.
- [x] Checked: git history (none exists pre-baseline — disclosed), configuration files (primary source used), experiment manifests (`data/manifest.json` contains no threshold values), dated run metadata (`k8s/metrics/*.json` mtimes used as secondary signal), issue/PR records (none exist), research notes (none found referencing these specific values).
- [x] Where provenance cannot be established with certainty, the threshold is labeled an engineering configuration and the limitation is disclosed above — not silently upgraded to "pre-registered."
