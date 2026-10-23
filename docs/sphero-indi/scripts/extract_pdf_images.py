"""Extract native embedded images + text captions from the FCC teardown PDF."""
import pymupdf
import os

PDF = '/Users/patrickford/projects/claude-env/INDI Teardown Internal Photos - FCC ID SXO-INDI.pdf'
OUT = '/tmp/sphero-indi/fcc/native'
os.makedirs(OUT, exist_ok=True)

doc = pymupdf.open(PDF)
print('pages:', len(doc))

# captions / all text, per page
for i, page in enumerate(doc):
    txt = page.get_text().strip()
    if txt:
        print(f'--- page {i+1} text ---')
        print(txt[:600])

# embedded images at native resolution
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
        name = f'{OUT}/img-p{i+1}-x{xref}-{w}x{h}.png'
        if w * h >= 300 * 300:  # skip logos/decorations
            pix.save(name)
            print(f'page {i+1} xref {xref}: {w}x{h} -> {os.path.basename(name)} ({os.path.getsize(name)//1024} KB)')
