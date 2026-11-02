#!/usr/bin/env python3
"""Apply books/pilgrims-progress/corrections-from-offor.txt to the Pilgrim's Progress Edition (John, 2026-11-02).

Every line of that list was read on Offor's 1855 page and re-read in context before it was written:

    add    | CH | words      a paragraph begins at these words (the paragraph keeps its class)
    stanza | CH | words      a verse paragraph is split before this line (a stanza gap)
    join   | CH | words      the paragraph beginning with these words runs on from the one before
    punct  | CH | old -> new the punctuation of these words, as Offor prints it

Words are matched in the text as read, through any markup (<em>, note references), and must occur exactly once in
the chapter, or the build stops. Spelling stays modern (John, 2026-11-01): only paragraphing and punctuation change.

    tools/correct_pilgrims.py BOOK.epub OUT.epub
"""
import html, pathlib, re, shutil, sys, tempfile, zipfile

HERE = pathlib.Path(__file__).resolve().parent
LIST = HERE.parent / 'books/pilgrims-progress/corrections-from-offor.txt'
BUILD = '2026-11-02.1'
NOTE = ('<p>In November 2026 the paragraphing and punctuation were read against Offor’s pages as well. Thirty-seven '
        'paragraphs he begins had been run into the one before, one had been broken in the middle of a speech, and three '
        'gaps between stanzas had closed; twenty-two marks of punctuation had slipped in transcription. Each is set as '
        'his page has it. The spelling is left modern, as it came to us.</p>')


def plain(x):
    """The text of an XHTML fragment, with a map from each text index to its index in the markup."""
    out, where, i = [], [], 0
    while i < len(x):
        if x[i] == '<':
            j = x.index('>', i)
            if re.match(r'<sup\b', x[i:j]):           # a note mark is not text
                j = x.index('</sup>', i) + len('</sup>') - 1
            elif x[i:j + 1].startswith('<br'):
                out.append(' '); where.append(i)
            i = j + 1
        elif x[i] == '&':
            j = x.index(';', i)
            out.append(html.unescape(x[i:j + 1])); where.append(i); i = j + 1
        else:
            out.append(x[i]); where.append(i); i += 1
    return ''.join(out), where


def norm(t):
    return re.sub(r'\s+', ' ', t)


def find(x, words, what):
    t, where = plain(x)
    t = norm(t) if False else t
    # match through runs of whitespace
    pat = re.compile(r'\s+'.join(re.escape(w) for w in words.split()))
    hits = list(pat.finditer(t))
    if len(hits) != 1:
        sys.exit(f'!! {what}: {words!r} found {len(hits)} times')
    m = hits[0]
    return m, where


def main():
    src, dst = sys.argv[1], sys.argv[2]
    work = pathlib.Path(tempfile.mkdtemp())
    with zipfile.ZipFile(src) as z:
        z.extractall(work)
    T = work / 'OEBPS/text'
    done = {'add': 0, 'stanza': 0, 'join': 0, 'punct': 0}
    for line in LIST.read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        kind, ch, words = [s.strip() for s in line.split('|', 2)]
        files = sorted(T.glob(f'{ch}-*.xhtml')) or sorted(T.glob(f'{ch}.xhtml'))
        if len(files) != 1:
            sys.exit(f'!! no single chapter {ch}')
        f = files[0]; x = f.read_text(encoding='utf-8')
        what = f'{kind} {ch}'
        if kind == 'punct':
            old, new = [s.strip() for s in words.split(' -> ')]
            m, where = find(x, old, what)
            # edit only the characters that differ, at their places in the markup
            import difflib
            a = m.group(0); ops = difflib.SequenceMatcher(None, a, new, autojunk=False).get_opcodes()
            for tag, i1, i2, j1, j2 in reversed(ops):
                if tag == 'equal':
                    continue
                if any(c.isalnum() for c in a[i1:i2] + new[j1:j2]):
                    sys.exit(f'!! {what}: a punctuation line changes letters: {a[i1:i2]!r} -> {new[j1:j2]!r}')
                if i1 < i2:
                    s, e = where[m.start() + i1], where[m.start() + i2 - 1] + 1
                else:   # an insertion after a[i1-1]
                    s = e = where[m.start() + i1 - 1] + 1
                    # past any closing inline tag or note mark that follows the character
                    while x[s:s + 2] == '</' or x[s:s + 4] == '<sup':
                        s = e = (x.index('</sup>', s) + 6) if x[s:s + 4] == '<sup' else x.index('>', s) + 1
                x = x[:s] + html.escape(new[j1:j2], quote=False) + x[e:]
        elif kind in ('add', 'stanza'):
            m, where = find(x, words, what)
            at = where[m.start()]
            # back over any opening inline tags that begin the words
            while at > 0 and x[:at].rstrip().endswith('>') and re.search(r'<(em|i|b|strong)\b[^>]*>\s*$', x[:at]):
                at = re.search(r'<(em|i|b|strong)\b[^>]*>\s*$', x[:at]).start()
            before = x[:at]
            p_open = before.rfind('<p')
            tag = re.match(r'<p\b[^>]*>', x[p_open:]).group(0)
            if '</p>' in x[p_open:at]:
                sys.exit(f'!! {what}: {words!r} already begins a paragraph')
            if kind == 'stanza' and 'verse' not in tag:
                sys.exit(f'!! {what}: not inside verse')
            head = before.rstrip()
            if re.search(r'(</p>|</ol>|</ul>|</li>|</blockquote>|</h\d>)\s*<p\b[^>]*>\s*$', before):
                sys.exit(f'!! {what}: {words!r} already begins a paragraph')
            if kind == 'stanza':
                head = re.sub(r'<br\s*/?>\s*$', '', head)
            x = head + '</p>\n' + tag + x[at:].lstrip()
        elif kind == 'join':
            m, where = find(x, words, what)
            at = where[m.start()]
            mm = re.search(r'</p>\s*<p\b[^>]*>\s*$', x[:at])
            if not mm:
                sys.exit(f'!! {what}: {words!r} does not begin a paragraph')
            x = x[:mm.start()] + ' ' + x[at:]
        else:
            sys.exit(f'!! unknown kind {kind}')
        f.write_text(x, encoding='utf-8'); done[kind] += 1
    print('applied', done)
    for q in T.glob('*.xhtml'):
        if re.search(r'<p\b[^>]*>\s*</p>', q.read_text(encoding='utf-8')):
            sys.exit(f'!! an empty paragraph in {q.name}')

    # the record: the Note on the Text says what was done; the stamp carries the build
    n = T / '99-note-on-the-text.xhtml'; t = n.read_text(encoding='utf-8')
    k = t.index('</table>', t.index('Corrections to the text')) + len('</table>')
    n.write_text(t[:k] + '\n' + NOTE + t[k:], encoding='utf-8')
    p = T / '00-proofing.xhtml'; t = p.read_text(encoding='utf-8')
    t2 = re.sub(r'build \d{4}-\d\d-\d\d\.\d+', f'build {BUILD}', t)
    assert t2 != t; p.write_text(t2, encoding='utf-8')
    opf = work / 'OEBPS/content.opf'; o = opf.read_text(encoding='utf-8')
    opf.write_text(re.sub(r'(<meta property="dcterms:modified">)[^<]*', r'\g<1>' + BUILD[:10] + 'T00:00:00Z', o), encoding='utf-8')

    out = pathlib.Path(dst)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, 'w') as z:
        z.write(work / 'mimetype', 'mimetype', compress_type=zipfile.ZIP_STORED)
        for q in sorted(work.rglob('*')):
            if q.is_file() and q.name != 'mimetype':
                z.write(q, q.relative_to(work).as_posix(), compress_type=zipfile.ZIP_DEFLATED)
    shutil.rmtree(work)
    print('wrote', out)


if __name__ == '__main__':
    main()
