import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.domain.models import (
    AgentRun,
    ApprovalChoice,
    ApprovalDecision,
    RunEvent,
    RunStatus,
    utc_now,
)
from app.domain.state_machine import transition_run


class ApprovalConflict(ValueError):
    """Raised when a caller tries to replace an existing human decision."""


class SQLiteStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = Path(database_path)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    task_type TEXT NOT NULL,
                    input_summary TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                    sequence INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(run_id, sequence),
                    UNIQUE(run_id, idempotency_key)
                );

                CREATE TABLE IF NOT EXISTS approvals (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
                    approval_id TEXT NOT NULL,
                    choice TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(run_id, approval_id)
                );
                """
            )

    def create_run(
        self,
        task_type: str,
        input_summary: str,
        *,
        run_id: str | None = None,
    ) -> AgentRun:
        run = AgentRun(
            id=run_id or str(uuid4()),
            task_type=task_type,
            input_summary=input_summary,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO runs (id, task_type, input_summary, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.task_type,
                    run.input_summary,
                    run.status.value,
                    run.created_at.isoformat(),
                    run.updated_at.isoformat(),
                ),
            )
        return run

    def get_run(self, run_id: str) -> AgentRun | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            return None
        return self._run_from_row(row)

    def transition_run(
        self,
        run_id: str,
        target: RunStatus,
        *,
        approval_recorded: bool = False,
    ) -> AgentRun:
        current = self.get_run(run_id)
        if current is None:
            raise KeyError(run_id)
        next_status = transition_run(
            current.status,
            target,
            approval_recorded=approval_recorded,
        )
        updated_at = utc_now()
        with self._connect() as connection:
            connection.execute(
                "UPDATE runs SET status = ?, updated_at = ? WHERE id = ?",
                (next_status.value, updated_at.isoformat(), run_id),
            )
        return current.model_copy(update={"status": next_status, "updated_at": updated_at})

    def append_event(
        self,
        run_id: str,
        *,
        kind: str,
        summary: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> RunEvent:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM events WHERE run_id = ? AND idempotency_key = ?",
                (run_id, idempotency_key),
            ).fetchone()
            if existing is not None:
                return self._event_from_row(existing)

            next_sequence = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 FROM events WHERE run_id = ?",
                (run_id,),
            ).fetchone()[0]
            event = RunEvent(
                id=str(uuid4()),
                run_id=run_id,
                sequence=next_sequence,
                kind=kind,
                summary=summary,
                payload=payload,
                idempotency_key=idempotency_key,
            )
            connection.execute(
                """
                INSERT INTO events
                    (id, run_id, sequence, kind, summary, payload, idempotency_key, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.run_id,
                    event.sequence,
                    event.kind,
                    event.summary,
                    json.dumps(event.payload, sort_keys=True),
                    event.idempotency_key,
                    event.created_at.isoformat(),
                ),
            )
            return event

    def list_events(self, run_id: str) -> list[RunEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY sequence",
                (run_id,),
            ).fetchall()
        return [self._event_from_row(row) for row in rows]

    def record_approval(
        self,
        run_id: str,
        *,
        approval_id: str,
        choice: ApprovalChoice,
    ) -> ApprovalDecision:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT * FROM approvals WHERE run_id = ? AND approval_id = ?",
                (run_id, approval_id),
            ).fetchone()
            if existing is not None:
                recorded = self._approval_from_row(existing)
                if recorded.choice is not choice:
                    raise ApprovalConflict(
                        f"approval {approval_id} is already recorded as {recorded.choice.value}"
                    )
                return recorded

            decision = ApprovalDecision(
                id=str(uuid4()),
                run_id=run_id,
                approval_id=approval_id,
                choice=choice,
            )
            connection.execute(
                """
                INSERT INTO approvals (id, run_id, approval_id, choice, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    decision.id,
                    decision.run_id,
                    decision.approval_id,
                    decision.choice.value,
                    decision.created_at.isoformat(),
                ),
            )
            return decision

    def has_approval(self, run_id: str, approval_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT choice FROM approvals WHERE run_id = ? AND approval_id = ?",
                (run_id, approval_id),
            ).fetchone()
        return row is not None and ApprovalChoice(row["choice"]) is ApprovalChoice.APPROVED

    @staticmethod
    def _run_from_row(row: sqlite3.Row) -> AgentRun:
        return AgentRun(
            id=row["id"],
            task_type=row["task_type"],
            input_summary=row["input_summary"],
            status=RunStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    @staticmethod
    def _event_from_row(row: sqlite3.Row) -> RunEvent:
        return RunEvent(
            id=row["id"],
            run_id=row["run_id"],
            sequence=row["sequence"],
            kind=row["kind"],
            summary=row["summary"],
            payload=json.loads(row["payload"]),
            idempotency_key=row["idempotency_key"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _approval_from_row(row: sqlite3.Row) -> ApprovalDecision:
        return ApprovalDecision(
            id=row["id"],
            run_id=row["run_id"],
            approval_id=row["approval_id"],
            choice=ApprovalChoice(row["choice"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
