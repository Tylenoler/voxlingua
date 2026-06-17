"""
Tests for core/session_manager.py — Session lifecycle, history, expiry.
"""

import time
from datetime import datetime, timedelta

from core.session_manager import Session, session_manager


class TestSession:
    def test_create(self):
        sess = Session(session_id="sess-001")
        assert sess.session_id == "sess-001"
        assert sess.message_count == 0
        assert isinstance(sess.created_at, datetime)
        assert isinstance(sess.last_active, datetime)

    def test_add_message(self):
        sess = Session(session_id="sess-001")
        sess.add_message("user", "Hello")
        assert sess.message_count == 1
        history = sess.get_history()
        assert len(history) == 1
        assert history[0] == {"role": "user", "content": "Hello"}

    def test_multiple_messages(self):
        sess = Session(session_id="sess-001")
        sess.add_message("user", "Hi")
        sess.add_message("assistant", "Hello!")
        sess.add_message("user", "How are you?")
        assert sess.message_count == 3
        history = sess.get_history()
        assert history[0]["content"] == "Hi"
        assert history[2]["role"] == "user"

    def test_updates_last_active(self):
        sess = Session(session_id="sess-001")
        t1 = sess.last_active
        time.sleep(0.01)
        sess.add_message("user", "test")
        t2 = sess.last_active
        assert t2 > t1

    def test_is_expired(self):
        sess = Session(
            session_id="sess-001",
            timeout_minutes=0,  # zero timeout → immediate expiry
        )
        # created_at and last_active are now; they need to be in the past
        sess.created_at = datetime.now() - timedelta(minutes=1)
        sess.last_active = datetime.now() - timedelta(minutes=1)
        assert sess.is_expired()

    def test_not_expired(self):
        sess = Session(session_id="sess-001", timeout_minutes=60)
        assert not sess.is_expired()

    def test_max_history_truncation(self):
        sess = Session(session_id="sess-001", max_history=5)
        for i in range(10):
            sess.add_message("user", f"Message {i}")
        assert sess.message_count == 5
        # Should keep the most recent messages
        history = sess.get_history()
        assert history[0]["content"] == "Message 5"

    def test_correction_mode_defaults(self):
        sess = Session(session_id="sess-001")
        assert sess.correction_mode.mode == "medium"
        assert sess.correction_mode.interrupt_on_severe is True


class TestSessionManager:
    def test_create_and_get(self):
        sess = session_manager.create_session(session_id="sess-001")
        assert sess is not None
        assert session_manager.get_session("sess-001") is sess

    def test_create_auto_id(self):
        sess = session_manager.create_session()
        assert sess.session_id.startswith("sess_")

    def test_get_nonexistent(self):
        assert session_manager.get_session("does-not-exist") is None

    def test_remove_session(self):
        session_manager.create_session(session_id="sess-001")
        session_manager.remove_session("sess-001")
        assert session_manager.get_session("sess-001") is None

    def test_active_count(self):
        assert session_manager.active_count == 0
        session_manager.create_session(session_id="sess-001")
        assert session_manager.active_count == 1
        session_manager.create_session(session_id="sess-002")
        assert session_manager.active_count == 2

    def test_remove_decrements_count(self):
        session_manager.create_session(session_id="sess-001")
        session_manager.create_session(session_id="sess-002")
        session_manager.remove_session("sess-001")
        assert session_manager.active_count == 1

    def test_remove_idempotent(self):
        """Removing a nonexistent session should not raise."""
        session_manager.remove_session("ghost-session")  # no raise

    def test_cleanup_expired(self):
        # Create two sessions, expire one
        sess1 = session_manager.create_session(session_id="sess-001")
        session_manager.create_session(session_id="sess-002")
        sess1.created_at = datetime.now() - timedelta(hours=2)
        sess1.last_active = datetime.now() - timedelta(hours=2)
        # sess1 has default timeout_minutes=60, so 2h ago is expired

        session_manager.cleanup_expired()
        assert session_manager.get_session("sess-001") is None
        assert session_manager.get_session("sess-002") is not None

    def test_duplicate_session_id(self):
        """Creating a session with an existing ID should overwrite."""
        session_manager.create_session(session_id="sess-001")
        sess2 = session_manager.create_session(session_id="sess-001")
        assert session_manager.get_session("sess-001") is sess2
