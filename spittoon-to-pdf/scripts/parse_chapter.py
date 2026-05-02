#!/usr/bin/env python3
"""
parse_chapter.py — Normalize a chapter file (.md, .txt, .docx, .html) into JSON.

Usage:
    python parse_chapter.py <input_file> <output_json> [--number N]

Output JSON shape:
    {
      "title": "The First Chapter",
      "body": "Plain text or markdown body...",
      "epigraph": "An optional pull-quote..." or null,
      "number": 1,
      "word_count": 4523,
      "format": "markdown" | "plaintext" | "docx" | "html"
    }

Designed to be called in parallel for many chapters (independent file I/O).
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


def parse_markdown(text: str) -> dict:
    """Parse a markdown chapter. First H1 is title; leading blockquote is epigraph."""
    lines = text.split("\n")
    title = None
    body_start = 0
    epigraph = None

    # Find first H1
    for i, line in enumerate(lines):
        if line.startswith("# ") and title is None:
            title = line[2:].strip()
            body_start = i + 1
            break

    # Skip blank lines after title
    while body_start < len(lines) and not lines[body_start].strip():
        body_start += 1

    # Check for an opening blockquote = epigraph
    if body_start < len(lines) and lines[body_start].startswith("> "):
        epi_lines = []
        while body_start < len(lines) and (
            lines[body_start].startswith("> ") or lines[body_start].startswith(">")
        ):
            epi_lines.append(lines[body_start].lstrip(">").strip())
            body_start += 1
        epigraph = " ".join(l for l in epi_lines if l)
        # Skip blank lines after epigraph
        while body_start < len(lines) and not lines[body_start].strip():
            body_start += 1

    body = "\n".join(lines[body_start:]).strip()

    return {"title": title, "body": body, "epigraph": epigraph, "format": "markdown"}


def parse_plaintext(text: str) -> dict:
    """Parse plain text. First non-empty line is title, rest is body."""
    lines = text.split("\n")
    title = None
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip():
            title = line.strip()
            body_start = i + 1
            break
    while body_start < len(lines) and not lines[body_start].strip():
        body_start += 1
    body = "\n".join(lines[body_start:]).strip()
    return {"title": title, "body": body, "epigraph": None, "format": "plaintext"}


def parse_docx(path: str) -> dict:
    """Parse a .docx file using python-docx."""
    try:
        import docx  # type: ignore
    except ImportError:
        print("python-docx is required to parse .docx files. Install with:", file=sys.stderr)
        print("  pip install --break-system-packages python-docx", file=sys.stderr)
        sys.exit(2)

    doc = docx.Document(path)
    paragraphs = [p.text for p in doc.paragraphs]
    title = None
    body_start = 0
    for i, para in enumerate(paragraphs):
        if para.strip():
            title = para.strip()
            body_start = i + 1
            break
    while body_start < len(paragraphs) and not paragraphs[body_start].strip():
        body_start += 1
    body = "\n\n".join(p for p in paragraphs[body_start:] if p.strip())
    return {"title": title, "body": body, "epigraph": None, "format": "docx"}


def parse_html(text: str) -> dict:
    """Parse HTML. First <h1> is title, first <blockquote> before <p> is epigraph."""
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError:
        # Fall back to crude regex
        title_match = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else None
        body = re.sub(r"<[^>]+>", "", text).strip()
        return {"title": title, "body": body, "epigraph": None, "format": "html"}

    soup = BeautifulSoup(text, "html.parser")
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else None

    epigraph = None
    if h1:
        # Check if a blockquote follows the h1 before any <p>
        next_el = h1.find_next_sibling()
        while next_el and next_el.name in ("br",):
            next_el = next_el.find_next_sibling()
        if next_el and next_el.name == "blockquote":
            epigraph = next_el.get_text(strip=True)
            next_el.decompose()
        h1.decompose()

    body = soup.get_text("\n").strip()
    return {"title": title, "body": body, "epigraph": epigraph, "format": "html"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Path to chapter file")
    ap.add_argument("output", help="Path to output JSON")
    ap.add_argument("--number", type=int, default=None, help="Chapter number (1-based)")
    args = ap.parse_args()

    path = Path(args.input)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    suffix = path.suffix.lower()
    if suffix in (".md", ".markdown"):
        text = path.read_text(encoding="utf-8")
        result = parse_markdown(text)
    elif suffix == ".txt":
        text = path.read_text(encoding="utf-8")
        result = parse_plaintext(text)
    elif suffix == ".docx":
        result = parse_docx(str(path))
    elif suffix in (".html", ".htm"):
        text = path.read_text(encoding="utf-8")
        result = parse_html(text)
    else:
        # Treat as plaintext
        text = path.read_text(encoding="utf-8", errors="replace")
        result = parse_plaintext(text)

    # Fall back to filename stem if no title found
    if not result["title"]:
        result["title"] = path.stem.replace("_", " ").replace("-", " ").title()

    result["word_count"] = len(result["body"].split())
    result["number"] = args.number
    result["source_file"] = str(path)

    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"Parsed {path.name}: '{result['title']}' ({result['word_count']} words)")


if __name__ == "__main__":
    main()
