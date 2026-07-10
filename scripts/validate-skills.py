#!/usr/bin/env python3
"""Validate every skill's YAML frontmatter.

A malformed `SKILL.md` frontmatter is invisible locally — agent harnesses tend to
read it with a lenient regex and load the skill anyway — but a strict YAML parser
rejects it, which breaks GitHub's rendering and any consumer that parses properly.
The failure this guards against, seen in practice: an unquoted description
containing a colon followed by a space.

    description: ... even if the user never says "glass": filling in a form ...
                                                        ^ plain scalars cannot hold ": "

Exits non-zero and prints every problem it finds.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

# A skill's name is its directory name, lowercase kebab-case by the Agent Skills convention.
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)


def check(skill_md: Path) -> list[str]:
    """Return a list of problems with this SKILL.md (empty if it is well-formed)."""
    rel = skill_md.relative_to(Path.cwd()) if skill_md.is_absolute() else skill_md
    text = skill_md.read_text(encoding="utf-8")

    m = FRONTMATTER_RE.match(text)
    if not m:
        return [f"{rel}: no YAML frontmatter — the file must start with a '---' delimited block"]

    try:
        meta = yaml.safe_load(m.group("body"))
    except yaml.YAMLError as e:
        # yaml's message already carries line/column; keep it on one line.
        detail = " ".join(str(e).split())
        return [f"{rel}: frontmatter is not valid YAML — {detail}"]

    problems: list[str] = []
    if not isinstance(meta, dict):
        return [f"{rel}: frontmatter must be a mapping, got {type(meta).__name__}"]

    for field in ("name", "description"):
        value = meta.get(field)
        if not isinstance(value, str) or not value.strip():
            problems.append(f"{rel}: '{field}' is missing or empty")

    name = meta.get("name")
    if isinstance(name, str):
        if not NAME_RE.match(name):
            problems.append(f"{rel}: name {name!r} is not lowercase kebab-case")
        if name != skill_md.parent.name:
            problems.append(
                f"{rel}: name {name!r} does not match its directory {skill_md.parent.name!r}"
            )

    return problems


def main() -> int:
    skills = sorted(Path("skills").glob("*/SKILL.md"))
    if not skills:
        print("error: no skills/*/SKILL.md found", file=sys.stderr)
        return 1

    problems = [p for skill in skills for p in check(skill)]
    for p in problems:
        print(f"error: {p}", file=sys.stderr)

    if problems:
        print(f"\n{len(problems)} problem(s) across {len(skills)} skill(s)", file=sys.stderr)
        return 1

    print(f"ok: {len(skills)} skill(s) have valid frontmatter")
    return 0


if __name__ == "__main__":
    sys.exit(main())
