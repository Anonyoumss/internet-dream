"""Google Calendar adapter — indexes events as Documents.

Yields one Document per event (meetings, reminders, birthdays). Uses
calendar.readonly scope. `sync` accepts a window: past_days / future_days.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Iterator

from ..store import Document
from . import google_auth


def _parse_dt(value) -> float | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def parse_event(ev: dict, calendar_name: str = "calendar") -> Document | None:
    """Pure parser — testable without network."""
    summary = ev.get("summary") or "(no title)"
    start = ev.get("start") or {}
    end = ev.get("end") or {}
    ts = _parse_dt(start.get("dateTime") or start.get("date"))
    location = ev.get("location") or ""
    desc = (ev.get("description") or "")[:2000]
    attendees = ", ".join(
        a.get("email", "") for a in (ev.get("attendees") or [])[:10])
    text_parts = [f"Event: {summary}"]
    if location:
        text_parts.append(f"Location: {location}")
    if attendees:
        text_parts.append(f"Attendees: {attendees}")
    if desc:
        text_parts.append(f"Notes: {desc}")
    if not text_parts[0]:
        return None
    return Document(
        source="calendar",
        kind="event",
        title=f"📅 {summary[:80]}",
        text="\n".join(text_parts),
        sender="google-calendar",
        chat=calendar_name,
        ts=ts,
        metadata={
            "event_id": ev.get("id", ""),
            "html_link": ev.get("htmlLink", ""),
            "status": ev.get("status", ""),
        },
    )


def iter_events(calendar_id: str = "primary",
                past_days: int = 365, future_days: int = 365,
                max_results: int = 2500) -> Iterator[Document]:
    from googleapiclient.discovery import build

    creds = google_auth.credentials()
    service = build("calendar", "v3", credentials=creds,
                    cache_discovery=False)
    now = datetime.now(timezone.utc)
    time_min = (now - timedelta(days=past_days)).isoformat()
    time_max = (now + timedelta(days=future_days)).isoformat()

    page_token = None
    fetched = 0
    cal_name = calendar_id
    try:
        cal = service.calendars().get(calendarId=calendar_id).execute()
        cal_name = cal.get("summary") or calendar_id
    except Exception:
        pass

    while fetched < max_results:
        resp = service.events().list(
            calendarId=calendar_id, timeMin=time_min, timeMax=time_max,
            maxResults=min(250, max_results - fetched),
            singleEvents=True, orderBy="startTime",
            pageToken=page_token).execute()
        for ev in resp.get("items", []):
            doc = parse_event(ev, cal_name)
            if doc:
                yield doc
            fetched += 1
            if fetched >= max_results:
                break
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
