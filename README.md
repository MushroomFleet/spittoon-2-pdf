# spittoon-to-pdf

A Claude skill that assembles a folder of draft pages into a single, print-ready PDF book with real book typography — recto chapter starts, drop caps, running heads, page numbers, scene-break ornaments, the works.

> *spittoon* (n.) — the working name for that folder of loose chapter and scene files you've been writing across many sessions, in many sittings, in whatever format was nearest to hand. The unfinished pile that wants to become a book.

This skill takes your spittoon and gives you back a typeset PDF you can send to a printer, hand to a designer, upload to a print-on-demand service, or just read on screen as if it were already a real book.

---

## What it does

You give it:

- **Pages** — one or more chapter or scene files in `.md`, `.txt`, `.docx`, or `.html`
- **`design.md`** *(optional)* — free-form notes describing trim size, fonts, margins, drop caps, running heads, page numbers, and scene-break ornaments

You get back:

- **`<book-slug>-book.pdf`** — the print-ready PDF with proper book interior typography
- **`<book-slug>-build-notes.md`** — an honest disclosure of which directives were honoured, which were defaulted, and what (if anything) couldn't be applied

The skill produces real book typography, not just a styled document:

- Verso/recto distinction with asymmetric inner/outer margins (the gutter is wider — that's the edge that disappears into the spine)
- Chapters always start on a recto page (right-hand), with blank versos where needed
- 3-line drop caps and small-caps first phrases on chapter openers
- Running heads pulled from the book title (verso) and chapter title (recto)
- Page numbers in the bottom outer corner, suppressed on chapter openers and blank versos
- Centred ornaments between scenes
- Italic indented epigraphs with small-caps attribution
- Embedded fonts via `@font-face` so the PDF doesn't depend on local font installs

If you don't supply a `design.md`, the skill uses literary-novel defaults — EB Garamond 11/15 on a 6×9 trim with the conventions above.

---

## Why this skill exists

Adobe's connector exposes InDesign as a data-merge and export engine, not an authoring environment. There is no tool that creates a `.indd` from prose alone. Earlier work tried to bridge this gap by rendering a PDF and then converting it back to `.indd` via Adobe's PDF→INDD route — but the reconstruction arrives broken enough that any designer would rather start fresh.

The PDF half of that workflow, by contrast, is genuinely production-quality.

`spittoon-to-pdf` is the PDF half, isolated and made first-class. Use it whenever the typeset PDF is what you actually want — for a printer, for a print-on-demand service, for a designer to take into InDesign manually as a starting reference, or just to read your own work as a finished object.

---

## Requirements

For the skill to function at all, you need a Claude environment with the `pdf` skill available — that's what does the actual HTML→PDF render via WeasyPrint or equivalent.

For the **full benefit** of `spittoon-to-pdf` and the broader creative-publishing workflows it slots into, install:

- The **Adobe for Creativity** Claude Connector and Plugin
- All Adobe-published Claude Skills (`adobe-batch-edit-photos`, `adobe-create-social-variations`, `adobe-design-from-template`, `adobe-edit-quick-cut`, `adobe-resize-photos-and-videos`, `adobe-retouch-portraits`, and the `indesign-draft-pages` skill that this one was forked from)

Some features of the wider Adobe-connector ecosystem require an active **Adobe Creative Cloud subscription**. The `spittoon-to-pdf` skill itself doesn't call the Adobe connector — it's pure HTML+CSS→PDF — so you can run it without a Creative Cloud subscription. The Adobe pieces only matter if you want to combine this skill with companion Adobe workflows (cover art, social-media variants of book pages, batch image work, etc.).

---

## Installation

1. Download `spittoon-to-pdf.skill` from this repo's releases (or build it yourself — see *Building from source* below).
2. In Claude, open Settings → Capabilities → Skills, and install the `.skill` file.
3. The skill is now available. It triggers automatically when you describe a book-assembly task; you can also invoke it explicitly by name.

---

## Usage

The simplest invocation is just to attach your pages and ask for a book PDF:

> Build a book PDF from these chapters.
>
> *(attach your chapter files)*

That's enough — the skill triggers, applies its literary-novel defaults, and gives you back a finished PDF.

For a specific design, supply a `design.md` either as an attached file or inline in your prompt. Here's a complete example for an A5 trade paperback:

> Use the `spittoon-to-pdf` skill to assemble these pages into an A5 book PDF.
>
> **Pages**: *(attach chapter files in reading order)*
>
> **design.md**:
>
> - Trim: A5 (148 × 210 mm)
> - Margins: top 15 mm, bottom 18 mm, inner 18 mm, outer 14 mm
> - Body: EB Garamond, 10.5 pt on 14 pt leading, justified, hyphenation on
> - Heading font: Cormorant Garamond
> - Chapter openers: start on recto, 3-line drop cap, first 5 words in small caps, no page number or running head on the opener
> - Running heads: book title verso, chapter title recto, small caps, centred
> - Page numbers: bottom outer, suppressed on openers and blank versos
> - Section breaks: centred `* * *`
> - Epigraphs: italic indented, attribution in roman small caps below
>
> Embed fonts via `@font-face` from Google Fonts. Save outputs to `/mnt/user-data/outputs/` and present them at the end with the honest-disclosure summary.

---

## How your pages are parsed

The skill is forgiving about input format. Here's what it looks for:

| Element | Markdown convention | Plain text fallback |
|---|---|---|
| Chapter title | First `# H1` heading | First non-empty line |
| Epigraph | A blockquote (`>`) before the first body paragraph | — |
| Epigraph attribution | A line starting with `—` or `--` immediately after the blockquote | — |
| Body | Everything after the title (and optional epigraph) | Everything after the title line |
| Scene break | A line containing exactly `* * *`, `***`, `---`, or `# # #` | Same |
| Emphasis | `*em*`, `_em_`, `**strong**` | — |

`.docx` and `.html` inputs are converted to markdown-equivalent structure first.

The default is **one source file = one chapter** in the output. Files are processed in filename order; if your filenames don't sort the way you intend (e.g. `chapter-10` sorts before `chapter-2` lexically), tell the skill the order you want and it'll honour your list.

---

## design.md cheat sheet

You can write `design.md` however you like — full prose, bullet list, single sentence. The skill scans for these kinds of directives:

- **Trim size** — "A5", "6 by 9 inches", "B-format", "trade paperback", explicit `WxH` in mm or inches
- **Margins** — "generous", "tight", or explicit top/bottom/inner/outer values
- **Body font** — a font name, a vibe ("Penguin Classic feel"), or a font URL the skill should fetch and embed
- **Body size and leading** — "11 on 15", "10.5/14", "small body with generous leading"
- **Chapter opener** — drop cap (yes/no, n-line), small-caps first phrase (yes/no, word count), recto-only chapter starts (yes/no)
- **Running heads** — what goes on verso, what goes on recto, or "none"
- **Page numbers** — position, and whether to suppress on chapter openers and blank versos
- **Scene breaks** — `* * *`, an ornament glyph (`❦`, `§`, `※`), a thin rule, or just extra space
- **Epigraphs** — formatting and attribution style

If `design.md` is absent or sparse, sensible literary defaults fill the gaps — and the build notes tell you exactly which defaults were used so nothing is silently invented.

---

## What this skill does NOT do

The skill is deliberately focused. Don't expect:

- **No `.indd` output.** If you need real InDesign-native files, take this skill's PDF into InDesign manually as a reference for trim, margins, and chapter break points, and rebuild the styles there.
- **No cover art.** Interior only. Pair with Adobe Express or Photoshop skills for covers.
- **No EPUB.** PDF is print-targeted. EPUB is a different workflow.
- **No editorial pass.** The skill typesets what it's given. Copy-edit before, not after.
- **No automatic ISBN, copyright page, or title page.** Front matter is just more pages — supply it as input files if you want it included.

---

## Building from source

The skill folder structure:

```
spittoon-to-pdf/
├── SKILL.md
├── references/
│   ├── design-md-conventions.md
│   └── honest-disclosure.md
├── scripts/
│   ├── parse_chapter.py
│   └── build_book_html.py
└── assets/
    └── book-template.html
```

To package into an installable `.skill` file, use Anthropic's `skill-creator` packager:

```bash
cd <writeable-directory>
PYTHONPATH=<path-to-skill-creator> python -m scripts.package_skill <path-to-spittoon-to-pdf-folder>
```

The result is a `spittoon-to-pdf.skill` archive ready to drop into Claude.

---

## Roadmap

Things that may land in future versions:

- A `front-matter.md` convention so title pages and copyright pages are recognised as such (and excluded from page-numbered body)
- Optional EPUB output as a sibling deliverable
- Automatic detection of common trim sizes from page-count constraints (e.g. "must fit on a 16-page signature")
- Hanging punctuation and optical margin alignment via WeasyPrint extensions when those are stable
- Cover-spec generation: given a finished PDF and a target trim, produce a flat cover spread sized for the spine width

Issues and suggestions welcome.

---

## 📚 Citation

### Academic Citation

If you use this codebase in your research or project, please cite:

```bibtex
@software{spittoon_to_pdf,
  title = {spittoon-to-pdf: a Claude skill for assembling draft pages into print-ready book PDFs},
  author = {Drift Johnson},
  year = {2025},
  url = {https://github.com/MushroomFleet/spittoon-2-pdf},
  version = {1.0.0}
}
```

### Donate

[![Ko-Fi](https://cdn.ko-fi.com/cdn/kofi3.png?v=3)](https://ko-fi.com/driftjohnson)
