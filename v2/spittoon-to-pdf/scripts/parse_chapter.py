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
      "designation": "Prologue" | "Chapter One" | null,   # H2 directly under the H1
      "dateline": "Journey Year 127.3.01 — ..." | null,    # H3 directly under that
      "number": 1,            # from --number, else number_hint, else null
      "number_hint": 1,       # parsed from "# Chapter N:" / "# Page N:" (0-based pages -> +1)
      "word_count": 4523,
      "dash_conversions": 12, # spaced-hyphen -> em-dash compositor pass count
      "format": "markdown" | "plaintext" | "docx" | "html"
    }

Designed to be called in parallel for many chapters (independent file I/O).
ALWAYS reads and writes UTF-8 — never rely on the platform default (cp1252 on
Windows produces mojibake downstream).
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROMAN = re.compile(r"^[IVXLCDM]+$")


def em_dash_pass(text: str):
    """Compositor's dash pass: ' -- ' then ' - ' (spaced) -> ' — '. Returns
    (converted_text, count). Requires a space on each side so hyphenated
    compounds (well-known) are never touched."""
    n = 0
    text, c = re.subn(r"(?<=\S) -- (?=\S)", " — ", text)
    n += c
    text, c = re.subn(r"(?<=\S) - (?=\S)", " — ", text)
    n += c
    return text, n


def extract_structured_headers(lines):
    """Detect a structured opener:
        line 1: '# Chapter N: Title'  or  '# Page N: Title'  or  '# Title'
        line 2: '## Designation'      (Prologue / Chapter One / Book One - X ...)
        line 3: '### Dateline'
    Markdown '#' prefixes are optional (plain .txt files in the wild use them).
    Returns dict with keys number_hint, title, designation, dateline, body_start.
    Any field may be None; body_start is the index where prose begins.
    """
    out = {"number_hint": None, "title": None, "designation": None,
           "dateline": None, "body_start": 0}
    i = 0
    n = len(lines)
    # skip leading blanks
    while i < n and not lines[i].strip():
        i += 1
    if i >= n:
        return out

    # H1 / title line
    first = lines[i].strip()
    h1 = first[2:].strip() if first.startswith("# ") else (first if not first.startswith("#") else None)
    if h1 is not None:
        m = re.match(r"(?:Chapter|Page)\s+(\d+)\s*:\s*(.+)", h1)
        if m:
            num = int(m.group(1))
            # "Page 0".."Page N" are 0-based -> chapters 1..N+1
            out["number_hint"] = num + 1 if h1.lower().startswith("page") else num
            out["title"] = m.group(2).strip()
        else:
            out["title"] = h1
        i += 1
        out["body_start"] = i
    else:
        return out

    # optional H2 designation
    while i < n and not lines[i].strip():
        i += 1
    if i < n and lines[i].strip().startswith("## "):
        desig = lines[i].strip()[3:].strip()
        # strip a leading "<Series>: Book <word>" prefix (with or without a
        # '-'/':' separator) so e.g. "THREEX: Book One - Prologue" and
        # "THREEX: Book One Conclusion" both reduce to the designation word(s).
        desig = re.sub(r"^.*?Book\s+\w+\s*[-:]?\s*", "", desig).strip() or desig
        out["designation"] = desig
        i += 1
        out["body_start"] = i
        # optional H3 dateline
        while i < n and not lines[i].strip():
            i += 1
        if i < n and lines[i].strip().startswith("### "):
            out["dateline"] = lines[i].strip()[4:].strip()
            i += 1
            out["body_start"] = i
    return out


def parse_markdown(text: str) -> dict:
    """Parse a markdown chapter. Structured headers first; else first H1 is
    title; a leading blockquote is the epigraph."""
    lines = text.replace("\r\n", "\n").split("\n")
    hdr = extract_structured_headers(lines)
    title = hdr["title"]
    body_start = hdr["body_start"]
    epigraph = None

    if title is None:
        # fall back to first H1
        for i, line in enumerate(lines):
            if line.startswith("# ") and title is None:
                title = line[2:].strip()
                body_start = i + 1
                break

    while body_start < len(lines) and not lines[body_start].strip():
        body_start += 1

    if body_start < len(lines) and lines[body_start].lstrip().startswith(">"):
        epi_lines = []
        while body_start < len(lines) and lines[body_start].lstrip().startswith(">"):
            epi_lines.append(lines[body_start].lstrip(">").strip())
            body_start += 1
        epigraph = " ".join(l for l in epi_lines if l)
        while body_start < len(lines) and not lines[body_start].strip():
            body_start += 1

    body = "\n".join(lines[body_start:]).strip()
    return {"title": title, "body": body, "epigraph": epigraph,
            "designation": hdr["designation"], "dateline": hdr["dateline"],
            "number_hint": hdr["number_hint"], "format": "markdown"}


def parse_plaintext(text: str) -> dict:
    """Parse plain text. Recognises markdown-style structured headers (common in
    .txt drafts); else first non-empty line is the title."""
    lines = text.replace("\r\n", "\n").split("\n")
    hdr = extract_structured_headers(lines)
    if hdr["title"] is not None:
        body = "\n".join(lines[hdr["body_start"]:]).strip()
        return {"title": hdr["title"], "body": body, "epigraph": None,
                "designation": hdr["designation"], "dateline": hdr["dateline"],
                "number_hint": hdr["number_hint"], "format": "plaintext"}
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
    return {"title": title, "body": body, "epigraph": None,
            "designation": None, "dateline": None, "number_hint": None,
            "format": "plaintext"}


def parse_docx(path: str) -> dict:
    try:
        import docx  # type: ignore
    except ImportError:
        print("python-docx is required to parse .docx files. Install with:", file=sys.stderr)
        print("  pip install python-docx", file=sys.stderr)
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
    return {"title": title, "body": body, "epigraph": None,
            "designation": None, "dateline": None, "number_hint": None,
            "format": "docx"}


def parse_html(text: str) -> dict:
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except ImportError:
        title_match = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else None
        body = re.sub(r"<[^>]+>", "", text).strip()
        return {"title": title, "body": body, "epigraph": None,
                "designation": None, "dateline": None, "number_hint": None,
                "format": "html"}
    soup = BeautifulSoup(text, "html.parser")
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else None
    epigraph = None
    if h1:
        nxt = h1.find_next_sibling()
        while nxt and nxt.name in ("br",):
            nxt = nxt.find_next_sibling()
        if nxt and nxt.name == "blockquote":
            epigraph = nxt.get_text(strip=True)
            nxt.decompose()
        h1.decompose()
    body = soup.get_text("\n").strip()
    return {"title": title, "body": body, "epigraph": epigraph,
            "designation": None, "dateline": None, "number_hint": None,
            "format": "html"}


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
        result = parse_markdown(path.read_text(encoding="utf-8"))
    elif suffix == ".txt":
        result = parse_plaintext(path.read_text(encoding="utf-8"))
    elif suffix == ".docx":
        result = parse_docx(str(path))
    elif suffix in (".html", ".htm"):
        result = parse_html(path.read_text(encoding="utf-8"))
    else:
        result = parse_plaintext(path.read_text(encoding="utf-8", errors="replace"))

    if not result["title"]:
        result["title"] = path.stem.replace("_", " ").replace("-", " ").title()

    # Compositor's em-dash pass on body + dateline.
    result["body"], dashes = em_dash_pass(result["body"])
    if result.get("dateline"):
        result["dateline"], _ = em_dash_pass(result["dateline"])
    result["dash_conversions"] = dashes

    result["word_count"] = len(result["body"].split())
    result["number"] = args.number if args.number is not None else result.get("number_hint")
    result["source_file"] = str(path)

    Path(args.output).write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Parsed {path.name}: '{result['title']}'"
          f"{' / ' + result['designation'] if result.get('designation') else ''}"
          f" ({result['word_count']} words, {dashes} dash conversions)")


if __name__ == "__main__":
    main()
