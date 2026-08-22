#!/usr/bin/env python3
"""Build a SchriftOhr Edition from a Project Gutenberg epub.

The editorial acts, in order: read the source in its own spine order,
cut it into real chapters, throw away the apparatus of the scan (page
numbers mid-sentence, Gutenberg's boilerplate and logo), reflow the
hard-wrapped lines, and set the result in the house style.

Every image in the source is ACCOUNTED FOR — kept and reported, or
dropped and reported. Nothing disappears silently.
"""
import re, os, html, glob, uuid, shutil, zipfile, subprocess, unicodedata
from PIL import Image

def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')

def flatten(x):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', x))).strip()

def spine_docs(src):
    """Reading order as the source itself declares it — never a filename sort."""
    opf = glob.glob(f'{src}/**/content.opf', recursive=True)[0]
    base = os.path.dirname(opf)
    s = open(opf, encoding='utf-8').read()
    man = {i: h for i, h in re.findall(r'<item id="([^"]+)"[^>]*href="([^"]+)"', s)}
    man.update({i: h for h, i in re.findall(r'<item[^>]*href="([^"]+)"[^>]*id="([^"]+)"', s)})
    order = [man[i] for i in re.findall(r'idref="([^"]+)"', s) if i in man]
    if not order:                                     # some PG epubs omit the spine
        docs = glob.glob(f'{base}/*-h-*.htm.xhtml')
        docs.sort(key=lambda p: int(re.search(r'-h-(\d+)\.htm', p).group(1)))
        return [os.path.relpath(d, base) for d in docs], base
    return order, base

CHAPTER_HEAD = re.compile(r'^(?:CHAPTER\s+)?([IVXL]+|\d+)\.?\s*(.*)$', re.I)

def body_of(doc):
    m = re.search(r'<body[^>]*>(.*)</body>', doc, re.S | re.I)
    return m.group(1) if m else doc

def clean(b, imgmap, kept):
    b = re.sub(r'<div class="pb"[^>]*>.*?</div>', '', b, flags=re.S)
    b = re.sub(r'\[\d+\]', '', b)
    b = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', b, flags=re.S)
    b = re.sub(r'</?span[^>]*>', '', b)
    out = []
    for m in re.finditer(r'<(p|blockquote|div|figure|h[3-6])\b[^>]*>(.*?)</\1>', b, flags=re.S):
        tag, inner = m.group(1), re.sub(r'\s+', ' ', m.group(2)).strip()
        img = re.search(r'<img[^>]*src="([^"]+)"', inner)
        if img:
            name = os.path.basename(img.group(1))
            if name in imgmap:                        # a plate the book owns
                kept.add(name)
                out.append(f'<figure><img alt="" src="../images/{imgmap[name]}" /></figure>')
            continue
        if not flatten(inner):
            continue
        out.append(f'<p>{inner}</p>' if tag in ('p', 'div') else f'<{tag}>{inner}</{tag}>')
    return '\n'.join(out)

def page(title, et, cls, inner, bt='bodymatter'):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n'
            f'<head><title>{html.escape(title)}</title><meta charset="utf-8"/>'
            '<link rel="stylesheet" type="text/css" href="../css/style.css"/></head>\n'
            f'<body epub:type="{bt}"><section epub:type="{et}" class="{cls}">\n{inner}\n'
            '</section></body></html>\n')

def build(src, out, meta, cover, tpl, plates=()):
    """plates: source image basenames to carry into the edition as its own art."""
    shutil.rmtree(out, ignore_errors=True)
    for d in ('META-INF', 'OEBPS/text', 'OEBPS/css', 'OEBPS/images'):
        os.makedirs(f'{out}/{d}')
    docs, base = spine_docs(src)

    all_imgs = {os.path.basename(p) for p in
                glob.glob(f'{base}/*.jpg') + glob.glob(f'{base}/*.jpeg') + glob.glob(f'{base}/*.png')}
    imgmap = {}
    for name in plates:
        match = next((i for i in all_imgs if i.endswith(name)), None)
        if match:
            dest = slug(name.rsplit('.', 1)[0]) + '.jpg'
            Image.open(f'{base}/{match}').convert('RGB').save(
                f'{out}/OEBPS/images/{dest}', 'JPEG', quality=88, optimize=True)
            imgmap[match] = dest

    kept, chapters = set(), []
    for d in docs:
        p = os.path.join(base, d.split('#')[0])
        if not os.path.exists(p):
            continue
        raw = open(p, encoding='utf-8', errors='ignore').read()
        # Skip the license PAGE, not every file that mentions the licence —
        # Gutenberg's own front matter names it, and that file can hold chapters.
        if re.search(r'<h[12][^>]*>\s*THE FULL PROJECT GUTENBERG LICENSE', raw, re.I):
            continue
        b = body_of(raw)
        for m in re.finditer(r'<h[12][^>]*>(.*?)</h[12]>', b, re.S | re.I):
            head = flatten(m.group(1))
            cm = CHAPTER_HEAD.match(head)
            if not cm or 'gutenberg' in head.lower():
                continue
            rest = b[m.end():]
            nxt = re.search(r'<h[12][^>]*>', rest)
            body = rest[:nxt.start()] if nxt else rest
            num, name = cm.group(1).upper(), cm.group(2).strip()
            title = f'Chapter {num}' + (f': {name}' if name else '')
            fn = f'C{len(chapters)+1:02d}' + (f'-{slug(name)}' if name else '') + '.xhtml'
            open(f'{out}/OEBPS/text/{fn}', 'w', encoding='utf-8').write(
                page(title, 'chapter', 'chapter',
                     f'<h2>{html.escape(title)}</h2>\n{clean(body, imgmap, kept)}'))
            chapters.append((fn, title))

    report = {'source_images': sorted(all_imgs), 'carried': sorted(imgmap.values()),
              'used_in_text': sorted(kept), 'chapters': len(chapters)}
    return chapters, report


HOUSE_NOTE = ('The work here has been to clear away what had gathered around the text in its '
              'passage into digital form — the page numbers scattered mid-sentence, the broken '
              'lines, the apparatus of the scan — so that the book reads cleanly on a screen and '
              'reads aloud cleanly to a listener.')

def package(out, chapters, meta, cover_png, tpl, epub_path):
    """Set the house front matter around the chapters and seal the epub."""
    T, A = meta['title'], meta['author']
    shutil.copy(f'{tpl}/OEBPS/css/style.css', f'{out}/OEBPS/css/style.css')
    for m in ('publisher-mark.png', 'publisher-mark-dark.png'):
        shutil.copy(f'{tpl}/OEBPS/images/{m}', f'{out}/OEBPS/images/{m}')
    Image.open(cover_png).convert('RGB').save(
        f'{out}/OEBPS/images/cover.jpg', 'JPEG', quality=90, optimize=True, progressive=True)

    open(f'{out}/OEBPS/text/cover.xhtml', 'w', encoding='utf-8').write(
        '<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n'
        '<head><title>Cover</title><meta charset="utf-8"/><style>body{margin:0;padding:0}'
        'img{max-width:100%;height:auto;display:block;margin:0 auto}</style></head>\n'
        '<body epub:type="frontmatter"><section epub:type="cover">'
        '<img src="../images/cover.jpg" alt="Cover"/></section></body></html>\n')
    series = f'<p>{html.escape(meta["series"])}</p>\n' if meta.get('series') else ''
    open(f'{out}/OEBPS/text/00-title.xhtml', 'w', encoding='utf-8').write(page(
        T, 'titlepage', 'titlepage',
        f'<h1>{html.escape(T)}</h1>\n<p><strong>{html.escape(A)}</strong></p>\n{series}'
        '<p>The SchriftOhr Edition</p>\n<p>Developed by RFRMDWordLabs, LLC</p>\n'
        '<p>For the benefit of readers, prayerfully, to the glory of God.</p>\n'
        '<p class="publisher-mark"><img src="../images/publisher-mark.png" '
        'alt="RFRMD Word Labs, LLC"/></p>', 'frontmatter'))
    open(f'{out}/OEBPS/text/01-edition-note.xhtml', 'w', encoding='utf-8').write(page(
        'About This Edition', 'preamble', 'preamble', '<h2>About This Edition</h2>\n'
        f'<p>This is the SchriftOhr edition of <i>{html.escape(T)}</i>, prepared by '
        f'RFRMDWordLabs, LLC. {html.escape(meta["surname"])}’s text is given as '
        f'{meta["pronoun"]} wrote it in {meta["year"]}. Nothing has been modernised, abridged, '
        f'or rewritten. {HOUSE_NOTE}</p>', 'frontmatter'))
    open(f'{out}/OEBPS/text/97-sources.xhtml', 'w', encoding='utf-8').write(page(
        'Sources and Acknowledgements', 'preamble', 'preamble',
        '<h2>Sources and Acknowledgements</h2>\n' + meta['sources'] +
        '\n<p>The arrangement of this edition is the work of RFRMDWordLabs, LLC. No claim is '
        'made upon the text.</p>\n<p><i>Soli Deo gloria.</i></p>', 'backmatter'))

    order = ([('cover.xhtml', 'Cover'), ('00-title.xhtml', T),
              ('01-edition-note.xhtml', 'About This Edition')] + chapters +
             [('97-sources.xhtml', 'Sources and Acknowledgements')])
    open(f'{out}/OEBPS/nav.xhtml', 'w', encoding='utf-8').write(
        '<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n'
        '<head><title>Contents</title><meta charset="utf-8"/></head><body>\n'
        '<nav epub:type="toc" role="doc-toc" id="toc"><h1>Contents</h1><ol>\n' +
        '\n'.join(f'      <li><a href="text/{f}">{html.escape(t)}</a></li>' for f, t in order[1:]) +
        '\n</ol></nav>\n</body></html>\n')

    man = ['    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
           '    <item id="css" href="css/style.css" media-type="text/css"/>',
           '    <item id="cover-img" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>',
           '    <item id="pubmark" href="images/publisher-mark.png" media-type="image/png"/>',
           '    <item id="pubmarkdark" href="images/publisher-mark-dark.png" media-type="image/png"/>']
    for j, extra in enumerate(sorted(set(os.listdir(f'{out}/OEBPS/images')) -
                                     {'cover.jpg', 'publisher-mark.png', 'publisher-mark-dark.png'})):
        man.append(f'    <item id="pl{j}" href="images/{extra}" media-type="image/jpeg"/>')
    spine = []
    for i, (f, t) in enumerate(order):
        man.append(f'    <item id="t{i}" href="text/{f}" media-type="application/xhtml+xml"/>')
        spine.append(f'    <itemref idref="t{i}"/>')
    open(f'{out}/OEBPS/content.opf', 'w', encoding='utf-8').write(
f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid" xml:lang="en-GB">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, "schriftohr:" + meta["id"])}</dc:identifier>
    <dc:title>{html.escape(T)}</dc:title>
    <dc:creator id="author">{html.escape(A)}</dc:creator>
    <meta refines="#author" property="role" scheme="marc:relators">aut</meta>
    <dc:language>en-GB</dc:language>
    <dc:publisher>SchriftOhr / RFRMDWordLabs, LLC</dc:publisher>
    <dc:description>{html.escape(meta["description"])}</dc:description>
    <dc:source>{html.escape(meta["source"])}</dc:source>
    <dc:rights>{html.escape(meta["rights"])}</dc:rights>
    <dc:date>{meta["date"]}</dc:date>
    <meta property="dcterms:modified">{meta["date"]}T00:00:00Z</meta>
    <meta name="cover" content="cover-img"/>
  </metadata>
  <manifest>
{chr(10).join(man)}
  </manifest>
  <spine>
{chr(10).join(spine)}
  </spine>
</package>
''')
    open(f'{out}/META-INF/container.xml', 'w', encoding='utf-8').write(
        '<?xml version="1.0" encoding="utf-8"?>\n<container version="1.0" '
        'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n  <rootfiles>\n'
        '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
        '  </rootfiles>\n</container>\n')
    open(f'{out}/mimetype', 'w').write('application/epub+zip')
    if os.path.exists(epub_path):
        os.remove(epub_path)
    subprocess.run(['zip', '-qX0', epub_path, 'mimetype'], cwd=out, check=True)
    subprocess.run(['zip', '-qXr9', epub_path, 'META-INF', 'OEBPS'], cwd=out, check=True)
    return epub_path
