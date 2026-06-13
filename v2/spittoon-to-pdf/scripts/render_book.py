#!/usr/bin/env python3
"""
render_book.py — Render an assembled book.html to PDF with WeasyPrint, padding
the final page count to a multiple of 4 with blank, folio-free leaves.

Usage:
    python render_book.py <book.html> <output.pdf> [--gtk "C:\\Program Files\\GTK3-Runtime Win64\\bin"]

Why a dedicated renderer: WeasyPrint needs GTK3 on PATH (Windows); page parity
can only be computed after a first render; and pad leaves appended after all
content cannot change earlier pagination, so one re-render is exact.
"""

import argparse
import os
import sys
from pathlib import Path

DEFAULT_GTK = r"C:\Program Files\GTK3-Runtime Win64\bin"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("pdf")
    ap.add_argument("--gtk", default=DEFAULT_GTK,
                    help="GTK3 bin dir to prepend to PATH (Windows). Ignored if missing.")
    ap.add_argument("--no-pad", action="store_true", help="Disable multiple-of-4 padding")
    args = ap.parse_args()

    if args.gtk and Path(args.gtk).exists():
        os.environ["PATH"] = args.gtk + os.pathsep + os.environ.get("PATH", "")

    import weasyprint  # imported after PATH is set

    html_path = Path(args.html)
    html = html_path.read_text(encoding="utf-8")

    doc = weasyprint.HTML(string=html, base_url=str(html_path.parent)).render()
    n = len(doc.pages)

    pad = 0 if args.no_pad else (-n) % 4
    if pad:
        inject = '<div class="pad-leaf"></div>' * pad
        html2 = html.replace("</body>", inject + "</body>")
        doc = weasyprint.HTML(string=html2, base_url=str(html_path.parent)).render()
        # pad leaves follow all content, so earlier pagination is unchanged
        html_path.write_text(html2, encoding="utf-8")

    doc.write_pdf(args.pdf)
    total = len(doc.pages)
    print(f"{Path(args.pdf).name}: {total} pages"
          + (f" ({pad} blank pad leaf/leaves appended to reach a multiple of 4)" if pad else ""))
    if total % 4 != 0 and not args.no_pad:
        print(f"  WARNING: page count {total} is not a multiple of 4", file=sys.stderr)


if __name__ == "__main__":
    main()
