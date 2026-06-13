---
name: spittoon-to-pdf
description: Convert a folder of draft pages (chapters, scenes, any long-form prose in .md, .txt, .docx, or .html) into a single print-ready PDF book with real book typography. Optionally accepts a design.md describing trim size, fonts, margins, drop caps, running heads, page numbers, and scene-break ornaments. Use whenever a user wants to assemble loose draft pages into a finished typeset book PDF for a printer, designer, print-on-demand service, or screen reading. Triggers on "turn these pages into a book PDF", "build a book from these chapters", "typeset this manuscript", "spittoon to PDF", "draft pages to PDF", "assemble these into a book", "lay out these pages as an A5/B5/6x9 book", or any request combining draft files with a print-ready PDF goal. Also trigger without the word "book" — "merge these into one document for print" or "make these flow with running heads" qualify. Prefer this over Markdown-to-PDF when the user wants real book typography (recto chapter starts, drop caps, running heads, ornaments).
---

# spittoon-to-pdf

Take a folder of draft pages and produce a single print-ready PDF with proper book typography. One linear workflow, one deliverable, no branching.

## What this skill does, in plain terms

The user has a corpus of draft pages — what they often call a "spittoon": loose chapter or scene files written across many sessions in `.md`, `.txt`, `.docx`, or `.html`. The user wants those pages assembled into a single beautifully typeset PDF: real trim size, real margins, recto chapter starts, running heads, page numbers, small-caps openers, scene ornaments — the things that distinguish a book interior from a styled document.

This skill assembles the pages, applies the user's `design.md` typography (or sensible literary defaults if no `design.md` is provided), and renders one PDF via the bundled HTML→PDF toolchain (WeasyPrint). That's the whole job.

```
Inputs:
  • pages       — REQUIRED, 1 or more files (.md, .txt, .docx, .html)
  • design.md   — OPTIONAL, free-form notes on typography and layout intent

Output:
  • <slug>-book.pdf         — the print-ready PDF
  • <slug>-build-notes.md   — disclosure of what was honored, defaulted, and skipped
```

## Why this skill exists separately from indesign-draft-pages

The `indesign-draft-pages` skill produces an InDesign deliverable — but in practice the only realistic InDesign route is a PDF→INDD reconstruction that arrives broken enough that a designer would rather start fresh. The PDF half of that workflow, by contrast, is genuinely production-quality. This skill is the PDF half, isolated and made first-class. Use it whenever the user wants the typeset PDF and doesn't actually need an `.indd`.

## Workflow

### 1. Inventory what the user provided

Before doing anything else, identify two things:

- **Page files**: list them in the order they should appear (filename order is the default; honor explicit ordering from the user, especially when filenames don't sort the way the user intends — e.g. `chapter-10` sorts before `chapter-2` lexically). Probe the first file to detect format and rough length.
- **`design.md` present?**: if yes, read it. It is free-form — extract typography hints (trim size, margins, font family, body size and leading, drop caps, running heads, page numbers, scene break style, epigraph style, chapter-opener treatment) but do not require a fixed schema. Whatever the user wrote is the source of truth. **If the project supplies a canonical `design.md` (e.g. a Tschichold-canon spec), its values win verbatim over any default in this skill.**

If page files are missing entirely, ask the user for them. Don't proceed without pages.

### 2. Parse pages in parallel

Page-file parsing is independent file I/O — run it in parallel via bash backgrounding (`&` + `wait`). Use `scripts/parse_chapter.py` to extract title, optional epigraph, designation, dateline, and body from each page into intermediate JSON, one JSON per source file in `<pages-dir>/_build/parsed/`.

Parsing rules (the script implements these — read the script if you need to debug):

- **Title detection**: structured headers first (`# Chapter N: Title` / `# Page N: Title` → number + title; an immediately-following `## Designation` and `### Dateline` are captured separately), then first `# H1` heading in markdown, or the first non-empty line in plain text, or the largest heading in `.docx`/`.html`. If none is detectable, fall back to a derived title from the filename.
- **Epigraph detection**: a blockquote (`>` lines) appearing before the first body paragraph is treated as an epigraph.
- **Body**: everything after the title (and optional epigraph) is body prose. Markdown emphasis (`*em*`, `**strong**`, `_em_`) is preserved. A compositor's em-dash pass converts spaced ` -- ` and ` - ` to ` — ` (count recorded in the JSON). A line that is exactly `* * *`, `***`, `---`, or `# # #` is treated as a scene break.
- **Encoding**: the script always reads/writes UTF-8. Never rely on the platform default (cp1252 on Windows produces mojibake downstream).

### 3. Apply design.md to a typography spec

Read `references/design-md-conventions.md` for how to interpret design notes. Build a single typography spec (`spec.json`) that will apply to the whole book. If `design.md` is absent, use these literary-novel defaults:

```yaml
trim_size: "6 x 9 in"           # US trade
margins: { top: "0.75in", bottom: "0.75in", inner: "0.875in", outer: "0.625in" }
body_font: "Alegreya"           # Google Fonts; humanist literary serif, defaults to old-style figures
smallcaps_font: "Alegreya SC"   # dedicated small-caps sibling — see "Small caps" below
body_size: "11pt"
body_leading: "15pt"
heading_font: "Alegreya SC"
chapter_opener: "small-caps first 5 words, start on recto"
running_heads: "verso=book-title, recto=chapter-title (small caps)"
page_numbers: "bottom-outer, suppress on openers and blank versos"
scene_break: "centered '* * *' (em-spaced asterisks)"
```

These defaults aim at a competent novel interior. If the user's content is non-fiction, poetry, anthology, or a screenplay, adjust trim and leading accordingly — and say so in the disclosure.

**Small caps — the load-bearing default.** Google's css2 endpoint strips OpenType features (`smcp`, `onum`) from every served font subset, so `font-variant-caps: small-caps` and `font-feature-settings: "smcp"` are silent no-ops with Google-served fonts, and WeasyPrint does not synthesize small caps. The skill therefore realizes true small caps by switching `font-family` to a **dedicated small-caps sibling family** whose lowercase glyphs *are* small capitals. The proven default is **Alegreya + Alegreya SC**: every chapter number, title, running head, section head, speaker label, and lead-in is set in `Alegreya SC`. If the user requests a different body face, only choose one that ships a real small-caps sibling on Google Fonts (or accept the italic-label fallback and disclose it); a face like EB Garamond, which has no SC sibling, will render small-caps contexts as plain mixed case.

**Drop caps are not implemented.** The float `::first-letter` route crashes WeasyPrint (AssertionError) and several house specs forbid drop caps outright. A request for a drop cap **degrades to the small-caps lead-in** (first few words of the opening paragraph in `Alegreya SC`), and that substitution is disclosed.

### 4. Build the HTML and render to PDF

The skill renders with WeasyPrint via two bundled scripts. The render is a single synchronous pass — do not parallelize it.

Pattern:

1. Run `scripts/build_book_html.py` against the parsed chapter JSONs and the `spec.json` to produce one combined HTML book at `<pages-dir>/_build/book.html`. It substitutes the spec into the bundled `assets/book-template.html`, runs the body block classifier (speaker labels, section heads, scene breaks, end marks, attribution blocks, draft-trailer stripping, lead-ins), and assembles each chapter as a `<section class="chapter grp-a|grp-b">` (alternating page-group classes so consecutive openers don't merge).
2. Run `scripts/render_book.py <book.html> <out.pdf>` to render. It prepends GTK3 to PATH, renders once, computes the page-parity deficit, and (unless `--no-pad`) appends blank folio-free pad leaves so the final count is a multiple of 4, then re-renders once (pad leaves follow all content, so earlier pagination is unchanged).

Critical details for book-quality PDFs (the bundled template handles these, but verify after render):

- `@page :left` and `@page :right` differentiate verso/recto margins (asymmetric inner/outer).
- `page-break-before: right` on chapter sections so chapters always start on a recto page (this produces blank versos, which is correct). Chapter 1 starts on a recto too.
- **Page-group opener suppression**: each chapter is its own page group (`grp-a`/`grp-b`, alternating); `@page :nth(1 of grpX)` blanks the six margin boxes on the opener *only*, leaving heads + folios live on every following page. Naming the whole chapter with a single `page: chapter-opener` is the historic bug (D1) that killed heads/folios book-wide — never reintroduce it.
- `string-set` / `string()` for running heads pulled from chapter titles and the book title.
- Page numbers via the `counter(page)` CSS counter, suppressed on openers, the title page (`@page :first`), blank versos (`@page :blank`), and pad leaves (`@page pad`).
- Bleed only if the user asks for it; for novel interiors it's almost always unnecessary.

### 5. Disclose what happened

Write `<output-dir>/<slug>-build-notes.md` and summarize the same in chat. The disclosure is part of the skill's contract — see `references/honest-disclosure.md` for the template, the verified-claims rule, and the "what was converted/stripped" counts.

## Windows / local environment notes

This skill runs on a local Windows workstation, **not** a Linux container. There is no `/home/claude` and no `/mnt/user-data/outputs`, and there is no `present_files` mechanism.

- **Working artefacts** go in a `_build/` directory next to the source pages: `<pages-dir>/_build/parsed/*.json`, `<pages-dir>/_build/book.html`, `<pages-dir>/_build/spec.json`, and a copy of the template if you patch it locally.
- **Final deliverables** go to the project root (or a per-book `outputs/` folder when the user has an established convention — e.g. `BRONZE/**/outputs/`). Present them by stating their paths in chat; there is no upload step.
- **WeasyPrint needs GTK3 on PATH at render time.** `render_book.py` prepends it automatically; if you call WeasyPrint directly, do:
  `os.environ["PATH"] = r"C:\Program Files\GTK3-Runtime Win64\bin;" + os.environ["PATH"]` **before** `import weasyprint`.
- **Always pass `encoding="utf-8"`** to every `read_text` / `write_text`. The console is cp1252: set `PYTHONIOENCODING=utf-8` when piping Python output, or avoid printing non-ASCII.
- Python 3.12 lives at `C:\Users\Genuine\AppData\Local\Programs\Python\Python312`.

### Verification (recommended, not mandatory)

- **pypdf** checks page count, trim size, and the embedded font list — but it **cannot see `@page` margin boxes**. Absence of running heads/folios in pypdf's `extract_text()` is **not** evidence they are missing. Never claim running heads or folios from pypdf extraction.
- **PyMuPDF** (`pip install pymupdf`) *does* extract margin-box text (`page.get_text()`) and renders rasterised proofs (`page.get_pixmap(dpi=150)` or `dpi=300` for a crop). A quick spot-proof of one chapter opener and one verso body page — confirming the verso head string, `folio == page number` on body pages, and openers folio-free — is recommended before writing the build notes. Small caps in particular must be confirmed in a raster proof (capital letterforms sitting at x-height), because a font without small caps fails silently.

## Structural markup conventions (recognised in source pages)

The body block classifier in `build_book_html.py` recognises these constructs:

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

## Parallelism guidance

Book layout is **not** an embarrassingly parallel problem. Pagination, running heads, and text flow are inherently sequential — chapter 3's starting page depends on chapter 2's length. Don't try to render chapters in parallel; the PDF render is a single synchronous pass.

What *can* run in parallel during prep:

- **Reading and parsing page files** — independent file I/O.
- **Resolving font URLs** declared in `design.md` — independent network fetches.
- **Generating per-chapter HTML fragments** — pure transformations, no shared state.

Use bash backgrounding (`&` + `wait`) for these. The actual render (`render_book.py`) is one call, at the end, on the assembled HTML. When rebuilding **several** books at once, run the per-book renders concurrently with `&` + `wait`.

## Choosing page granularity

The default is **one source file = one chapter = one section in the PDF**. Each chapter starts on a recto page (right-hand) with the configured opener treatment.

If a single source file is huge (say >20k words) and the user wants it split into multiple chapters in the output, ask them how to split — at `## H2` headings or at scene breaks. Don't infer it.

If multiple source files are tiny (a few hundred words each) and clearly represent scenes within a single chapter rather than separate chapters, ask the user whether they want them grouped under one chapter title or treated as separate openers. Either is fine; just don't guess.

## When to read which reference

- `references/design-md-conventions.md` — read whenever a `design.md` is present, or when the user describes typography in chat without a separate file.
- `references/honest-disclosure.md` — read at the end, before composing the final reply.

## Output convention

Final files go to the project root (or a per-book `outputs/` folder if the user has an established convention) — there is no `/mnt/user-data/outputs` and no `present_files`. State the delivered paths in chat. Filename convention:

```
<book-slug>-book.pdf          (the deliverable)
<book-slug>-build-notes.md    (disclosure)
```

The `<book-slug>` is derived from the book title (if the user provides one), or from the first chapter's title, or from the input folder name — lowercased and hyphenated. Strip filler words ("the", "a", "of") if the resulting slug is unwieldy.

## What this skill does NOT do

Be upfront if any of these are asked for, and don't pretend to deliver them:

- **No `.indd` output.** If the user wants InDesign-native files, point them at `indesign-draft-pages` — but warn that the PDF→INDD reconstruction is rough and they may prefer to take this skill's PDF into InDesign manually.
- **No cover art.** This skill produces the interior only.
- **No EPUB or other ebook formats.** The output is print-targeted PDF. If the user wants EPUB, that's a different workflow.
- **No copy-editing or proof-reading.** The skill typesets what it's given. If the user wants editorial pass, that's outside scope.
- **No automatic ISBN, copyright page, or front-matter generation** beyond what the user supplies as page files. Front matter is just more pages — give them as input files if you want them in the output.
- **No drop caps.** The float `::first-letter` route crashes WeasyPrint and is a design.md anti-pattern; drop-cap requests degrade to the small-caps lead-in, disclosed.
