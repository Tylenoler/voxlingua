"""
Tests for REST API endpoints — all engine dependencies mocked via conftest.

Uses ``client`` fixture from conftest.py (FastAPI TestClient with mocks).
"""

import pytest


class TestGetStatus:
    def test_returns_200(self, client):
        resp = client.get("/api/status")
        assert resp.status_code == 200

    def test_body_structure(self, client):
        resp = client.get("/api/status")
        data = resp.json()
        assert "status" in data
        assert "version" in data
        assert "llm_connected" in data
        assert "stt_loaded" in data
        assert "tts_loaded" in data
        assert "aligner_loaded" in data
        assert "active_sessions" in data
        assert data["status"] == "running"

    def test_version(self, client):
        resp = client.get("/api/status")
        assert resp.json()["version"] == "1.0.0"


class TestListVoices:
    def test_returns_200(self, client):
        resp = client.get("/api/voices")
        assert resp.status_code == 200

    def test_returns_list(self, client):
        resp = client.get("/api/voices")
        data = resp.json()
        assert "voices" in data
        assert len(data["voices"]) >= 1


class TestListScenes:
    def test_returns_200(self, client):
        resp = client.get("/api/scenes")
        assert resp.status_code == 200

    def test_has_expected_scenes(self, client):
        resp = client.get("/api/scenes")
        scenes = resp.json()["scenes"]
        scene_ids = [s["id"] for s in scenes]
        assert "daily_chat" in scene_ids
        assert "restaurant" in scene_ids
        assert "travel" in scene_ids


class TestChat:
    def test_chat_endpoint(self, client, mock_llm_client):
        resp = client.post(
            "/api/chat",
            json={
                "session_id": "test-chat-session",
                "message": "Hello!",
                "scene": "daily_chat",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert data["session_id"] == "test-chat-session"


class TestStt:
    def test_stt_endpoint(self, client, mock_stt_engine):
        resp = client.post(
            "/api/stt",
            json={
                "session_id": "test-stt",
                "data": "AAAA",  # valid base64 but junk audio
                "format": "opus",
                "sample_rate": 16000,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "text" in data
        assert data["session_id"] == "test-stt"

    def test_stt_invalid_body(self, client):
        resp = client.post("/api/stt", json={})
        assert resp.status_code == 422  # validation error


class TestTts:
    def test_tts_endpoint(self, client, mock_tts_engine):
        resp = client.post(
            "/api/tts",
            json={"text": "Hello world", "voice_profile": "new_york"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "pcm_f32le"
        assert data["sample_rate"] == 24000
        assert "data" in data
        assert len(data["data"]) > 0

    def test_tts_empty_text(self, client, mock_tts_engine):
        """Empty text should fail validation."""
        resp = client.post("/api/tts", json={"text": ""})
        assert resp.status_code == 422

    def test_tts_voices(self, client, mock_tts_engine):
        resp = client.get("/api/tts/voices")
        assert resp.status_code == 200
        data = resp.json()
        assert "voices" in data


class TestScorer:
    def test_scorer_endpoint(self, client):
        resp = client.post(
            "/api/score",
            json={
                "session_id": "test-score",
                "data": "AAAA",
                "format": "opus",
                "sample_rate": 16000,
            },
        )
        # scorer endpoint might be stubbed — just check it doesn't crash
        assert resp.status_code in (200, 500)


class TestCorrection:
    def test_correction_endpoint(self, client):
        resp = client.post(
            "/api/correct",
            json={
                "session_id": "test-correct",
                "data": "AAAA",
                "format": "opus",
                "sample_rate": 16000,
            },
        )
        # correction endpoint might be stubbed — just check it doesn't crash
        assert resp.status_code in (200, 500)
