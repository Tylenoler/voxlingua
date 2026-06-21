"""Server API + WebSocket integration tests."""

import sys; sys.path.insert(0, ".")
from server import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_rest_endpoints():
    endpoints = ["/api/status", "/api/voices", "/api/scenes"]
    for path in endpoints:
        r = client.get(path)
        assert r.status_code == 200, f"GET {path} -> {r.status_code}"
    print(f"  PASS: {len(endpoints)} REST endpoints OK")

def test_websocket():
    with client.websocket_connect("/ws/mobile") as ws:
        ws.send_json({"type": "handshake", "payload": {}})
        
        # Read all available messages (testclient may delay them)
        import time; time.sleep(0.5)
        ws.send_json({"type": "set_scene", "payload": {"scene": "restaurant"}})
        ws.send_json({"type": "set_correction_mode", "payload": {"mode": "all", "interrupt_on_severe": True}})
        ws.send_json({"type": "set_voice", "payload": {"voice_profile_id": "new_york"}})
        
        # Read responses (may be shifted by testclient async behavior)
        types_seen = set()
        for _ in range(5):
            try:
                msg = ws.receive_json()
                types_seen.add(msg["type"])
            except Exception:
                break
        
        assert "handshake_ack" in types_seen
        assert "scene_updated" in types_seen
        assert "correction_mode_updated" in types_seen
        assert "voice_updated" in types_seen
        print(f"  PASS: WebSocket - all message types received: {types_seen}")


if __name__ == "__main__":
    test_rest_endpoints()
    test_websocket()
    print("\n=== ALL SERVER TESTS PASSED ===")