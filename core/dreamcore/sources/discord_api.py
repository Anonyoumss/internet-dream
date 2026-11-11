"""Discord source — read-only export of your own account's messages.

Uses a user token you provide yourself (saved at
~/.internet-dream/discord_token.txt or discord_token in config.json).
Only GET requests are made; nothing is ever sent to Discord.

Covers guild text channels + announcement channels. DM channels are
skipped by default (set include_dms=true to include them).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterator

import httpx

from ..store import Document

API = "https://discord.com/api/v10"
_TOKEN_FILE = Path.home() / ".internet-dream" / "discord_token.txt"

# channel types we index: GUILD_TEXT(0), GUILD_ANNOUNCEMENT(5),
# GUILD_FORUM(15) is skipped (threads need separate calls), DM(1) optional
_TEXT_TYPES = {0, 5}
_DM_TYPE = 1


def load_token() -> str | None:
    if _TOKEN_FILE.exists():
        tok = _TOKEN_FILE.read_text().strip()
        if tok:
            return tok
    try:
        cfg = json.loads(
            (Path.home() / ".internet-dream" / "config.json").read_text())
        return cfg.get("discord_token")
    except Exception:
        return None


class _Client:
    def __init__(self, token: str):
        self.http = httpx.Client(
            base_url=API,
            headers={"Authorization": token,
                     "User-Agent": "DiscordBot (internet-dream, 1.0)"},
            timeout=30.0)

    def get(self, path: str, **params):
        for attempt in range(4):
            r = self.http.get(path, params=params)
            if r.status_code == 429:
                retry = float(r.headers.get("Retry-After", 1.0))
                time.sleep(min(retry + 0.25, 10.0))
                continue
            if r.status_code == 401:
                raise PermissionError(
                    "Discord token rejected (401) — regenerate it")
            r.raise_for_status()
            return r.json()
        r.raise_for_status()
        return r.json()

    def close(self):
        self.http.close()


def _msg_to_doc(channel_label: str, guild_name: str,
                msg: dict) -> Document | None:
    content = (msg.get("content") or "").strip()
    attachments = msg.get("attachments") or []
    embeds = msg.get("embeds") or []
    att_txt = " ".join(
        f"[attachment: {a.get('filename') or a.get('url', '')}]"
        for a in attachments)
    emb_txt = " ".join(
        (e.get("title") or "") + " " + (e.get("description") or "")
        for e in embeds).strip()
    text = "\n".join(t for t in (content, att_txt, emb_txt) if t).strip()
    if not text:
        return None
    author = ((msg.get("author") or {}).get("global_name")
              or (msg.get("author") or {}).get("username") or "unknown")
    ts = None
    if msg.get("timestamp"):
        try:
            from datetime import datetime
            ts = datetime.fromisoformat(
                msg["timestamp"].replace("Z", "+00:00")).timestamp()
        except ValueError:
            pass
    chat = f"{guild_name} / #{channel_label}" if guild_name else f"#{channel_label}"
    return Document(
        source="discord",
        kind="message",
        title=f"{chat} · {author}",
        text=text,
        sender=author,
        chat=chat,
        ts=ts,
        metadata={"message_id": msg.get("id", ""),
                  "channel_id": msg.get("channel_id", "")},
    )


def _iter_channel_messages(cli: _Client, channel_id: str,
                           channel_label: str, guild_name: str,
                           max_per_channel: int) -> Iterator[Document]:
    before = None
    fetched = 0
    while fetched < max_per_channel:
        params = {"limit": min(100, max_per_channel - fetched)}
        if before:
            params["before"] = before
        try:
            msgs = cli.get(f"/channels/{channel_id}/messages", **params)
        except httpx.HTTPStatusError:
            break  # no access / deleted channel — skip
        if not msgs:
            break
        for msg in reversed(msgs):  # API returns newest-first
            doc = _msg_to_doc(channel_label, guild_name, msg)
            if doc:
                yield doc
            fetched += 1
            if fetched >= max_per_channel:
                break
        if len(msgs) < 100:
            break
        before = msgs[-1]["id"]
        time.sleep(0.35)  # stay well under rate limits


def iter_discord(opts: dict) -> Iterator[Document]:
    """Yield Documents from Discord via the REST API (read-only)."""
    token = load_token()
    if not token:
        raise RuntimeError(
            "No Discord token — save it to ~/.internet-dream/discord_token.txt")
    max_per_channel = int(opts.get("max_per_channel", 500))
    include_dms = bool(opts.get("include_dms", False))
    guild_filter = opts.get("guild")  # optional substring filter

    cli = _Client(token)
    try:
        guilds = cli.get("/users/@me/guilds")
        for g in guilds:
            if guild_filter and guild_filter.lower() not in (g.get("name") or "").lower():
                continue
            guild_name = g.get("name") or "DMs"
            try:
                channels = cli.get(f"/guilds/{g['id']}/channels")
            except httpx.HTTPStatusError:
                continue
            for ch in channels:
                if ch.get("type") not in _TEXT_TYPES:
                    continue
                if not ch.get("permissions") and ch.get("guild_id"):
                    pass  # permission check happens implicitly per-request
                yield from _iter_channel_messages(
                    cli, ch["id"], ch.get("name") or "channel",
                    guild_name, max_per_channel)
        if include_dms:
            dms = cli.get("/users/@me/channels")
            for ch in dms:
                if ch.get("type") != _DM_TYPE:
                    continue
                recipient = (ch.get("recipients") or [{}])[0]
                label = recipient.get("global_name") or recipient.get("username") or "dm"
                yield from _iter_channel_messages(
                    cli, ch["id"], label, "", max_per_channel)
    finally:
        cli.close()
