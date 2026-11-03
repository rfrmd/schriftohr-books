#!/usr/bin/env python3
"""Sugar Creek Gang Editions built straight from a Project Gutenberg HTML file.

    tools/build_sugar_creek.py BOOK-ID PG.html COVER.jpg

BOOK-ID is a key of BOOKS below. Digs for Treasure is the template for every page that is not story, so the
series reads as a set. Not tools/build_edition.py: that builder drops any block that holds other blocks (a stanza
in its container, a letter in a blockquote). Here every block in the story is set by kind, an unknown block stops
the run, and so does any difference between the words of the source and the words of the edition.
"""
import html, pathlib, re, shutil, subprocess, sys, tempfile, uuid, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = next((ROOT / 'books/sugar-creek-digs-for-treasure').glob('*.epub'))
AUTHOR, BUILD, DATE = 'Paul Hutchens', '2026-11-02.1', '2026-11-02'
WORD = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)*")
DIGS = '<i>The Sugar Creek Gang Digs for Treasure</i>'


def end_before_back_cover(src):
    return src.rindex('<div class="figcenter', 0, src.index('alt="Back cover"'))


BOOKS = {
    'north-woods-manhunt': dict(
        title='North Woods Manhunt', file='North_Woods_Manhunt', pg=58626, year=1948,
        end=lambda s: s.index('<p class="center p120">THE END</p>'),
        published='in 1948, published by Scripture Press of Wheaton, Illinois, as the sequel to ' + DIGS + '.',
        note='It follows straight on from ' + DIGS + ', where the gang has just dug the ransom money out of the old '
             'icehouse, and it finishes that story.',
        description='The Sugar Creek Gang in the North Woods: the story begun in The Sugar Creek Gang Digs for '
                    'Treasure, carried to its end.'),
    'shenanigans-at-sugar-creek': dict(
        title='Shenanigans at Sugar Creek', file='Shenanigans_at_Sugar_Creek', pg=27426, year=1947, curl=True,
        end=lambda s: s.index('<p class="center"><br>THE END</p>'),
        published='in 1947, published by Wm. B. Eerdmans of Grand Rapids, Michigan. It comes just before '
                  '<i>The Sugar Creek Gang Goes North</i> in the order of the stories.',
        note='It is a winter story at home, with a new schoolteacher the gang does not want, and it comes just '
             'before <i>The Sugar Creek Gang Goes North</i>.',
        description='A winter at Sugar Creek: a new teacher, a mischievous idea from a library book, and the '
                    'trouble that follows.'),
    'watermelon-mystery': dict(
        title='Watermelon Mystery at Sugar Creek', file='Watermelon_Mystery_at_Sugar_Creek', pg=58628, year=1955,
        end=end_before_back_cover,
        published='in 1955, published by Scripture Press of Wheaton, Illinois. It is the latest of the Sugar Creek '
                  'stories on this shelf.',
        note='It is a summer story at home, some years on from the gang’s trips to the North Woods.',
        description='Something strange is going on in the watermelon patch in the middle of the night, and the '
                    'Sugar Creek Gang means to find out what.'),
}


def words(x):
    x = html.unescape(re.sub(r'<[^>]+>', ' ', x))
    return [w.lower().replace('’', "'") for w in WORD.findall(x)]


def strip_apparatus(x):
    x = re.sub(r'<!--.*?-->', '', x, flags=re.S)
    return re.sub(r'<span class="pagenum"[^>]*>.*?</span>', '', x, flags=re.S)


ELIDED = ("'cause", "'em", "'til", "'n'", "'round", "'bout", "'s'")


def curl(x):
    """Straight quotes to curly ones by position, in text only (never inside a tag)."""
    parts = re.split(r'(<[^>]+>)', x)
    prev = ' '
    for k, part in enumerate(parts):
        if part.startswith('<'):
            continue
        out = []
        for j, ch in enumerate(part):
            if j + 1 < len(part):
                nxt = part[j + 1]
            else:   # the next character may sit after a tag: ’<i>drastic</i>’
                nxt = next((q[0] for q in parts[k + 1:] if q and not q.startswith('<')), ' ')
            if ch == '"':
                after_dash = prev in '—–-' and not nxt.isspace() and nxt not in ',.;:!?)'   # —“Now  vs  but—” then
                out.append('“' if prev in ' \n(“‘' or after_dash else '”')
            elif ch == "'":
                rest = part[j:j + 6].lower()
                if prev in ' \n(—–“' and nxt.isalpha() and not rest.startswith(ELIDED):
                    out.append('‘')
                else:
                    out.append('’')
            else:
                out.append(ch)
            prev = ch
        parts[k] = ''.join(out).replace('--', '—')
    return ''.join(parts)


def inline(x, book):
    """Keep italics; drop anchors, page numbers, comments and every other span."""
    x = strip_apparatus(x)
    x = re.sub(r'</?(?:a|span)\b[^>]*>', '', x)
    x = re.sub(r'<br\s*/?>', '<br/>', x)
    x = re.sub(r'\s+', ' ', x).strip()
    return curl(x) if book.get('curl') else x


def chapter_body(src, book):
    """Each block of the story, in order, set by kind. Unknown blocks stop the run."""
    out = []
    pos = 0
    blocks = re.compile(r'<(p|blockquote|div)\b([^>]*)>', re.S)
    empty = lambda s: not re.sub(r'<hr[^>]*>|</div>|<div class="chapter">|\s', '', strip_apparatus(s))   # the wrapper a chapter sits in
    while True:
        m = blocks.search(src, pos)
        if not m:
            if not empty(src[pos:]):
                sys.exit(f'unplaced text: {src[pos:pos + 120]}')
            break
        if not empty(src[pos:m.start()]):
            sys.exit(f'text outside a block: {src[pos:m.start()][:120]}')
        tag, attrs = m.group(1), m.group(2)
        depth, i = 1, m.end()
        opener, closer = re.compile(rf'<{tag}\b'), f'</{tag}>'
        while depth:
            c = src.find(closer, i)
            o = opener.search(src, i)
            if o and o.start() < c:
                depth, i = depth + 1, o.end()
            else:
                depth, i = depth - 1, c + len(closer)
        inner = src[m.end():i - len(closer)]
        pos = i
        if tag == 'p':
            out.append(f'<p>{inline(inner, book)}</p>')
        elif tag == 'blockquote':           # a written note or letter in the story
            ps = [inline(p, book) for p in re.findall(r'<p\b[^>]*>(.*?)</p>', inner, re.S)]
            out.append('<blockquote>\n' + '\n'.join(f'<p>{p}</p>' for p in ps) + '\n</blockquote>')
        elif 'poetry-container' in attrs:   # a poem, line by line
            lines = [inline(l, book) for l in re.findall(r'<div class="line[^"]*">(.*?)</div>', inner, re.S)]
            out.append('<p class="verse">' + '<br/>'.join(lines) + '</p>')
        elif 'class="poem"' in attrs or 'class="blockcenter"' in attrs:   # older markup: lines split by <br>
            lines = [inline(l, book) for l in re.split(r'<br\s*/?>', inner)]
            out.append('<p class="verse">' + '<br/>'.join(l for l in lines if l) + '</p>')
        elif empty(inner):
            continue
        else:
            sys.exit(f'unhandled block <{tag}{attrs}>: {inner[:120]}')
    return '\n'.join(out)


def page(title, body, kind='bodymatter', sect='chapter'):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n'
            f'<head><title>{html.escape(title)}</title><meta charset="utf-8"/><link rel="stylesheet" '
            'type="text/css" href="../css/style.css"/></head>\n'
            f'<body epub:type="{kind}"><section epub:type="{sect}" class="{sect}">\n{body}\n</section></body></html>\n')


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in BOOKS:
        sys.exit(__doc__ + '\nbooks: ' + ', '.join(BOOKS))
    bid, book = sys.argv[1], BOOKS[sys.argv[1]]
    TITLE = book['title']
    out_dir = ROOT / 'books' / bid
    epub = out_dir / f'Hutchens_Paul-SchriftOhr_Edition-{book["file"]}.epub'
    src = open(sys.argv[2], encoding='utf-8').read()
    cover = pathlib.Path(sys.argv[3])
    heads_re = r'<h2><a id="[^"]+"></a>(\d+)</h2>'
    start = re.search(heads_re, src).start()
    start = src.rfind('<div class="chapter">', 0, start) if src.rfind('<div class="chapter">', 0, start) > src.rfind('</p>', 0, start) else start
    story = src[start:book['end'](src)]
    # The older files wrap each heading in its own <div class="chapter">; unwrap it so the heading stands alone.
    story = re.sub(r'<div class="chapter">\s*((?:<!--.*?-->|<span class="pagenum".*?</span>|\s)*)(<h2>.*?</h2>)\s*</div>',
                   r'\1\2', story, flags=re.S)
    heads = list(re.finditer(heads_re, story))
    chapters = []
    for k, h in enumerate(heads):
        body = story[h.end():heads[k + 1].start() if k + 1 < len(heads) else len(story)]
        chapters.append((int(h.group(1)), chapter_body(body, book)))
    if [n for n, _ in chapters] != list(range(1, len(chapters) + 1)):
        sys.exit(f'chapters out of order: {[n for n, _ in chapters]}')

    # Words in, words out: the edition must carry every word of the story, and nothing else.
    src_words = words(re.sub(r'</?span[^>]*>', '', strip_apparatus(story)))
    src_words = [w for w in src_words if not re.fullmatch(r'\d+', w)]
    ed_words = [w for _, b in chapters for w in words(b) if not re.fullmatch(r'\d+', w)]
    if src_words != ed_words:
        import difflib
        for op, a1, a2, b1, b2 in difflib.SequenceMatcher(None, src_words, ed_words, autojunk=False).get_opcodes():
            if op != 'equal':
                print(op, src_words[a1:a2][:20], ed_words[b1:b2][:20])
        sys.exit('words differ between source and edition')
    print(f'{len(chapters)} chapters, {len(ed_words)} words, every source word accounted for')

    with zipfile.ZipFile(TEMPLATE) as z:
        tpl = {n: z.read(n) for n in z.namelist()}
    work = pathlib.Path(tempfile.mkdtemp())
    for n, data in tpl.items():
        if n.endswith('/') or re.search(r'/text/C\d\d\.xhtml$', n):
            continue
        p = work / n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    t = work / 'OEBPS/text'
    for n, body in chapters:
        (t / f'C{n:02d}.xhtml').write_text(page(f'Chapter {n}', f'<h2>Chapter {n}</h2>\n{body}'), encoding='utf-8')
    shutil.copy(cover, work / 'OEBPS/images/cover.jpg')

    def swap(rel, pairs):
        p = work / rel
        s = p.read_text(encoding='utf-8')
        for old, new in pairs:
            if s.count(old) != 1:
                sys.exit(f'{rel}: expected one "{old[:50]}", found {s.count(old)}')
            s = s.replace(old, new)
        p.write_text(s, encoding='utf-8')

    swap('OEBPS/text/00-title.xhtml', [
        ('<title>The Sugar Creek Gang Digs for Treasure</title>', f'<title>{TITLE}</title>'),
        ('<h1>The Sugar Creek Gang Digs for Treasure</h1>', f'<h1>{TITLE}</h1>'),
        ('<p class="reissue">Reissued September 2026</p>\n', '')])
    swap('OEBPS/text/01-edition-note.xhtml', [
        ('<i>The Sugar Creek Gang Digs for Treasure</i>', f'<i>{TITLE}</i>'),
        ('as he wrote it in 1948. Nothing has been modernised, abridged, or rewritten. ',
         f'as he wrote it in {book["year"]}. '),
        ('— the page numbers scattered mid-sentence, the broken lines, the apparatus of the scan — ',
         'the page numbers scattered mid-sentence, the broken lines, the apparatus of the scan, '),
        ('<p>This copy (build 2026-11-02.1) puts right twenty-four places where a word had gone wrong in transcription, '
         'found by reading every sentence for its sense.</p>',
         f'<p>{book["note"]} Every sentence has been read for its sense before this copy was set.</p>')])
    swap('OEBPS/text/97-sources.xhtml', [
        ('<i>The Sugar Creek Gang Digs for Treasure</i> as one of his Sugar Creek Gang stories, published in 1948.',
         f'<i>{TITLE}</i> {book["published"]}'),
        ('made the digital edition from which ours was prepared, and we retrieved it through <i>OpenChapter.io</i>, '
         'which keeps those files reachable when Project Gutenberg itself is not. Freely given',
         f'made the digital edition (ebook {book["pg"]}) from which ours was prepared. Freely given')])
    swap('OEBPS/text/00-proofing.xhtml', [
        ('The Sugar Creek Gang Digs for Treasure &#183; Paul Hutchens', f'{TITLE} &#183; {AUTHOR}')])

    nav = work / 'OEBPS/nav.xhtml'
    s = nav.read_text(encoding='utf-8').replace('>The Sugar Creek Gang Digs for Treasure<', f'>{TITLE}<')
    s = re.sub(r'(\s*<li><a href="text/C\d\d\.xhtml">Chapter \d+</a></li>)+',
               ''.join(f'\n      \n      <li><a href="text/C{n:02d}.xhtml">Chapter {n}</a></li>' for n, _ in chapters),
               s, count=1)
    nav.write_text(s, encoding='utf-8')
    opf = work / 'OEBPS/content.opf'
    s = opf.read_text(encoding='utf-8')
    s = re.sub(r'\s*<item id="t\d+" href="text/C\d\d\.xhtml"[^>]*/>', '', s)
    s = re.sub(r'\s*<itemref idref="t([3-9]|1[01])"/>', '', s)
    s = s.replace('    <item id="t12" href="text/97-sources.xhtml"',
                  ''.join(f'    <item id="c{n:02d}" href="text/C{n:02d}.xhtml" media-type="application/xhtml+xml"/>\n'
                          for n, _ in chapters) + '    <item id="t12" href="text/97-sources.xhtml"')
    s = s.replace('    <itemref idref="t1"/>',
                  '    <itemref idref="t1"/>' + ''.join(f'\n    <itemref idref="c{n:02d}"/>' for n, _ in chapters))
    opf.write_text(s, encoding='utf-8')
    swap('OEBPS/content.opf', [
        ('urn:uuid:698974f4-4495-43e9-a844-664628ba2b23', f'urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, "schriftohr:" + bid)}'),
        ('<dc:title>The Sugar Creek Gang Digs for Treasure</dc:title>', f'<dc:title>{TITLE}</dc:title>'),
        ('<dc:description>A reading edition of Paul Hutchens&#x27;s Sugar Creek Gang story, set with real chapter '
         'divisions and cleaned for reading and listening.</dc:description>',
         f'<dc:description>{html.escape(book["description"])}</dc:description>'),
        ('Project Gutenberg ebook 56553, retrieved via OpenChapter.io', f'Project Gutenberg ebook {book["pg"]}'),
        ('<dc:date>2026-08-22</dc:date>', f'<dc:date>{DATE}</dc:date>'),
        ('<meta property="dcterms:modified">2026-09-24T19:52:57Z</meta>',
         f'<meta property="dcterms:modified">{DATE}T00:00:00Z</meta>')])

    out_dir.mkdir(exist_ok=True)
    if cover.resolve() != (out_dir / 'cover.jpg').resolve():
        shutil.copy(cover, out_dir / 'cover.jpg')
    if epub.exists():
        epub.unlink()
    subprocess.run(['zip', '-qX0', str(epub), 'mimetype'], cwd=work, check=True)
    subprocess.run(['zip', '-qXr9', str(epub), 'META-INF', 'OEBPS'], cwd=work, check=True)
    print(epub)


if __name__ == '__main__':
    main()
