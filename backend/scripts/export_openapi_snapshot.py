import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app


def main():
    schema = app.openapi()
    out_path = os.path.join(os.path.dirname(__file__), "..", "openapi.snapshot.json")
    out_path = os.path.abspath(out_path)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=True, indent=2, sort_keys=True)
    print(f"Wrote OpenAPI snapshot to {out_path}")


if __name__ == "__main__":
    main()
