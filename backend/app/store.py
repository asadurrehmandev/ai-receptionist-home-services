"""SQLite persistence for calls, bookings, leads, and webhook events."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

from app.agent.calendar import SlotTaken, _digits, _name_matches
from app.agent.engine import SessionState, summarize
from app.metrics import summarize as summarize_latency


SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
    id TEXT PRIMARY KEY,
    external_id TEXT,
    channel TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    caller_name TEXT,
    caller_phone TEXT,
    caller_address TEXT,
    issue TEXT,
    intent TEXT,
    outcome TEXT,
    phase TEXT,
    summary TEXT,
    state_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id TEXT NOT NULL,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    latency_ms REAL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bookings (
    id TEXT PRIMARY KEY,
    call_id TEXT,
    name TEXT,
    phone TEXT,
    address TEXT,
    issue TEXT,
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS leads (
    id TEXT PRIMARY KEY,
    call_id TEXT,
    name TEXT,
    phone TEXT,
    address TEXT,
    issue TEXT,
    intent TEXT,
    status TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    call_id TEXT,
    type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS verification_locks (
    booking_id TEXT PRIMARY KEY,
    phone TEXT,
    failures INTEGER NOT NULL DEFAULT 0,
    locked_until TEXT,
    updated_at TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._guard_slots()

    def close(self) -> None:
        self.conn.close()

    def _guard_slots(self) -> None:
        self.conn.execute("BEGIN IMMEDIATE")
        self.conn.execute(
            """
            UPDATE bookings SET status='cancelled'
            WHERE status='booked' AND rowid NOT IN (
                SELECT MIN(rowid) FROM bookings WHERE status='booked' GROUP BY start_at
            )
            """
        )
        self.conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS bookings_active_start ON bookings(start_at) WHERE status='booked'"
        )
        self.conn.execute("COMMIT")

    def purge_before(self, cutoff: datetime) -> int:
        """Delete calls, turns, leads, and events older than the retention cutoff."""
        stamp = cutoff.isoformat()
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            rows = self.conn.execute("SELECT id FROM calls WHERE started_at < ?", (stamp,)).fetchall()
            ids = [row["id"] for row in rows]
            for call_id in ids:
                self.conn.execute("DELETE FROM turns WHERE call_id=?", (call_id,))
                self.conn.execute("DELETE FROM events WHERE call_id=?", (call_id,))
                self.conn.execute("DELETE FROM leads WHERE call_id=?", (call_id,))
                self.conn.execute("DELETE FROM calls WHERE id=?", (call_id,))
            self.conn.execute(
                "DELETE FROM bookings WHERE status!='booked' AND start_at < ?",
                (stamp,),
            )
            self.conn.execute("COMMIT")
        return len(ids)

    def wipe(self) -> None:
        with self._lock:
            for table in ("events", "leads", "turns", "bookings", "verification_locks", "calls"):
                self.conn.execute(f"DELETE FROM {table}")
            self.conn.commit()

    def delete_call(self, call_id: str) -> None:
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            self.conn.execute("DELETE FROM turns WHERE call_id=?", (call_id,))
            self.conn.execute("DELETE FROM events WHERE call_id=?", (call_id,))
            self.conn.execute("DELETE FROM leads WHERE call_id=?", (call_id,))
            self.conn.execute("DELETE FROM calls WHERE id=?", (call_id,))
            self.conn.execute("COMMIT")

    def count_calls(self) -> int:
        with self._lock:
            return int(self.conn.execute("SELECT COUNT(*) AS n FROM calls").fetchone()["n"])

    def create_call(self, call_id: str, channel: str, external_id: str | None, started_at: datetime, state: SessionState) -> None:
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO calls (
                    id, external_id, channel, started_at, caller_name, caller_phone,
                    caller_address, issue, intent, outcome, phase, summary, state_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    call_id,
                    external_id,
                    channel,
                    started_at.isoformat(),
                    state.name,
                    state.phone,
                    state.address,
                    state.issue,
                    state.intent,
                    state.outcome,
                    state.phase,
                    summarize(state),
                    json.dumps(state.to_dict()),
                ),
            )
            self.conn.commit()

    def save_state(self, call_id: str, state: SessionState, ended: bool, ended_at: datetime | None) -> None:
        with self._lock:
            self.conn.execute(
                """
                UPDATE calls
                SET caller_name=?, caller_phone=?, caller_address=?, issue=?, intent=?,
                    outcome=?, phase=?, summary=?, state_json=?, ended_at=?
                WHERE id=?
                """,
                (
                    state.name,
                    state.phone,
                    state.address,
                    state.issue,
                    state.intent,
                    state.outcome,
                    state.phase,
                    summarize(state),
                    json.dumps(state.to_dict()),
                    ended_at.isoformat() if ended and ended_at else None,
                    call_id,
                ),
            )
            self.conn.commit()

    def load_state(self, call_id: str) -> SessionState:
        with self._lock:
            row = self.conn.execute("SELECT state_json FROM calls WHERE id=?", (call_id,)).fetchone()
        if row is None:
            raise KeyError(call_id)
        return SessionState.from_dict(json.loads(row["state_json"]))

    def add_turn(self, call_id: str, role: str, text: str, latency_ms: float | None, created_at: datetime) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT INTO turns (call_id, role, text, latency_ms, created_at) VALUES (?, ?, ?, ?, ?)",
                (call_id, role, text, latency_ms, created_at.isoformat()),
            )
            self.conn.commit()

    def add_event(self, call_id: str, event_type: str, payload: dict, status: str | None, created_at: datetime) -> None:
        with self._lock:
            self.conn.execute(
                "INSERT INTO events (call_id, type, payload_json, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (call_id, event_type, json.dumps(payload), status, created_at.isoformat()),
            )
            self.conn.commit()

    def upsert_lead(self, payload: dict, created_at: datetime) -> None:
        with self._lock:
            self.conn.execute(
                """
                INSERT INTO leads (id, call_id, name, phone, address, issue, intent, status, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status=excluded.status,
                    payload_json=excluded.payload_json
                """,
                (
                    payload.get("id"),
                    payload.get("call_id"),
                    payload.get("name"),
                    payload.get("phone"),
                    payload.get("address"),
                    payload.get("issue"),
                    payload.get("intent"),
                    payload.get("status"),
                    json.dumps(payload),
                    created_at.isoformat(),
                ),
            )
            self.conn.commit()

    def insert_booking(self, draft: dict) -> dict:
        record = {
            "id": draft["id"],
            "call_id": draft.get("call_id"),
            "name": draft.get("name"),
            "phone": draft.get("phone"),
            "address": draft.get("address"),
            "issue": draft.get("issue"),
            "start": draft["start"],
            "end": draft["end"],
            "status": "booked",
        }
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                if record["call_id"]:
                    prior = self.conn.execute(
                        "SELECT * FROM bookings WHERE call_id=? AND status='booked'",
                        (record["call_id"],),
                    ).fetchone()
                    if prior is not None:
                        self.conn.execute("COMMIT")
                        return _booking_dict(prior)
                conflict = self.conn.execute(
                    """
                    SELECT id FROM bookings
                    WHERE status='booked' AND start_at < ? AND end_at > ?
                    """,
                    (record["end"], record["start"]),
                ).fetchone()
                if conflict is not None:
                    self.conn.execute("ROLLBACK")
                    raise SlotTaken(record["start"])
                self.conn.execute(
                    """
                    INSERT INTO bookings (id, call_id, name, phone, address, issue, start_at, end_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["id"],
                        record["call_id"],
                        record["name"],
                        record["phone"],
                        record["address"],
                        record["issue"],
                        record["start"],
                        record["end"],
                        record["status"],
                    ),
                )
                self.conn.execute("COMMIT")
            except sqlite3.IntegrityError as exc:
                self.conn.execute("ROLLBACK")
                raise SlotTaken(record["start"]) from exc
        return record

    def cancel_booking(self, booking_id: str) -> dict:
        with self._lock:
            self.conn.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (booking_id,))
            self.conn.commit()
            row = self.conn.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
        if row is None:
            raise KeyError(booking_id)
        return _booking_dict(row)

    def reschedule_booking(self, booking_id: str, start: datetime, end: datetime) -> dict:
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            conflict = self.conn.execute(
                """
                SELECT id FROM bookings
                WHERE status='booked' AND id!=? AND start_at < ? AND end_at > ?
                """,
                (booking_id, end.isoformat(), start.isoformat()),
            ).fetchone()
            if conflict is not None:
                self.conn.execute("ROLLBACK")
                raise SlotTaken(start.isoformat())
            self.conn.execute(
                "UPDATE bookings SET start_at=?, end_at=?, status='booked' WHERE id=?",
                (start.isoformat(), end.isoformat(), booking_id),
            )
            self.conn.execute("COMMIT")
            row = self.conn.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
        if row is None:
            raise KeyError(booking_id)
        return _booking_dict(row)

    def busy_spans(self) -> list[tuple[datetime, datetime]]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT start_at, end_at FROM bookings WHERE status='booked'"
            ).fetchall()
        return [(datetime.fromisoformat(row["start_at"]), datetime.fromisoformat(row["end_at"])) for row in rows]

    def find_booking(self, name: str | None, phone: str | None) -> dict | None:
        with self._lock:
            rows = self.conn.execute("SELECT * FROM bookings WHERE status='booked'").fetchall()
        records = [_booking_dict(row) for row in rows]
        if phone:
            target = _digits(phone)[-10:]
            for record in records:
                if _digits(record.get("phone"))[-10:] == target and target:
                    return record
        if name:
            matches = [record for record in records if _name_matches(record.get("name") or "", name)]
            if len(matches) == 1:
                return matches[0]
        return None

    def match_visit(self, last4: str, day: str) -> list[dict]:
        with self._lock:
            rows = self.conn.execute("SELECT * FROM bookings WHERE status='booked'").fetchall()
        found = []
        for row in rows:
            record = _booking_dict(row)
            phone = _digits(record.get("phone"))
            if len(phone) < 4 or phone[-4:] != str(last4):
                continue
            if datetime.fromisoformat(record["start"]).date().isoformat() != day:
                continue
            found.append(record)
        return found

    def bookings_with_last4(self, last4: str) -> list[dict]:
        with self._lock:
            rows = self.conn.execute("SELECT * FROM bookings WHERE status='booked'").fetchall()
        found = []
        for row in rows:
            record = _booking_dict(row)
            phone = _digits(record.get("phone"))
            if len(phone) >= 4 and phone[-4:] == str(last4):
                found.append(record)
        return found

    def verify_status(self, booking_id: str, now: datetime) -> dict:
        with self._lock:
            row = self.conn.execute(
                "SELECT failures, locked_until FROM verification_locks WHERE booking_id=?",
                (booking_id,),
            ).fetchone()
        failures = 0 if row is None else int(row["failures"])
        locked = None if row is None or not row["locked_until"] else datetime.fromisoformat(row["locked_until"])
        active = bool(locked and now < locked)
        return {
            "failures": failures,
            "locked_until": locked,
            "hard_lock": active and failures >= 3,
            "delayed": active and failures == 2,
        }

    def record_verify_failure(self, booking_id: str, phone: str, now: datetime) -> dict:
        with self._lock:
            row = self.conn.execute(
                "SELECT failures FROM verification_locks WHERE booking_id=?",
                (booking_id,),
            ).fetchone()
            failures = (0 if row is None else int(row["failures"])) + 1
            locked_until = None
            if failures == 2:
                locked_until = (now + timedelta(minutes=10)).isoformat()
            elif failures >= 3:
                locked_until = (now + timedelta(hours=24)).isoformat()
            self.conn.execute(
                """
                INSERT INTO verification_locks (booking_id, phone, failures, locked_until, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(booking_id) DO UPDATE SET
                    phone=excluded.phone,
                    failures=excluded.failures,
                    locked_until=excluded.locked_until,
                    updated_at=excluded.updated_at
                """,
                (booking_id, phone, failures, locked_until, now.isoformat()),
            )
            self.conn.commit()
        return {"failures": failures, "alert": failures >= 3, "phone": phone}

    def get_call_by_external(self, external_id: str) -> str | None:
        with self._lock:
            row = self.conn.execute(
                "SELECT id FROM calls WHERE external_id=? ORDER BY started_at DESC LIMIT 1",
                (external_id,),
            ).fetchone()
        return None if row is None else row["id"]

    def list_calls(self) -> list[dict]:
        with self._lock:
            rows = self.conn.execute("SELECT * FROM calls ORDER BY started_at DESC").fetchall()
            latency_rows = self.conn.execute(
                """
                SELECT call_id, AVG(latency_ms) AS avg_ms, MAX(latency_ms) AS max_ms, COUNT(latency_ms) AS n
                FROM turns WHERE latency_ms IS NOT NULL GROUP BY call_id
                """
            ).fetchall()
        latency = {row["call_id"]: row for row in latency_rows}
        calls = []
        for row in rows:
            stats = latency.get(row["id"])
            calls.append(
                {
                    "id": row["id"],
                    "external_id": row["external_id"],
                    "channel": row["channel"],
                    "started_at": row["started_at"],
                    "ended_at": row["ended_at"],
                    "caller_name": row["caller_name"],
                    "caller_phone": row["caller_phone"],
                    "caller_address": row["caller_address"],
                    "issue": row["issue"],
                    "intent": row["intent"],
                    "outcome": row["outcome"],
                    "phase": row["phase"],
                    "summary": row["summary"],
                    "avg_latency_ms": None if stats is None or stats["avg_ms"] is None else round(stats["avg_ms"], 2),
                    "max_latency_ms": None if stats is None or stats["max_ms"] is None else round(stats["max_ms"], 2),
                    "timed_turns": 0 if stats is None else stats["n"],
                }
            )
        return calls

    def get_call(self, call_id: str) -> dict | None:
        calls = [call for call in self.list_calls() if call["id"] == call_id]
        if not calls:
            return None
        with self._lock:
            turns = self.conn.execute(
                "SELECT role, text, latency_ms, created_at FROM turns WHERE call_id=? ORDER BY id",
                (call_id,),
            ).fetchall()
            events = self.conn.execute(
                "SELECT type, payload_json, status, created_at FROM events WHERE call_id=? ORDER BY id",
                (call_id,),
            ).fetchall()
        call = calls[0]
        call["turns"] = [
            {
                "role": row["role"],
                "text": row["text"],
                "latency_ms": row["latency_ms"],
                "created_at": row["created_at"],
            }
            for row in turns
        ]
        call["events"] = [
            {
                "type": row["type"],
                "payload": json.loads(row["payload_json"]),
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in events
        ]
        return call

    def list_bookings(self) -> list[dict]:
        with self._lock:
            rows = self.conn.execute("SELECT * FROM bookings ORDER BY start_at").fetchall()
        return [_booking_dict(row) for row in rows]

    def list_leads(self) -> list[dict]:
        with self._lock:
            rows = self.conn.execute("SELECT * FROM leads ORDER BY created_at DESC").fetchall()
        leads = []
        for row in rows:
            leads.append(
                {
                    "id": row["id"],
                    "call_id": row["call_id"],
                    "name": row["name"],
                    "phone": row["phone"],
                    "address": row["address"],
                    "issue": row["issue"],
                    "intent": row["intent"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "payload": json.loads(row["payload_json"]),
                }
            )
        missed = [item for item in leads if item["status"] == "missed_transfer"]
        rest = [item for item in leads if item["status"] != "missed_transfer"]
        return missed + rest

    def list_events(self, event_type: str | None = None) -> list[dict]:
        with self._lock:
            if event_type:
                rows = self.conn.execute(
                    "SELECT * FROM events WHERE type=? ORDER BY id DESC",
                    (event_type,),
                ).fetchall()
            else:
                rows = self.conn.execute("SELECT * FROM events ORDER BY id DESC").fetchall()
        return [
            {
                "id": row["id"],
                "call_id": row["call_id"],
                "type": row["type"],
                "status": row["status"],
                "created_at": row["created_at"],
                "payload": json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    def latency_values(self) -> list[float]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT latency_ms FROM turns WHERE latency_ms IS NOT NULL"
            ).fetchall()
        return [float(row["latency_ms"]) for row in rows]

    def outcome_counts(self) -> dict[str, int]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT COALESCE(outcome, 'open') AS outcome, COUNT(*) AS n FROM calls GROUP BY outcome"
            ).fetchall()
        return {row["outcome"]: row["n"] for row in rows}

    def metrics(self) -> dict:
        values = self.latency_values()
        summary = summarize_latency(values)
        summary["outcomes"] = self.outcome_counts()
        return summary


def _booking_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "call_id": row["call_id"],
        "name": row["name"],
        "phone": row["phone"],
        "address": row["address"],
        "issue": row["issue"],
        "start": row["start_at"],
        "end": row["end_at"],
        "status": row["status"],
    }


class StoreCalendar:
    def __init__(self, store: Store) -> None:
        self.store = store

    def busy(self):
        return self.store.busy_spans()

    def find(self, name, phone):
        return self.store.find_booking(name, phone)

    def match_visit(self, last4, day):
        return self.store.match_visit(last4, day)

    def bookings_with_last4(self, last4):
        return self.store.bookings_with_last4(last4)

    def verify_status(self, booking_id, now):
        return self.store.verify_status(booking_id, now)

    def record_verify_failure(self, booking_id, phone, now):
        return self.store.record_verify_failure(booking_id, phone, now)

    def book(self, draft):
        return self.store.insert_booking(draft)

    def cancel(self, booking_id):
        return self.store.cancel_booking(booking_id)

    def reschedule(self, booking_id, start, end):
        return self.store.reschedule_booking(booking_id, start, end)
