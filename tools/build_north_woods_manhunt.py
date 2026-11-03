#!/usr/bin/env python3
"""North Woods Manhunt (Hutchens, 1948), the sequel that finishes The Sugar Creek Gang Digs for Treasure.

    tools/build_north_woods_manhunt.py PG58626.html COVER.jpg

Built from Project Gutenberg 58626 (the HTML), with Digs for Treasure as the template for every page that is
not story, so the two read as a pair. Not tools/build_edition.py: that builder drops any block that holds other
blocks (a stanza in its container, a letter in a blockquote). Here every block in the story is set by kind, and the
run stops if the words in the edition differ from the words in the source.
"""
import html, pathlib, re, shutil, subprocess, sys, tempfile, uuid, zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = next((ROOT / 'books/sugar-creek-digs-for-treasure').glob('*.epub'))
BOOK = ROOT / 'books/north-woods-manhunt'
EPUB = BOOK / 'Hutchens_Paul-SchriftOhr_Edition-North_Woods_Manhunt.epub'
TITLE, AUTHOR, BUILD, DATE = 'North Woods Manhunt', 'Paul Hutchens', '2026-11-02.1', '2026-11-02'
UID = uuid.uuid5(uuid.NAMESPACE_URL, 'schriftohr:north-woods-manhunt')
WORD = re.compile(r"[A-Za-z0-9]+(?:['’][A-Za-z]+)*")


def words(x):
    x = html.unescape(re.sub(r'<[^>]+>', ' ', x))
    return [w.lower().replace('’', "'") for w in WORD.findall(x)]


def inline(x):
    """Keep italics; drop anchors, page numbers and every other span."""
    x = re.sub(r'<span class="pagenum"[^>]*>.*?</span>', '', x, flags=re.S)
    x = re.sub(r'</?(?:a|span)\b[^>]*>', '', x)
    x = re.sub(r'<i>', '<i>', x)
    x = re.sub(r'<br\s*/?>', '<br/>', x)
    return re.sub(r'\s+', ' ', x).strip()


def chapter_body(src):
    """Each block of the story, in order, set by kind. Unknown blocks stop the run."""
    out = []
    pos = 0
    blocks = re.compile(r'<(p|blockquote|div)\b([^>]*)>', re.S)
    while True:
        m = blocks.search(src, pos)
        if not m:
            rest = re.sub(r'<hr[^>]*>|\s', '', src[pos:])
            if rest:
                sys.exit(f'unplaced text: {rest[:120]}')
            break
        gap = re.sub(r'<hr[^>]*>|<span class="pagenum"[^>]*>.*?</span>|\s', '', src[pos:m.start()], flags=re.S)
        if gap:
            sys.exit(f'text outside a block: {gap[:120]}')
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
            out.append(f'<p>{inline(inner)}</p>')
        elif tag == 'blockquote':          # a written note or letter in the story
            ps = [inline(p) for p in re.findall(r'<p\b[^>]*>(.*?)</p>', inner, re.S)]
            out.append('<blockquote>\n' + '\n'.join(f'<p>{p}</p>' for p in ps) + '\n</blockquote>')
        elif 'poetry-container' in attrs:  # a poem, line by line
            lines = [inline(l) for l in re.findall(r'<div class="line[^"]*">(.*?)</div>', inner, re.S)]
            out.append('<p class="verse">' + '<br/>'.join(lines) + '</p>')
        elif not re.sub(r'<hr[^>]*>|<span class="pagenum"[^>]*>.*?</span>|\s', '', inner, flags=re.S):
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
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src = open(sys.argv[1], encoding='utf-8').read()
    cover = pathlib.Path(sys.argv[2])
    start = src.index('<h2><a id="i"></a>1</h2>')
    end = src.index('<p class="center p120">THE END</p>')
    story = src[start:end]
    heads = list(re.finditer(r'<h2><a id="[ivx]+"></a>(\d+)</h2>', story))
    chapters = []
    for k, h in enumerate(heads):
        body = story[h.end():heads[k + 1].start() if k + 1 < len(heads) else len(story)]
        chapters.append((int(h.group(1)), chapter_body(body)))

    # Words in, words out: the edition must carry every word of the story, and nothing else.
    src_words = words(re.sub(r'</?span[^>]*>', '', re.sub(r'<span class="pagenum"[^>]*>.*?</span>', '', story, flags=re.S)))
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
        ('as he wrote it in 1948. Nothing has been modernised, abridged, or rewritten. ', 'as he wrote it in 1948. '),
        ('— the page numbers scattered mid-sentence, the broken lines, the apparatus of the scan — ',
         'the page numbers scattered mid-sentence, the broken lines, the apparatus of the scan, '),
        ('<p>This copy (build 2026-11-02.1) puts right twenty-four places where a word had gone wrong in transcription, '
         'found by reading every sentence for its sense.</p>',
         '<p>It follows straight on from <i>The Sugar Creek Gang Digs for Treasure</i>, where the gang has just dug the '
         'ransom money out of the old icehouse, and it finishes that story. Every sentence has been read for its sense '
         'before this copy was set.</p>')])
    swap('OEBPS/text/97-sources.xhtml', [
        ('<i>The Sugar Creek Gang Digs for Treasure</i> as one of his Sugar Creek Gang stories, published in 1948.',
         f'<i>{TITLE}</i> in 1948, published by Scripture Press of Wheaton, Illinois, as the sequel to <i>The Sugar '
         'Creek Gang Digs for Treasure</i>.'),
        ('made the digital edition from which ours was prepared, and we retrieved it through <i>OpenChapter.io</i>, '
         'which keeps those files reachable when Project Gutenberg itself is not. Freely given',
         'made the digital edition (ebook 58626) from which ours was prepared. Freely given')])
    swap('OEBPS/text/00-proofing.xhtml', [
        ('The Sugar Creek Gang Digs for Treasure &#183; Paul Hutchens', f'{TITLE} &#183; {AUTHOR}')])
    nav = work / 'OEBPS/nav.xhtml'
    s = nav.read_text(encoding='utf-8').replace('>The Sugar Creek Gang Digs for Treasure<', f'>{TITLE}<')
    s = s.replace('      <li><a href="text/C09.xhtml">Chapter 9</a></li>',
                  '      <li><a href="text/C09.xhtml">Chapter 9</a></li>\n      \n'
                  '      <li><a href="text/C10.xhtml">Chapter 10</a></li>')
    nav.write_text(s, encoding='utf-8')
    swap('OEBPS/content.opf', [
        ('urn:uuid:698974f4-4495-43e9-a844-664628ba2b23', f'urn:uuid:{UID}'),
        ('<dc:title>The Sugar Creek Gang Digs for Treasure</dc:title>', f'<dc:title>{TITLE}</dc:title>'),
        ('<dc:description>A reading edition of Paul Hutchens&#x27;s Sugar Creek Gang story, set with real chapter '
         'divisions and cleaned for reading and listening.</dc:description>',
         '<dc:description>The Sugar Creek Gang in the North Woods: the story begun in The Sugar Creek Gang Digs for '
         'Treasure, carried to its end.</dc:description>'),
        ('Project Gutenberg ebook 56553, retrieved via OpenChapter.io', 'Project Gutenberg ebook 58626'),
        ('<dc:date>2026-08-22</dc:date>', f'<dc:date>{DATE}</dc:date>'),
        ('<meta property="dcterms:modified">2026-09-24T19:52:57Z</meta>',
         f'<meta property="dcterms:modified">{DATE}T00:00:00Z</meta>'),
        ('    <item id="t11" href="text/C09.xhtml" media-type="application/xhtml+xml"/>',
         '    <item id="t11" href="text/C09.xhtml" media-type="application/xhtml+xml"/>\n'
         '    <item id="t13" href="text/C10.xhtml" media-type="application/xhtml+xml"/>'),
        ('    <itemref idref="t11"/>', '    <itemref idref="t11"/>\n    <itemref idref="t13"/>')])

    BOOK.mkdir(exist_ok=True)
    shutil.copy(cover, BOOK / 'cover.jpg')
    if EPUB.exists():
        EPUB.unlink()
    subprocess.run(['zip', '-qX0', str(EPUB), 'mimetype'], cwd=work, check=True)
    subprocess.run(['zip', '-qXr9', str(EPUB), 'META-INF', 'OEBPS'], cwd=work, check=True)
    print(EPUB)


if __name__ == '__main__':
    main()
