---
name: spittoon-to-pdf
description: Convert a folder of draft pages (chapters, scenes, any long-form prose in .md, .txt, .docx, or .html) into a single print-ready PDF book with real book typography. Optionally accepts a design.md describing trim size, fonts, margins, drop caps, running heads, page numbers, and scene-break ornaments. Use whenever a user wants to assemble loose draft pages into a finished typeset book PDF for a printer, designer, print-on-demand service, or screen reading. Triggers on "turn these pages into a book PDF", "build a book from these chapters", "typeset this manuscript", "spittoon to PDF", "draft pages to PDF", "assemble these into a book", "lay out these pages as an A5/B5/6x9 book", or any request combining draft files with a print-ready PDF goal. Also trigger without the word "book" — "merge these into one document for print" or "make these flow with running heads" qualify. Prefer this over Markdown-to-PDF when the user wants real book typography (recto chapter starts, drop caps, running heads, ornaments).
---

# spittoon-to-pdf

Take a folder of draft pages and produce a single print-ready PDF with proper book typography. One linear workflow, one deliverable, no branching.

## What this skill does, in plain terms

The user has a corpus of draft pages — what they often call a "spittoon": loose chapter or scene files written across many sessions in `.md`, `.txt`, `.docx`, or `.html`. The user wants those pages assembled into a single beautifully typeset PDF: real trim size, real margins, recto chapter starts, running heads, page numbers, drop caps, scene ornaments — the things that distinguish a book interior from a styled document.

This skill assembles the pages, applies the user's `design.md` typography (or sensible literary defaults if no `design.md` is provided), and renders one PDF via HTML→PDF using the `pdf` skill. That's the whole job.

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
- **`design.md` present?**: if yes, read it. It is free-form — extract typography hints (trim size, margins, font family, body size and leading, drop caps, running heads, page numbers, scene break style, epigraph style, chapter-opener treatment) but do not require a fixed schema. Whatever the user wrote is the source of truth.

If page files are missing entirely, ask the user for them. Don't proceed without pages.

### 2. Parse pages in parallel

Page-file parsing is independent file I/O — run it in parallel via bash backgrounding (`&` + `wait`). Use `scripts/parse_chapter.py` to extract title, optional epigraph, and body from each page into intermediate JSON, one JSON per source file in `/home/claude/parsed/`.

Parsing rules (the script implements these — read the script if you need to debug):

- **Title detection**: first `# H1` heading in markdown, or the first non-empty line in plain text, or the largest heading in `.docx`/`.html`. If none is detectable, fall back to a derived title from the filename.
- **Epigraph detection**: a blockquote (`>` lines) appearing before the first body paragraph is treated as an epigraph; an attribution line starting with `—` or `--` immediately after is treated as the attribution.
- **Body**: everything after the title (and optional epigraph) is body prose. Markdown emphasis (`*em*`, `**strong**`, `_em_`) is preserved. A line that is exactly `* * *`, `***`, `---`, or `# # #` is treated as a scene break.

### 3. Apply design.md to a typography spec

Read `references/design-md-conventions.md` for how to interpret design notes. Build a single typography spec that will apply to the whole book. If `design.md` is absent, use these literary-novel defaults:

```yaml
trim_size: "6 x 9 in"          # US trade
margins: { top: "0.75in", bottom: "0.75in", inner: "0.875in", outer: "0.625in" }
body_font: "EB Garamond"        # Google Fonts, freely loadable
body_size: "11pt"
body_leading: "15pt"
heading_font: "Cormorant Garamond"
chapter_opener: "drop-cap, 3-line, small-caps first 5 words, start on recto"
running_heads: "verso=book-title, recto=chapter-title"
page_numbers: "bottom-outer, suppress on openers and blank versos"
scene_break: "centered '* * *'"
```

These defaults aim at a competent novel interior. If the user's content is non-fiction, poetry, anthology, or a screenplay, adjust trim and leading accordingly — and say so in the disclosure.

### 4. Build the HTML and render to PDF

Use the `pdf` skill to do the actual rendering — that skill knows the environment's HTML→PDF tooling (typically WeasyPrint, which respects `@page` rules and CSS counters properly).

Pattern:

1. Run `scripts/build_book_html.py` against the parsed chapter JSONs and the typography spec to produce a single combined HTML book at `/home/claude/<slug>/book.html`. The script substitutes the spec into the bundled `assets/book-template.html` and applies per-chapter wrapping.
2. Hand that HTML to the `pdf` skill's HTML-to-PDF route.
3. Save the PDF first to `/home/claude/<slug>-book.pdf`, then copy to `/mnt/user-data/outputs/`.

Critical details for book-quality PDFs (the bundled template handles these, but verify after render):

- `@page :left` and `@page :right` to differentiate verso/recto margins (asymmetric inner/outer).
- `page-break-before: right` on chapter sections so chapters always start on a recto page (this will produce blank versos, which is correct).
- `string-set` and `string()` for running heads pulled from chapter titles and the book title.
- `@font-face` declarations embedding Google Fonts directly — do not rely on system fonts.
- Page numbers via the `counter(page)` CSS counter, with suppression rules on `.chapter-opener` and `.blank-verso` pages.
- Bleed only if the user asks for it; for novel interiors it's almost always unnecessary.

### 5. Disclose what happened

Write `/mnt/user-data/outputs/<slug>-build-notes.md` and summarize the same in chat. The disclosure is part of the skill's contract — see `references/honest-disclosure.md` for the template and tone.

## Parallelism guidance

Book layout is **not** an embarrassingly parallel problem. Pagination, running heads, and text flow are inherently sequential — chapter 3's starting page depends on chapter 2's length. Don't try to render chapters in parallel; the PDF render is a single synchronous pass.

What *can* run in parallel during prep:

- **Reading and parsing page files** — independent file I/O.
- **Resolving font URLs** declared in `design.md` — independent network fetches.
- **Generating per-chapter HTML fragments** — pure transformations, no shared state.

Use bash backgrounding (`&` + `wait`) for these. The actual `pdf` skill render is one call, at the end, on the assembled HTML.

## Choosing page granularity

The default is **one source file = one chapter = one section in the PDF**. Each chapter starts on a recto page (right-hand) with the configured opener treatment.

If a single source file is huge (say >20k words) and the user wants it split into multiple chapters in the output, ask them how to split — at `## H2` headings or at scene breaks. Don't infer it.

If multiple source files are tiny (a few hundred words each) and clearly represent scenes within a single chapter rather than separate chapters, ask the user whether they want them grouped under one chapter title or treated as separate openers. Either is fine; just don't guess.

## When to read which reference

- `references/design-md-conventions.md` — read whenever a `design.md` is present, or when the user describes typography in chat without a separate file.
- `references/honest-disclosure.md` — read at the end, before composing the final reply.

## Output convention

Final files go in `/mnt/user-data/outputs/` and are presented via `present_files`. Filename convention:

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
