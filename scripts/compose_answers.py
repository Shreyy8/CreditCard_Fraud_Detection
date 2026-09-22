"""Compose deterministic local draft answers for the benchmark cases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent.investigation.composer import compose_answer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=Path, default=Path("artifacts/case_profiles.json"))
    parser.add_argument("--patterns", type=Path, default=Path("artifacts/pattern_matches.json"))
    parser.add_argument("--output", type=Path, default=Path("cases"))
    args = parser.parse_args()

    profiles = json.loads(args.profiles.read_text(encoding="utf-8"))
    patterns = {
        result["case_id"]: result
        for result in json.loads(args.patterns.read_text(encoding="utf-8"))
    }
    args.output.mkdir(parents=True, exist_ok=True)
    for profile in profiles:
        answer = compose_answer(profile, patterns[profile["case_id"]])
        path = args.output / f"{profile['case_id']}.json"
        path.write_text(json.dumps(answer, indent=2), encoding="utf-8")
    print(f"wrote {len(profiles)} draft answers to {args.output}")


if __name__ == "__main__":
    main()