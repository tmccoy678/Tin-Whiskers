import sqlite3
import unittest

from lab_access import (
    FROZEN_WORKER_ROSTER,
    LAB_ONLY_IDENTITIES,
    MUSE_REVIEWER_ID,
    OWNER_ID,
    ROOM_ID,
    AccessDenied,
    Capability,
    CapacityExceeded,
    LabAccess,
    RoomCaps,
    initialize,
)


class LabAccessTests(unittest.TestCase):
    def setUp(self):
        self.database = sqlite3.connect(":memory:")
        self.clock_value = 1_700_000_000
        self.caps = RoomCaps(
            max_posts=4,
            max_comments=4,
            max_content_bytes=4_096,
            max_audit_events=32,
        )
        initialize(self.database, caps=self.caps, now=self.clock_value)
        self.access = LabAccess(self.database, clock=lambda: self.clock_value)
        self.worker = FROZEN_WORKER_ROSTER[0]

    def tearDown(self):
        self.database.close()

    def test_frozen_roster_is_exactly_six_workers_plus_reviewer_and_owner(self):
        rows = [
            tuple(row)
            for row in self.database.execute(
                "SELECT identity_id,role FROM lab_memberships ORDER BY identity_id"
            )
        ]
        workers = {identity for identity, role in rows if role == "worker"}
        self.assertEqual(workers, set(FROZEN_WORKER_ROSTER))
        self.assertEqual(len(workers), 6)
        self.assertIn((MUSE_REVIEWER_ID, "reviewer"), rows)
        self.assertIn((OWNER_ID, "owner"), rows)
        with self.assertRaises(sqlite3.IntegrityError):
            self.database.execute(
                """INSERT INTO lab_memberships(
                    room_id,identity_id,role,created_at
                ) VALUES(?,?,?,?)""",
                (ROOM_ID, "codex-lab-seventh-worker", "worker", self.clock_value),
            )

    def test_worker_is_room_local_and_has_no_other_dobeworks_authority(self):
        for capability in (
            Capability.LAB_READ,
            Capability.LAB_POST,
            Capability.LAB_COMMENT,
        ):
            self.assertTrue(self.access.authorize(self.worker, capability).allowed)
        for capability in (
            Capability.JOB_SUBMIT,
            Capability.PUBLIC_PUBLISH,
            Capability.GENERAL_BOARD_READ,
            Capability.GENERAL_BOARD_WRITE,
            Capability.DIRECT_MESSAGE,
            Capability.LAB_ADMIN,
        ):
            self.assertFalse(self.access.authorize(self.worker, capability).allowed)
        self.assertFalse(
            self.access.authorize(
                self.worker, Capability.LAB_READ, room_id="another-room"
            ).allowed
        )

    def test_muse_can_read_and_comment_but_arithmetic_never_authenticates(self):
        post, duplicate = self.access.create_post(
            self.worker,
            message_id="post-1",
            title="Question",
            text="A bounded laboratory question.",
        )
        self.assertFalse(duplicate)
        self.assertTrue(
            self.access.authorize(MUSE_REVIEWER_ID, Capability.LAB_READ).allowed
        )
        self.assertTrue(
            self.access.authorize(MUSE_REVIEWER_ID, Capability.LAB_COMMENT).allowed
        )
        self.assertFalse(
            self.access.authorize(MUSE_REVIEWER_ID, Capability.LAB_POST).allowed
        )
        self.access.create_comment(
            MUSE_REVIEWER_ID,
            message_id="muse-comment-1",
            parent_sequence=post["sequence"],
            text="The arithmetic connector check is separate from this review.",
        )
        self.assertTrue(
            self.access.record_muse_arithmetic_check(
                MUSE_REVIEWER_ID, passed=True
            )
        )
        self.assertFalse(
            self.access.authorize(MUSE_REVIEWER_ID, Capability.LAB_POST).allowed
        )
        with self.assertRaises(AccessDenied):
            self.access.record_muse_arithmetic_check(
                "codex-unknown", passed=True
            )

    def test_owner_can_oversee_and_revoke_without_deleting_history(self):
        post, _ = self.access.create_post(
            self.worker,
            message_id="post-2",
            title="Retained work",
            text="This remains after membership revocation.",
        )
        self.assertTrue(self.access.revoke(OWNER_ID, self.worker))
        self.assertFalse(self.access.revoke(OWNER_ID, self.worker))
        decision = self.access.authorize(self.worker, Capability.LAB_READ)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "membership_revoked")
        entries = self.access.list_entries(OWNER_ID)
        self.assertEqual(entries[0]["sequence"], post["sequence"])

    def test_unknown_identities_fail_closed(self):
        decision = self.access.authorize("codex-unknown", Capability.LAB_READ)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "unknown_identity")
        with self.assertRaises(AccessDenied):
            self.access.create_post(
                "codex-unknown",
                message_id="unknown-post",
                title="Denied",
                text="This must never be stored.",
            )
        count = self.database.execute("SELECT COUNT(*) FROM lab_posts").fetchone()[0]
        self.assertEqual(count, 0)

    def test_storage_caps_fail_closed_and_retain_existing_content(self):
        limited = sqlite3.connect(":memory:")
        try:
            initialize(
                limited,
                caps=RoomCaps(
                    max_posts=1,
                    max_comments=1,
                    max_content_bytes=1_024,
                    max_audit_events=8,
                ),
                now=self.clock_value,
            )
            access = LabAccess(limited, clock=lambda: self.clock_value)
            first, _ = access.create_post(
                self.worker,
                message_id="only-post",
                title="First",
                text="Retained.",
            )
            with self.assertRaises(CapacityExceeded):
                access.create_post(
                    FROZEN_WORKER_ROSTER[1],
                    message_id="second-post",
                    title="Second",
                    text="Rejected at the cap.",
                )
            rows = access.list_entries(OWNER_ID)
            self.assertEqual([row["sequence"] for row in rows], [first["sequence"]])
        finally:
            limited.close()

    def test_audit_contains_metadata_not_content_or_challenge_material(self):
        secret_text = "CONTENT-MUST-NOT-ENTER-AUDIT"
        self.access.create_post(
            self.worker,
            message_id="audit-safe-post",
            title="Audit boundary",
            text=secret_text,
        )
        self.access.record_muse_arithmetic_check(MUSE_REVIEWER_ID, passed=False)
        columns = {
            row[1] for row in self.database.execute("PRAGMA table_info(lab_audit_events)")
        }
        self.assertNotIn("text", columns)
        self.assertNotIn("title", columns)
        self.assertNotIn("token", columns)
        rows = [tuple(row) for row in self.database.execute("SELECT * FROM lab_audit_events")]
        self.assertNotIn(secret_text, repr(rows))

    def test_all_lab_only_identities_are_denied_external_capabilities(self):
        for identity_id in LAB_ONLY_IDENTITIES:
            for capability in (
                Capability.JOB_SUBMIT,
                Capability.PUBLIC_PUBLISH,
                Capability.GENERAL_BOARD_READ,
                Capability.GENERAL_BOARD_WRITE,
                Capability.DIRECT_MESSAGE,
            ):
                self.assertFalse(
                    self.access.authorize(identity_id, capability).allowed,
                    (identity_id, capability),
                )


if __name__ == "__main__":
    unittest.main()
