#!/usr/bin/env python3
"""An Edition's light modernising, after spelling (the Rare Jewel method made general, 2026-11-03).

    tools/modern_forms.py BOOK.epub OUT.epub WORKDIR BOOKDIR AUTHOR YEAR UNIT

BOOKDIR holds the book's hand-read ledgers (grammar.tsv, clarity.tsv, shifted-words.tsv; each optional). AUTHOR is the
surname for the lettered notes ("Owen wrote"), YEAR and UNIT word the Words Brought Forward page ("since 1668",
"in each chapter"). About This Edition is not touched here: its wording is the book's own ledger.

Originally: The Rare Jewel, step two of its modernising: the forms of address and the old verb endings (John, 2026-11-02:
"One modernised edition", "modernization for reading clarity, not interpretation").

    tools/rare_jewel_modern_forms.py BOOK.epub OUT.epub WORKDIR

The same rules and the same proof as the Confessions (schriftohr-editions-working/tools/augustine_modernize.py and
augustine_prove_modern.py, run unchanged): thou, thee, thy, ye become you and your, the verb after thou loses its
-est, the -eth of the third person becomes -s (hath has, doth does, saith says), unto to, whence and whither and
wherefore by their sense. The proof then checks word for word that nothing else changed.

The book's markup, and the Greek and Hebrew with their sounds, are set aside as numbered marks {n} before the rules
run, so the rules see only Burroughs's English, and put back after. WORKDIR keeps the text before and after, the
doubts the rules wrote, and the proof's ledger.
"""
import html, pathlib, re, shutil, subprocess, sys, tempfile, zipfile

TOOLS = pathlib.Path('/Volumes/data/Developer/schriftohr-editions-working/tools')
SKIP = re.compile(r'<(span|i|b)\b[^>]*class="(?:gk|hb|ph)"[^>]*>.*?</\1>|<sup\b.*?</sup>|<[^>]+>', re.S)


def main():
    src, dst, wd = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
    BOOKDIR, AUTHOR, YEAR, UNIT = pathlib.Path(sys.argv[4]), sys.argv[5], sys.argv[6], sys.argv[7]
    wd.mkdir(parents=True, exist_ok=True)
    work = pathlib.Path(tempfile.mkdtemp())
    with zipfile.ZipFile(src) as z:
        z.extractall(work)
    T = work / 'OEBPS/text'
    FILES = sys.argv[8] if len(sys.argv) > 8 else r'(C\d\d|S\d\d|P\d\d|02-preface|02-to-the-reader|9\d-(?!sources|why|closing|words))'
    files = [f for f in sorted(T.glob('*.xhtml')) if re.match(FILES, f.name)]
    marks, parts = [], []
    for f in files:
        x = f.read_text(encoding='utf-8')
        a = x.index('<body')
        marks.append(x[:a]); parts.append('{%d}' % (len(marks) - 1))     # the head, set aside whole
        body, pos = x[a:], 0
        for m in SKIP.finditer(body):
            parts.append(html.unescape(body[pos:m.start()]))
            marks.append(m.group(0)); parts.append('{%d}' % (len(marks) - 1))
            pos = m.end()
        parts.append(html.unescape(body[pos:]))
        marks.append('\x00' + f.name); parts.append('{%d}' % (len(marks) - 1))   # where this file ends
    before = wd / 'before.txt'; after = wd / 'after.txt'
    before.write_text(''.join(parts), encoding='utf-8')
    r = subprocess.run([sys.executable, str(TOOLS / 'augustine_modernize.py'), str(before), str(after), str(wd / 'doubts.tsv')],
                       capture_output=True, text=True)
    print(r.stdout, r.stderr[-2000:])
    if r.returncode:
        sys.exit('!! the rules failed')
    p = subprocess.run([sys.executable, str(TOOLS / 'augustine_prove_modern.py'), str(before), str(after)],
                       capture_output=True, text=True)
    (wd / 'proof.txt').write_text(p.stdout + p.stderr, encoding='utf-8')
    print(p.stdout[-1500:], p.stderr[-1500:])
    if p.returncode:
        sys.exit('!! the proof failed; nothing written')
    # the grammar the rules cannot give, listed by hand (books/rare-jewel-of-christian-contentment/grammar.tsv):
    # each line must match exactly as often as it says, or nothing is written
    out = after.read_text(encoding='utf-8')
    G = BOOKDIR / 'grammar.tsv'
    for line in (G.read_text(encoding='utf-8').splitlines()[1:] if G.exists() else []):
        if not line.strip() or line.startswith('#'):
            continue
        g = line.split('\t')
        times = int(g[2]) if len(g) > 2 and g[2] else 1
        if out.count(g[0]) != times:
            sys.exit(f'!! grammar: {g[0]!r} found {out.count(g[0])} times, not {times}')
        out = out.replace(g[0], g[1])
    # clarity (step three): long sentences divided, punctuation made modern. Each line keeps the same words in the
    # same order, only stops, commas, semicolons and capitals may differ, and must match exactly once.
    C = G.parent / 'clarity.tsv'
    words = lambda x: re.findall(r"[A-Za-z0-9\u2019']+", x.lower())
    missed = []
    if C.exists():
        for line in C.read_text(encoding='utf-8').splitlines()[1:]:
            if not line.strip() or line.startswith('#'):
                continue
            a, b = line.split('\t')[:2]
            if words(a) != words(b):
                sys.exit(f'!! clarity changes words: {a[:60]!r}')
            if out.count(a) != 1:
                missed.append(f'{out.count(a)}x {a!r}'); continue
            out = out.replace(a, b)
        if missed:
            sys.exit('!! clarity lines that do not match exactly once:\n' + '\n'.join(missed))
    # references and abbreviations, spelled out for the voice (tools/rare_jewel_refs.py); every change listed
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import rare_jewel_refs
    reflog = []
    out = rare_jewel_refs.refs(out, reflog)
    (wd / 'references.tsv').write_text('was\tnow\n' + ''.join(f'{a}\t{b}\n' for a, b in reflog), encoding='utf-8')
    print(f'{len(reflog)} references and abbreviations spelled out')
    caplog, before_caps = [], out
    # never in a heading or the editor's line under it: those are titles, set in title case
    seen = set(re.findall(r"\b[a-z][a-z’']+\b", out))
    # caps-keep.txt (one word a line) widens the rule for a book that capitalised nearly every noun (Owen): any word
    # an English dictionary has in lower case may be lowered, except the names listed there (Job, Peter) and a
    # book of Scripture before its chapter (Revelation 3:4). Repeated until nothing changes, so a run of capitals
    # (a Metaphorical Expression) comes down whole.
    KEEP = BOOKDIR / 'caps-keep.txt'
    widen = KEEP.exists()
    if widen:
        common = {w.strip() for w in open('/usr/share/dict/words', encoding='utf-8') if w[:1].islower()}
        seen |= common | {w + 's' for w in common} | {w + 'es' for w in common} | {w[:-1] + 'ies' for w in common if w.endswith('y')}
        rare_jewel_refs.PROTECT |= {w.strip() for w in KEEP.read_text(encoding='utf-8').split() if w.strip()}
        out = re.sub(r'\b([A-Z][a-z]+)(?= \d)', '\x03\\1', out)
    pieces, keep = re.split(r'(\{\d+\})', out), False
    for i, piece in enumerate(pieces):
        m = re.fullmatch(r'\{(\d+)\}', piece)
        if m:
            mk = marks[int(m.group(1))]
            if re.match(r'<h\d|<p class="argument"', mk):
                keep = True
            elif re.match(r'</h\d|</p>', mk):
                keep = False
        elif not keep:
            while True:
                was = piece; piece = rare_jewel_refs.caps(piece, caplog, seen)
                if piece == was or not widen:
                    break
            pieces[i] = piece
    out = ''.join(pieces).replace('\x03', '')
    before_caps = before_caps.replace('\x03', '')
    if before_caps.lower() != out.lower():
        sys.exit('!! capitals step changed more than capitals')
    print(f'{len(caplog)} common nouns set in lower case')
    # put the marks back, one file at a time
    cur, buf = None, []
    for piece in re.split(r'(\{\d+\})', out):
        m = re.fullmatch(r'\{(\d+)\}', piece)
        if not m:
            buf.append(html.escape(piece, quote=False)); continue
        mark = marks[int(m.group(1))]
        if mark.startswith('\x00'):
            (T / mark[1:]).write_text(''.join(buf), encoding='utf-8'); buf = []
        else:
            buf.append(mark)
    # Words whose meaning has moved (shifted-words.tsv): the modern word in the text, and on its first use in each
    # chapter a lettered note giving the word Burroughs wrote. Letters, so a word note is told at a glance from the
    # numbered notes on Greek and Scripture. Text only: never inside markup, the Greek or a note.
    rows = []
    SW = G.parent / 'shifted-words.tsv'
    for line in (SW.read_text(encoding='utf-8').splitlines() if SW.exists() else []):
        if line.strip() and not line.startswith('#'):
            pat, rep, old_w = line.split('\t')
            rows.append((re.compile(r'\b' + pat + r'\b', re.I), rep, old_w))
    LET = 'abcdefghijklmnopqrstuvwxyz'
    total = 0
    for f in files:
        x = f.read_text(encoding='utf-8')
        a = x.index('<body'); body = x[a:]
        k = body.find('<section epub:type="endnotes"')
        main, tail = (body[:k], body[k:]) if k >= 0 else (body, '')
        notes, seen = [], set()
        def edit(seg):
            def textnode(t):
                s = html.unescape(t.group(0))
                for rx, rep, old_w in rows:
                    def one(m):
                        nonlocal_total[0] += 1
                        new = rep[0].upper() + rep[1:] if m.group(0)[0].isupper() else rep
                        if old_w in seen:
                            return new
                        seen.add(old_w); notes.append(old_w); n = len(notes) - 1
                        return new + '\x01%d\x02' % n
                    s = rx.sub(one, s)
                return html.escape(s, quote=False)
            return re.sub(r'(?<=>)[^<]+', textnode, seg)
        nonlocal_total = [0]
        out_main, pos = [], 0
        for m in re.finditer(r'<(span|i|b)\b[^>]*class="(?:gk|hb|ph)"[^>]*>.*?</\1>|<a\b[^>]*class="nref".*?</a>', main, re.S):
            out_main.append(edit(main[pos:m.start()])); out_main.append(m.group(0)); pos = m.end()
        out_main.append(edit(main[pos:]))
        main = ''.join(out_main)
        main = re.sub('\x01(\d+)\x02', lambda m: (f'<a epub:type="noteref" href="#wn{m.group(1)}" id="wr{m.group(1)}" '
                      f'class="nref wref"><sup>{LET[int(m.group(1))]}</sup></a>'), main)
        if notes:
            asides = ''.join(f' <aside epub:type="footnote" id="wn{i}" class="fn wn"><p><a href="#wr{i}">{LET[i]}.</a> '
                             f'{AUTHOR} wrote <i>{html.escape(w)}</i>.</p></aside>' for i, w in enumerate(notes))
            if tail:
                tail = tail.replace('<hr/>', '<hr/>' + asides, 1)
            else:
                main = main.replace('</section></body>', '<section epub:type="endnotes" class="notes"><hr/>' + asides
                                    + '</section></section></body>', 1)
        total += nonlocal_total[0]
        f.write_text(x[:a] + main + tail, encoding='utf-8')
    print(f'{total} words whose meaning has moved, given their modern word')
    # The back page: every word brought forward, in one list
    pairs = []
    for rx, rep, old_w in rows:
        if (old_w, rep) not in pairs and not (old_w == 'dispose' and rep == 'disposal'):
            pairs.append((old_w, rep))
    pairs = sorted(set(pairs) | ({('dispose', 'ordering, disposal')} if any(o == 'dispose' for o, _ in pairs) else set()))
    pairs = [x for x in pairs if not (x[0] == 'dispose' and x[1] == 'ordering')]
    if not pairs:
        rows = []
    head = (T / '01-edition-note.xhtml').read_text(encoding='utf-8')
    head = head[:head.index('<body')].replace('<title>About This Edition</title>', '<title>Words Brought Forward</title>')
    items = ''.join(f'<tr><td><i>{html.escape(o)}</i></td><td>{html.escape(n)}</td></tr>' for o, n in pairs)
    (T / '96-words.xhtml').write_text(head + '<body epub:type="backmatter"><section epub:type="glossary" class="preamble">'
        '<h2>Words Brought Forward</h2><p>A few of ' + AUTHOR + '\u2019s words have changed their meaning since ' + YEAR + '. In this '
        'edition each is given in the word we would use now, and a lettered note at its first use in each ' + UNIT + ' shows '
        'the word he wrote. These are the words.</p><table class="words"><tr><th>He wrote</th><th>This edition has'
        '</th></tr>' + items + '</table></section></body></html>', encoding='utf-8')
    opf = work / 'OEBPS/content.opf'; o = opf.read_text(encoding='utf-8')
    if '96-words.xhtml' not in o:
        o = o.replace('</manifest>', '  <item id="words" href="text/96-words.xhtml" media-type="application/xhtml+xml"/>\n  </manifest>', 1)
        ed = re.search(r'<item id="([^"]+)" href="text/01-edition-note.xhtml"', o).group(1)
        o = re.sub(r'(<itemref idref="' + re.escape(ed) + r'"[^>]*/>)', r'\1\n    <itemref idref="words"/>', o, 1)
        opf.write_text(o, encoding='utf-8')
    nav = work / 'OEBPS/nav.xhtml'; n = nav.read_text(encoding='utf-8')
    if '96-words.xhtml' not in n:
        n = n.replace('<li><a href="text/01-edition-note.xhtml">About This Edition</a></li>',
                      '<li><a href="text/01-edition-note.xhtml">About This Edition</a></li>\n'
                      '      <li><a href="text/96-words.xhtml">Words Brought Forward</a></li>', 1)
        nav.write_text(n, encoding='utf-8')
    css = work / 'OEBPS/css/style.css'; c = css.read_text(encoding='utf-8')
    if 'table.words' not in c:
        css.write_text(c + '\ntable.words{border-collapse:collapse;margin:1em 0}table.words td,table.words th{text-align:left;'
                       'padding:.2em 1.2em .2em 0;vertical-align:top}\n', encoding='utf-8')
    o = pathlib.Path(dst)
    if o.exists():
        o.unlink()
    with zipfile.ZipFile(o, 'w') as z:
        z.write(work / 'mimetype', 'mimetype', compress_type=zipfile.ZIP_STORED)
        for q in sorted(work.rglob('*')):
            if q.is_file() and q.name != 'mimetype':
                z.write(q, q.relative_to(work).as_posix(), compress_type=zipfile.ZIP_DEFLATED)
    shutil.rmtree(work)
    print('wrote', o)


if __name__ == '__main__':
    main()
