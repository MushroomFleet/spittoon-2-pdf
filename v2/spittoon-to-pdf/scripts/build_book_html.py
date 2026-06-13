#!/usr/bin/env python3
"""
build_book_html.py — Assemble a single HTML book from parsed chapter JSONs + a
typography spec, ready to render with render_book.py (WeasyPrint).

Usage:
    python build_book_html.py \
        --output book.html \
        --spec spec.json \
        --book-title "My Book" \
        --book-subtitle "An optional subtitle" \
        --template /path/to/book-template.html \
        chapters/*.json

Body conversion (the block classifier) handles loose-draft realities:
  - paragraph-leading **LABEL**: / **Q11. NAME**:  -> small-caps speaker label
    (interview & epistolary formats). Bold never survives as bold.
  - in-body '## Section' / '### Section'           -> centred small-caps head
    (ALL-CAPS head text is case-normalised so small caps read; roman numerals kept)
  - '---' / '* * *' / '***' between paragraphs      -> em-spaced asterisk break,
    DROPPED when adjacent to a head or at a chapter edge (redundant)
  - draft trailers (**[To be continued...]**, *End of Chapter N*,
    *To be continued in Page N...*)                 -> stripped, counted
  - '**END**' / '*End of Book ...*'                  -> small-caps end mark
  - consecutive '**- ...**' lines                    -> right-aligned attribution
  - the first plain-prose paragraph of a chapter gets a small-caps lead-in
    (first N words); paragraphs after an end mark become closing quotes.

Small caps are realized by the spec's `smallcaps_font` (a dedicated SC sibling
family) via font-family switch — NOT the smcp OpenType feature, which Google's
css2 endpoint does not serve. See the template header for the rationale.
"""

import argparse
import html as html_module
import json
import re
import sys
from pathlib import Path

EM_SPACE = " "
ASTERISM = f"*{EM_SPACE}*{EM_SPACE}*"
ROMAN = re.compile(r"^[IVXLCDM]+$")

SPEAKER = re.compile(r"^\*\*([A-Z][^*]*?)\*\*\s*:\s*")
TRAILER = re.compile(
    r"^(\*\*\[To be continued[^\]]*\]\*\*"
    r"|\*End of (?:Chapter|Page) \d+\*"
    r"|\*To be continued in Page \d+\.{0,3}\*)$")
END_MARK = re.compile(r"^\*\*END\*\*$|^\*End of Book[^*]*\*$")
ATTRIB = re.compile(r"^\*\*-\s*(.+?)\*\*$")


def normalise_head(text: str) -> str:
    """Lowercase ALL-CAPS heads so small-cap glyphs render; keep roman numerals;
    re-capitalise the word after a colon."""
    if text != text.upper():
        return text
    words = []
    for w in text.split(" "):
        core = re.sub(r"[^A-Za-z]", "", w)
        if core and ROMAN.fullmatch(core):
            words.append(w)
        else:
            words.append(w.capitalize())
    out = " ".join(words)
    out = re.sub(r"(:\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), out)
    return out


def inline_md(text: str) -> str:
    """Escape + inline emphasis. **bold** -> <strong> (styled italic, never bold)."""
    t = html_module.escape(text, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
    t = re.sub(r"(?<![\w])_(.+?)_(?![\w])", r"<em>\1</em>", t)
    t = re.sub(r"\s*\n\s*", " ", t)
    return t


def convert_body(body: str, lead_in_words: int):
    """Return (html, leadin_applied, trailers_stripped, rules_dropped)."""
    blocks = [b.strip() for b in re.split(r"\n\s*\n", body.replace("\r\n", "\n")) if b.strip()]

    kinds = []
    for b in blocks:
        if re.fullmatch(r"-{3,}|\*\s*\*\s*\*|#\s*#\s*#", b):
            kinds.append("rule")
        elif b.startswith("## ") or b.startswith("### "):
            kinds.append("head")
        elif TRAILER.fullmatch(b):
            kinds.append("trailer")
        elif END_MARK.fullmatch(b):
            kinds.append("end")
        elif all(ATTRIB.fullmatch(ln.strip()) for ln in b.split("\n")):
            kinds.append("attrib")
        else:
            kinds.append("para")

    trailers = sum(1 for k in kinds if k == "trailer")
    keep = [(b, k) for b, k in zip(blocks, kinds) if k != "trailer"]

    out = []
    para_count = 0
    leadin_applied = False
    rules_dropped = 0
    after_end = False
    for idx, (b, k) in enumerate(keep):
        if k == "rule":
            prev_k = keep[idx - 1][1] if idx > 0 else None
            next_k = keep[idx + 1][1] if idx + 1 < len(keep) else None
            if prev_k == "para" and next_k == "para":
                out.append(f'<div class="scene-break">{ASTERISM}</div>')
            else:
                rules_dropped += 1
            continue
        if k == "head":
            text = b.lstrip("#").strip()
            out.append(f'<div class="section-head">{inline_md(normalise_head(text))}</div>')
            continue
        if k == "end":
            label = re.sub(r"^\*+|\*+$", "", b).strip()
            out.append(f'<div class="end-mark">{html_module.escape(label)}</div>')
            after_end = True
            continue
        if k == "attrib":
            spans = []
            for ln in b.split("\n"):
                m = ATTRIB.fullmatch(ln.strip())
                spans.append("— " + inline_md(m.group(1)))
            out.append('<div class="closing-attribution">' + "<br>".join(spans) + "</div>")
            continue

        # paragraph
        raw = b
        speaker_html = ""
        m = SPEAKER.match(raw)
        if m:
            label = m.group(1)
            if label == label.upper():
                label = label.title()
            speaker_html = f'<span class="speaker">{html_module.escape(label)}:</span> '
            raw = raw[m.end():]
        p_html = speaker_html + inline_md(raw)
        cls = []
        if para_count == 0:
            cls.append("opener")
            plain = not m and not b.startswith("*")
            if plain and lead_in_words > 0:
                words = p_html.split(" ")
                if len(words) > lead_in_words:
                    p_html = ('<span class="smallcaps">' + " ".join(words[:lead_in_words])
                              + "</span> " + " ".join(words[lead_in_words:]))
                    leadin_applied = True
        if after_end:
            cls.append("closing-quote")
        cls_attr = f' class="{" ".join(cls)}"' if cls else ""
        out.append(f"<p{cls_attr}>{p_html}</p>")
        para_count += 1

    return "\n".join(out), leadin_applied, trailers, rules_dropped


def font_import(*families) -> str:
    """Build a single Google Fonts css2 @import covering the given families,
    each with roman 400 + italic 400 (where the family offers italic)."""
    parts = []
    for fam in families:
        if not fam:
            continue
        name = fam.replace(" ", "+")
        parts.append(f"family={name}:ital,wght@0,400;1,400")
    url = "https://fonts.googleapis.com/css2?" + "&".join(parts) + "&display=swap"
    # Wrap in its own <style>: a bare @import in <head> (outside any stylesheet)
    # is ignored; @import must also be the first rule in its stylesheet.
    return f"<style>@import url('{url}');</style>"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--book-title", required=True)
    ap.add_argument("--book-subtitle", default="")
    ap.add_argument("--template", default=None)
    ap.add_argument("inputs", nargs="+", help="Parsed chapter JSON files in order")
    args = ap.parse_args()

    template_path = Path(args.template) if args.template else (
        Path(__file__).parent.parent / "assets" / "book-template.html")
    template = template_path.read_text(encoding="utf-8")
    spec = json.loads(Path(args.spec).read_text(encoding="utf-8"))

    body_font = spec.get("body", {}).get("font", "Alegreya")
    smallcaps_font = spec.get("smallcaps_font", "Alegreya SC")
    heading_font = spec.get("heading", {}).get("font", smallcaps_font)
    lead_in_words = spec.get("chapter_opener", {}).get("small_caps_first_words", 5)

    chapters = []
    for inp in args.inputs:
        chapters.append(json.loads(Path(inp).read_text(encoding="utf-8")))
    for i, ch in enumerate(chapters, 1):
        if ch.get("number") is None:
            ch["number"] = i

    blocks_html = []
    for idx, ch in enumerate(chapters):
        grp = "grp-a" if idx % 2 == 0 else "grp-b"
        body_html, leadin, trailers, dropped = convert_body(ch.get("body", ""), lead_in_words)
        label = ch.get("designation") or f"Chapter {ch['number']}"
        subtitle = ch.get("dateline")
        title = ch.get("title", "")
        title_cls = "chapter-title has-subtitle" if subtitle else "chapter-title"
        sec = [f'<section class="chapter {grp}">',
               f'  <div class="chapter-number">{html_module.escape(label)}</div>',
               f'  <h2 class="{title_cls}">{html_module.escape(title)}</h2>']
        if subtitle:
            sec.append(f'  <div class="chapter-subtitle">{html_module.escape(subtitle)}</div>')
        if ch.get("epigraph"):
            sec.append(f'  <div class="epigraph">{html_module.escape(ch["epigraph"])}</div>')
        sec.append('  <div class="chapter-body">')
        sec.append(body_html)
        sec.append("  </div>\n</section>")
        blocks_html.append("\n".join(sec))
        if trailers or dropped:
            print(f"  ch{ch['number']}: {trailers} trailer(s) stripped, "
                  f"{dropped} redundant rule(s) dropped, lead-in={'yes' if leadin else 'no'}")

    vars_ = {
        "book_title": html_module.escape(args.book_title),
        "book_subtitle": html_module.escape(args.book_subtitle),
        "font_import": font_import(body_font, smallcaps_font, heading_font
                                   if heading_font not in (body_font, smallcaps_font) else None),
        "trim_width": spec.get("trim", {}).get("width", "148mm"),
        "trim_height": spec.get("trim", {}).get("height", "210mm"),
        "margin_top": spec.get("margins", {}).get("top", "18mm"),
        "margin_bottom": spec.get("margins", {}).get("bottom", "36mm"),
        "margin_inner": spec.get("margins", {}).get("inner", "12mm"),
        "margin_outer": spec.get("margins", {}).get("outer", "24mm"),
        "body_font": body_font,
        "smallcaps_font": smallcaps_font,
        "body_size": spec.get("body", {}).get("size", "10.5pt"),
        "body_leading": spec.get("body", {}).get("leading", "14pt"),
        "chapters_html": "\n\n".join(blocks_html),
    }
    out = template
    for k, v in vars_.items():
        out = out.replace("{{ " + k + " }}", str(v))

    Path(args.output).write_text(out, encoding="utf-8")
    print(f"Wrote {args.output}: {len(chapters)} chapters")


if __name__ == "__main__":
    main()
