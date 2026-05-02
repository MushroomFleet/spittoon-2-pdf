#!/usr/bin/env python3
"""
build_book_html.py — Assemble a single HTML book from parsed chapters + spec.

Usage:
    python build_book_html.py \
        --output book.html \
        --spec spec.json \
        --book-title "My Book" \
        --author "Some Author" \
        chapters/*.json

The spec.json is the typography spec described in references/design-md-conventions.md.
This script substitutes the spec values into the bundled book-template.html.
"""

import argparse
import html as html_module
import json
import re
import sys
from pathlib import Path


def md_to_html(text: str) -> str:
    """Minimal markdown-to-HTML for body text. Handles paragraphs, em, strong, scene breaks."""
    text = text.replace("\r\n", "\n")
    paragraphs = re.split(r"\n\s*\n", text.strip())
    out = []
    for i, p in enumerate(paragraphs):
        p_stripped = p.strip()
        # Scene breaks
        if re.fullmatch(r"\*\s*\*\s*\*|---+|#\s*#\s*#", p_stripped):
            out.append('<div class="scene-break">* * *</div>')
            continue
        # Inline emphasis
        p_html = html_module.escape(p_stripped)
        p_html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p_html)
        p_html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", p_html)
        p_html = re.sub(r"_(.+?)_", r"<em>\1</em>", p_html)
        # Replace single newlines inside a paragraph with spaces
        p_html = re.sub(r"\s*\n\s*", " ", p_html)
        # The first paragraph of each chapter gets the .opener class
        # (caller wraps the first paragraph with smallcaps if desired)
        cls = ' class="opener"' if i == 0 else ""
        out.append(f"<p{cls}>{p_html}</p>")
    return "\n".join(out)


def add_smallcaps_to_first_words(html: str, n_words: int) -> str:
    """Wrap the first n words of the first <p class="opener"> in <span class="smallcaps">."""
    if n_words <= 0:
        return html

    def replacer(match):
        full_p = match.group(0)
        # Find the first letter (drop cap) and skip it
        # Then wrap the next n_words in smallcaps
        # Simple approach: split the inner text on whitespace
        inner_match = re.match(r'(<p class="opener">)(.*?)(</p>)', full_p, re.DOTALL)
        if not inner_match:
            return full_p
        open_tag, inner, close_tag = inner_match.groups()
        # Skip the first character (it's the drop cap), then wrap next n_words
        if not inner:
            return full_p
        first_char = inner[0]
        rest = inner[1:]
        words = rest.split(" ", n_words)
        if len(words) <= n_words:
            return full_p
        wrapped = " ".join(words[:n_words])
        remainder = words[n_words]
        return f'{open_tag}{first_char}<span class="smallcaps">{wrapped}</span> {remainder}{close_tag}'

    return re.sub(
        r'<p class="opener">.*?</p>',
        replacer,
        html,
        count=1,
        flags=re.DOTALL,
    )


def render_template(template: str, spec: dict, chapters: list, book_title: str, author: str) -> str:
    """Tiny template engine — just enough for our needs (no jinja2 dep)."""
    # Variable substitutions
    vars_ = {
        "book_title": book_title,
        "author": author or "",
        "trim_width": spec.get("trim", {}).get("width", "6in"),
        "trim_height": spec.get("trim", {}).get("height", "9in"),
        "margin_top": spec.get("margins", {}).get("top", "0.75in"),
        "margin_bottom": spec.get("margins", {}).get("bottom", "0.75in"),
        "margin_inner": spec.get("margins", {}).get("inner", "0.875in"),
        "margin_outer": spec.get("margins", {}).get("outer", "0.625in"),
        "body_font": spec.get("body", {}).get("font", "EB Garamond"),
        "body_size": spec.get("body", {}).get("size", "11pt"),
        "body_leading": spec.get("body", {}).get("leading", "15pt"),
        "heading_font": spec.get("heading", {}).get("font", "Cormorant Garamond"),
    }

    out = template
    for k, v in vars_.items():
        out = out.replace("{{ " + k + " }}", str(v))

    # Author conditional
    if author:
        out = re.sub(r"{%\s*if author\s*%}(.*?){%\s*endif\s*%}", r"\1", out, flags=re.DOTALL)
    else:
        out = re.sub(r"{%\s*if author\s*%}.*?{%\s*endif\s*%}", "", out, flags=re.DOTALL)

    # Chapters loop
    chapter_match = re.search(
        r"{%\s*for chapter in chapters\s*%}(.*?){%\s*endfor\s*%}", out, re.DOTALL
    )
    if chapter_match:
        chapter_template = chapter_match.group(1)
        smallcaps_n = spec.get("chapter_opener", {}).get("small_caps_first_words", 0)
        chapter_blocks = []
        for ch in chapters:
            body_html = md_to_html(ch.get("body", ""))
            if smallcaps_n:
                body_html = add_smallcaps_to_first_words(body_html, smallcaps_n)
            block = chapter_template
            block = block.replace("{{ chapter.number }}", str(ch.get("number", "")))
            block = block.replace("{{ chapter.title }}", html_module.escape(ch.get("title", "")))
            # Epigraph conditional
            if ch.get("epigraph"):
                block = re.sub(
                    r"{%\s*if chapter\.epigraph\s*%}(.*?){%\s*endif\s*%}",
                    r"\1",
                    block,
                    flags=re.DOTALL,
                )
                block = block.replace(
                    "{{ chapter.epigraph }}", html_module.escape(ch["epigraph"])
                )
            else:
                block = re.sub(
                    r"{%\s*if chapter\.epigraph\s*%}.*?{%\s*endif\s*%}",
                    "",
                    block,
                    flags=re.DOTALL,
                )
            block = block.replace("{{ chapter.body_html | safe }}", body_html)
            chapter_blocks.append(block)
        out = (
            out[: chapter_match.start()]
            + "\n".join(chapter_blocks)
            + out[chapter_match.end() :]
        )

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--spec", required=True, help="Typography spec JSON path")
    ap.add_argument("--book-title", required=True)
    ap.add_argument("--author", default="")
    ap.add_argument("--template", default=None, help="Override path to book-template.html")
    ap.add_argument("inputs", nargs="+", help="Parsed chapter JSON files in order")
    args = ap.parse_args()

    template_path = Path(args.template) if args.template else (
        Path(__file__).parent.parent / "assets" / "book-template.html"
    )
    if not template_path.exists():
        print(f"Template not found: {template_path}", file=sys.stderr)
        sys.exit(1)

    template = template_path.read_text(encoding="utf-8")

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)

    chapters = []
    for inp in args.inputs:
        with open(inp, encoding="utf-8") as f:
            chapters.append(json.load(f))
    for i, ch in enumerate(chapters, 1):
        if ch.get("number") is None:
            ch["number"] = i

    out = render_template(template, spec, chapters, args.book_title, args.author)
    Path(args.output).write_text(out, encoding="utf-8")
    print(f"Wrote {args.output}: {len(chapters)} chapters")


if __name__ == "__main__":
    main()
