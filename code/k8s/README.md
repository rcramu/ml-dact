# Local EKS (kind) for the reference stack

This folder deploys the same services as Docker Compose onto a local Kubernetes
cluster that uses EKS-shaped objects (Deployments, Services, Jobs, PVCs, Secrets).
It is **not** Amazon EKS. It is the local cluster path named in the manuscript
(kind / k3d).

## Prerequisites

- Docker Desktop (or another local Docker engine)
- `kubectl`
- `openssl`, `curl`, `python3`

`kind` is installed automatically by the deploy script if it is missing.

## Bring up, run, collect metrics

```bash
cd code
chmod +x k8s/deploy-local-eks.sh k8s/collect-metrics.sh
./k8s/deploy-local-eks.sh
```

The script:

1. Writes synthetic CSVs into `data/` (check-in copy).
2. Creates kind cluster `dact-local-eks` with host ports 3066 / 8166 / 5026 / 8766 / 5476.
3. Creates a namespace `dact` and a gitignored Secret (`k8s/.local-secret.env`).
4. Builds `dact-backend:local` and `dact-frontend:local`, loads them into kind.
5. Applies postgres, MLflow, backend, frontend, and Airflow.
6. Waits until the backend seed pipeline has finished (`GET /ready`).
7. Writes `k8s/metrics/eks-run.json` and `k8s/metrics/eks-run.md`.

URLs after a successful deploy:

| Service | URL |
| --- | --- |
| Frontend | http://127.0.0.1:3066 |
| Backend / OpenAPI | http://127.0.0.1:8166/docs |
| MLflow | http://127.0.0.1:5026 |
| Airflow | http://127.0.0.1:8766 |
| PostgreSQL | 127.0.0.1:5476 |

Airflow admin username is `admin`. The password is in `k8s/.local-secret.env` (not committed).

Re-snapshot metrics without redeploying:

```bash
./k8s/collect-metrics.sh
```

Tear down:

```bash
kind delete cluster --name dact-local-eks
# if kind was installed by the script:
# ./k8s/.kind-$(uname -s | tr A-Z a-z)-arm64 delete cluster --name dact-local-eks
```
