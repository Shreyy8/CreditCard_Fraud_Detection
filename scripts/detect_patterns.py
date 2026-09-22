"""Run deterministic local pattern detectors for all case profiles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agent.detection import detect_cases


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=Path, default=Path("artifacts/case_profiles.json"))
    parser.add_argument("--shared-entities", type=Path, default=Path("artifacts/shared_entities.json"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/pattern_matches.json"))
    args = parser.parse_args()

    profiles = json.loads(args.profiles.read_text(encoding="utf-8"))
    shared_entities = json.loads(args.shared_entities.read_text(encoding="utf-8"))
    results = detect_cases(profiles, shared_entities)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps({result["case_id"]: result["matched_patterns"] for result in results}, indent=2))
    print(f"wrote {len(results)} pattern results to {args.output}")


if __name__ == "__main__":
    main()