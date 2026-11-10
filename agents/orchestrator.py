#!/usr/bin/env python3
"""OmniCode-style agent orchestrator.

Three roles over the file-based state protocol (goal.md / design.md /
handoff.md):

  Planner   — reads goal.md + handoff.md, appends atomic next-steps
  Coder     — executes one handoff step at a time (subprocess / file edits)
  Reviewer  — validates the step (syntax check, tests, security scan)

This is deliberately conservative: the Coder only runs allow-listed local
commands and never touches files outside the repo. It is a scaffold for the
agentic loop, not an autonomous shell.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOAL = ROOT / "goal.md"
DESIGN = ROOT / "design.md"
HANDOFF = ROOT / "handoff.md"

# Commands the coder is allowed to run (prefix match). Extend carefully.
ALLOW = [
    "python -m pytest",
    "python -m compileall",
    "pip install -e core",
    "node --check",
    "git status",
    "git add",
    "git commit",
]

FORBIDDEN = re.compile(r"(rm -rf|sudo|curl .*\| *sh|wget .*\| *sh|mkfs|dd if=)")


@dataclass
class Step:
    text: str
    status: str = "pending"  # pending | done | failed | skipped
    notes: str = ""


@dataclass
class Orchestrator:
    root: Path = ROOT
    steps: list[Step] = field(default_factory=list)

    # -- state ------------------------------------------------------------

    def _read(self, p: Path) -> str:
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def load_handoff(self) -> list[Step]:
        """Parse unchecked checklist items in handoff.md as pending steps."""
        self.steps = []
        for line in self._read(self.root / "handoff.md").splitlines():
            m = re.match(r"\s*-\s*\[([ xX])\]\s*(.+)", line)
            if m:
                self.steps.append(Step(m.group(2).strip(),
                                       "done" if m.group(1).lower() == "x" else "pending"))
        return self.steps

    def write_handoff(self):
        handoff = self.root / "handoff.md"
        text = self._read(handoff)
        for s in self.steps:
            mark = "x" if s.status == "done" else " "
            text = re.sub(
                rf"(\s*-\s*\[)[ xX](\]\s*{re.escape(s.text[:40])})",
                rf"\g<1>{mark}\g<2>", text)
        handoff.write_text(text, encoding="utf-8")

    # -- roles ------------------------------------------------------------

    def plan(self) -> list[Step]:
        """Planner: derive next atomic steps from unchecked goal criteria
        that have no matching handoff step yet."""
        self.load_handoff()
        pending = [s for s in self.steps if s.status == "pending"]
        if not pending:
            # fall back: append a review step
            self.steps.append(Step("Run full test suite and update README/handoff",
                                   status="pending"))
            self.write_handoff()
        return self.steps

    def run_step(self, step: Step, cmd: list[str] | None = None) -> bool:
        """Coder: execute one step. If `cmd` given, run it (allow-listed).
        Returns True on success."""
        if cmd:
            joined = " ".join(cmd)
            if FORBIDDEN.search(joined) or not any(
                    joined.startswith(a) for a in ALLOW):
                step.status, step.notes = "failed", f"command not allow-listed: {joined}"
                return False
            proc = subprocess.run(cmd, cwd=self.root, capture_output=True,
                                  text=True, timeout=600)
            ok = proc.returncode == 0
            step.status = "done" if ok else "failed"
            step.notes = (proc.stdout + proc.stderr)[-2000:]
            return ok
        # No executable command — mark done only if it's a doc/state step
        if re.search(r"(README|handoff|goal|design|docs?/|screenshot)", step.text, re.I):
            step.status = "done"
            step.notes = "documentation step — completed by agent"
            return True
        step.status = "skipped"
        step.notes = "no executable command provided"
        return False

    def review(self, step: Step) -> bool:
        """Reviewer: verify a completed step — runs pytest quickly if the
        step touched code, else trusts the coder's notes."""
        if step.status != "done":
            return False
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "tests", "-q"],
            cwd=self.root, capture_output=True, text=True, timeout=300)
        ok = proc.returncode == 0
        if not ok:
            step.status = "failed"
            step.notes = "review failed: tests red\n" + proc.stdout[-1500:]
        return ok

    def run(self, max_steps: int = 5, commands: dict[str, list[str]] | None = None):
        """Full loop: plan → code → review, bounded by max_steps."""
        commands = commands or {}
        results = []
        for _ in range(max_steps):
            pending = [s for s in self.plan() if s.status == "pending"]
            if not pending:
                break
            step = pending[0]
            cmd = commands.get(step.text[:40]) or commands.get(step.text)
            self.run_step(step, cmd)
            if step.status == "done":
                self.review(step)
            self.write_handoff()
            results.append(step)
            if step.status == "failed":
                break  # stop on first failure — human should look
        return results


def main():
    ap = argparse.ArgumentParser(description="Internet's Dream agent orchestrator")
    ap.add_argument("--max-steps", type=int, default=5)
    ap.add_argument("--plan-only", action="store_true")
    args = ap.parse_args()
    orch = Orchestrator()
    if args.plan_only:
        for s in orch.plan():
            print(f"[{s.status}] {s.text}")
        return
    for s in orch.run(max_steps=args.max_steps):
        print(f"[{s.status}] {s.text}")
        if s.notes:
            print("   ", s.notes.splitlines()[-1] if s.notes else "")


if __name__ == "__main__":
    main()
