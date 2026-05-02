# design.md conventions

A `design.md` is a free-form note from the user describing typography and layout intent. Don't impose a fixed schema. Instead, scan it for the following kinds of information and map them into the typography spec.

## What to look for

The user might write any of these in any phrasing. Examples follow each.

**Trim size / page size**
- "6 by 9 inches", "trade paperback size", "B-format", "letter size", "A5"
- Map to a width × height in inches or mm. Common sizes:
  - 6×9 in (US trade paperback)
  - 5×8 in (mass market US)
  - 5.5×8.5 in (digest US)
  - 148×210 mm (A5 — common UK and European trade)
  - 129×198 mm (B-format UK paperback)
  - 178×111 mm (A-format UK pulp paperback)

**Margins**
- "generous margins", "wide gutter for binding", "0.75 inch all around"
- Convert to top/bottom/inner/outer in inches or mm. The inner margin (gutter) should be larger than the outer margin for any perfect-bound book — the inner edge disappears into the spine. If only "generous" or "tight" is given, pick sensible defaults: generous = 1in/1in/1.125in/0.875in; tight = 0.5in/0.5in/0.625in/0.5in.
- For A5 specifically, a good default is top 15mm / bottom 18mm / inner 18mm / outer 14mm.

**Body font**
- "Garamond", "I want it to feel like a Penguin Classic", "use Crimson Pro"
- If a specific name is given, prefer it. If a vibe is given, choose a freely loadable Google Font that fits:
  - Penguin Classic → EB Garamond
  - Vintage → Cormorant
  - Modernist → Source Serif Pro
  - Literary → Crimson Pro
  - Clean academic → Charter (or its open clone, Charis SIL)
- If the user gives a font URL, fetch it and embed via `@font-face`.

**Body size and leading**
- "11 on 15", "11pt with generous leading", "small body"
- "11 on 15" means 11pt size, 15pt leading. Defaults:
  - 11/15 for novels at 6×9
  - 10.5/14 for A5 (denser characters per line)
  - 10/14 for tighter mass-market
  - 12/17 for large print

**Chapter opener style**
- "drop cap", "small caps first line", "ornament above chapter title", "chapter starts on recto"
- Drop cap: 3-line by default. Small-caps first line: usually first 2-7 words. Recto-only chapter starts: use `page-break-before: right` (this is the default — chapter openers should always be recto unless the user explicitly turns it off).

**Running heads**
- "book title on left, chapter title on right", "no running heads", "just page numbers"
- Map to `@page` rules with `string-set` and `string()`. If no preference is given, default to verso=book title, recto=chapter title, both in small caps centred.

**Page numbers**
- "bottom center", "outer corner", "no page numbers on chapter openers"
- Use `@page` margin boxes and the `counter(page)` CSS counter. Default: bottom outer corner, suppressed on chapter-opener pages and on blank verso pages.

**Drop caps**
- "drop cap on every chapter", "no drop caps"
- Default: drop cap on chapter openers only, 3-line, in the heading font.

**Pull quotes / epigraphs**
- "epigraphs italicized", "pull quotes in the outer margin"
- Default for epigraphs: italic, indented from both sides, with attribution in small caps roman below.

**Section breaks**
- "use ornaments between scenes", "blank line is enough", "three asterisks"
- Default: centred `* * *`. Other common choices: a small ornament glyph (❦, §, ※), a thin centred rule, or simply extra vertical space.

## Free-form is fine

If the user's `design.md` is just one paragraph saying "make it look like a nice literary novel with chapter openers", that's enough — interpret it as the literary defaults: EB Garamond 11/15, 6×9 trim, drop cap chapter openers, running heads with book title verso and chapter title recto, page numbers bottom outer.

## What to do if design.md asks for something unsupported

Most CSS-expressible typography is achievable in the HTML→PDF render path. Things that *aren't* easily achievable: complex hanging punctuation, optical margin alignment, fine kerning controls, true small caps if the chosen font lacks a small-caps variant, true book ligatures beyond what the OpenType layout features expose. If `design.md` asks for any of these, do your best within CSS and note the limitation in the build notes.

## Encoding the spec

Internally, after parsing `design.md`, build a small spec object you can carry through the run and pass to `build_book_html.py`:

```json
{
  "trim": {"width": "148mm", "height": "210mm"},
  "margins": {"top": "15mm", "bottom": "18mm", "inner": "18mm", "outer": "14mm"},
  "body": {"font": "EB Garamond", "size": "10.5pt", "leading": "14pt"},
  "heading": {"font": "Cormorant Garamond"},
  "chapter_opener": {"drop_cap_lines": 3, "small_caps_first_words": 5, "start_on_recto": true},
  "running_heads": {"verso": "book_title", "recto": "chapter_title"},
  "page_numbers": {"position": "bottom-outer", "suppress_on_opener": true},
  "scene_break": {"style": "asterism", "glyph": "* * *"},
  "fonts_to_fetch": ["https://..."]
}
```

This spec then drives the CSS in the rendered HTML.
