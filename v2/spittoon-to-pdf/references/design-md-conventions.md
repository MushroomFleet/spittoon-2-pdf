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
- **If the project supplies a canonical `design.md` (e.g. a Tschichold-canon spec), its margins win verbatim.** The 15mm / 18mm / 18mm / 14mm A5 numbers below are a fallback for spec-less A5 runs *only* — they do not override a canon spec, which on this project is the Tschichold construction (≈ top 18 / bottom 36 / inner 12 / outer 24).
- For a spec-less A5 run, a reasonable fallback is top 15mm / bottom 18mm / inner 18mm / outer 14mm.

**Body font**
- "Garamond", "I want it to feel like a Penguin Classic", "use Crimson Pro"
- If a specific name is given, prefer it. If a vibe is given, choose a freely loadable Google Font that fits:
  - Literary / default → **Alegreya** (humanist literary serif, true italics, ships **Alegreya SC** for small caps, defaults to old-style figures)
  - Penguin Classic → EB Garamond
  - Vintage → Cormorant
  - Modernist → Source Serif 4
  - Literary alt → Crimson Pro
  - Clean academic → Charter (or its open clone, Charis SIL)
- **Small-caps caveat (load-bearing).** Google's css2 endpoint strips OpenType features (`smcp`, `onum`) from every served subset, so `font-variant-caps: small-caps` is a silent no-op and WeasyPrint will not synthesize small caps. Small caps are realized by switching to a dedicated small-caps **sibling family** (e.g. `Alegreya SC`). So whenever you pick a body face, also set `smallcaps_font` to its real SC sibling. Faces *without* an SC sibling on Google Fonts (EB Garamond, Crimson Pro, Cormorant Garamond) will render every small-caps context — chapter numbers, running heads, speaker labels, lead-ins — as plain mixed case unless you fall back to italic labels and disclose it. **Alegreya + Alegreya SC is the proven combo and the default.**
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
- **Drop caps are not implemented.** The float `::first-letter` route crashes WeasyPrint and several house specs forbid them; a request for a drop cap **degrades to the small-caps lead-in** (first few words in the SC sibling family) and is disclosed. Small-caps lead-in: usually first 2–7 words (default 5). Recto-only chapter starts: use `page-break-before: right` (this is the default — chapter openers, including chapter 1, should always be recto unless the user explicitly turns it off).

**Running heads**
- "book title on left, chapter title on right", "no running heads", "just page numbers"
- Map to `@page` rules with `string-set` and `string()`. If no preference is given, default to verso=book title, recto=chapter title, both in small caps centred.

**Page numbers**
- "bottom center", "outer corner", "no page numbers on chapter openers"
- Use `@page` margin boxes and the `counter(page)` CSS counter. Default: bottom outer corner, suppressed on chapter-opener pages and on blank verso pages.

**Drop caps**
- "drop cap on every chapter", "no drop caps"
- Not implemented (see "Chapter opener style" above). A drop-cap request degrades to a small-caps lead-in on the opening paragraph and is disclosed; "no drop caps" is already the realized behaviour.

**Pull quotes / epigraphs**
- "epigraphs italicized", "pull quotes in the outer margin"
- Default for epigraphs: italic, indented from both sides, with attribution in small caps roman below.

**Section breaks**
- "use ornaments between scenes", "blank line is enough", "three asterisks"
- Default: centred `* * *`. Other common choices: a small ornament glyph (❦, §, ※), a thin centred rule, or simply extra vertical space.

## Free-form is fine

If the user's `design.md` is just one paragraph saying "make it look like a nice literary novel with chapter openers", that's enough — interpret it as the literary defaults: Alegreya 11/15 (with Alegreya SC for small caps), 6×9 trim, small-caps lead-in chapter openers (no drop caps), running heads with book title verso and chapter title recto in small caps, page numbers bottom outer.

## What to do if design.md asks for something unsupported

Most CSS-expressible typography is achievable in the HTML→PDF render path. Things that *aren't* easily achievable: complex hanging punctuation, optical margin alignment, fine kerning controls, and the `smcp`/`onum` OpenType features on Google-served fonts (stripped by the css2 endpoint — realize small caps via a dedicated SC sibling family instead, never the `smcp` feature). Drop caps are deliberately not implemented (WeasyPrint crash + anti-pattern). If `design.md` asks for any of these, do your best within CSS and note the limitation in the build notes.

## Encoding the spec

Internally, after parsing `design.md`, build a small spec object you can carry through the run and pass to `build_book_html.py`:

```json
{
  "trim": {"width": "148mm", "height": "210mm"},
  "margins": {"top": "18mm", "bottom": "36mm", "inner": "12mm", "outer": "24mm"},
  "body": {"font": "Alegreya", "size": "10.5pt", "leading": "14pt"},
  "smallcaps_font": "Alegreya SC",
  "heading": {"font": "Alegreya SC"},
  "chapter_opener": {"small_caps_first_words": 5, "start_on_recto": true},
  "running_heads": {"verso": "book_title", "recto": "chapter_title"},
  "page_numbers": {"position": "bottom-outer", "suppress_on_opener": true},
  "scene_break": {"style": "asterism", "glyph": "* * *"},
  "fonts_to_fetch": ["https://..."]
}
```

`build_book_html.py` reads `body.font` (default `Alegreya`), `smallcaps_font` (default `Alegreya SC`), `heading.font`, `body.size`/`body.leading`, `trim`, and `margins` from this spec. The margins shown above are the Tschichold-canon A5 values used on this project; for a spec-less run substitute the fallback A5 numbers from the Margins section. The spec then drives the CSS in the rendered HTML. There is no `drop_cap_lines` key — drop caps are not implemented.

## Structural markup conventions (recognised in source pages)

`build_book_html.py`'s body block classifier maps these source constructs onto book typography:

| Construct | Source form | Typeset as |
|---|---|---|
| Chapter header | `# Chapter N: T` / `# Page N: T` | opener number + title |
| Designation | `## <Book> - Prologue/Chapter One/Conclusion` directly under H1 | chapter-number slot |
| Dateline / subtitle | `###` line directly under the designation | italic line under the title |
| Section head | `## Name` inside the body | centred small-caps head (ALL-CAPS normalised; roman numerals kept) |
| Scene break | `---`, `* * *`, `***` between paragraphs | em-spaced asterisks; dropped when adjacent to a heading or chapter edge |
| Speaker / log label | paragraph-leading `**LABEL**:` | small-caps label (never bold) |
| Draft trailer | `**[To be continued...]**`, `*End of Chapter N*`, `*To be continued in Page N...*` | stripped, counted, disclosed |
| End mark | `**END**`, `*End of Book One*` | small-caps end mark |
| Attribution block | consecutive `**- text**` lines | right-aligned small-caps block |
