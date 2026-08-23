#!/usr/bin/env python3
"""Put the house front matter into a finished EPUB, without rebuilding it.

Two things, on every SchriftOhr Edition:

  · the cover as a FULL PAGE — set as an SVG with a viewBox, because a bare
    <img> is scaled by each reader's own rules and can land small and centred
    on a field of white;
  · the proofing notice, with a build stamp, so a reader who finds something
    wrong knows where to send it and which copy it came from.

Working on the finished file rather than the source is deliberate: these
eleven were set from eleven different sources, and re-deriving their text to
add a page in front would risk the text to change the wrapper. Everything
here is additive and reversible.

    python3 add_front_matter.py [--published] <epub> [<epub> …]

The notice comes in two tempers. By default it is the PROOFING COPY page —
"this edition is not finished … please do not pass it on" — which is right
for a book being read for errors. With --published it is the quieter
"About This Copy", which asks for the same corrections without telling the
reader a finished book is unfinished. Running it again replaces whichever
notice is already there, so a book can move from one to the other.
"""
import re, sys, os, zipfile, shutil, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edition_parts import (cover_xhtml, proofing_xhtml, corrections_xhtml,
                           PROOFING_CSS)

def relpath(href, base):
    return f'{base}/{href}' if base else href

def add(path, published=False):
    notice = corrections_xhtml if published else proofing_xhtml
    label  = 'About This Copy' if published else 'Proofing Copy'
    z = zipfile.ZipFile(path)
    names = z.namelist()
    opf_path = re.search(r'full-path="([^"]+)"',
                         z.read('META-INF/container.xml').decode()).group(1)
    base = opf_path.rsplit('/', 1)[0] if '/' in opf_path else ''
    opf = z.read(opf_path).decode('utf-8')
    had = 'id="proofing"' in opf
    title  = html.unescape(re.search(r'<dc:title[^>]*>(.*?)</dc:title>', opf, re.S).group(1)).strip()
    author = html.unescape(re.search(r'<dc:creator[^>]*>(.*?)</dc:creator>', opf, re.S).group(1)).strip()

    man = dict(re.findall(r'<item id="([^"]+)"[^>]*href="([^"]+)"', opf))
    man.update({i: h for h, i in re.findall(r'<item href="([^"]+)"[^>]*id="([^"]+)"', opf)})
    spine = re.findall(r'<itemref idref="([^"]+)"', opf)
    first = man.get(spine[0], '')
    textdir = first.rsplit('/', 1)[0] if '/' in first else ''
    css = next((h for h in man.values() if h.endswith('.css')), None)

    out = {}                                   # path -> bytes, the changes
    # 1. the cover, set to fill the page
    cover_img = re.search(r'<item[^>]*href="([^"]+)"[^>]*properties="cover-image"', opf) or \
                re.search(r'<item[^>]*properties="cover-image"[^>]*href="([^"]+)"', opf)
    if cover_img and first.endswith('cover.xhtml'):
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(z.read(relpath(cover_img.group(1), base))))
        src = os.path.relpath(cover_img.group(1), textdir) if textdir else cover_img.group(1)
        out[relpath(first, base)] = cover_xhtml(*img.size, src=src).encode('utf-8')

    # 2. the proofing notice, straight after the cover
    fn = f'{textdir}/00-proofing.xhtml' if textdir else '00-proofing.xhtml'
    css_href = os.path.relpath(css, textdir) if (css and textdir) else (css or 'style.css')
    page = notice(title, author).replace('../css/style.css', css_href)
    out[relpath(fn, base)] = page.encode('utf-8')
    if css:
        style = z.read(relpath(css, base))
        # Replace any block this tool appended before, rather than testing for
        # one selector and appending the lot again: checking for `.proof{` left
        # the replacement notice unstyled, and checking loosely stacked the
        # block up twice.
        mark = PROOFING_CSS.split('\n')[1].encode('utf-8')       # its first comment line
        i = style.find(mark)
        if i > 0:
            style = style[:style.rfind(b'\n', 0, i)]
        out[relpath(css, base)] = style + PROOFING_CSS.encode('utf-8')

    opf2 = opf
    if not had:
        opf2 = opf2.replace('</manifest>',
            f'  <item id="proofing" href="{fn}" media-type="application/xhtml+xml"/>\n  </manifest>')
        opf2 = re.sub(r'(<itemref idref="' + re.escape(spine[0]) + r'"\s*/>)',
                      r'\1\n    <itemref idref="proofing"/>', opf2, count=1)
    out[opf_path] = opf2.encode('utf-8')

    nav = next((h for h in man.values() if h.endswith('nav.xhtml')), None)
    if nav:
        n = z.read(relpath(nav, base)).decode('utf-8')
        href = os.path.relpath(relpath(fn, base), os.path.dirname(relpath(nav, base)))
        entry = f'<li><a href="{href}">{label}</a></li>'
        if had:
            n = re.sub(r'<li><a href="' + re.escape(href) + r'">[^<]*</a></li>', entry, n, count=1)
        else:
            n = re.sub(r'(<ol>\s*)', r'\1\n      ' + entry, n, count=1)
        out[relpath(nav, base)] = n.encode('utf-8')

    tmp = path + '.new'
    with zipfile.ZipFile(tmp, 'w') as w:
        w.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip',
                   compress_type=zipfile.ZIP_STORED)
        for n in names:
            if n == 'mimetype': continue
            w.writestr(n, out.pop(n, z.read(n)), compress_type=zipfile.ZIP_DEFLATED)
        for n, data in out.items():
            w.writestr(n, data, compress_type=zipfile.ZIP_DEFLATED)
    z.close()
    shutil.move(tmp, path)
    what = 'notice replaced' if had else 'cover set full-page, notice added'
    print(f'  {os.path.basename(path)}: {what} — {label} ({title})')
    return True

if __name__ == '__main__':
    args = sys.argv[1:]
    pub = '--published' in args
    n = sum(bool(add(p, pub)) for p in args if p != '--published')
    print(f'{n} edition(s) changed')
