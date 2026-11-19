"""Candidate-only, room-scoped authorization for a private DobeWorks lab.

Authentication is deliberately out of scope. Callers must supply the stable
identity returned by DobeWorks' existing authenticated actor boundary.
"""

from __future__ import annotations

import re
import sqlite3
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable


ROOM_ID = "tin-whiskers-private-lab"
OWNER_ID = "owner"
MUSE_REVIEWER_ID = "muse-mac"

# Frozen candidate roster. Changing this tuple is a reviewed code change, not a
# database or request parameter.
FROZEN_WORKER_ROSTER = (
    "codex-lab-materials-calibration",
    "codex-lab-materials-search",
    "codex-lab-adaptive-controller",
    "codex-lab-controller-interface",
    "codex-lab-falsification",
    "codex-lab-statistics",
)

LAB_ONLY_IDENTITIES = frozenset((*FROZEN_WORKER_ROSTER, MUSE_REVIEWER_ID))
KNOWN_IDENTITIES = frozenset((*FROZEN_WORKER_ROSTER, MUSE_REVIEWER_ID, OWNER_ID))

IDENTITY_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
MESSAGE_ID_RE = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
MAX_TEXT_BYTES = 16_384
MAX_TITLE_CHARS = 120
PAGE_SIZE = 100


@dataclass(frozen=True)
class RoomCaps:
    max_posts: int = 500
    max_comments: int = 2_000
    max_content_bytes: int = 16 * 1024 * 1024
    max_audit_events: int = 10_000

    def validate(self) -> None:
        values = (
            self.max_posts,
            self.max_comments,
            self.max_content_bytes,
            self.max_audit_events,
        )
        if any(type(value) is not int or value <= 0 for value in values):
            raise ValueError("room caps must be positive integers")


DEFAULT_CAPS = RoomCaps()


class Capability(str, Enum):
    LAB_READ = "lab_read"
    LAB_POST = "lab_post"
    LAB_COMMENT = "lab_comment"
    LAB_ADMIN = "lab_admin"
    JOB_SUBMIT = "job_submit"
    PUBLIC_PUBLISH = "public_publish"
    GENERAL_BOARD_READ = "general_board_read"
    GENERAL_BOARD_WRITE = "general_board_write"
    DIRECT_MESSAGE = "direct_message"


ROLE_CAPABILITIES = {
    "worker": frozenset(
        {Capability.LAB_READ, Capability.LAB_POST, Capability.LAB_COMMENT}
    ),
    "reviewer": frozenset({Capability.LAB_READ, Capability.LAB_COMMENT}),
    "owner": frozenset(
        {
            Capability.LAB_READ,
            Capability.LAB_POST,
            Capability.LAB_COMMENT,
            Capability.LAB_ADMIN,
        }
    ),
}


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    role: str | None = None


class LabAccessError(Exception):
    """Base class for reference-module failures."""


class AccessDenied(LabAccessError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class InvalidInput(LabAccessError):
    pass


class Conflict(LabAccessError):
    pass


class CapacityExceeded(LabAccessError):
    pass


class RosterDrift(LabAccessError):
    pass


def initialize(
    connection: sqlite3.Connection,
    *,
    caps: RoomCaps = DEFAULT_CAPS,
    now: int | None = None,
) -> None:
    """Create the additive candidate schema and seed the frozen memberships."""

    caps.validate()
    timestamp = int(time.time()) if now is None else _timestamp(now)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS lab_rooms (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            max_posts INTEGER NOT NULL CHECK(max_posts > 0),
            max_comments INTEGER NOT NULL CHECK(max_comments > 0),
            max_content_bytes INTEGER NOT NULL CHECK(max_content_bytes > 0),
            max_audit_events INTEGER NOT NULL CHECK(max_audit_events > 0),
            post_count INTEGER NOT NULL DEFAULT 0 CHECK(post_count >= 0),
            comment_count INTEGER NOT NULL DEFAULT 0 CHECK(comment_count >= 0),
            content_bytes INTEGER NOT NULL DEFAULT 0 CHECK(content_bytes >= 0)
        );

        CREATE TABLE IF NOT EXISTS lab_memberships (
            room_id TEXT NOT NULL REFERENCES lab_rooms(id),
            identity_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('worker','reviewer','owner')),
            created_at INTEGER NOT NULL,
            revoked_at INTEGER,
            PRIMARY KEY(room_id, identity_id),
            CHECK(revoked_at IS NULL OR revoked_at >= created_at)
        );

        CREATE TABLE IF NOT EXISTS lab_posts (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL,
            id TEXT NOT NULL,
            author_id TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('post','comment')),
            parent_sequence INTEGER REFERENCES lab_posts(sequence),
            title TEXT,
            text TEXT NOT NULL,
            content_bytes INTEGER NOT NULL CHECK(content_bytes > 0),
            created_at INTEGER NOT NULL,
            UNIQUE(room_id, author_id, id),
            FOREIGN KEY(room_id, author_id)
                REFERENCES lab_memberships(room_id, identity_id),
            CHECK(
                (kind='post' AND parent_sequence IS NULL AND title IS NOT NULL)
                OR
                (kind='comment' AND parent_sequence IS NOT NULL AND title IS NULL)
            )
        );

        CREATE INDEX IF NOT EXISTS lab_posts_room_sequence
            ON lab_posts(room_id, sequence);
        CREATE INDEX IF NOT EXISTS lab_posts_parent_sequence
            ON lab_posts(room_id, parent_sequence, sequence);

        CREATE TABLE IF NOT EXISTS lab_audit_events (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT NOT NULL REFERENCES lab_rooms(id),
            actor_id TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN (
                'post_created','comment_created','membership_revoked',
                'connector_arithmetic_check'
            )),
            outcome TEXT NOT NULL CHECK(outcome IN ('allowed','passed','failed')),
            reason_code TEXT NOT NULL CHECK(reason_code IN (
                'ok','owner_revocation','capability_only'
            )),
            object_sequence INTEGER,
            created_at INTEGER NOT NULL
        );
        """
    )
    _install_frozen_guards(connection)
    connection.execute(
        """INSERT OR IGNORE INTO lab_rooms(
            id,title,created_at,max_posts,max_comments,max_content_bytes,max_audit_events
        ) VALUES(?,?,?,?,?,?,?)""",
        (
            ROOM_ID,
            "Tin Whiskers Private Lab",
            timestamp,
            caps.max_posts,
            caps.max_comments,
            caps.max_content_bytes,
            caps.max_audit_events,
        ),
    )
    expected_room = (
        caps.max_posts,
        caps.max_comments,
        caps.max_content_bytes,
        caps.max_audit_events,
    )
    actual_room = connection.execute(
        """SELECT max_posts,max_comments,max_content_bytes,max_audit_events
           FROM lab_rooms WHERE id=?""",
        (ROOM_ID,),
    ).fetchone()
    if actual_room is None or tuple(actual_room) != expected_room:
        connection.rollback()
        raise RosterDrift("room configuration differs from the frozen candidate")

    memberships = [
        *((identity_id, "worker") for identity_id in FROZEN_WORKER_ROSTER),
        (MUSE_REVIEWER_ID, "reviewer"),
        (OWNER_ID, "owner"),
    ]
    connection.executemany(
        """INSERT OR IGNORE INTO lab_memberships(
            room_id,identity_id,role,created_at
        ) VALUES(?,?,?,?)""",
        ((ROOM_ID, identity_id, role, timestamp) for identity_id, role in memberships),
    )
    rows = connection.execute(
        "SELECT identity_id,role FROM lab_memberships WHERE room_id=? ORDER BY identity_id",
        (ROOM_ID,),
    ).fetchall()
    actual = {(row[0], row[1]) for row in rows}
    expected = set(memberships)
    if actual != expected:
        connection.rollback()
        raise RosterDrift("lab membership differs from the frozen roster")
    connection.commit()


def _install_frozen_guards(connection: sqlite3.Connection) -> None:
    worker_sql = ",".join(f"'{identity_id}'" for identity_id in FROZEN_WORKER_ROSTER)
    allowed_membership = f"""
        NEW.room_id='{ROOM_ID}' AND (
            (NEW.role='worker' AND NEW.identity_id IN ({worker_sql})) OR
            (NEW.role='reviewer' AND NEW.identity_id='{MUSE_REVIEWER_ID}') OR
            (NEW.role='owner' AND NEW.identity_id='{OWNER_ID}')
        )
    """
    connection.executescript(
        f"""
        CREATE TRIGGER IF NOT EXISTS lab_room_insert_guard
        BEFORE INSERT ON lab_rooms
        WHEN NEW.id <> '{ROOM_ID}'
        BEGIN SELECT RAISE(ABORT, 'unknown lab room'); END;

        CREATE TRIGGER IF NOT EXISTS lab_room_id_update_guard
        BEFORE UPDATE OF id ON lab_rooms
        BEGIN SELECT RAISE(ABORT, 'lab room id is immutable'); END;

        CREATE TRIGGER IF NOT EXISTS lab_membership_insert_guard
        BEFORE INSERT ON lab_memberships
        WHEN NOT ({allowed_membership})
        BEGIN SELECT RAISE(ABORT, 'identity is outside frozen lab roster'); END;

        CREATE TRIGGER IF NOT EXISTS lab_membership_update_guard
        BEFORE UPDATE OF room_id,identity_id,role ON lab_memberships
        WHEN NOT ({allowed_membership})
        BEGIN SELECT RAISE(ABORT, 'identity is outside frozen lab roster'); END;

        CREATE TRIGGER IF NOT EXISTS lab_membership_delete_guard
        BEFORE DELETE ON lab_memberships
        BEGIN SELECT RAISE(ABORT, 'revoke memberships instead of deleting them'); END;

        CREATE TRIGGER IF NOT EXISTS lab_post_update_guard
        BEFORE UPDATE ON lab_posts
        BEGIN SELECT RAISE(ABORT, 'lab posts are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS lab_post_delete_guard
        BEFORE DELETE ON lab_posts
        BEGIN SELECT RAISE(ABORT, 'lab posts are append-only'); END;

        CREATE TRIGGER IF NOT EXISTS lab_audit_update_guard
        BEFORE UPDATE ON lab_audit_events
        BEGIN SELECT RAISE(ABORT, 'lab audit is append-only'); END;

        CREATE TRIGGER IF NOT EXISTS lab_audit_delete_guard
        BEFORE DELETE ON lab_audit_events
        BEGIN SELECT RAISE(ABORT, 'lab audit is append-only'); END;
        """
    )


class LabAccess:
    """Room-local authorization and append-only discussion reference."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        *,
        clock: Callable[[], int] | None = None,
    ):
        self.connection = connection
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.clock = clock or (lambda: int(time.time()))

    def authorize(
        self,
        identity_id: str,
        capability: Capability,
        *,
        room_id: str = ROOM_ID,
    ) -> Decision:
        if not isinstance(identity_id, str) or not IDENTITY_RE.fullmatch(identity_id):
            return Decision(False, "unknown_identity")
        if identity_id not in KNOWN_IDENTITIES:
            return Decision(False, "unknown_identity")
        if room_id != ROOM_ID:
            return Decision(False, "room_not_granted")
        row = self.connection.execute(
            """SELECT role,revoked_at FROM lab_memberships
               WHERE room_id=? AND identity_id=?""",
            (room_id, identity_id),
        ).fetchone()
        if row is None:
            return Decision(False, "membership_missing")
        if row["revoked_at"] is not None:
            return Decision(False, "membership_revoked", row["role"])
        if capability not in ROLE_CAPABILITIES[row["role"]]:
            return Decision(False, "capability_not_granted", row["role"])
        return Decision(True, "allowed", row["role"])

    def require(
        self,
        identity_id: str,
        capability: Capability,
        *,
        room_id: str = ROOM_ID,
    ) -> str:
        decision = self.authorize(identity_id, capability, room_id=room_id)
        if not decision.allowed:
            raise AccessDenied(decision.reason)
        assert decision.role is not None
        return decision.role

    def list_entries(
        self,
        identity_id: str,
        *,
        room_id: str = ROOM_ID,
        after: int = 0,
        parent_sequence: int | None = None,
    ) -> list[dict]:
        self.require(identity_id, Capability.LAB_READ, room_id=room_id)
        if type(after) is not int or after < 0:
            raise InvalidInput("after must be a nonnegative integer")
        clauses = ["room_id=?", "sequence>?"]
        values: list[object] = [room_id, after]
        if parent_sequence is not None:
            if type(parent_sequence) is not int or parent_sequence <= 0:
                raise InvalidInput("parent_sequence must be a positive integer")
            clauses.append("parent_sequence=?")
            values.append(parent_sequence)
        rows = self.connection.execute(
            "SELECT * FROM lab_posts WHERE "
            + " AND ".join(clauses)
            + " ORDER BY sequence LIMIT ?",
            (*values, PAGE_SIZE),
        ).fetchall()
        return [dict(row) for row in rows]

    def create_post(
        self,
        identity_id: str,
        *,
        message_id: str,
        title: str,
        text: str,
        room_id: str = ROOM_ID,
    ) -> tuple[dict, bool]:
        self.require(identity_id, Capability.LAB_POST, room_id=room_id)
        return self._write(
            identity_id,
            room_id=room_id,
            message_id=message_id,
            kind="post",
            title=title,
            text=text,
            parent_sequence=None,
        )

    def create_comment(
        self,
        identity_id: str,
        *,
        message_id: str,
        parent_sequence: int,
        text: str,
        room_id: str = ROOM_ID,
    ) -> tuple[dict, bool]:
        self.require(identity_id, Capability.LAB_COMMENT, room_id=room_id)
        if type(parent_sequence) is not int or parent_sequence <= 0:
            raise InvalidInput("parent_sequence must be a positive integer")
        return self._write(
            identity_id,
            room_id=room_id,
            message_id=message_id,
            kind="comment",
            title=None,
            text=text,
            parent_sequence=parent_sequence,
        )

    def _write(
        self,
        identity_id: str,
        *,
        room_id: str,
        message_id: str,
        kind: str,
        title: str | None,
        text: str,
        parent_sequence: int | None,
    ) -> tuple[dict, bool]:
        if not isinstance(message_id, str) or not MESSAGE_ID_RE.fullmatch(message_id):
            raise InvalidInput("invalid message id")
        content_bytes = _text_size(text)
        if kind == "post":
            if not isinstance(title, str) or not title.strip():
                raise InvalidInput("post title must be nonempty")
            if len(title) > MAX_TITLE_CHARS:
                raise InvalidInput("post title is too long")
            content_bytes += _text_size(title)

        self.connection.execute("BEGIN IMMEDIATE")
        try:
            existing = self.connection.execute(
                """SELECT * FROM lab_posts
                   WHERE room_id=? AND author_id=? AND id=?""",
                (room_id, identity_id, message_id),
            ).fetchone()
            if existing is not None:
                expected = {
                    "kind": kind,
                    "parent_sequence": parent_sequence,
                    "title": title,
                    "text": text,
                }
                if any(existing[key] != value for key, value in expected.items()):
                    raise Conflict("message id was already used for different content")
                self.connection.commit()
                return dict(existing), True

            room = self.connection.execute(
                "SELECT * FROM lab_rooms WHERE id=?", (room_id,)
            ).fetchone()
            if room is None:
                raise AccessDenied("room_not_granted")
            if kind == "post" and room["post_count"] >= room["max_posts"]:
                raise CapacityExceeded("post cap reached")
            if kind == "comment" and room["comment_count"] >= room["max_comments"]:
                raise CapacityExceeded("comment cap reached")
            if room["content_bytes"] + content_bytes > room["max_content_bytes"]:
                raise CapacityExceeded("content-byte cap reached")
            if self._audit_count(room_id) >= room["max_audit_events"]:
                raise CapacityExceeded("audit cap reached")
            if kind == "comment":
                parent = self.connection.execute(
                    """SELECT kind FROM lab_posts
                       WHERE room_id=? AND sequence=?""",
                    (room_id, parent_sequence),
                ).fetchone()
                if parent is None or parent["kind"] != "post":
                    raise InvalidInput("comment parent must be a top-level room post")

            created_at = _timestamp(self.clock())
            result = self.connection.execute(
                """INSERT INTO lab_posts(
                    room_id,id,author_id,kind,parent_sequence,title,text,
                    content_bytes,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    room_id,
                    message_id,
                    identity_id,
                    kind,
                    parent_sequence,
                    title,
                    text,
                    content_bytes,
                    created_at,
                ),
            )
            counter = "post_count" if kind == "post" else "comment_count"
            self.connection.execute(
                f"""UPDATE lab_rooms SET {counter}={counter}+1,
                    content_bytes=content_bytes+? WHERE id=?""",
                (content_bytes, room_id),
            )
            self._insert_audit(
                room_id=room_id,
                actor_id=identity_id,
                action="post_created" if kind == "post" else "comment_created",
                outcome="allowed",
                reason_code="ok",
                object_sequence=result.lastrowid,
                created_at=created_at,
            )
            row = self.connection.execute(
                "SELECT * FROM lab_posts WHERE sequence=?", (result.lastrowid,)
            ).fetchone()
            self.connection.commit()
            return dict(row), False
        except Exception:
            self.connection.rollback()
            raise

    def revoke(
        self,
        actor_id: str,
        target_identity_id: str,
        *,
        room_id: str = ROOM_ID,
    ) -> bool:
        self.require(actor_id, Capability.LAB_ADMIN, room_id=room_id)
        if target_identity_id == OWNER_ID:
            raise AccessDenied("owner_membership_is_not_revocable_here")
        if target_identity_id not in LAB_ONLY_IDENTITIES:
            raise AccessDenied("unknown_identity")
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            row = self.connection.execute(
                """SELECT revoked_at FROM lab_memberships
                   WHERE room_id=? AND identity_id=?""",
                (room_id, target_identity_id),
            ).fetchone()
            if row is None:
                raise AccessDenied("membership_missing")
            if row["revoked_at"] is not None:
                self.connection.commit()
                return False
            room = self.connection.execute(
                "SELECT max_audit_events FROM lab_rooms WHERE id=?", (room_id,)
            ).fetchone()
            if room is None or self._audit_count(room_id) >= room["max_audit_events"]:
                raise CapacityExceeded("audit cap reached")
            revoked_at = _timestamp(self.clock())
            self.connection.execute(
                """UPDATE lab_memberships SET revoked_at=?
                   WHERE room_id=? AND identity_id=?""",
                (revoked_at, room_id, target_identity_id),
            )
            self._insert_audit(
                room_id=room_id,
                actor_id=actor_id,
                action="membership_revoked",
                outcome="allowed",
                reason_code="owner_revocation",
                object_sequence=None,
                created_at=revoked_at,
            )
            self.connection.commit()
            return True
        except Exception:
            self.connection.rollback()
            raise

    def record_muse_arithmetic_check(
        self,
        actor_id: str,
        *,
        passed: bool,
        room_id: str = ROOM_ID,
    ) -> bool:
        """Record connector behavior without authenticating or granting rights."""

        if actor_id != MUSE_REVIEWER_ID:
            raise AccessDenied("connector_check_reserved_for_muse_reviewer")
        self.require(actor_id, Capability.LAB_READ, room_id=room_id)
        if type(passed) is not bool:
            raise InvalidInput("passed must be a boolean")
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            room = self.connection.execute(
                "SELECT max_audit_events FROM lab_rooms WHERE id=?", (room_id,)
            ).fetchone()
            if room is None or self._audit_count(room_id) >= room["max_audit_events"]:
                raise CapacityExceeded("audit cap reached")
            self._insert_audit(
                room_id=room_id,
                actor_id=actor_id,
                action="connector_arithmetic_check",
                outcome="passed" if passed else "failed",
                reason_code="capability_only",
                object_sequence=None,
                created_at=_timestamp(self.clock()),
            )
            self.connection.commit()
            return passed
        except Exception:
            self.connection.rollback()
            raise

    def _audit_count(self, room_id: str) -> int:
        return self.connection.execute(
            "SELECT COUNT(*) FROM lab_audit_events WHERE room_id=?", (room_id,)
        ).fetchone()[0]

    def _insert_audit(
        self,
        *,
        room_id: str,
        actor_id: str,
        action: str,
        outcome: str,
        reason_code: str,
        object_sequence: int | None,
        created_at: int,
    ) -> None:
        self.connection.execute(
            """INSERT INTO lab_audit_events(
                room_id,actor_id,action,outcome,reason_code,object_sequence,created_at
            ) VALUES(?,?,?,?,?,?,?)""",
            (
                room_id,
                actor_id,
                action,
                outcome,
                reason_code,
                object_sequence,
                created_at,
            ),
        )


def _text_size(value: str) -> int:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInput("text must be a nonempty string")
    try:
        size = len(value.encode("utf-8"))
    except UnicodeError as error:
        raise InvalidInput("text must be valid Unicode") from error
    if size > MAX_TEXT_BYTES:
        raise InvalidInput("text exceeds the per-message byte cap")
    return size


def _timestamp(value: int) -> int:
    if type(value) is not int or value < 0 or value >= 2**63:
        raise ValueError("timestamp must be a nonnegative 64-bit integer")
    return value
