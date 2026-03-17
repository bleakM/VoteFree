from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json_loads(raw: str, fallback: Any) -> Any:
    try:
        return json.loads(raw)
    except Exception:
        return fallback


class VoteFreeDB:
    def __init__(self, db_file: Path):
        self.db_file = db_file

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _table_columns(self, conn: sqlite3.Connection, table: str) -> set[str]:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {row["name"] for row in rows}

    def _ensure_column(self, conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
        if column in self._table_columns(conn, table):
            return
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS questionnaires (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    identity_mode TEXT NOT NULL,
                    allow_repeat INTEGER NOT NULL DEFAULT 0,
                    passcode_hash TEXT,
                    auth_mode TEXT NOT NULL DEFAULT 'open',
                    auth_roster_id TEXT,
                    identity_fields_json TEXT NOT NULL DEFAULT '{}',
                    schema_json TEXT NOT NULL,
                    current_version INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS questionnaire_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    questionnaire_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    identity_mode TEXT NOT NULL,
                    allow_repeat INTEGER NOT NULL,
                    passcode_hash TEXT,
                    auth_mode TEXT NOT NULL DEFAULT 'open',
                    auth_roster_id TEXT,
                    identity_fields_json TEXT NOT NULL DEFAULT '{}',
                    schema_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(questionnaire_id, version)
                );

                CREATE TABLE IF NOT EXISTS submissions (
                    id TEXT PRIMARY KEY,
                    questionnaire_id TEXT NOT NULL,
                    questionnaire_version INTEGER NOT NULL DEFAULT 1,
                    roster_id TEXT,
                    verified_member_key TEXT,
                    submitted_at TEXT NOT NULL,
                    respondent_name TEXT,
                    respondent_code TEXT,
                    anonymous INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    vote_file TEXT NOT NULL,
                    client_token TEXT,
                    session_label TEXT,
                    target_label TEXT,
                    FOREIGN KEY(questionnaire_id) REFERENCES questionnaires(id)
                );

                CREATE TABLE IF NOT EXISTS rosters (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    columns_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS roster_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    roster_id TEXT NOT NULL,
                    member_key TEXT NOT NULL,
                    member_name TEXT,
                    member_code TEXT,
                    tags TEXT,
                    extra_json TEXT NOT NULL DEFAULT '{}',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(roster_id, member_key),
                    FOREIGN KEY(roster_id) REFERENCES rosters(id)
                );

                CREATE TABLE IF NOT EXISTS auth_sessions (
                    token TEXT PRIMARY KEY,
                    questionnaire_id TEXT NOT NULL,
                    roster_id TEXT,
                    member_key TEXT,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used INTEGER NOT NULL DEFAULT 0,
                    consumed_at TEXT
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    at TEXT NOT NULL,
                    action TEXT NOT NULL,
                    detail_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS sql_views (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    questionnaire_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    sql_text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(questionnaire_id, name),
                    FOREIGN KEY(questionnaire_id) REFERENCES questionnaires(id)
                );

                CREATE TABLE IF NOT EXISTS template_sql_views (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    template_key TEXT NOT NULL,
                    name TEXT NOT NULL,
                    sql_text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(template_key, name)
                );

                CREATE INDEX IF NOT EXISTS idx_questionnaires_status
                    ON questionnaires(status);
                CREATE INDEX IF NOT EXISTS idx_questionnaire_versions_qid
                    ON questionnaire_versions(questionnaire_id, version DESC);
                CREATE INDEX IF NOT EXISTS idx_submissions_questionnaire
                    ON submissions(questionnaire_id);
                CREATE INDEX IF NOT EXISTS idx_submissions_client_token
                    ON submissions(questionnaire_id, client_token);
                CREATE INDEX IF NOT EXISTS idx_submissions_respondent_code
                    ON submissions(questionnaire_id, respondent_code);
                CREATE INDEX IF NOT EXISTS idx_submissions_verified_member
                    ON submissions(questionnaire_id, verified_member_key);
                CREATE INDEX IF NOT EXISTS idx_roster_members_roster
                    ON roster_members(roster_id);
                CREATE INDEX IF NOT EXISTS idx_roster_members_code
                    ON roster_members(roster_id, member_code);
                CREATE INDEX IF NOT EXISTS idx_auth_sessions_qid
                    ON auth_sessions(questionnaire_id, member_key, used);
                CREATE INDEX IF NOT EXISTS idx_audit_logs_at
                    ON audit_logs(at DESC);
                CREATE INDEX IF NOT EXISTS idx_sql_views_qid
                    ON sql_views(questionnaire_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_template_sql_views_tkey
                    ON template_sql_views(template_key, updated_at DESC);
                """
            )

            # Compatible migration for legacy databases.
            self._ensure_column(conn, "questionnaires", "auth_mode", "auth_mode TEXT NOT NULL DEFAULT 'open'")
            self._ensure_column(conn, "questionnaires", "auth_roster_id", "auth_roster_id TEXT")
            self._ensure_column(
                conn,
                "questionnaires",
                "identity_fields_json",
                "identity_fields_json TEXT NOT NULL DEFAULT '{}'",
            )
            self._ensure_column(
                conn,
                "questionnaires",
                "current_version",
                "current_version INTEGER NOT NULL DEFAULT 1",
            )
            self._ensure_column(
                conn,
                "submissions",
                "questionnaire_version",
                "questionnaire_version INTEGER NOT NULL DEFAULT 1",
            )
            self._ensure_column(conn, "submissions", "roster_id", "roster_id TEXT")
            self._ensure_column(conn, "submissions", "verified_member_key", "verified_member_key TEXT")
            self._ensure_column(conn, "rosters", "columns_json", "columns_json TEXT NOT NULL DEFAULT '[]'")

    def get_setting(self, key: str) -> Optional[str]:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else None

    def set_setting(self, key: str, value: str) -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, now),
            )

    def append_audit_log(self, action: str, detail: Dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO audit_logs (at, action, detail_json) VALUES (?, ?, ?)",
                (utc_now(), action, json.dumps(detail, ensure_ascii=False)),
            )

    def list_audit_logs(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT id, at, action, detail_json FROM audit_logs ORDER BY at DESC LIMIT ?",
                (max(1, min(limit, 1000)),),
            ).fetchall()
            result: List[Dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                item["detail"] = _safe_json_loads(item.pop("detail_json"), {})
                result.append(item)
            return result

    def _insert_questionnaire_version(
        self,
        conn: sqlite3.Connection,
        questionnaire_id: str,
        version: int,
        title: str,
        description: str,
        identity_mode: str,
        allow_repeat: bool,
        passcode_hash: str,
        auth_mode: str,
        auth_roster_id: str,
        identity_fields_json: str,
        schema_json: str,
    ) -> None:
        conn.execute(
            """
            INSERT INTO questionnaire_versions (
                questionnaire_id, version, title, description, identity_mode, allow_repeat,
                passcode_hash, auth_mode, auth_roster_id, identity_fields_json, schema_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(questionnaire_id, version) DO UPDATE SET
                title = excluded.title,
                description = excluded.description,
                identity_mode = excluded.identity_mode,
                allow_repeat = excluded.allow_repeat,
                passcode_hash = excluded.passcode_hash,
                auth_mode = excluded.auth_mode,
                auth_roster_id = excluded.auth_roster_id,
                identity_fields_json = excluded.identity_fields_json,
                schema_json = excluded.schema_json
            """,
            (
                questionnaire_id,
                version,
                title,
                description,
                identity_mode,
                1 if allow_repeat else 0,
                passcode_hash,
                auth_mode,
                auth_roster_id or "",
                identity_fields_json,
                schema_json,
                utc_now(),
            ),
        )

    def save_questionnaire(
        self,
        questionnaire_id: str,
        title: str,
        description: str,
        identity_mode: str,
        allow_repeat: bool,
        passcode_hash: str,
        schema: Dict[str, Any],
        auth_mode: str = "open",
        auth_roster_id: str = "",
        identity_fields: Optional[Dict[str, Any]] = None,
        status: str = "active",
    ) -> int:
        now = utc_now()
        schema_json = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
        identity_fields_json = json.dumps(identity_fields or {}, ensure_ascii=False, separators=(",", ":"))

        with self.connect() as conn:
            existing = conn.execute("SELECT * FROM questionnaires WHERE id = ?", (questionnaire_id,)).fetchone()
            if not existing:
                version = 1
                conn.execute(
                    """
                    INSERT INTO questionnaires (
                        id, title, description, identity_mode, allow_repeat, passcode_hash,
                        auth_mode, auth_roster_id, identity_fields_json, schema_json,
                        current_version, status, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        questionnaire_id,
                        title,
                        description,
                        identity_mode,
                        1 if allow_repeat else 0,
                        passcode_hash,
                        auth_mode,
                        auth_roster_id or "",
                        identity_fields_json,
                        schema_json,
                        version,
                        status,
                        now,
                        now,
                    ),
                )
                self._insert_questionnaire_version(
                    conn=conn,
                    questionnaire_id=questionnaire_id,
                    version=version,
                    title=title,
                    description=description,
                    identity_mode=identity_mode,
                    allow_repeat=allow_repeat,
                    passcode_hash=passcode_hash,
                    auth_mode=auth_mode,
                    auth_roster_id=auth_roster_id,
                    identity_fields_json=identity_fields_json,
                    schema_json=schema_json,
                )
                return version

            changed = any(
                [
                    existing["title"] != title,
                    (existing["description"] or "") != description,
                    existing["identity_mode"] != identity_mode,
                    int(existing["allow_repeat"]) != (1 if allow_repeat else 0),
                    (existing["passcode_hash"] or "") != passcode_hash,
                    (existing["auth_mode"] or "open") != auth_mode,
                    (existing["auth_roster_id"] or "") != (auth_roster_id or ""),
                    (existing["identity_fields_json"] or "{}") != identity_fields_json,
                    (existing["schema_json"] or "{}") != schema_json,
                ]
            )

            current_version = int(existing["current_version"] or 1)
            if changed:
                current_version += 1

            conn.execute(
                """
                UPDATE questionnaires
                SET title = ?,
                    description = ?,
                    identity_mode = ?,
                    allow_repeat = ?,
                    passcode_hash = ?,
                    auth_mode = ?,
                    auth_roster_id = ?,
                    identity_fields_json = ?,
                    schema_json = ?,
                    current_version = ?,
                    status = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    title,
                    description,
                    identity_mode,
                    1 if allow_repeat else 0,
                    passcode_hash,
                    auth_mode,
                    auth_roster_id or "",
                    identity_fields_json,
                    schema_json,
                    current_version,
                    status,
                    now,
                    questionnaire_id,
                ),
            )

            if changed:
                self._insert_questionnaire_version(
                    conn=conn,
                    questionnaire_id=questionnaire_id,
                    version=current_version,
                    title=title,
                    description=description,
                    identity_mode=identity_mode,
                    allow_repeat=allow_repeat,
                    passcode_hash=passcode_hash,
                    auth_mode=auth_mode,
                    auth_roster_id=auth_roster_id,
                    identity_fields_json=identity_fields_json,
                    schema_json=schema_json,
                )
            return current_version

    def list_questionnaires(self, active_only: bool = False) -> List[Dict[str, Any]]:
        sql = """
            SELECT id, title, description, identity_mode, allow_repeat, passcode_hash,
                   auth_mode, auth_roster_id, identity_fields_json, current_version,
                   status, created_at, updated_at
            FROM questionnaires
        """
        params: tuple[Any, ...] = ()
        if active_only:
            sql += " WHERE status = 'active'"
        sql += " ORDER BY updated_at DESC"
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            result = [dict(row) for row in rows]
            for item in result:
                item["allow_repeat"] = bool(item["allow_repeat"])
                item["identity_fields"] = _safe_json_loads(item.pop("identity_fields_json", "{}"), {})
            return result

    def get_questionnaire(self, questionnaire_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM questionnaires WHERE id = ?", (questionnaire_id,)).fetchone()
            if not row:
                return None
            data = dict(row)
            data["schema"] = _safe_json_loads(data.pop("schema_json"), {"questions": []})
            data["identity_fields"] = _safe_json_loads(data.pop("identity_fields_json", "{}"), {})
            data["allow_repeat"] = bool(data["allow_repeat"])
            data["current_version"] = int(data.get("current_version") or 1)
            return data

    def get_questionnaire_version(
        self,
        questionnaire_id: str,
        version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            if version is None:
                row = conn.execute(
                    """
                    SELECT * FROM questionnaire_versions
                    WHERE questionnaire_id = ?
                    ORDER BY version DESC
                    LIMIT 1
                    """,
                    (questionnaire_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM questionnaire_versions
                    WHERE questionnaire_id = ? AND version = ?
                    LIMIT 1
                    """,
                    (questionnaire_id, version),
                ).fetchone()
            if not row:
                return None
            data = dict(row)
            data["schema"] = _safe_json_loads(data.pop("schema_json"), {"questions": []})
            data["identity_fields"] = _safe_json_loads(data.pop("identity_fields_json", "{}"), {})
            data["allow_repeat"] = bool(data["allow_repeat"])
            return data

    def list_questionnaire_versions(self, questionnaire_id: str) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT questionnaire_id, version, title, created_at
                FROM questionnaire_versions
                WHERE questionnaire_id = ?
                ORDER BY version DESC
                """,
                (questionnaire_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def set_questionnaire_status(self, questionnaire_id: str, status: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE questionnaires SET status = ?, updated_at = ? WHERE id = ?",
                (status, utc_now(), questionnaire_id),
            )

    def delete_questionnaire(self, questionnaire_id: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM sql_views WHERE questionnaire_id = ?", (questionnaire_id,))
            conn.execute("DELETE FROM auth_sessions WHERE questionnaire_id = ?", (questionnaire_id,))
            conn.execute("DELETE FROM submissions WHERE questionnaire_id = ?", (questionnaire_id,))
            conn.execute("DELETE FROM questionnaire_versions WHERE questionnaire_id = ?", (questionnaire_id,))
            conn.execute("DELETE FROM questionnaires WHERE id = ?", (questionnaire_id,))

    def create_roster(self, roster_id: str, name: str, description: str = "", columns_json: str = "[]") -> None:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO rosters (id, name, description, columns_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    columns_json = excluded.columns_json,
                    updated_at = excluded.updated_at
                """,
                (roster_id, name, description, columns_json or "[]", now, now),
            )

    def list_rosters(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT r.id, r.name, r.description, r.columns_json, r.created_at, r.updated_at,
                       COUNT(m.id) AS member_count
                FROM rosters r
                LEFT JOIN roster_members m ON m.roster_id = r.id AND m.active = 1
                GROUP BY r.id
                ORDER BY r.updated_at DESC
                """
            ).fetchall()
            result = [dict(row) for row in rows]
            for item in result:
                item["columns"] = _safe_json_loads(item.pop("columns_json", "[]"), [])
            return result

    def get_roster(self, roster_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM rosters WHERE id = ?", (roster_id,)).fetchone()
            if not row:
                return None
            data = dict(row)
            data["columns"] = _safe_json_loads(data.pop("columns_json", "[]"), [])
            return data

    def update_roster_columns(self, roster_id: str, columns_json: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE rosters SET columns_json = ?, updated_at = ? WHERE id = ?",
                (columns_json or "[]", utc_now(), roster_id),
            )

    def upsert_roster_members(
        self,
        roster_id: str,
        members: List[Dict[str, Any]],
        replace_all: bool = False,
    ) -> Dict[str, int]:
        now = utc_now()
        inserted = 0
        updated = 0
        with self.connect() as conn:
            if replace_all:
                conn.execute("DELETE FROM roster_members WHERE roster_id = ?", (roster_id,))
            for member in members:
                member_key = str(member.get("member_key", "")).strip()
                if not member_key:
                    continue
                member_name = str(member.get("member_name", "")).strip()
                member_code = str(member.get("member_code", "")).strip()
                tags = str(member.get("tags", "")).strip()
                extra = member.get("extra", {})
                extra_json = json.dumps(extra if isinstance(extra, dict) else {}, ensure_ascii=False)
                exists = conn.execute(
                    """
                    SELECT id FROM roster_members
                    WHERE roster_id = ? AND member_key = ?
                    """,
                    (roster_id, member_key),
                ).fetchone()
                if exists:
                    conn.execute(
                        """
                        UPDATE roster_members
                        SET member_name = ?,
                            member_code = ?,
                            tags = ?,
                            extra_json = ?,
                            active = 1,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (member_name, member_code, tags, extra_json, now, exists["id"]),
                    )
                    updated += 1
                else:
                    conn.execute(
                        """
                        INSERT INTO roster_members (
                            roster_id, member_key, member_name, member_code, tags,
                            extra_json, active, created_at, updated_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                        """,
                        (roster_id, member_key, member_name, member_code, tags, extra_json, now, now),
                    )
                    inserted += 1
            conn.execute("UPDATE rosters SET updated_at = ? WHERE id = ?", (now, roster_id))
        return {"inserted": inserted, "updated": updated}

    def list_roster_members(self, roster_id: str, limit: int = 5000) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, roster_id, member_key, member_name, member_code, tags, extra_json, active
                FROM roster_members
                WHERE roster_id = ? AND active = 1
                ORDER BY member_code, member_name, member_key
                LIMIT ?
                """,
                (roster_id, max(1, min(limit, 100000))),
            ).fetchall()
            result = [dict(row) for row in rows]
            for item in result:
                item["extra"] = _safe_json_loads(item.pop("extra_json", "{}"), {})
                item["active"] = bool(item["active"])
            return result

    def add_roster_member(
        self,
        roster_id: str,
        member_key: str,
        member_name: str,
        member_code: str,
        tags: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.upsert_roster_members(
            roster_id=roster_id,
            members=[
                {
                    "member_key": member_key,
                    "member_name": member_name,
                    "member_code": member_code,
                    "tags": tags,
                    "extra": extra or {},
                }
            ],
            replace_all=False,
        )

    def remove_roster_member(self, member_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM roster_members WHERE id = ?", (member_id,))

    def delete_roster(self, roster_id: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM roster_members WHERE roster_id = ?", (roster_id,))
            conn.execute("DELETE FROM auth_sessions WHERE roster_id = ?", (roster_id,))
            conn.execute("DELETE FROM rosters WHERE id = ?", (roster_id,))

    def _list_roster_members_raw(self, conn: sqlite3.Connection, roster_id: str) -> List[Dict[str, Any]]:
        rows = conn.execute(
            """
            SELECT id, roster_id, member_key, member_name, member_code, tags, extra_json
            FROM roster_members
            WHERE roster_id = ? AND active = 1
            """,
            (roster_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def _member_field_text(self, member: Dict[str, Any], field_key: str) -> str:
        key = str(field_key or "").strip()
        if not key:
            return ""
        if key in {"member_key", "key", "唯一标识"}:
            return str(member.get("member_key", "")).strip()
        if key in {"member_name", "name", "姓名"}:
            return str(member.get("member_name", "")).strip()
        if key in {"member_code", "code", "编号"}:
            return str(member.get("member_code", "")).strip()
        extra = _safe_json_loads(str(member.get("extra_json", "{}")), {})
        if isinstance(extra, dict):
            return str(extra.get(key, "")).strip()
        return ""

    def find_roster_member_by_fields(
        self,
        roster_id: str,
        fields: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        normalized_fields: Dict[str, str] = {}
        for key, value in fields.items():
            k = str(key or "").strip()
            if not k:
                continue
            v = str(value or "").strip()
            if not v:
                return None
            normalized_fields[k] = v
        if not normalized_fields:
            return None
        with self.connect() as conn:
            for member in self._list_roster_members_raw(conn, roster_id):
                matched = True
                for key, expected in normalized_fields.items():
                    actual = self._member_field_text(member, key)
                    if actual != expected:
                        matched = False
                        break
                if not matched:
                    continue
                data = dict(member)
                data["extra"] = _safe_json_loads(data.pop("extra_json", "{}"), {})
                return data
        return None

    def find_roster_member(
        self,
        roster_id: str,
        mode: str,
        member_code: str,
        member_name: str = "",
    ) -> Optional[Dict[str, Any]]:
        code = member_code.strip()
        name = member_name.strip()
        if mode == "roster_name_code":
            return self.find_roster_member_by_fields(
                roster_id=roster_id,
                fields={"member_code": code, "member_name": name},
            )
        return self.find_roster_member_by_fields(
            roster_id=roster_id,
            fields={"member_code": code},
        )

    def submission_exists(self, submission_id: str) -> bool:
        with self.connect() as conn:
            row = conn.execute("SELECT 1 FROM submissions WHERE id = ?", (submission_id,)).fetchone()
            return row is not None

    def detect_duplicate(
        self,
        questionnaire_id: str,
        client_token: Optional[str],
        respondent_code: Optional[str],
        verified_member_key: Optional[str] = None,
    ) -> bool:
        with self.connect() as conn:
            if verified_member_key:
                row = conn.execute(
                    """
                    SELECT 1 FROM submissions
                    WHERE questionnaire_id = ? AND verified_member_key = ?
                    LIMIT 1
                    """,
                    (questionnaire_id, verified_member_key),
                ).fetchone()
                if row:
                    return True
            if respondent_code:
                row = conn.execute(
                    """
                    SELECT 1 FROM submissions
                    WHERE questionnaire_id = ? AND respondent_code = ?
                    LIMIT 1
                    """,
                    (questionnaire_id, respondent_code),
                ).fetchone()
                if row:
                    return True
            if client_token:
                row = conn.execute(
                    """
                    SELECT 1 FROM submissions
                    WHERE questionnaire_id = ? AND client_token = ?
                    LIMIT 1
                    """,
                    (questionnaire_id, client_token),
                ).fetchone()
                if row:
                    return True
        return False

    def save_submission_meta(
        self,
        submission_id: str,
        questionnaire_id: str,
        questionnaire_version: int,
        respondent_name: str,
        respondent_code: str,
        anonymous: bool,
        source: str,
        vote_file: str,
        client_token: Optional[str] = None,
        session_label: Optional[str] = None,
        target_label: Optional[str] = None,
        roster_id: str = "",
        verified_member_key: str = "",
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO submissions (
                    id, questionnaire_id, questionnaire_version, roster_id, verified_member_key,
                    submitted_at, respondent_name, respondent_code, anonymous, source,
                    vote_file, client_token, session_label, target_label
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    submission_id,
                    questionnaire_id,
                    questionnaire_version,
                    roster_id or "",
                    verified_member_key or "",
                    utc_now(),
                    respondent_name,
                    respondent_code,
                    1 if anonymous else 0,
                    source,
                    vote_file,
                    client_token,
                    session_label,
                    target_label,
                ),
            )

    def list_submissions(self, questionnaire_id: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = """
            SELECT id, questionnaire_id, questionnaire_version, roster_id, verified_member_key,
                   submitted_at, respondent_name, respondent_code, anonymous, source,
                   vote_file, client_token, session_label, target_label
            FROM submissions
        """
        params: Iterable[Any] = ()
        if questionnaire_id:
            sql += " WHERE questionnaire_id = ?"
            params = (questionnaire_id,)
        sql += " ORDER BY submitted_at DESC"
        with self.connect() as conn:
            rows = conn.execute(sql, tuple(params)).fetchall()
            result = [dict(row) for row in rows]
            for row in result:
                row["anonymous"] = bool(row["anonymous"])
            return result

    def get_submission(self, submission_id: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id, questionnaire_id, questionnaire_version, roster_id, verified_member_key,
                       submitted_at, respondent_name, respondent_code, anonymous, source,
                       vote_file, client_token, session_label, target_label
                FROM submissions
                WHERE id = ?
                LIMIT 1
                """,
                (submission_id,),
            ).fetchone()
            if not row:
                return None
            data = dict(row)
            data["anonymous"] = bool(data.get("anonymous", 0))
            return data

    def delete_submission(self, submission_id: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))

    def save_sql_view(self, questionnaire_id: str, name: str, sql_text: str) -> int:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO sql_views (questionnaire_id, name, sql_text, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(questionnaire_id, name) DO UPDATE SET
                    sql_text = excluded.sql_text,
                    updated_at = excluded.updated_at
                """,
                (questionnaire_id, name, sql_text, now, now),
            )
            row = conn.execute(
                "SELECT id FROM sql_views WHERE questionnaire_id = ? AND name = ? LIMIT 1",
                (questionnaire_id, name),
            ).fetchone()
            return int(row["id"]) if row else 0

    def get_sql_view(self, view_id: int) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT id, questionnaire_id, name, sql_text, created_at, updated_at
                FROM sql_views
                WHERE id = ?
                LIMIT 1
                """,
                (view_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_sql_views(self, questionnaire_id: str) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, questionnaire_id, name, sql_text, created_at, updated_at
                FROM sql_views
                WHERE questionnaire_id = ?
                ORDER BY updated_at DESC, id DESC
                """,
                (questionnaire_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def remove_sql_view(self, view_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM sql_views WHERE id = ?", (view_id,))

    def save_template_sql_view(self, template_key: str, name: str, sql_text: str) -> int:
        now = utc_now()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO template_sql_views (template_key, name, sql_text, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(template_key, name) DO UPDATE SET
                    sql_text = excluded.sql_text,
                    updated_at = excluded.updated_at
                """,
                (template_key, name, sql_text, now, now),
            )
            row = conn.execute(
                "SELECT id FROM template_sql_views WHERE template_key = ? AND name = ? LIMIT 1",
                (template_key, name),
            ).fetchone()
            return int(row["id"]) if row else 0

    def list_template_sql_views(self, template_key: str) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, template_key, name, sql_text, created_at, updated_at
                FROM template_sql_views
                WHERE template_key = ?
                ORDER BY updated_at DESC, id DESC
                """,
                (template_key,),
            ).fetchall()
            return [dict(row) for row in rows]

    def remove_template_sql_view(self, template_key: str, name: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "DELETE FROM template_sql_views WHERE template_key = ? AND name = ?",
                (template_key, name),
            )

    def create_auth_session(
        self,
        token: str,
        questionnaire_id: str,
        roster_id: str,
        member_key: str,
        expires_at: str,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO auth_sessions (
                    token, questionnaire_id, roster_id, member_key,
                    issued_at, expires_at, used
                )
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (token, questionnaire_id, roster_id, member_key, utc_now(), expires_at),
            )

    def get_auth_session(self, token: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT token, questionnaire_id, roster_id, member_key, issued_at, expires_at, used, consumed_at
                FROM auth_sessions
                WHERE token = ?
                LIMIT 1
                """,
                (token,),
            ).fetchone()
            return dict(row) if row else None

    def consume_auth_session(self, token: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE auth_sessions
                SET used = 1, consumed_at = ?
                WHERE token = ? AND used = 0
                """,
                (utc_now(), token),
            )

    def purge_expired_auth_sessions(self, now_iso: str) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM auth_sessions WHERE expires_at < ?", (now_iso,))

    def count_questionnaires(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM questionnaires").fetchone()
            return int(row["c"]) if row else 0

    def count_submissions(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM submissions").fetchone()
            return int(row["c"]) if row else 0

    def count_rosters(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM rosters").fetchone()
            return int(row["c"]) if row else 0
