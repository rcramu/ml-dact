# ML DACT

Reference implementation, synthetic check-in corpus, and kind-run snapshots for the paper *Quality-Gated Continuous Training under Drift: An Observational Case Study of an Inspectable MLOps Architecture*.

```bash
git clone https://github.com/rcramu/ml-dact.git
cd ml-dact
```

Then see [`code/README.md`](code/README.md) to run the stack (Docker Compose or a local kind cluster, `dact-local-eks`).

- Stack: FastAPI, PyTorch, MLflow, Airflow, PostgreSQL.
- No personal data. Every `customer_id` is generated.
- Reviewable copy at the repo root: [`data/`](data/) (corpus CSVs plus kind-run snapshots).
- The same files also live under [`code/data/`](code/data/) and [`code/k8s/metrics/`](code/k8s/metrics/).
- Live pipeline runs still synthesize a batch at trigger time.

Local secrets (`code/.env`, `code/k8s/.local-secret.env`) and the optional kind binary (`code/k8s/.kind-*`) are not committed. `deploy-local-eks.sh` writes a fresh secret file if it is missing.

License: MIT.
