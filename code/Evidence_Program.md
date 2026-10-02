# Quality-Gated Model Evolution in MLOps — Resubmission Evidence Program

**Document type:** Experimental validation plan
**Project:** Quality-Gated Model Evolution in MLOps: An Empirical Study of an Inspectable Decision Procedure for Distribution Shift
**Target:** journal resubmission
**Version:** 1.1 — updated 2026-10-02 (EXP-03, EXP-06 complete; see Section 17)
**Status:** In execution — 2 of 7 experiments complete, 5 remaining (see Section 17 for the live log)
**Repository:** `rcramu/ml-dact` (this evidence program lives on branch `evidence-program` of fork `rchencha-cs/ml-dact`, baseline commit `df2ad38`)
**Rule:** No fabricated results. Results enter the paper only after executable experiments produce them.

---

## 1. Objective

Close the remaining evidence gaps identified during the five-pass hostile review while preserving the manuscript's current claim boundaries.

The objective is **not** to make the paper longer. The objective is to produce evidence that addresses the specific reviewer attacks that cannot be resolved by prose.

---

# 2. Priority Backlog

| ID | Experiment / Evidence | Priority | Type | Current Status |
|---|---|---:|---|---|
| EXP-01 | Independent post-selection holdout | P0 | Methodological validity | Not run |
| EXP-02 | Matched policy baselines | P0 | Comparative evaluation | Not run |
| EXP-03 | Threshold provenance audit | P0 | Reproducibility | **Complete** — `evidence/exp03_threshold_provenance.md` |
| EXP-04 | Structured Electricity replication | P1 | External/transferability | Partial |
| EXP-05 | Reproducibility artifact audit | P1 | Artifact quality | Partial |
| EXP-06 | Policy-state transition test suite | P1 | Software-engineering validation | **Complete** — `evidence/exp06_policy_tests.json` (26/26 passing) |
| EXP-07 | Decision-lineage replay test | P1 | Auditability | Design ready |

---

# 3. EXP-01 — Independent Post-Selection Holdout

## Attack addressed

The controller-facing test data participate in candidate promotion. Therefore the reported evaluation can be affected by model-selection exposure.

## Objective

Create a final holdout that is completely invisible to:

- threshold selection
- candidate selection
- promotion decisions
- policy tuning
- exploratory analysis

## Protocol

```text
Training data
      ↓
Candidate generation
      ↓
Controller-facing evaluation
      ↓
MEDP decision
      ↓
Freeze policy decision
      ↓
Independent final holdout
```

## Required outputs

For every promoted/rejected candidate where applicable:

- controller-facing F1
- controller-facing precision
- controller-facing recall
- controller-facing accuracy
- final-holdout F1
- final-holdout precision
- final-holdout recall
- final-holdout accuracy
- difference between controller-facing and holdout metrics

## Acceptance criteria

- Holdout never reaches the controller.
- Holdout never influences thresholds.
- Holdout is evaluated only after policy decisions are frozen.
- Code/configuration proves separation.

## Paper impact

If successful, strengthen the predictive-validity discussion.

If not feasible, retain the limitation and do not claim unbiased post-selection performance.

---

# 4. EXP-02 — Matched Policy Baselines

## Attack addressed

The paper currently cannot establish that MEDP is superior to alternative retraining policies.

## Policies

Run exactly the same workload/model/training budget under:

1. **Drift-only**
2. **Periodic retraining**
3. **Performance-triggered retraining**
4. **MEDP**

Optional fifth policy:

5. **Manual/static champion baseline**

## Controlled variables

Keep identical:

- dataset
- data ordering
- workload
- model family
- candidate generator
- training budget
- evaluation windows
- deployment latency assumptions
- rollback mechanism
- compute budget
- observation period

Only the decision policy changes.

## Metrics

### Quality

- F1
- precision
- recall
- accuracy

### Evolution behavior

- retraining count
- promotion count
- rejection count
- rollback count
- time to recovery
- time between model changes

### Efficiency

- training compute
- training duration
- token/compute cost where applicable
- unnecessary retraining count

## Required statistical treatment

Use matched runs with identical seeds/workload conditions where possible.

Report:

- per-run values
- mean
- standard deviation
- paired differences
- effect sizes where appropriate

Do not rely only on aggregate averages.

## Acceptance criteria

A superiority claim is allowed only if the matched experiment supports it.

Otherwise report the experiment as comparative characterization.

---

# 5. EXP-03 — Threshold Provenance Audit

**Status: COMPLETE** — `code/evidence/exp03_threshold_provenance.md` + `.json`, commit `808dd9f`.
All 6 thresholds traced to exact file:line. The `req.md` document cited in code
comments as rationale could not be located anywhere in the repository, so those
citations are recorded but flagged unverifiable. No pre-existing git history
exists before this program's baseline (`df2ad38`), so provenance is disclosed
as "engineering configuration," not a pre-registered trail, per Section 5's own
fallback rule below.

## Attack addressed

Reviewers may ask whether thresholds were selected before observing the results.

## Required table

| Parameter | Actual value | Source/rationale | Fixed before primary run? | Evidence |
|---|---:|---|---|---|
| PSI warning | TBD | TBD | TBD | commit/config |
| PSI significant | TBD | TBD | TBD | commit/config |
| F1 floor | TBD | TBD | TBD | commit/config |
| Precision floor | TBD | TBD | TBD | commit/config |
| Recall floor | TBD | TBD | TBD | commit/config |
| Regression budget | TBD | TBD | TBD | commit/config |

## Rules

Never infer provenance from memory.

Use:

- git history
- configuration files
- experiment manifests
- dated run metadata
- issue/PR records
- research notes

If provenance cannot be established, label the threshold as an engineering configuration and disclose the limitation.

---

# 6. EXP-04 — Structured Electricity Replication

## Objective

Test whether the MEDP state relationships appear outside the primary workload.

## Required protocol

Document:

1. Dataset/version
2. Chronological split
3. Drift definition
4. Incumbent definition
5. Candidate generation
6. Quality gate
7. Thresholds
8. Replicate count
9. Deviations from primary protocol

## Required outputs

- drift evidence
- incumbent quality
- candidate quality
- policy action
- state transition
- promotion/rejection result

## Interpretation

This is a **transferability evaluation**, not evidence of population-wide generalization.

---

# 7. EXP-05 — Reproducibility Artifact Audit

## Objective

Make every reported result executable and traceable.

## Required metadata

Every experiment should record:

```text
experiment_id
git_commit
dataset_version
model_version
policy_version
threshold_config_version
random_seed
replicate_id
environment
timestamp
evaluation_window
result_artifact
```

## Acceptance criteria

Every paper table/figure can be traced to:

```text
paper result
   ↓
experiment ID
   ↓
script/config
   ↓
code commit
   ↓
raw result artifact
```

If a result cannot be traced, remove it from the final quantitative claims.

---

# 8. EXP-06 — MEDP Policy-State Test Suite

**Status: COMPLETE** — `code/evidence/exp06_policy_tests.json`, commit `808dd9f`.
The Section 8.4 joint-cell decision matrix (previously duplicated across
`routers/joint.py`, `ml/electricity.py`, and `scripts/run_electricity_natural.py`)
was extracted into one module, `backend/app/ml/policy.py`, verified
behavior-preserving (byte-identical decisions for every fold against the
pre-refactor stored output). 26/26 tests pass in `backend/tests/test_policy.py`,
covering the table below plus boundary/epsilon, missing-metric, stale-champion,
duplicate/repeated-candidate, and rollback-after-promotion cases against the
real production functions. One finding surfaced (not hidden): the
`SIGNIFICANT`+`UNKNOWN` cell is labeled "Obtain ground truth" but the code
actually fires retraining there — a label/behavior mismatch in production.

## Objective

Demonstrate that the decision policy itself is testable software.

## Required policy tests

| State | Expected action |
|---|---|
| Stable distribution + healthy incumbent | RETAIN |
| Drift + healthy incumbent | EVALUATE |
| Drift + degraded incumbent | RETRAIN |
| Candidate below quality floor | REJECT |
| Candidate violates recall constraint | REJECT |
| Candidate passes all constraints | PROMOTE |
| Failed promoted candidate | ROLLBACK |

## Additional tests

- boundary threshold
- threshold ± epsilon
- missing metric
- stale champion
- duplicate candidate
- repeated candidate
- rollback after promotion

## Paper impact

Strengthens the claim:

> Model-evolution policy logic can be independently tested as decision software.

---

# 9. EXP-07 — Decision-Lineage Replay

## Objective

Prove that a historical model-evolution decision can be reconstructed from its persisted evidence.

## Required record

```text
trigger
distribution evidence
champion ID
candidate ID
candidate metrics
policy version
threshold configuration
gate decisions
final action
rollback status
timestamp
```

## Replay test

Given only the persisted decision record and the corresponding policy version:

```text
record
  ↓
replay policy
  ↓
expected action
  ==
recorded action
```

## Acceptance criterion

Replay must reproduce the original decision.

## Paper impact

Strengthens the auditability and reproducibility contribution.

---

# 10. Claim-Evidence Matrix

Do not change the paper's claims until the evidence is available.

| Claim | Current evidence | Additional evidence |
|---|---|---|
| Drift can be detected under the configured protocol | Available | None for bounded claim |
| Drift is not equivalent to degradation | Available | Secondary replication strengthens |
| Retraining is associated with improved quality in evaluated scenario | Available | Causal experiment only for causal claim |
| Multi-metric gating changes decisions | Available | None required for counterexample claim |
| Incumbent state affects decisions | Available | More repetitions strengthen |
| Thresholds influence decisions | Available | Provenance audit — **done, EXP-03** |
| MEDP is auditable | Partially available | Replay experiment strengthens |
| MEDP is independently testable | Design established | Policy test suite — **done, EXP-06** |
| MEDP outperforms drift-only | Not established | EXP-02 |
| MEDP outperforms periodic retraining | Not established | EXP-02 |
| MEDP outperforms performance-triggered retraining | Not established | EXP-02 |
| Post-selection performance is unbiased | Not established | EXP-01 |
| Results generalize broadly | Not established | EXP-04 + more workloads |
| MEDP is universally optimal | Not claimed | Do not claim |

---

# 11. Execution Order

Recommended sequence:

```text
EXP-03 Threshold provenance
        ↓
EXP-06 Policy-state tests
        ↓
EXP-07 Decision-lineage replay
        ↓
EXP-01 Independent holdout
        ↓
EXP-02 Matched policy baselines
        ↓
EXP-04 Electricity replication
        ↓
EXP-05 Artifact audit
        ↓
Update manuscript
        ↓
Final Pass 5 review
```

---

# 12. Manuscript Update Rules

After experiments complete:

### If an experiment succeeds

Update:

- Methods
- Results
- tables/figures
- RQ answers
- Discussion
- Threats to validity
- Conclusion

### If an experiment produces mixed results

Report the mixed result.

Do not optimize the narrative around only favorable outcomes.

### If an experiment fails

Report the failure if scientifically relevant and preserve the limitation.

Never replace a failed experiment with an assumed result.

---

# 13. Final Submission Gate

Before submission, all of the following should be answered:

- [ ] Can every quantitative claim be reproduced?
- [ ] Are all thresholds traceable?
- [ ] Is the final holdout independent?
- [ ] Are competing policies matched?
- [ ] Are primary and exploratory analyses clearly separated?
- [ ] Is incumbent state explicitly represented?
- [ ] Is decision lineage replayable?
- [ ] Is policy logic independently testable?
- [ ] Are causal claims avoided unless causality was experimentally established?
- [ ] Are broad generalization claims avoided?
- [ ] Does every major contribution have direct evidence?

**Submission recommendation:** only proceed after the evidence matrix is updated from actual experiment outputs.

---

## Non-Negotiable Research Rule

> **No fabricated results. No retroactive threshold provenance. No converting exploratory runs into confirmatory evidence. No superiority claims without matched baselines.**

The manuscript may be polished aggressively, but numerical evidence must always come from the executable research code and retained artifacts.


---

# 14. Pass 6 Pre-Submission Gate — Added

The manuscript has now been hardened for final pre-submission review. The following are **not prose defects** and remain evidence-dependent:

## P6-01 — Experimental claim verification

Before replacing any `TBD` or provisional statement with a numerical result:

- execute the corresponding experiment;
- retain raw output;
- record code commit and configuration;
- update the claim-evidence matrix;
- update the manuscript only from the observed output.

## P6-02 — Figure/table provenance

Every final numerical table or figure must have:

```text
paper table/figure
    ↓
experiment ID
    ↓
code/config version
    ↓
raw result
```

If this chain is missing, do not use the result as primary evidence.

## P6-03 — RQ traceability

After experiments complete, verify:

```text
RQ
 ↓
hypothesis/proposition
 ↓
experiment
 ↓
raw output
 ↓
statistical/empirical analysis
 ↓
result
 ↓
discussion
 ↓
conclusion
```

No RQ should have a conclusion stronger than its experiment.

## P6-04 — Final reviewer attack

After EXP-01 through EXP-07 are executed where applicable, run one final hostile review specifically asking:

1. What claim would a skeptical reviewer say is unsupported?
2. Which result could be explained by an alternative mechanism?
3. Which threshold could be accused of retrospective tuning?
4. Which comparison is missing?
5. Which conclusion exceeds the evidence?
6. Which implementation detail is being incorrectly presented as research novelty?

The manuscript should be changed only where the evidence supports the change.

## P6-05 — No-result policy

If an experiment produces:

- null result,
- contradictory result,
- unexpected result,
- failed replication,
- unstable result,

report it according to its scientific relevance. Do not rerun selectively until a favorable result appears without a predefined rationale.



---

# 15. Pass 7 — Editorial Consistency Gate

The following fixable issues were addressed directly in V26:

- Removed duplicated wording such as "controlled ... controlled empirical evaluation".
- Replaced remaining manuscript uses of "case-study" terminology with evaluation terminology where it referred to the present study.
- Replaced ambiguous "held-out F1/metrics" language with "test-split F1/metrics" where the metric is consumed by the promotion controller.
- Preserved "independent holdout" only for the future EXP-01 methodology.
- Corrected future-work numbering/order without changing the underlying research proposals.
- Added an explicit editorial consistency gate covering evidence hierarchy and research-object framing.

No numerical results were changed in this pass.

## Still evidence-dependent

No new result was invented. As of v1.1 (Section 17), EXP-03 and EXP-06 are
complete; the remaining open items are:

- EXP-01 independent post-selection holdout
- EXP-02 matched policy baselines
- EXP-04 structured Electricity replication
- EXP-05 reproducibility artifact audit
- EXP-07 decision-lineage replay


---

# 16. Pass 8 — Methods/Results Traceability Gate

## Fixes completed in V27

- Added a **Reproducibility Contract** to methodology.
- Explicitly defined the **unit of analysis** as a model-evolution decision cycle under a specified policy state.
- Clarified that primary replicates characterize protocol stability rather than population effects.
- Added an explicit **evidence hierarchy** separating primary, ablation/sensitivity, and secondary transferability analyses.
- Added a final conclusion boundary preventing unsupported production-scale, universal-superiority, or unbiased-post-selection claims.
- Reduced potential novelty overstatement where infrastructure/architecture wording could be interpreted as the research contribution.

## Evidence-dependent items remain unchanged

No results were fabricated or inferred. As of v1.1, EXP-03 and EXP-06 have been
executed from the research code with verified artifacts (Section 17); EXP-01,
EXP-02, EXP-04, EXP-05, and EXP-07 remain open.

---

# 17. Execution Log — Evidence Program v1.1

Tracks actual progress against Sections 2–9. Updated only from real command
output and committed artifacts, never from memory, per this document's
non-negotiable research rule.

| Step | Status | Commit | Evidence |
|---|---|---|---|
| Step 0 — git init + baseline | Done | `df2ad38` | First version control this project has had; anchors all provenance from here forward |
| EXP-03 — threshold provenance audit | **Done** | `808dd9f` | `code/evidence/exp03_threshold_provenance.md`, `.json` |
| EXP-06 — policy-state test suite | **Done** | `808dd9f`, `8a70e1d` | `code/evidence/exp06_policy_tests.json`; 26/26 tests passing in `backend/tests/test_policy.py` |
| EXP-07 — decision-lineage replay | Not started | — | Needs `policy_version`/`threshold_config_version` columns + a live Postgres to generate replayable runs |
| EXP-01 — independent holdout | Not started | — | Needs a new seeded split never wired into ingestion |
| EXP-02 — matched policy baselines | Not started | — | Needs drift-only/periodic/performance-triggered policy variants alongside MEDP |
| EXP-04 — structured Electricity replication | Not started | — | Will extend `scripts/run_electricity_natural.py` to call the real `policy.py`/`gates.py` |
| EXP-05 — reproducibility artifact audit | Not started | — | Will stamp every `evidence/*.json` with the full provenance block once the other experiments exist to audit |

**Where this lives:** the working repository is `code/` in this project directory
(its own local git history, commits above). A snapshot of this work was also
pushed to branch `evidence-program` on `rchencha-cs/ml-dact` (a fork of the
paper's repository `rcramu/ml-dact`) for review; no PR has been opened yet.
