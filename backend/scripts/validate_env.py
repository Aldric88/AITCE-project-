import os
import re
import sys
from pathlib import Path


def _read_env_example_keys(path: Path) -> set[str]:
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        if re.match(r"^[A-Z0-9_]+$", key):
            keys.add(key)
    return keys


def main():
    root = Path(__file__).resolve().parents[1]
    env_example = root / ".env.example"
    if not env_example.exists():
        print("Missing backend/.env.example")
        return 1

    required = _read_env_example_keys(env_example)
    allow_missing = {
        "EMAIL_HOST",
        "EMAIL_PORT",
        "EMAIL_USER",
        "EMAIL_PASS",
        "EMAIL_FROM",
        "RAZORPAY_WEBHOOK_SECRET",
        "OLLAMA_URL",
        "OLLAMA_MODEL",
    }

    missing = sorted(
        key for key in required if key not in os.environ and key not in allow_missing
    )
    if missing:
        print("Missing required env keys:")
        for key in missing:
            print(f"- {key}")
        return 1

    print("Environment validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
