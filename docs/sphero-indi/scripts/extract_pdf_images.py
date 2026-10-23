"""Extract native embedded images + per-page caption text from an FCC exhibit PDF.

Usage: python3 extract_pdf_images.py [pdf-path] [out-dir]
"""
import sys
import os
import pymupdf

PDF = sys.argv[1] if len(sys.argv) > 1 else '/Users/patrickford/projects/claude-env/INDI Teardown Internal Photos - FCC ID SXO-INDI.pdf'
OUT = sys.argv[2] if len(sys.argv) > 2 else '/tmp/sphero-indi/fcc/native'
os.makedirs(OUT, exist_ok=True)

doc = pymupdf.open(PDF)
print('pages:', len(doc))

for i, page in enumerate(doc):
    txt = ' | '.join(t.strip() for t in page.get_text().splitlines() if t.strip())
    print(f'page {i+1}: {txt[:200]}')

seen = set()
for i, page in enumerate(doc):
    for img in page.get_images(full=True):
        xref = img[0]
        if xref in seen:
            continue
        seen.add(xref)
        pix = pymupdf.Pixmap(doc, xref)
        if pix.n - pix.alpha > 3:
            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
        w, h = pix.width, pix.height
        if w * h < 300 * 300:
            continue
        name = f'{OUT}/p{i+1}-x{xref}-{w}x{h}.png'
        pix.save(name)
        print(f'page {i+1} xref {xref}: {w}x{h} -> {os.path.basename(name)} ({os.path.getsize(name)//1024} KB)')
