#!/usr/bin/env bash
# Bring up the reference stack on a local kind cluster (EKS-shaped Kubernetes).
# Does not print secret values. Local-only demo credentials live in k8s/.local-secret.env (gitignored).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
K8S="$ROOT/k8s"
CLUSTER="${CLUSTER:-dact-local-eks}"
NS=dact
KIND_BIN="${KIND_BIN:-}"

log() { printf '%s\n' "$*"; }

install_kind() {
  if command -v kind >/dev/null 2>&1; then
    KIND_BIN="$(command -v kind)"
    return
  fi
  local arch os dest
  os="$(uname -s | tr '[:upper:]' '[:lower:]')"
  case "$(uname -m)" in
    arm64|aarch64) arch="arm64" ;;
    x86_64|amd64) arch="amd64" ;;
    *) log "Unsupported architecture: $(uname -m)"; exit 1 ;;
  esac
  dest="$K8S/.kind-${os}-${arch}"
  if [[ ! -x "$dest" ]]; then
    log "Installing kind to $dest"
    curl -fsSL -o "$dest" "https://kind.sigs.k8s.io/dl/v0.29.0/kind-${os}-${arch}"
    chmod +x "$dest"
  fi
  KIND_BIN="$dest"
}

ensure_secret() {
  local secret_file="$K8S/.local-secret.env"
  if [[ ! -f "$secret_file" ]]; then
    local pg_pass af_pass af_key
    pg_pass="$(openssl rand -hex 12)"
    af_pass="$(openssl rand -hex 12)"
    af_key="$(openssl rand -hex 16)"
    umask 077
    cat >"$secret_file" <<EOF
POSTGRES_USER=dact_user
POSTGRES_PASSWORD=${pg_pass}
POSTGRES_DB=dact_training
DATABASE_URL=postgresql+psycopg2://dact_user:${pg_pass}@postgres:5432/dact_training
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://dact_user:${pg_pass}@postgres:5432/airflow
AIRFLOW__WEBSERVER__SECRET_KEY=${af_key}
AIRFLOW_ADMIN_PASSWORD=${af_pass}
EOF
    log "Wrote local secret file (gitignored): $secret_file"
  fi
  # shellcheck disable=SC1090
  set -a
  source "$secret_file"
  set +a
  kubectl -n "$NS" create secret generic dact-secrets \
    --from-env-file="$secret_file" \
    --dry-run=client -o yaml | kubectl apply -f -
}

export_data() {
  log "Exporting synthetic datasets to code/data/"
  docker run --rm \
    -v "$ROOT:/work" \
    -w /work \
    python:3.11-slim \
    bash -c "pip install -q numpy && python scripts/export_data.py"
}

build_images() {
  log "Building backend and frontend images"
  mkdir -p "$ROOT/backend/data"
  cp "$ROOT/data/electricity.csv" "$ROOT/backend/data/electricity.csv"
  docker build -t dact-backend:local "$ROOT/backend"
  docker build -t dact-frontend:local "$ROOT/frontend"
}

load_images() {
  log "Loading images into kind"
  "$KIND_BIN" load docker-image dact-backend:local --name "$CLUSTER"
  "$KIND_BIN" load docker-image dact-frontend:local --name "$CLUSTER"
}

wait_http() {
  local url="$1" tries="${2:-90}"
  local i
  for i in $(seq 1 "$tries"); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      log "Ready: $url"
      return 0
    fi
    sleep 5
  done
  log "Timed out waiting for $url"
  return 1
}

main() {
  command -v docker >/dev/null || { log "docker is required"; exit 1; }
  command -v kubectl >/dev/null || { log "kubectl is required"; exit 1; }
  command -v openssl >/dev/null || { log "openssl is required"; exit 1; }
  install_kind
  export_data

  if ! "$KIND_BIN" get clusters | grep -qx "$CLUSTER"; then
    log "Creating kind cluster $CLUSTER"
    "$KIND_BIN" create cluster --config "$K8S/kind-config.yaml"
  else
    log "Kind cluster $CLUSTER already exists"
  fi
  kubectl cluster-info --context "kind-$CLUSTER" >/dev/null

  kubectl apply -f "$K8S/namespace.yaml"
  ensure_secret
  kubectl -n "$NS" create configmap airflow-dags \
    --from-file=retraining_dag.py="$ROOT/airflow/dags/retraining_dag.py" \
    --from-file=joint_retrain_dag.py="$ROOT/airflow/dags/joint_retrain_dag.py" \
    --from-file=electricity_joint_dag.py="$ROOT/airflow/dags/electricity_joint_dag.py" \
    --dry-run=client -o yaml | kubectl apply -f -

  build_images
  load_images

  kubectl apply -f "$K8S/postgres.yaml"
  kubectl apply -f "$K8S/mlflow.yaml"
  log "Waiting for postgres and MLflow"
  kubectl -n "$NS" rollout status deployment/postgres --timeout=180s
  kubectl -n "$NS" rollout status deployment/mlflow --timeout=180s

  kubectl apply -f "$K8S/backend.yaml"
  kubectl apply -f "$K8S/frontend.yaml"
  kubectl apply -f "$K8S/airflow.yaml"

  log "Waiting for backend seed (PyTorch training; can take several minutes)"
  kubectl -n "$NS" rollout status deployment/backend --timeout=2400s
  kubectl -n "$NS" rollout status deployment/frontend --timeout=180s
  kubectl -n "$NS" wait --for=condition=complete job/airflow-init --timeout=300s || log "Airflow init still running; webserver may start after migrate"
  kubectl -n "$NS" rollout status deployment/airflow-webserver --timeout=300s || true

  wait_http "http://127.0.0.1:8166/health" 60
  wait_http "http://127.0.0.1:8166/ready" 120
  wait_http "http://127.0.0.1:3066/" 30 || true

  bash "$K8S/collect-metrics.sh"
  log ""
  log "Local EKS stack is up:"
  log "  UI        http://127.0.0.1:3066"
  log "  API       http://127.0.0.1:8166/docs"
  log "  MLflow    http://127.0.0.1:5026"
  log "  Airflow   http://127.0.0.1:8766  (admin / password in k8s/.local-secret.env)"
  log "  Metrics   $K8S/metrics/eks-run.json"
}

main "$@"
