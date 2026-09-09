#!/usr/bin/env bash
# Snapshot live API metrics from the local EKS NodePorts into k8s/metrics/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/k8s/metrics"
API="${API_URL:-http://127.0.0.1:8166}"
MODEL="${MODEL_NAME:-churn-predictor}"
mkdir -p "$OUT"

stamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

fetch() {
  local name="$1" path="$2"
  if curl -fsS "$API$path" -o "$tmp/$name.json"; then
    return 0
  fi
  echo "{\"error\":\"fetch failed\",\"path\":\"$path\"}" >"$tmp/$name.json"
}

fetch ready /ready
fetch summary /data/summary
fetch models /api/v1/models
fetch versions "/api/v1/models/${MODEL}/versions?limit=100"
fetch training "/api/v1/models/${MODEL}/training/history?limit=50"
fetch drift "/api/v1/models/${MODEL}/drift"
fetch drift_history "/api/v1/models/${MODEL}/drift/history"
fetch deployment "/api/v1/models/${MODEL}/deployment"
fetch sla /pipeline/sla
fetch alerts /alerts
fetch seed_scenarios /data/seed-scenarios

python3 - "$tmp" "$OUT/eks-run.json" "$stamp" "$API" "$MODEL" <<'PY'
import json, pathlib, sys
src, dest, stamp, api, model = sys.argv[1:6]
blob = {"captured_at": stamp, "api": api, "model": model, "runtime": "kind-local-eks"}
for p in pathlib.Path(src).glob("*.json"):
    blob[p.stem] = json.loads(p.read_text())
pathlib.Path(dest).write_text(json.dumps(blob, indent=2) + "\n")
print("Wrote", dest)
PY

# Human-readable summary for the paper update
python3 - "$OUT/eks-run.json" "$OUT/eks-run.md" <<'PY'
import json, pathlib, sys
data = json.loads(pathlib.Path(sys.argv[1]).read_text())
md = []
md.append("# Local EKS (kind) run snapshot\n")
md.append(f"- Captured: `{data.get('captured_at')}`")
md.append(f"- API: `{data.get('api')}`")
md.append(f"- Model: `{data.get('model')}`")
md.append(f"- Runtime: `{data.get('runtime')}`\n")
ready = data.get("ready") or {}
if isinstance(ready, dict) and "detail" in ready:
    ready = ready["detail"]
md.append("## Readiness\n")
md.append("```json")
md.append(json.dumps(ready, indent=2))
md.append("```\n")
md.append("## Data summary\n")
md.append("```json")
md.append(json.dumps(data.get("summary"), indent=2))
md.append("```\n")
md.append("## Models\n")
md.append("```json")
md.append(json.dumps(data.get("models"), indent=2))
md.append("```\n")
versions = data.get("versions") or []
md.append(f"## Versions ({len(versions)} rows)\n")
if isinstance(versions, list):
    md.append("| Version | Stage | Champion | F1 | Precision | Recall | ROC-AUC |")
    md.append("| --- | --- | --- | --- | --- | --- | --- |")
    for v in versions:
        md.append(
            f"| {v.get('version')} | {v.get('stage')} | {v.get('is_champion')} | "
            f"{v.get('test_f1')} | {v.get('precision')} | {v.get('recall')} | {v.get('roc_auc')} |"
        )
runs = data.get("training") or []
md.append(f"\n## Training runs ({len(runs) if isinstance(runs, list) else 'n/a'})\n")
if isinstance(runs, list):
    md.append("| ID | Trigger | Status | Outcome | Scenario |")
    md.append("| --- | --- | --- | --- | --- |")
    for r in runs:
        md.append(
            f"| `{str(r.get('id', ''))[:8]}` | {r.get('trigger_type')} | {r.get('status')} | "
            f"{r.get('outcome')} | {r.get('scenario') or r.get('trigger_detail', '')} |"
        )
md.append("\n## SLA\n")
md.append("```json")
md.append(json.dumps(data.get("sla"), indent=2))
md.append("```\n")
md.append("## Drift (current)\n")
md.append("```json")
md.append(json.dumps(data.get("drift"), indent=2))
md.append("```\n")
pathlib.Path(sys.argv[2]).write_text("\n".join(md) + "\n")
print("Wrote", sys.argv[2])
PY
