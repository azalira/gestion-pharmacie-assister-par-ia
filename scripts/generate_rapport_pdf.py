#!/usr/bin/env python3
"""Génère le PDF du rapport (docs/rapport-projet.pdf) depuis docs/rapport-projet.md.

markdown -> HTML -> PDF (WeasyPrint), avec les photos des membres embarquées.
Usage : python3 scripts/generate_rapport_pdf.py
"""
import os

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, "docs", "rapport-projet.md")
OUT = os.path.join(ROOT, "docs", "rapport-projet.pdf")

CSS = """
@page {
    size: A4;
    margin: 2cm 1.8cm;
    @bottom-center { content: counter(page) " / " counter(pages); font-size: 9pt; color: #666; }
}
body { font-family: 'DejaVu Sans', sans-serif; font-size: 10.5pt; line-height: 1.5; color: #1a1a2e; }
h1 { color: #0d3b66; font-size: 21pt; border-bottom: 3px solid #0d3b66; padding-bottom: 6px; }
h2 { color: #0d3b66; font-size: 15pt; border-bottom: 1px solid #b8c4d9; padding-bottom: 3px;
     margin-top: 22px; page-break-after: avoid; }
h3 { color: #14548c; font-size: 12pt; margin-top: 16px; page-break-after: avoid; }
code { background: #eef1f6; padding: 1px 4px; border-radius: 3px; font-size: 9pt; }
pre { background: #f4f6fa; border: 1px solid #d7dee9; border-radius: 5px; padding: 10px;
      font-size: 8pt; line-height: 1.35; overflow: hidden; page-break-inside: avoid; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; page-break-inside: avoid; }
th { background: #0d3b66; color: white; padding: 5px 8px; text-align: left; font-size: 9.5pt; }
td { border: 1px solid #c9d3e0; padding: 4px 8px; font-size: 9.5pt; }
tr:nth-child(even) td { background: #f2f5f9; }
blockquote { border-left: 4px solid #0d3b66; margin-left: 0; padding-left: 12px; color: #444; }
hr { border: none; border-top: 1px solid #ccc; margin: 18px 0; }
/* Cartes membres : photo à gauche, texte à droite */
h2 + p + p + p img { display: block; }
img { max-width: 100%; }
"""

MEMBER_CSS = """
/* Les 3 images qui suivent directement un h2 membre (rôle puis photo) */
h3 ~ p img, h2 ~ p img { height: 115px; width: auto; border-radius: 8px;
                         border: 1px solid #b8c4d9; margin: 4px 0; }
"""


def main():
    with open(MD, "r", encoding="utf-8") as f:
        md_text = f.read()

    body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "toc"])

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><style>{CSS}{MEMBER_CSS}</style></head>
<body>{body}</body>
</html>"""

    from weasyprint import HTML
    HTML(string=html, base_url=os.path.join(ROOT, "docs")).write_pdf(OUT)
    size = os.path.getsize(OUT) / 1024
    print(f"OK -> {OUT} ({size:.0f} Ko)")


if __name__ == "__main__":
    main()
