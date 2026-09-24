"""Validate benchmark answer JSON files against the dataset contract."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from agent.investigation.validator import build_dataset_index, validate_answer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("answers", type=Path, default=Path("cases"), nargs="?")
    parser.add_argument("--data-dir", type=Path, default=Path("DataSet"))
    parser.add_argument("--mapping", type=Path, default=Path("artifacts/transaction_cards.csv"))
    args = parser.parse_args()
    index = build_dataset_index(args.data_dir, args.mapping)
    try:
        current_sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path.cwd(),
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        current_sha = ""
    files = sorted(args.answers.glob("*.json"))
    failures = 0
    for path in files:
        answer = json.loads(path.read_text(encoding="utf-8"))
        errors = validate_answer(answer, index)
        generation_meta = answer.get("generation_meta", {})
        if not isinstance(generation_meta, dict):
            errors.append("generation_meta: expected object")
        elif not generation_meta.get("code_version"):
            errors.append("generation_meta.code_version: required; regenerate this artifact")
        elif current_sha and generation_meta["code_version"] != current_sha:
            errors.append(
                f"generation_meta.code_version: artifact has {generation_meta['code_version']}, "
                f"current checkout is {current_sha}; regenerate this artifact"
            )
        if errors:
            failures += 1
            print(f"{path}:\n  " + "\n  ".join(errors))
    print(f"validated {len(files)} answer file(s); failures={failures}")
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()