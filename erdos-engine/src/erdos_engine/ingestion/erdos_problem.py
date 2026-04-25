"""Import Erdős problems from erdosproblems.com pages."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

import requests


def _strip_tags(text: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def import_erdos_problem(number: int, data_dir: Path) -> str:
    """Fetch problem page and materialize local problem fixture.

    Returns local problem id, e.g. ``erdos_004``.
    """
    url = f"https://www.erdosproblems.com/{number}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    page = resp.text

    content_match = re.search(r'<div id="content">([\s\S]*?)</div>', page)
    if not content_match:
        raise RuntimeError(f"Could not parse statement content from {url}")
    statement = _strip_tags(content_match.group(1))

    status_match = re.search(
        r'<span class="tooltip">\s*([A-Z ()]+)\s*<span class="tooltiptext">\s*([\s\S]*?)</span>',
        page,
    )
    status_raw = (status_match.group(1).strip().lower() if status_match else "open")
    status = "solved" if status_raw in {"proved", "solved", "disproved", "proved (lean)", "disproved (lean)"} else "open"

    tags_block = re.search(r'<div id="tags">([\s\S]*?)</div>', page)
    tags: list[str] = []
    if tags_block:
        tags = [
            _strip_tags(match)
            for match in re.findall(r"<a [^>]*>([\s\S]*?)</a>", tags_block.group(1))
            if _strip_tags(match)
        ]

    additional_block = re.search(
        r'<div class="problem-additional-text"[^>]*>([\s\S]*?)<p style="text-align: center; font-family: \'Courier New\'',
        page,
    )
    known_solution = _strip_tags(additional_block.group(1)) if additional_block else ""

    problem_id = f"erdos_{number:03d}"
    pdir = data_dir / "problems" / problem_id
    pdir.mkdir(parents=True, exist_ok=True)

    title = f"Erdos Problem #{number}"
    metadata = {
        "id": problem_id,
        "title": title,
        "status": status,
        "tags": tags,
        "known_solution_path": "known_solution.md" if known_solution else None,
        "source_url": url,
        "difficulty_guess": "unknown",
        "computationally_testable": True,
        "formalizable": True,
    }

    (pdir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (pdir / "statement.md").write_text(statement.strip() + "\n", encoding="utf-8")
    if known_solution:
        (pdir / "known_solution.md").write_text(known_solution.strip() + "\n", encoding="utf-8")

    return problem_id
