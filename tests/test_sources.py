import base64
import json
import time
from pathlib import Path

import pytest

from dreamcore.sources import browser, calendar, files, gmail, photos
from dreamcore.sources.sync import SOURCES, list_sources, sync_source
from dreamcore.store import Store
from dreamcore.embed import HashEmbedder


def _b64(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


# ---------- gmail ----------

def _gmail_msg(subject="Lunch?", sender="Alice <alice@x.com>", body="thai place at 7?"):
    return {
        "id": "m1", "threadId": "t1", "internalDate": "1735689600000",
        "snippet": "thai place at 7?",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": sender},
                {"name": "To", "value": "me@x.com"},
            ],
            "parts": [
                {"mimeType": "text/plain", "body": {"data": _b64(body)}},
                {"mimeType": "text/html", "body": {"data": _b64("<p>thai place</p>")}},
            ],
        },
    }


def test_gmail_parse_message():
    d = gmail.parse_message(_gmail_msg())
    assert d.source == "gmail" and d.kind == "email"
    assert "Lunch" in d.title and d.sender.startswith("Alice")
    assert "thai place" in d.text and d.ts == pytest.approx(1735689600.0)
    assert d.metadata["thread_id"] == "t1"


def test_gmail_html_fallback_and_empty():
    msg = _gmail_msg()
    msg["payload"]["parts"] = [
        {"mimeType": "text/html", "body": {"data": _b64("<b>bold</b> html body")}}]
    d = gmail.parse_message(msg)
    assert "bold" in d.text and "<" not in d.text
    assert gmail.parse_message({"payload": {"headers": [], "parts": []}}) is None


# ---------- calendar ----------

def test_calendar_parse_event():
    ev = {
        "id": "e1", "summary": "Dentist",
        "start": {"dateTime": "2026-11-12T15:30:00-08:00"},
        "end": {"dateTime": "2026-11-12T16:00:00-08:00"},
        "location": "5th Ave clinic",
        "attendees": [{"email": "mom@x.com"}],
        "description": "bring insurance card",
    }
    d = calendar.parse_event(ev, "Family Cal")
    assert d.source == "calendar" and d.kind == "event"
    assert "Dentist" in d.title and "5th Ave" in d.text
    assert "mom@x.com" in d.text and d.ts is not None
    assert d.chat == "Family Cal"


def test_calendar_all_day_event():
    ev = {"id": "e2", "summary": "Mom birthday", "start": {"date": "2026-12-01"}}
    d = calendar.parse_event(ev)
    assert d is not None and d.ts is not None


# ---------- photos ----------

def test_photos_parse_media_item():
    item = {
        "id": "mi1",
        "mediaFile": {"filename": "IMG_2041.HEIC", "mimeType": "image/heic",
                      "description": "sunset at the pier"},
        "mediaMetadata": {"width": 4032, "height": 3024,
                          "creationTime": "2026-10-04T19:12:00Z"},
    }
    d = photos.parse_media_item(item)
    assert d.source == "photos" and d.kind == "photo"
    assert "IMG_2041" in d.title and "sunset" in d.text
    assert "4032x3024" in d.text and d.ts is not None


# ---------- browser ----------

def test_browser_parse_visit_filters():
    d = browser.parse_visit("https://example.com/a", "Example", 1735689600.0, 3, "chrome")
    assert d.source == "browser" and d.kind == "visit"
    assert "example.com" in d.text
    assert browser.parse_visit("chrome://settings", "", None, 1, "chrome") is None
    assert browser.parse_visit("about:blank", "", None, 1, "firefox") is None


def _make_chrome_history(tmp_path):
    import sqlite3
    db = tmp_path / "History"
    conn = sqlite3.connect(str(db))
    conn.execute("CREATE TABLE urls (url TEXT, title TEXT, last_visit_time INTEGER, visit_count INTEGER)")
    conn.execute("INSERT INTO urls VALUES (?,?,?,?)",
                 ("https://news.ycombinator.com", "Hacker News", 13300000000000000, 12))
    conn.execute("INSERT INTO urls VALUES (?,?,?,?)",
                 ("chrome://settings", "Settings", 13300000000000000, 1))
    conn.commit(); conn.close()
    return db


def test_browser_iter_chrome(tmp_path):
    db = _make_chrome_history(tmp_path)
    docs = list(browser._chrome_history(db))
    assert len(docs) == 2  # raw rows incl. chrome://
    d = browser.parse_visit(*docs[0], "chrome")
    assert d is not None and "Hacker News" in d.text


# ---------- files ----------

def test_files_iter(tmp_path):
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "ideas.md").write_text("# Ideas\nsecond brain for my chats", encoding="utf-8")
    (tmp_path / "data.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (tmp_path / "skip.bin").write_bytes(b"\x00\x01\x02binary")
    docs = list(files.iter_files(tmp_path))
    titles = [d.title for d in docs]
    assert any("ideas.md" in t for t in titles)
    assert any("data.csv" in t for t in titles)
    assert not any("skip.bin" in t for t in titles)
    assert all(d.source == "files" for d in docs)


def test_files_missing_dir(tmp_path):
    with pytest.raises(ValueError):
        list(files.iter_files(tmp_path / "nope"))


# ---------- sync registry ----------

def test_sources_registry():
    ids = {s["id"] for s in list_sources()}
    assert {"gmail", "calendar", "photos", "browser", "files"} <= ids
    for s in list_sources():
        assert s["factory"] if "factory" in s else True


def test_sync_files_into_store(tmp_path):
    (tmp_path / "a.txt").write_text("remember the wifi password is hunter2", encoding="utf-8")
    store = Store(tmp_path / "s.sqlite3")
    n = sync_source(store, HashEmbedder(), "files", {"path": str(tmp_path)})
    store.close()
    assert n >= 1
