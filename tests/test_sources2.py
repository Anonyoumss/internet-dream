import time
from pathlib import Path

import pytest

from dreamcore.sources import drive, telegram, youtube


# ---------- telegram ----------

def _tg_update(text="hello dream", uid=1):
    return {"update_id": uid, "message": {
        "message_id": uid, "date": 1735689600,
        "chat": {"id": 42, "type": "private", "first_name": "Sam"},
        "from": {"id": 7, "first_name": "Sam", "last_name": "Lee"},
        "text": text}}


def test_telegram_parse_text():
    d = telegram.parse_update(_tg_update("remember the gate code"))
    assert d.source == "telegram" and d.kind == "text"
    assert "gate code" in d.text and d.sender == "Sam Lee"
    assert d.chat == "Sam Lee" and d.ts == 1735689600.0


def test_telegram_parse_photo_and_doc():
    u = _tg_update()
    u["message"].pop("text")
    u["message"]["photo"] = [{"file_id": "s", "width": 90, "height": 90},
                            {"file_id": "b", "width": 1280, "height": 720}]
    d = telegram.parse_update(u)
    assert d.kind == "photo" and "1280" in d.text
    u["message"]["document"] = {"file_id": "f", "file_name": "notes.pdf",
                                "file_size": 12345}
    d = telegram.parse_update(u)
    assert d.kind == "document" and "notes.pdf" in d.text


def test_telegram_parse_ignores_service():
    assert telegram.parse_update({"update_id": 9}) is None
    assert telegram.parse_update({"update_id": 9, "message": {"chat": {}}}) is None


def test_telegram_group_chat_name():
    u = _tg_update()
    u["message"]["chat"] = {"id": 1, "type": "group", "title": "Dream Team"}
    d = telegram.parse_update(u)
    assert d.chat == "Dream Team"


# ---------- youtube takeout ----------

_TAKEOUT_HTML = """<html><body>
<div class="content-cell">
  <a href="https://www.youtube.com/watch?v=abc123" class="paper-material">Great Lo-Fi Mix</a>
  <div class="meta"><ul>
    <li><a href="https://www.youtube.com/channel/UCxyz">Lofi Girl</a></li>
    <li>Watched on 4 October 2026, 19:12</li>
  </ul></div>
</div>
<div class="content-cell">
  <a href="https://www.youtube.com/watch?v=def456">Second Video &amp; More</a>
  <div class="meta"><ul><li>Watched on 5 October 2026, 20:00</li></ul></div>
</div>
</body></html>"""


def test_youtube_parse_html(tmp_path):
    f = tmp_path / "watch-history.html"
    f.write_text(_TAKEOUT_HTML, encoding="utf-8")
    docs = youtube.parse_watch_history_html(f)
    assert len(docs) == 2
    assert "Great Lo-Fi" in docs[0].title and "Lofi Girl" in docs[0].text
    assert "youtube.com/watch?v=abc123" in docs[0].text
    assert docs[0].source == "youtube" and docs[0].kind == "watch"
    assert "Second Video" in docs[1].title  # html entity decoded


def test_youtube_parse_json(tmp_path):
    f = tmp_path / "activity.json"
    f.write_text('[{"title":"My Video","titleUrl":"https://youtu.be/x",'
                 '"time":"2026-10-04T19:12:00.000Z","header":"YouTube"}]',
                 encoding="utf-8")
    docs = youtube.parse_takeout_json(f)
    assert len(docs) == 1 and docs[0].ts is not None


def test_youtube_needs_path(tmp_path):
    from dreamcore.sources.sync import sync_source
    from dreamcore.store import Store
    from dreamcore.embed import HashEmbedder
    store = Store(tmp_path / "s.db")
    with pytest.raises(ValueError):
        list(youtube.iter_youtube({}))
    store.close()


# ---------- drive ----------

def test_drive_parse_meta():
    f = {"id": "f1", "name": "Q3 Report.docx",
         "mimeType": "application/vnd.google-apps.document",
         "modifiedTime": "2026-10-01T12:00:00.000Z", "size": "12345",
         "webViewLink": "https://drive.google.com/x",
         "owners": [{"displayName": "Sam"}]}
    d = drive.parse_file_meta(f)
    assert d.source == "drive" and "Q3 Report" in d.title
    assert "Sam" in d.text and "12345" in d.text
    assert d.metadata["file_id"] == "f1"


# ---------- discord api ----------

def test_discord_msg_to_doc():
    from dreamcore.sources import discord_api
    msg = {
        "id": "123", "channel_id": "c1",
        "content": "hello world",
        "timestamp": "2026-10-01T12:00:00.000Z",
        "author": {"username": "sam", "global_name": "Sam"},
        "attachments": [{"filename": "pic.png", "url": "https://x/pic.png"}],
        "embeds": [],
    }
    d = discord_api._msg_to_doc("general", "MyGuild", msg)
    assert d.source == "discord" and d.sender == "Sam"
    assert "hello world" in d.text and "pic.png" in d.text
    assert "MyGuild / #general" in d.chat
    assert d.ts is not None


def test_discord_msg_empty_skipped():
    from dreamcore.sources import discord_api
    assert discord_api._msg_to_doc("c", "g", {"content": "  "}) is None


def test_discord_source_registered():
    from dreamcore.sources.sync import SOURCES
    assert "discord" in SOURCES
    assert SOURCES["discord"]["requires_google_auth"] is False


# ---------- whatsapp folder source + agent ----------

def test_whatsapp_source_registered():
    from dreamcore.sources.sync import SOURCES
    assert "whatsapp" in SOURCES
    assert SOURCES["whatsapp"]["requires_google_auth"] is False


def test_agent_dispatch_remember(tmp_path):
    from dreamcore.store import Store
    from dreamcore.embed import HashEmbedder
    from dreamcore import agent
    store = Store(tmp_path / "a.db")
    emb = HashEmbedder()
    out = agent._tool_remember(store, emb, {"title": "t", "text": "hello"})
    assert "Saved" in out
    hits = store.hybrid_search("hello", emb.embed("hello"), 3)
    assert hits and "hello" in hits[0].snippet
    store.close()


# ---------- research / agent tools ----------

def test_parse_json_array_robust():
    from dreamcore.research import _parse_json_array
    assert _parse_json_array('["a","b"]') == ["a", "b"]
    assert _parse_json_array('```json\n["x","y"]\n```') == ["x", "y"]
    out = _parse_json_array('Here you go:\n- query one\n- query two')
    assert "query one" in out


def test_strip_html():
    from dreamcore.agent import _strip_html
    assert "hello" in _strip_html("<p>hello <b>world</b></p><script>x()</script>")
    assert "x()" not in _strip_html("<p>hi</p><script>x()</script>")


def test_store_delete(tmp_path):
    from dreamcore.store import Store, Document
    store = Store(tmp_path / "d.db")
    did = store.add(Document(source="t", kind="note", title="x", text="bye"), None)
    assert store.count() == 1
    assert store.delete(did) is True
    assert store.count() == 0
    store.close()
