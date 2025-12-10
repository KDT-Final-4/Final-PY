from __future__ import annotations

import httpx

from app import config, logs


def test_send_log_posts_payload_and_prints(capsys, monkeypatch):
    sent_payload = {}

    def mock_send(request: httpx.Request) -> httpx.Response:
        nonlocal sent_payload
        sent_payload = request.json()
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(mock_send)
    client = httpx.Client(transport=transport, base_url="https://log.example.com")

    monkeypatch.setenv(config.LOG_ENDPOINT_KEY, "https://log.example.com/ingest")

    response = logs.send_log(
        message="hello log",
        level="WARN",
        meta={"foo": "bar"},
        client=client,
        source="test-suite",
        timeout=1.5,
    )

    assert response.status_code == 200
    assert sent_payload["message"] == "hello log"
    assert sent_payload["level"] == "WARN"
    assert sent_payload["meta"] == {"foo": "bar"}
    assert sent_payload["source"] == "test-suite"
    assert "timestamp" in sent_payload

    captured = capsys.readouterr().out
    assert "[LOG][WARN] hello log" in captured
    assert "meta={'foo': 'bar'}" in captured
