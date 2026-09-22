"""Validate benchmark answer JSON files against the dataset contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent.investigation.validator import build_dataset_index, validate_answer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("answers", type=Path, default=Path("cases"), nargs="?")
    parser.add_argument("--data-dir", type=Path, default=Path("DataSet"))
    parser.add_argument("--mapping", type=Path, default=Path("artifacts/transaction_cards.csv"))
    args = parser.parse_args()
    index = build_dataset_index(args.data_dir, args.mapping)
    files = sorted(args.answers.glob("*.json"))
    failures = 0
    for path in files:
        errors = validate_answer(json.loads(path.read_text(encoding="utf-8")), index)
        if errors:
            failures += 1
            print(f"{path}:\n  " + "\n  ".join(errors))
    print(f"validated {len(files)} answer file(s); failures={failures}")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()