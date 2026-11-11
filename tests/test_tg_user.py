"""Tests for the Telethon userbot message mapper (no network)."""

import time
from datetime import datetime, timezone
from types import SimpleNamespace

from dreamcore import tg_user


def _msg(text="hello", sender_name="Sam Lee", chat_title="Family",
         media=None, ts=1735689600):
    sender = SimpleNamespace(first_name="Sam", last_name="Lee",
                             username="samlee")
    chat = SimpleNamespace(title=chat_title)
    return SimpleNamespace(
        raw_text=text, message=text, media=media, sender=sender,
        chat=chat, date=datetime.fromtimestamp(ts, tz=timezone.utc))


def test_message_to_document_text():
    d = tg_user.message_to_document(_msg("dinner at 7?"))
    assert d.source == "telegram-account" and d.kind == "message"
    assert "dinner" in d.text and d.sender == "Sam Lee"
    assert d.chat == "Family" and d.ts == 1735689600.0


def test_message_to_document_media_only():
    media = SimpleNamespace(__class__=SimpleNamespace(__name__="MessageMediaPhoto"))
    d = tg_user.message_to_document(_msg(text="", media=media))
    assert d is not None and "attachment" in d.text


def test_message_to_document_empty():
    assert tg_user.message_to_document(_msg(text="", media=None)) is None


def test_message_to_document_defaults():
    msg = SimpleNamespace(raw_text="x", message="x", media=None,
                          sender=None, chat=None, date=None)
    d = tg_user.message_to_document(msg, default_chat="Saved Messages")
    assert d.sender == "unknown" and d.chat == "Saved Messages" and d.ts is None
