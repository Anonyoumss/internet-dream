import json
import time
from pathlib import Path

import pytest

from dreamcore.crypto import get_or_create_key
from dreamcore.embed import HashEmbedder
from dreamcore.ingest.discord import parse_discord_export
from dreamcore.ingest.whatsapp import parse_whatsapp_export
from dreamcore.store import Document, Store


@pytest.fixture()
def store(tmp_path, monkeypatch):
    # isolate key material per-test
    monkeypatch.setenv("HOME", str(tmp_path))
    s = Store(tmp_path / "mem.sqlite3")
    yield s
    s.close()


def test_crypto_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    aes = get_or_create_key("correct horse")
    nonce = b"0" * 12
    ct = aes.encrypt(nonce, b"secret memory", b"doc1")
    assert aes.decrypt(nonce, ct, b"doc1") == b"secret memory"


def test_store_add_search(store):
    emb = HashEmbedder()
    docs = [
        Document(source="whatsapp", kind="message",
                 title="Family · Alice", text="let's meet at Luigi's pizza on Friday",
                 sender="Alice", chat="Family", ts=time.time()),
        Document(source="whatsapp", kind="message",
                 title="Work · Bob", text="the deploy pipeline is green again",
                 sender="Bob", chat="Work", ts=time.time()),
    ]
    store.add_many((d, emb.embed(d.title + "\n" + d.text)) for d in docs)
    assert store.count() == 2
    hits = store.hybrid_search("pizza restaurant friday", emb.embed("pizza restaurant friday"), 5)
    assert hits and hits[0].title == "Family · Alice"
    assert "Luigi" in hits[0].snippet or "pizza" in hits[0].snippet.lower()


def test_encrypted_payload_not_plaintext(store):
    import sqlite3
    store.add(Document(source="x", kind="note", title="t", text="super secret text"))
    raw = store._conn.execute("SELECT payload FROM documents").fetchone()[0]
    assert b"super secret text" not in raw


def test_stats_and_graph(store):
    emb = HashEmbedder()
    for i in range(3):
        d = Document(source="discord", kind="message", title="#general · Sam",
                     text=f"hello world {i}", sender="Sam", chat="#general",
                     ts=time.time())
        store.add(d, emb.embed(d.text))
    st = store.stats()
    assert st["total"] == 3 and st["by_source"]["discord"] == 3
    g = store.graph()
    assert g["nodes"] and g["edges"]


def test_whatsapp_parser(tmp_path):
    chat = tmp_path / "_chat.txt"
    chat.write_text(
        "[12/01/24, 10:15:32 AM] Alice: hey are we still on for lunch?\n"
        "[12/01/24, 10:16:01 AM] Bob: yes! Luigi's at noon\n"
        "this message has a\n"
        "continuation line\n"
        "[12/01/24, 10:17:00 AM] Alice: awesome see you there\n"
        "[12/01/24, 10:18:00 AM] Bob: Alice added Carol\n",
        encoding="utf-8",
    )
    docs = parse_whatsapp_export(chat, chat_name="Lunch Crew")
    assert len(docs) == 3  # system line skipped
    assert docs[1].text.endswith("continuation line")
    assert docs[0].sender == "Alice" and docs[0].chat == "Lunch Crew"
    assert docs[0].ts is not None


def test_discord_parser(tmp_path):
    f = tmp_path / "general.json"
    f.write_text(json.dumps({
        "channel": {"name": "general"},
        "messages": [
            {"id": "1", "timestamp": "2024-12-01T10:15:32.000Z",
             "content": "deploy finished", "author": {"name": "sam"},
             "attachments": []},
            {"id": "2", "timestamp": "2024-12-01T10:16:00.000Z",
             "content": "", "author": {"name": "sam"},
             "attachments": [{"fileName": "screenshot.png"}]},
        ],
    }), encoding="utf-8")
    docs = parse_discord_export(f)
    assert len(docs) == 2
    assert docs[0].sender == "sam" and docs[0].chat == "#general"
    assert "attachment" in docs[1].text


def test_hybrid_dedup(store):
    emb = HashEmbedder()
    d = Document(source="x", kind="note", title="unique zebra token",
                 text="the quick brown fox jumps", ts=time.time())
    store.add(d, emb.embed(d.title + "\n" + d.text))
    hits = store.hybrid_search("zebra", emb.embed("zebra"), 10)
    assert len(hits) == 1


def test_api_health_and_search(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from fastapi.testclient import TestClient
    from dreamcore.api import create_app
    client = TestClient(create_app(db_path=tmp_path / "api.sqlite3"))
    assert client.get("/health").json()["ok"] is True
    r = client.post("/ingest-text", json={
        "title": "Dinner rec", "text": "try the ramen place on 5th",
        "sender": "maya", "chat": "friends"})
    assert r.status_code == 200
    hits = client.get("/search", params={"q": "ramen"}).json()
    assert hits and "ramen" in hits[0]["snippet"].lower()
    g = client.get("/graph").json()
    assert g["nodes"]
