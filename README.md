# ML DACT

Reference implementation, synthetic check-in corpus, and kind-run snapshots for the paper *A Closed-Loop MLOps Architecture for Drift-Aware, Quality-Gated Continuous Training*.

- Stack: FastAPI, PyTorch, MLflow, Airflow, PostgreSQL. Run with Docker Compose or a local kind cluster (`dact-local-eks`). See [`code/README.md`](code/README.md).
- No personal data. Every `customer_id` is generated.
- Frozen scenario CSVs plus public Electricity / IBM Telco copies: [`code/data/`](code/data/).
- Live pipeline runs still synthesize a batch at trigger time; these files are the reviewable copy.
- Kind-run snapshots: [`code/k8s/metrics/`](code/k8s/metrics/).

Local secrets (`code/.env`, `code/k8s/.local-secret.env`) and the optional kind binary (`code/k8s/.kind-*`) are not committed. `deploy-local-eks.sh` writes a fresh secret file if it is missing.

License: MIT.
