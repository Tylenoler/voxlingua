"""Tests for session manager."""

import sys; sys.path.insert(0, ".")
from core.session_manager import SessionManager


def test_session_create():
    sm = SessionManager()
    s = sm.create_session(language="en", scene="daily_chat")
    assert s.session_id.startswith("sess_")
    assert s.language == "en"
    assert s.scene == "daily_chat"
    assert s.message_count == 0
    print(f"  Session: {s.session_id}")
    return True


def test_session_messages():
    sm = SessionManager()
    s = sm.create_session()
    s.add_message("user", "Hello")
    s.add_message("assistant", "Hi there")
    assert s.message_count == 2
    history = s.get_history()
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["content"] == "Hi there"
    return True


def test_session_expiry():
    sm = SessionManager(timeout_minutes=0)  # Immediate expiry
    s = sm.create_session()
    import time; time.sleep(0.01)
    assert sm.active_count == 0  # Session should be expired
    assert sm.get_session(s.session_id) is None
    return True


def test_multiple_sessions():
    sm = SessionManager(timeout_minutes=60)
    s1 = sm.create_session(scene="daily_chat")
    s2 = sm.create_session(scene="restaurant", language="en")
    s3 = sm.create_session(scene="travel")
    assert sm.active_count == 3
    sm.remove_session(s2.session_id)
    assert sm.active_count == 2
    return True


if __name__ == "__main__":
    print("test_session_create...", end=" ")
    assert test_session_create()
    print("PASS")
    
    print("test_session_messages...", end=" ")
    assert test_session_messages()
    print("PASS")
    
    print("test_session_expiry...", end=" ")
    assert test_session_expiry()
    print("PASS")
    
    print("test_multiple_sessions...", end=" ")
    assert test_multiple_sessions()
    print("PASS")
    
    print("\n=== ALL SESSION TESTS PASSED ===")