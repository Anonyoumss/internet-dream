"""Scheduled agent jobs — the 'works while you sleep' layer.

Jobs are stored in ~/.internet-dream/jobs.json:
  [{"id","prompt","interval_seconds","last_run","enabled"}]

A background asyncio task inside `dream serve` checks every 30s and
runs due jobs through the agent loop. Jobs can themselves call
sync_source/remember — so a daily job can keep memory fresh and even
write daily recaps.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Any

JOBS_FILE = Path.home() / ".internet-dream" / "jobs.json"
CHECK_EVERY = 30  # seconds


def _load() -> list[dict]:
    try:
        return json.loads(JOBS_FILE.read_text())
    except Exception:
        return []


def _save(jobs: list[dict]) -> None:
    JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    JOBS_FILE.write_text(json.dumps(jobs, indent=2))
    try:
        JOBS_FILE.chmod(0o600)
    except OSError:
        pass


def list_jobs() -> list[dict]:
    return _load()


def add_job(prompt: str, interval_seconds: int = 3600,
            enabled: bool = True) -> dict:
    jobs = _load()
    job = {
        "id": uuid.uuid4().hex[:8],
        "prompt": prompt,
        "interval_seconds": max(60, int(interval_seconds)),
        "last_run": 0,
        "enabled": enabled,
        "created": time.time(),
    }
    jobs.append(job)
    _save(jobs)
    return job


def remove_job(job_id: str) -> bool:
    jobs = _load()
    new = [j for j in jobs if j["id"] != job_id]
    if len(new) == len(jobs):
        return False
    _save(new)
    return True


def update_job(job_id: str, **fields) -> bool:
    jobs = _load()
    for j in jobs:
        if j["id"] == job_id:
            for k in ("prompt", "interval_seconds", "enabled"):
                if k in fields:
                    j[k] = fields[k]
            _save(jobs)
            return True
    return False


async def scheduler_loop(store, embedder, log=None) -> None:
    """Runs forever inside the FastAPI process. Never raises."""
    while True:
        try:
            now = time.time()
            jobs = _load()
            dirty = False
            for job in jobs:
                if not job.get("enabled", True):
                    continue
                due = now - float(job.get("last_run", 0)) >= float(
                    job.get("interval_seconds", 3600))
                if not due:
                    continue
                job["last_run"] = now
                dirty = True
                try:
                    from .agent import run_agent
                    result = await asyncio.to_thread(
                        run_agent, store, embedder,
                        [{"role": "user", "content": job["prompt"]}])
                    if log:
                        log(f"job {job['id']} done: "
                            f"{str(result.get('answer',''))[:120]}")
                except Exception as e:
                    if log:
                        log(f"job {job['id']} failed: {e}")
            if dirty:
                _save(jobs)
        except Exception as e:
            if log:
                log(f"scheduler error: {e}")
        await asyncio.sleep(CHECK_EVERY)
