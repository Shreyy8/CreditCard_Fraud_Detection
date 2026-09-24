"""
Batch investigation runner.

Usage:
    python run_investigations.py              # All 20 cases
    python run_investigations.py HHG-001      # Single case
    python run_investigations.py --all        # All 20 cases (explicit)

Outputs:
    cases/<case_id>.json   — one answer file per case
    cases/batch_summary.json — aggregate results
"""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

OUTPUT_DIR = Path(__file__).parent.parent / "cases"


def _generation_meta() -> dict[str, str]:
    try:
        code_version = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=OUTPUT_DIR.parent,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        code_version = "unknown"
    return {
        "code_version": code_version,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


async def investigate_all(case_ids: list[str] | None = None) -> dict:
    from app.agents.fraud_agent import FraudAgent
    from app.cases.case_manager import CaseManager
    from app.data_layer import get_data_layer

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dl = get_data_layer()

    if case_ids:
        rows = [dl.get_case_pack_row(cid) for cid in case_ids if dl.get_case_pack_row(cid)]
    else:
        rows = dl.get_all_case_pack_rows()

    if not rows:
        logger.error("No cases found in case_pack")
        return {"error": "no cases"}

    logger.info("Investigating %d case(s)...", len(rows))
    agent = FraudAgent()
    mgr = CaseManager()

    summary = {
        "total": len(rows),
        "completed": 0,
        "failed": 0,
        "results": {},
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    for row in rows:
        case_id = row.get("case_id", "UNKNOWN")
        logger.info("Investigating %s ...", case_id)
        t0 = time.monotonic()
        try:
            answer = await agent.investigate(row)
            # Save to DB
            mgr.save_answer(answer)
            # Write answer file
            out_path = OUTPUT_DIR / f"{case_id}.json"
            document = answer.model_dump(mode="json")
            document["generation_meta"] = _generation_meta()
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(document, f, indent=2)
            elapsed = round(time.monotonic() - t0, 2)
            summary["results"][case_id] = {
                "status": answer.case.status.value,
                "verdict": answer.case.verdict.value,
                "fraud_probability": answer.case.fraud_probability,
                "pattern": answer.case.pattern.value,
                "exposure_usd": answer.case.exposure_usd,
                "sar_filed": answer.sar.file,
                "latency_s": elapsed,
                "tool_calls": answer.tool_calls,
                "tokens": answer.tokens,
            }
            summary["completed"] += 1
            logger.info(
                "  %s → %s (p=%.2f, pattern=%s, $%.2f, %.1fs)",
                case_id,
                answer.case.verdict.value,
                answer.case.fraud_probability,
                answer.case.pattern.value,
                answer.case.exposure_usd,
                elapsed,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("  FAILED %s: %s", case_id, exc)
            summary["failed"] += 1
            summary["results"][case_id] = {"error": str(exc)}

    summary["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # Write batch summary
    with open(OUTPUT_DIR / "batch_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(
        "Done: %d/%d succeeded, %d failed. Output in %s/",
        summary["completed"],
        summary["total"],
        summary["failed"],
        OUTPUT_DIR,
    )
    return summary


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] not in ("--all",):
        case_ids = args
    else:
        case_ids = None

    result = asyncio.run(investigate_all(case_ids))
    if result.get("failed", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
