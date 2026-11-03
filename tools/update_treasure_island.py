#!/usr/bin/env python3
"""Treasure Island, build 2026-11-02.1: the cleanup proposed and approved on 2026-11-02.

    tools/update_treasure_island.py CLOSING.jpg

Works on the published EPUB in books/treasure-island/ and writes it back in place. The dc:identifier is kept, so a
reader's place and notes carry over and the shelf can offer this copy as an update. No word of Stevenson's changes.

  1. The songs set line by line, as printed (six places that had run their lines together).
  2. The one footnote (chapter 21) taken out of the story into a note the voice steps over.
  3. Chapters numbered in figures (Chapter 1, not Chapter I), headings and contents both.
  4. Every full plate given its caption as alt text (books/treasure-island/plate-captions.tsv).
  5. The Sources page no longer points to "A Note on the Text", which the book never had.
  6. The house pages it lacked: This Book Is Made to Be Heard, How These Books Are Made, the closing cover.
  7. About This Edition says what this copy did; About This Copy carries the new build stamp.

Every replacement must match exactly once, or the run stops.
"""
import pathlib, re, shutil, subprocess, sys, tempfile, zipfile
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import edition_parts as EP

BUILD = '2026-11-02.1'
BOOK = ROOT / 'books/treasure-island'
EPUB = next(BOOK.glob('*.epub'))
CAPTIONS = BOOK / 'plate-captions.tsv'


def once(text, old, new, where):
    n = text.count(old)
    if n != 1:
        sys.exit(f'{where}: expected one "{old[:60]}", found {n}')
    return text.replace(old, new)


ROMAN = {v: i for i, v in enumerate(
    'I II III IV V VI VII VIII IX X XI XII XIII XIV XV XVI XVII XVIII XIX XX XXI XXII XXIII XXIV XXV XXVI '
    'XXVII XXVIII XXIX XXX XXXI XXXII XXXIII XXXIV'.split(), 1)}

SONG = '“Fifteen men on the dead man’s chest— Yo-ho-ho, and a bottle of rum!'
SONG_SET = '“Fifteen men on the dead man’s chest—<br/>Yo-ho-ho, and a bottle of rum!'
VERSE = [
    ('C01', f'<p>{SONG}”</p>', f'<p class="verse">{SONG_SET}”</p>'),
    ('C01', f'<p>{SONG} Drink and the devil had done for the rest— Yo-ho-ho, and a bottle of rum!”</p>',
            f'<p class="verse">{SONG_SET}<br/>Drink and the devil had done for the rest—<br/>Yo-ho-ho, and a bottle of rum!”</p>'),
    ('C23', '<p>“But one man of her crew alive, What put to sea with seventy-five.”</p>',
            '<p class="verse">“But one man of her crew alive,<br/>What put to sea with seventy-five.”</p>'),
    ('C23', f'<p>{SONG} Drink and the devil had done for the rest— Yo-ho-ho, and a bottle of rum!”</p>',
            f'<p class="verse">{SONG_SET}<br/>Drink and the devil had done for the rest—<br/>Yo-ho-ho, and a bottle of rum!”</p>'),
    ('C32', f'<p>{SONG}”</p>', f'<p class="verse">{SONG_SET}”</p>'),
    ('C34', '<p>With one man of her crew alive, What put to sea with seventy-five.</p>',
            '<p class="verse">With one man of her crew alive,<br/>What put to sea with seventy-five.</p>'),
]

NOTE_REF = ('that’s as bad to bear.” *</p>',
            'that’s as bad to bear.”<a epub:type="noteref" role="doc-noteref" class="footnote-ref" '
            'id="fnref:1" href="#fn:1">*</a></p>')
NOTE_TEXT = ('The mutineers were soon only eight in number, for the man shot by Mr. Trelawney on board the schooner '
             'died that same evening of his wound. But this was, of course, not known till after by the faithful party.')
NOTE_BODY = ('<section epub:type="footnotes" class="footnotes">\n<hr />\n<ol>\n'
             f'<li id="fn:1" epub:type="footnote">\n<p>{NOTE_TEXT}&#160;<a class="footnote-backref" '
             'href="#fnref:1">&#8617;</a></p>\n</li>\n</ol>\n</section>\n')

SOURCES_OLD = ('<p>This edition\'s arrangement, its treatment of the illustrations, and the restoration described in '
               '<em>A Note on the Text</em> are the work of RFRMD Word Labs LLC.</p>')
SOURCES_NEW = ('<p>This edition’s arrangement and its treatment of the illustrations are the work of RFRMD Word Labs '
               'LLC. The captions of the plates are read from the plates themselves.</p>')

NOTE_OLD = ('The work here has been to clear away what had gathered around the text in its passage into digital form, '
            'so that the book reads cleanly on a screen and reads aloud cleanly to a listener.</p>')
NOTE_NEW = (NOTE_OLD + '\n<p>This copy (build ' + BUILD + ') sets the songs line by line, as they were printed, and '
            'moves the one footnote out of the story so that the voice does not read it in the middle of a '
            'sentence. Chapters are numbered in figures for the same reason. Each plate carries its caption in '
            'words, for readers who use a screen reader. Not a word of Stevenson’s has changed.</p>')

CSS_ADD = '\np.verse{text-indent:0;margin:.6em 0 .6em 2em;font-style:italic}\n'


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    closing = pathlib.Path(sys.argv[1])
    work = pathlib.Path(tempfile.mkdtemp(prefix='ti-update-'))
    with zipfile.ZipFile(EPUB) as z:
        z.extractall(work)
    oebps = work / 'OEBPS'
    text = oebps / 'text'
    chapters = {p.name[:3]: p for p in text.glob('C??-*.xhtml')}

    for key, old, new in VERSE:
        p = chapters[key]
        p.write_text(once(p.read_text(encoding='utf-8'), old, new, p.name), encoding='utf-8')

    p = chapters['C21']
    t = p.read_text(encoding='utf-8')
    t = once(t, NOTE_REF[0], NOTE_REF[1], p.name)
    t = once(t, f'<p>*{NOTE_TEXT}</p>\n', '', p.name)
    t = once(t, '</section></body>', NOTE_BODY + '</section></body>', p.name)
    p.write_text(t, encoding='utf-8')

    def figures(m):
        return f'Chapter {ROMAN[m.group(1)]}:'
    for p in list(chapters.values()) + [oebps / 'nav.xhtml']:
        t = p.read_text(encoding='utf-8')
        t2, n = re.subn(r'Chapter ([IVXL]+):', figures, t)
        if p.name != 'nav.xhtml' and n not in (1, 2):   # the heading, and in one chapter its <title>
            sys.exit(f'{p.name}: {n} chapter headings')
        p.write_text(t2, encoding='utf-8')

    captions = {}
    for line in CAPTIONS.read_text(encoding='utf-8').splitlines():
        if line and not line.startswith('#'):
            plate, alt = line.split('\t')
            alt = alt.removeprefix('scene: ').replace(' (colour plate)', '')
            captions[plate] = alt.replace('&', '&amp;').replace('"', '&quot;')
    found = set()
    for p in text.glob('*.xhtml'):
        t = p.read_text(encoding='utf-8')
        for plate, alt in captions.items():
            tag = f'<img alt="" src="../images/{plate}.jpg" />'
            if tag in t:
                t = once(t, tag, f'<img alt="{alt}" src="../images/{plate}.jpg" />', p.name)
                found.add(plate)
        p.write_text(t, encoding='utf-8')
    if found != set(captions):
        sys.exit(f'plates not found: {sorted(set(captions) - found)}')

    p = text / '97-sources.xhtml'
    p.write_text(once(p.read_text(encoding='utf-8'), SOURCES_OLD, SOURCES_NEW, p.name), encoding='utf-8')
    p = text / '01-edition-note.xhtml'
    p.write_text(once(p.read_text(encoding='utf-8'), NOTE_OLD, NOTE_NEW, p.name), encoding='utf-8')
    p = text / '00-proofing.xhtml'
    p.write_text(once(p.read_text(encoding='utf-8'), 'build 2026-08-23<', f'build {BUILD}<', p.name),
                 encoding='utf-8')

    css = oebps / 'css/style.css'
    css.write_text(css.read_text(encoding='utf-8') + CSS_ADD, encoding='utf-8')

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

    opf = oebps / 'content.opf'
    t = opf.read_text(encoding='utf-8')
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
