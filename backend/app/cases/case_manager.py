"""
Case manager — persists cases to SQLite and manages lifecycle.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from uuid import uuid4
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from ..config import get_settings
from ..models.case import CaseAnswer, CaseStatus, InvestigationState, Verdict

logger = logging.getLogger(__name__)
settings = get_settings()
OUTPUT_DIR = Path(__file__).resolve().parents[3] / "output"


def _db_path() -> str:
    url = settings.database_url
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///"):]
    return "fraud_cases.db"


@contextmanager
def _conn():
    db = _db_path()
    Path(db).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _init_db() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                status TEXT,
                verdict TEXT,
                fraud_probability REAL,
                pattern TEXT,
                exposure_usd REAL,
                opened_at TEXT,
                closed_at TEXT,
                answer_json TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT,
                step INTEGER,
                action TEXT,
                status TEXT,
                ts TEXT,
                data_json TEXT
            );
            CREATE TABLE IF NOT EXISTS evidence_requests (
                request_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                requested_from TEXT,
                reason TEXT,
                status TEXT NOT NULL,
                response_json TEXT,
                created_at TEXT NOT NULL,
                received_at TEXT
            );
            CREATE TABLE IF NOT EXISTS investigation_checkpoints (
                case_id TEXT PRIMARY KEY,
                phase TEXT NOT NULL,
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)


class CaseManager:
    def __init__(self) -> None:
        _init_db()

    @staticmethod
    def _output_document(answer: CaseAnswer) -> dict[str, Any]:
        """Build the concise, human-readable investigation report artifact."""
        return {
            "case_id": answer.case_id,
            "case": answer.case.model_dump(mode="json"),
            "evidence_requests": [
                {
                    "type": request.type.value,
                    "asked_after_step": request.asked_after_step,
                    "assumed_response": request.assumed_response,
                }
                for request in answer.evidence_requests
            ],
            "next_best_actions": answer.next_best_actions.model_dump(mode="json"),
            "sar": answer.sar.model_dump(mode="json"),
            "stop_reason": answer.stop_reason,
            "tool_calls": answer.tool_calls,
            "tokens": answer.tokens,
            "latency_s": answer.latency_s,
            "subgraph": answer.subgraph.model_dump(mode="json"),
        }

    def write_answer_file(self, answer: CaseAnswer) -> Path:
        """Persist a concise investigation report as an atomic JSON artifact."""
        case_id = answer.case_id
        if not case_id or Path(case_id).name != case_id:
            raise ValueError("case_id must be a simple filename")

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        destination = OUTPUT_DIR / f"{case_id}.json"
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(self._output_document(answer), indent=2), encoding="utf-8"
        )
        os.replace(temporary, destination)
        return destination

    def save_answer(self, answer: CaseAnswer) -> None:
        with _conn() as con:
            con.execute(
                """
                INSERT OR REPLACE INTO cases
                  (case_id, status, verdict, fraud_probability, pattern,
                   exposure_usd, opened_at, closed_at, answer_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    answer.case_id,
                    answer.case.status.value,
                    answer.case.verdict.value,
                    answer.case.fraud_probability,
                    answer.case.pattern.value,
                    answer.case.exposure_usd,
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    answer.model_dump_json(),
                ),
            )
            for request in answer.evidence_requests:
                con.execute(
                    "INSERT OR IGNORE INTO evidence_requests "
                    "(request_id, case_id, evidence_type, requested_from, reason, status, response_json, created_at, received_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (request.request_id, answer.case_id, request.type.value,
                     request.requested_from, request.reason, request.status,
                     json.dumps(request.response), request.created_at.isoformat(),
                     request.received_at.isoformat() if request.received_at else None),
                )
        self.write_answer_file(answer)

    def get_answer(self, case_id: str) -> Optional[CaseAnswer]:
        with _conn() as con:
            row = con.execute(
                "SELECT answer_json FROM cases WHERE case_id = ?", (case_id,)
            ).fetchone()
        if row:
            return CaseAnswer.model_validate_json(row[0])
        return None

    def list_cases(self, limit: int = 100) -> list[dict]:
        with _conn() as con:
            rows = con.execute(
                "SELECT case_id, status, verdict, fraud_probability, pattern, "
                "exposure_usd, created_at FROM cases ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_answers(self, limit: int = 100) -> list[CaseAnswer]:
        with _conn() as con:
            rows = con.execute(
                "SELECT answer_json FROM cases ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [CaseAnswer.model_validate_json(row[0]) for row in rows if row[0]]

    def log_audit(self, case_id: str, entries: list[dict]) -> None:
        with _conn() as con:
            for e in entries:
                con.execute(
                    "INSERT INTO audit_log (case_id, step, action, status, ts, data_json) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        case_id,
                        e.get("step", 0),
                        e.get("action", ""),
                        e.get("status", ""),
                        e.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        json.dumps({k: v for k, v in e.items()
                                    if k not in ("step", "action", "status", "timestamp")}),
                    ),
                )

    def get_audit(self, case_id: str) -> list[dict[str, Any]]:
        with _conn() as con:
            rows = con.execute(
                "SELECT step, action, status, ts, data_json FROM audit_log "
                "WHERE case_id = ? ORDER BY id",
                (case_id,),
            ).fetchall()
        entries = []
        for row in rows:
            entry = {
                "step": row["step"],
                "action": row["action"],
                "status": row["status"],
                "timestamp": row["ts"],
            }
            if row["data_json"]:
                entry.update(json.loads(row["data_json"]))
            entries.append(entry)
        return entries

    def update_answer(self, answer: CaseAnswer) -> None:
        self.save_answer(answer)

    def save_checkpoint(self, state: InvestigationState, phase: str) -> None:
        """Persist a resumable typed state after each orchestration phase."""
        with _conn() as con:
            con.execute(
                "INSERT OR REPLACE INTO investigation_checkpoints "
                "(case_id, phase, state_json, updated_at) VALUES (?, ?, ?, ?)",
                (
                    state.case_id,
                    phase,
                    state.model_dump_json(),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def get_checkpoint(self, case_id: str) -> tuple[str, InvestigationState] | None:
        with _conn() as con:
            row = con.execute(
                "SELECT phase, state_json FROM investigation_checkpoints "
                "WHERE case_id = ?",
                (case_id,),
            ).fetchone()
        if not row:
            return None
        return row["phase"], InvestigationState.model_validate_json(row["state_json"])

    def clear_checkpoint(self, case_id: str) -> None:
        with _conn() as con:
            con.execute(
                "DELETE FROM investigation_checkpoints WHERE case_id = ?",
                (case_id,),
            )

    def create_evidence_request(self, case_id: str, request: dict[str, Any]) -> dict[str, Any]:
        request_id = request.get("request_id") or str(uuid4())
        created_at = request.get("created_at") or datetime.now(timezone.utc).isoformat()
        record = {
            "request_id": request_id,
            "case_id": case_id,
            "evidence_type": request.get("type", "analyst_info"),
            "requested_from": request.get("requested_from", "external_provider"),
            "reason": request.get("reason", "Additional evidence required."),
            "status": "pending",
            "response": {},
            "created_at": str(created_at),
            "received_at": None,
        }
        with _conn() as con:
            con.execute(
                "INSERT OR IGNORE INTO evidence_requests "
                "(request_id, case_id, evidence_type, requested_from, reason, status, response_json, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (request_id, case_id, record["evidence_type"], record["requested_from"],
                 record["reason"], "pending", "{}", record["created_at"]),
            )
        return self.get_evidence_request(request_id) or record

    def get_evidence_request(self, request_id: str) -> Optional[dict[str, Any]]:
        with _conn() as con:
            row = con.execute(
                "SELECT * FROM evidence_requests WHERE request_id = ?", (request_id,)
            ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["response"] = json.loads(item.pop("response_json") or "{}")
        return item

    def fulfill_evidence_request(
        self, request_id: str, response: dict[str, Any], received_at: str
    ) -> dict[str, Any]:
        with _conn() as con:
            cursor = con.execute(
                "UPDATE evidence_requests SET status = 'fulfilled', response_json = ?, received_at = ? "
                "WHERE request_id = ? AND status = 'pending'",
                (json.dumps(response), received_at, request_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Evidence request is missing or already fulfilled")
        return self.get_evidence_request(request_id) or {}
