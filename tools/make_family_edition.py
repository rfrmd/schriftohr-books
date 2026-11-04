#!/usr/bin/env python3
"""Relabel an Edition already reworded as a SchriftOhr Family Edition (John, 2026-11-03).

    make_family_edition.py BOOK_ID COVER.jpg CLOSING.jpg

Title page, About This Edition, About This Copy, Sources and the description say what the book is; the front and
closing covers are replaced; the build goes up by one. The chapters are checked byte for byte. Identifiers are kept,
so a reader's place carries over. Blurb and log are handled by the shelf step.
"""
import json, pathlib, re, sys, zipfile, datetime
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
book, cover, closing = sys.argv[1:4]
entry = next(b for b in json.load(open(ROOT / 'shelf.json'))['books'] if b['id'] == book)
author, title = entry['author'], entry['title']
epub = next((ROOT / 'books' / book).glob('*SchriftOhr_Edition*.epub'))
with zipfile.ZipFile(epub) as z:
    names = z.namelist(); infos = {i.filename: i for i in z.infolist()}; data = {n: z.read(n) for n in names}
orig = dict(data)


def edit(name, fn):
    data[name] = fn(data[name].decode('utf-8')).encode('utf-8')


def one(rx, new, s, flags=re.S):
    s, n = re.subn(rx, new, s, flags=flags)
    assert n == 1, (book, rx, n)
    return s


def title_page(s):
    s = one(r'<p><strong>[^<]+</strong></p>\n(<p>[^<]+ Story</p>)\n<p>The SchriftOhr Edition</p>',
            lambda m: f'<p><strong>The SchriftOhr Family Edition</strong></p>\n<p>Based on the beloved classic by {author}</p>\n{m.group(1)}', s)
    return s.replace('Reissued September 2026', 'Reissued November 2026')


def note(s):
    m = re.search(r'given as (he|she) wrote it(?: in (\d{4}))?', s)
    assert m, book
    his = {'he': 'his', 'she': 'hers'}[m.group(1)]
    first = f', first published in {m.group(2)}' if m.group(2) else ''
    return one(r'<p>This is the SchriftOhr edition of (<(em|i)>.*?</\2>).*?reads aloud cleanly to a listener\.</p>',
               lambda k: f'<p>This is the SchriftOhr Family Edition of {k.group(1)}, prepared by RFRMD Word Labs LLC and based on the '
                         f'beloved classic by {author}{first}.</p>\n<p>The story and its people are {his}. The wording is not '
                         f'always {his}, and we say below where it differs. Spelling is brought up to date where an older form '
                         'would slow a reader, and the book is set so that it reads cleanly on a screen and reads aloud '
                         'cleanly to a listener.</p>', s)


old = entry['build']
day, n = old.rsplit('.', 1)
new_build = f'{day}.{int(n) + 1}'


def copy_page(s):
    s = one(r'<p>This is a <i>SchriftOhr Edition</i>: a book long out of copyright, set again with care\s*[—,]?\s*for reading on a page,? and for listening to aloud\.',
            '<p>This is a <i>SchriftOhr Family Edition</i>: based on a book long out of copyright, reworded where it needed it, and set again with care for reading on a page and for listening to aloud.', s)
    s = one(r'If something reads wrongly — (a misprint.*?the wrong place) — we would', r'If something reads wrongly (\1), we would', s)
    return one(r'SchriftOhr Edition &#183; build ' + re.escape(old), f'SchriftOhr Family Edition &#183; build {new_build}', s)


def sources(s):
    return one(r'The arrangement of this edition is the work of', 'The arrangement and rewording of this SchriftOhr Family Edition are the work of', s)


def opf(s):
    desc = escape(f'The SchriftOhr Family Edition, based on the beloved classic by {author}. {entry["blurb"]}')
    s = one(r'<dc:description>.*?</dc:description>', lambda m: f'<dc:description>{desc}</dc:description>', s)
    now = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return one(r'(<meta property="dcterms:modified">)[^<]+', lambda m: m.group(1) + now, s)


edit('OEBPS/text/00-title.xhtml', title_page)
edit('OEBPS/text/01-edition-note.xhtml', note)
edit('OEBPS/text/00-proofing.xhtml', copy_page)
edit('OEBPS/text/97-sources.xhtml', sources)
edit('OEBPS/content.opf', opf)
data['OEBPS/images/cover.jpg'] = pathlib.Path(cover).read_bytes()
data['OEBPS/images/closing-cover.jpg'] = pathlib.Path(closing).read_bytes()
changed = {n for n in names if data[n] != orig[n]}
expected = {'OEBPS/text/00-title.xhtml', 'OEBPS/text/01-edition-note.xhtml', 'OEBPS/text/00-proofing.xhtml',
            'OEBPS/text/97-sources.xhtml', 'OEBPS/content.opf', 'OEBPS/images/cover.jpg', 'OEBPS/images/closing-cover.jpg'}
assert changed == expected, changed ^ expected
out = epub.with_suffix('.new.epub')
with zipfile.ZipFile(out, 'w') as z:
    for n in names:
        z.writestr(infos[n], data[n], compress_type=zipfile.ZIP_STORED if n == 'mimetype' else zipfile.ZIP_DEFLATED)
out.replace(epub)
(ROOT / 'books' / book / 'cover.jpg').write_bytes(pathlib.Path(cover).read_bytes())
print(f'{book}: {old} -> {new_build}')
