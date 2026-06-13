# Honest disclosure template

Every run produces a `<slug>-build-notes.md` file alongside the PDF, and the chat reply summarizes the same information. The user needs to know what the skill did, what it defaulted, and where the result might need manual correction. This is part of the skill's contract — don't skip it.

## The build notes file

Use this exact structure. Skip sections that don't apply, but keep the section order.

```markdown
# Build notes — <book title>

**Date:** <ISO date>

## Inputs received
- Pages: <N> files (<total word count> words total)
- design.md: <yes/no — short note on whether it was rich or sparse>

## What was produced
- `<slug>-book.pdf` — <one-line description: trim size, page count, font>

## What was honored from design.md
- <bullet per directive CONFIRMED in the rendered PDF — see the verified-claims rule below>

## Intended but unverified
- <bullet per feature implemented in CSS but NOT confirmed in the artifact>

## What was defaulted
- <bullet per design.md directive that was vague or absent and was filled with a default>
- <or: "design.md was not provided; literary novel defaults were used (Alegreya 11/15 with Alegreya SC for small caps, on 6×9 trim, small-caps lead-in recto chapter openers, small-caps running heads, bottom-outer page numbers)">

## What was converted / stripped
- <N spaced hyphens/double-hyphens → em dashes>
- <N speaker/log labels → small-caps spans>
- <N draft trailers stripped (list them)>
- <N redundant rules dropped next to headings>
- <N blank pad pages appended (multiple-of-4 rule)>

## What was NOT applied
- <bullet per directive that asked for something the HTML→PDF toolchain can't do (hanging punctuation, optical margin alignment, fine kerning, the smcp/onum OpenType features on Google-served fonts, drop caps, etc.)>

## Things to review before printing
- Confirm trim size matches your printer's spec.
- Check the first line of each chapter — the small-caps lead-in (drop caps are not used).
- Pagination, running heads, and recto chapter starts.
- Any blank verso pages and the appended pad leaves (these are correct and expected for recto-only chapter starts and the multiple-of-4 rule, but worth confirming you want them).

## Tool path
- Parsed pages (`parse_chapter.py`) → typography spec → assembled HTML (`build_book_html.py`) → PDF (`render_book.py`, WeasyPrint + GTK3, padded to a multiple of 4).
```

## Verified-claims rule

"What was honored" may list **only** features confirmed in the rendered PDF — by a rasterised proof (PyMuPDF `get_pixmap`) or PyMuPDF margin-box text extraction. Anything implemented in CSS but not confirmed goes under "Intended but unverified" instead. This rule exists because earlier build notes on this project claimed running heads and small caps that were silently absent from the artifact (pypdf cannot see `@page` margin boxes, and Google-served fonts drop the `smcp` feature, so both failed invisibly). When in doubt, spot-proof one opener and one verso body page before writing the notes.

## What was converted / stripped

The body classifier rewrites and strips source markup; record the counts (the build scripts print them) so the user knows what changed:

- N spaced hyphens/double-hyphens → em dashes
- N speaker/log labels → small-caps spans (source bold removed)
- N draft trailers stripped (list them verbatim)
- N redundant scene-break rules dropped next to headings or chapter edges
- N blank pad pages appended to reach a multiple of 4

## What to say in chat

Keep the chat reply shorter than the build notes file — don't duplicate everything, just hit the points the user can't ignore:

- The names of the files presented.
- The trim size, body font, and final page count of the PDF.
- Any disclosure that materially affects whether the output is usable (defaulted directives, fonts that fell back, things `design.md` asked for that weren't possible).

Example chat reply:

> Built your book PDF: 248 pages on A5 trim, set in Alegreya 10.5/14 with Alegreya SC for small caps. Chapter openers start on recto with a small-caps lead-in (no drop caps), running heads carry the book title on verso and chapter title on recto in small caps, page numbers are bottom-outer and suppressed on openers and blank versos. Verified in a 300-dpi proof: small-caps openers, verso head string, and folio == page number on a mid-book spread. One thing to flag: your `design.md` asked for hanging punctuation, which the HTML→PDF toolchain can't do reliably — the rest of the spec is honoured. Full details are in the build-notes.md file.

## Tone

Direct, not apologetic. The constraints are real and the user benefits from knowing them. Avoid:

- "Unfortunately I couldn't..." — just say what was and wasn't done.
- Burying the limitations in the middle of a long success summary.
- Promising to "do better next time" — there's no next time inside a single run.

The disclosure is a feature, not a confession.
