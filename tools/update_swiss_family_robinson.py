#!/usr/bin/env python3
"""The Swiss Family Robinson, build 2026-11-02.1: the cleanup proposed and approved on 2026-11-02.

    tools/update_swiss_family_robinson.py CLOSING.jpg

Works on the published EPUB in books/swiss-family-robinson/ and writes it back in place. The dc:identifier is kept,
so a reader's place and notes carry over and the shelf can offer this copy as an update. Kingston's wording is kept;
only spelling and the conventions of the page change (John, 2026-11-01: readable spelling, modern forms welcome
where they help a reader or the voice).

  1. Curly quotation marks set by position, in the text only (never inside a tag).
  2. Juno's epitaph set as the verse it is.
  3. Older spellings brought up to date: to-day, to-morrow, to-night; cajack (kayak), parroquet (parakeet),
     putrify (putrefy), nonse (nonce); "the 2d" (the 2nd); "i. e." written out.
  4. Chapters numbered in figures (Chapter 1, not Chapter I), headings and contents both.
  5. The description no longer calls the book Stevenson's; the language is American English, as the spelling is.
  6. The house pages it lacked: This Book Is Made to Be Heard, How These Books Are Made, the closing cover.
  7. About This Edition says what this copy did; About This Copy carries the new build stamp.

Every fixed replacement must match exactly once, and every word count is checked, or the run stops.
"""
import pathlib, re, shutil, sys, tempfile, zipfile
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import edition_parts as EP

BUILD = '2026-11-02.1'
BOOK = ROOT / 'books/swiss-family-robinson'
EPUB = next(BOOK.glob('*.epub'))


def once(text, old, new, where):
    n = text.count(old)
    if n != 1:
        sys.exit(f'{where}: expected one "{old[:60]}", found {n}')
    return text.replace(old, new)


ROMAN = {v: i for i, v in enumerate(
    'I II III IV V VI VII VIII IX X XI XII XIII XIV XV XVI XVII XVIII'.split(), 1)}

# word, replacement, how many the published copy holds (a different count stops the run)
SPELLINGS = [
    (r'\bto-day\b', 'today', 6), (r'\bto-morrow\b', 'tomorrow', 8), (r'\bTo-morrow\b', 'Tomorrow', 2),
    (r'\bto-night\b', 'tonight', 1), (r'\bTo-night\b', 'Tonight', 1),
    (r'\bcajack\b', 'kayak', 38), (r'\bparroquets\b', 'parakeets', 1), (r'\bparroquet\b', 'parakeet', 1),
    (r'\bputrifying\b', 'putrefying', 1), (r'\bputrify\b', 'putrefy', 1),
    (r'\bfor the nonse\b', 'for the nonce', 1), (r'\bon the 2d\b', 'on the 2nd', 1),
    (r'<em>i\. e\.</em>,', 'that is,', 1),
]

EPITAPH_OLD = ("<p>JUNO, A servant true lies here; A faithful friend, A Dog, To all most dear; Who met her end "
               "Fighting right bravely in her master's cause.</p>")
EPITAPH_NEW = ('<p class="verse">JUNO,<br/>A servant true lies here;<br/>A faithful friend,<br/>A Dog,<br/>'
               'To all most dear;<br/>Who met her end<br/>Fighting right bravely in her master’s cause.</p>')

OPEN_BEFORE = set('  (—[‘“\n') | {''}


def curl(text):
    """Straight quotes to curly ones, by position, in text between tags only."""
    state = {'last': ''}

    def fix(seg):
        out = []
        for i, c in enumerate(seg):
            prev = out[-1] if out else state['last']
            nxt = seg[i + 1] if i + 1 < len(seg) else ''
            if c == '"':
                out.append('“' if prev in OPEN_BEFORE and nxt not in ' \n' else '”')
            elif c == "'":
                out.append('‘' if prev in OPEN_BEFORE and nxt.isalpha() else '’')
            else:
                out.append(c)
        if out:
            state['last'] = out[-1]
        return ''.join(out)
    m = re.search(r'<body[^>]*>', text)
    head, sep, body = text[:m.start()], m.group(0), text[m.end():]
    parts = re.split(r'(<[^>]+>)', body)
    # Inline tags (em, a, sup) run on from the text before them; a block tag starts fresh, so a quote after it opens.
    fixed = []
    for part in parts:
        if part.startswith('<'):
            if re.match(r'</?(p|h\d|li|div|blockquote|section|br|td|body)\b', part):
                state['last'] = ''
            fixed.append(part)
        else:
            fixed.append(fix(part))
    return head + sep + ''.join(fixed)


def check_balance(text, where):
    for para in re.findall(r'<p[^>]*>(.*?)</p>', text, flags=re.S):
        plain = re.sub(r'<[^>]+>', '', para)
        if '"' in plain or "'" in plain:
            sys.exit(f'{where}: a straight quote survived: {plain[:80]}')


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    closing = pathlib.Path(sys.argv[1])
    work = pathlib.Path(tempfile.mkdtemp(prefix='sfr-update-'))
    with zipfile.ZipFile(EPUB) as z:
        z.extractall(work)
    oebps = work / 'OEBPS'
    text = oebps / 'text'
    chapters = sorted(text.glob('C??-*.xhtml'))

    p = next(c for c in chapters if c.name.startswith('C17'))
    p.write_text(once(p.read_text(encoding='utf-8'), EPITAPH_OLD, EPITAPH_NEW, p.name), encoding='utf-8')

    counts = {pat: 0 for pat, _, _ in SPELLINGS}
    for p in chapters + [oebps / 'nav.xhtml']:
        t = p.read_text(encoding='utf-8')
        for pat, new, _ in SPELLINGS:
            if p.name == 'nav.xhtml':
                break   # its only match is a file name in an href; the files keep their names
            t, n = re.subn(pat, new, t)
            counts[pat] += n
        t, n = re.subn(r'Chapter ([IVX]+)\b', lambda m: f'Chapter {ROMAN[m.group(1)]}', t)
        if p.name != 'nav.xhtml' and n not in (1, 2):
            sys.exit(f'{p.name}: {n} chapter headings')
        if p.name != 'nav.xhtml':
            t = curl(t)
            check_balance(t, p.name)
        p.write_text(t, encoding='utf-8')
    for pat, _, want in SPELLINGS:
        if counts[pat] != want:
            sys.exit(f'{pat}: {counts[pat]} replaced, expected {want}')

    opf = oebps / 'content.opf'
    t = opf.read_text(encoding='utf-8')
    t = once(t, "A reading edition of Stevenson's The Swiss Family Robinson",
             'A reading edition of Johann David Wyss’s The Swiss Family Robinson, in the translation by W. H. G. '
             'Kingston,', 'content.opf')
    t = once(t, '<dc:language>en-GB</dc:language>', '<dc:language>en-US</dc:language>', 'content.opf')
    t = t.replace('xml:lang="en-GB"', 'xml:lang="en-US"', 1)
    t = once(t, '</manifest>',
             '    <item id="heard" href="text/02-heard.xhtml" media-type="application/xhtml+xml"/>\n'
             '    <item id="why" href="text/98-why.xhtml" media-type="application/xhtml+xml"/>\n'
             '    <item id="backcoverimg" href="images/closing-cover.jpg" media-type="image/jpeg"/>\n'
             '    <item id="backcover" href="text/99-closing-cover.xhtml" media-type="application/xhtml+xml"/>\n'
             '  </manifest>', 'content.opf')
    note_id = re.search(r'<item id="([^"]+)" href="text/01-edition-note.xhtml"', t).group(1)
    src_id = re.search(r'<item id="([^"]+)" href="text/97-sources.xhtml"', t).group(1)
    t = once(t, f'<itemref idref="{note_id}"/>', f'<itemref idref="heard"/>\n    <itemref idref="{note_id}"/>', 'spine')
    t = once(t, f'<itemref idref="{src_id}"/>', f'<itemref idref="{src_id}"/>\n    <itemref idref="why"/>', 'spine')
    t = once(t, '</spine>', '  <itemref idref="backcover"/>\n  </spine>', 'spine')
    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    t, n = re.subn(r'(<meta property="dcterms:modified">)[^<]+(</meta>)', rf'\g<1>{now}\g<2>', t)
    if n != 1:
        sys.exit('content.opf: no dcterms:modified')
    opf.write_text(t, encoding='utf-8')

    p = text / '01-edition-note.xhtml'
    t = p.read_text(encoding='utf-8')
    t = once(t, '</section></body>',
             '<p>This copy (build ' + BUILD + ') brings some older spellings up to date, so the book reads easily '
             'and sounds right when read aloud: <i>today</i>, <i>tomorrow</i> and <i>tonight</i> without their '
             'hyphens, <i>kayak</i> for Kingston’s <i>cajack</i>, <i>parakeet</i> for <i>parroquet</i>. It sets the '
             'quotation marks properly, sets Juno’s epitaph as verse, and numbers the chapters in figures. '
             'Kingston’s words are otherwise unchanged.</p>\n</section></body>', p.name)
    p.write_text(t, encoding='utf-8')
    p = text / '00-proofing.xhtml'
    p.write_text(once(p.read_text(encoding='utf-8'), 'build 2026-08-23<', f'build {BUILD}<', p.name),
                 encoding='utf-8')

    css = oebps / 'css/style.css'
    css.write_text(css.read_text(encoding='utf-8') +
                   '\np.verse{text-indent:0;margin:.6em 0 .6em 2em;font-style:italic}\n', encoding='utf-8')

    (text / '02-heard.xhtml').write_text(EP.heard_xhtml(), encoding='utf-8')
    (text / '98-why.xhtml').write_text(EP.closing_xhtml(), encoding='utf-8')
    shutil.copy(closing, oebps / 'images/closing-cover.jpg')
    (text / '99-closing-cover.xhtml').write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n'
        '<head><title>The SchriftOhr Editions</title><meta charset="utf-8"/>'
        '<style>body{margin:0;padding:0}img{max-width:100%;height:auto;display:block;margin:0 auto}</style>'
        '</head>\n<body epub:type="backmatter"><section epub:type="colophon"><img src="../images/closing-cover.jpg" '
        'alt="The SchriftOhr Editions"/></section></body></html>\n', encoding='utf-8')

    nav = oebps / 'nav.xhtml'
    t = nav.read_text(encoding='utf-8')
    t = once(t, '<li><a href="text/01-edition-note.xhtml">',
             '<li><a href="text/02-heard.xhtml">This Book Is Made to Be Heard</a></li>\n'
             '<li><a href="text/01-edition-note.xhtml">', 'nav.xhtml')
    t = once(t, '<li><a href="text/97-sources.xhtml">Sources and Acknowledgements</a></li>',
             '<li><a href="text/97-sources.xhtml">Sources and Acknowledgements</a></li>\n'
             '<li><a href="text/98-why.xhtml">How These Books Are Made</a></li>', 'nav.xhtml')
    nav.write_text(t, encoding='utf-8')

    out = EPUB.with_suffix('.new.epub')
    with zipfile.ZipFile(out, 'w') as z:
        z.write(work / 'mimetype', 'mimetype', compress_type=zipfile.ZIP_STORED)
        for p in sorted(work.rglob('*')):
            if p.is_file() and p.name != 'mimetype':
                z.write(p, p.relative_to(work).as_posix(), compress_type=zipfile.ZIP_DEFLATED)
    out.replace(EPUB)
    shutil.rmtree(work)
    print(f'{EPUB.name}: build {BUILD}')


if __name__ == '__main__':
    main()
