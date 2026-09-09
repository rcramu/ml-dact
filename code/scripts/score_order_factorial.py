"""Print the Table 14 summary from the 4! snapshot."""
import json
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "k8s" / "metrics" / "order-factorial.json"


def main() -> None:
    blob = json.loads(SRC.read_text())
    print("n_perm", blob["n_permutations"], "n_runs", blob["n_runs"])
    print(json.dumps(blob["summary"], indent=2))


if __name__ == "__main__":
    main()
