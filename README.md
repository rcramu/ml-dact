# ML DACT

Synthetic check-in corpus and kind-run snapshots for the paper *A Closed-Loop MLOps Architecture for Drift-Aware, Quality-Gated Continuous Training*.

- No personal data. Every `customer_id` is generated.
- Frozen scenario CSVs: [`code/dat/`](code/dat/) (`manifest.json` records seeds and row counts).
- Live pipeline runs still synthesize a batch at trigger time; these files are the reviewable copy.
- Five-seed metrics: [`code/k8s/metrics/replicates.json`](code/k8s/metrics/replicates.json)
- First-seed snapshot: [`code/k8s/metrics/eks-run.json`](code/k8s/metrics/eks-run.json)

License: MIT.
