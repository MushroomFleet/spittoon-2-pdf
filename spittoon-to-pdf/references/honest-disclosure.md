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
- <bullet per directive that made it through>

## What was defaulted
- <bullet per design.md directive that was vague or absent and was filled with a default>
- <or: "design.md was not provided; literary novel defaults were used (EB Garamond 11/15 on 6×9 trim, drop-cap recto chapter openers, running heads, bottom-outer page numbers)">

## What was NOT applied
- <bullet per directive that asked for something the HTML→PDF toolchain can't do (hanging punctuation, optical margin alignment, fine kerning, true small caps if font lacks them, etc.)>

## Things to review before printing
- Confirm trim size matches your printer's spec.
- Check the first line of each chapter — small-caps and drop-cap interaction can produce edge cases.
- Pagination, running heads, and recto chapter starts.
- Any blank verso pages (these are correct and expected for recto-only chapter starts, but worth confirming you want them).

## Tool path
- Parsed pages → typography spec → HTML → PDF (via the `pdf` skill).
```

## What to say in chat

Keep the chat reply shorter than the build notes file — don't duplicate everything, just hit the points the user can't ignore:

- The names of the files presented.
- The trim size, body font, and final page count of the PDF.
- Any disclosure that materially affects whether the output is usable (defaulted directives, fonts that fell back, things `design.md` asked for that weren't possible).

Example chat reply:

> Built your book PDF: 248 pages on A5 trim, set in EB Garamond 10.5/14. Chapter openers start on recto with a 3-line drop cap and small-caps first phrase, running heads carry the book title on verso and chapter title on recto, page numbers are bottom-outer and suppressed on openers and blank versos. One thing to flag: your `design.md` asked for hanging punctuation, which the HTML→PDF toolchain can't do reliably — the rest of the spec is honoured. Full details are in the build-notes.md file.

## Tone

Direct, not apologetic. The constraints are real and the user benefits from knowing them. Avoid:

- "Unfortunately I couldn't..." — just say what was and wasn't done.
- Burying the limitations in the middle of a long success summary.
- Promising to "do better next time" — there's no next time inside a single run.

The disclosure is a feature, not a confession.
