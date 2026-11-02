#!/usr/bin/env python3
"""The Rare Jewel, step two of its modernising: the forms of address and the old verb endings (John, 2026-11-02:
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
    wd.mkdir(parents=True, exist_ok=True)
    work = pathlib.Path(tempfile.mkdtemp())
    with zipfile.ZipFile(src) as z:
        z.extractall(work)
    T = work / 'OEBPS/text'
    files = [f for f in sorted(T.glob('*.xhtml')) if re.match(r'(S\d\d|90-|02-to-the-reader)', f.name)]
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
    G = pathlib.Path(__file__).resolve().parent.parent / 'books/rare-jewel-of-christian-contentment/grammar.tsv'
    for line in G.read_text(encoding='utf-8').splitlines()[1:]:
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
    out = rare_jewel_refs.caps(out, caplog)
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
    # About This Edition says what this edition now is
    note = T / '01-edition-note.xhtml'; t = note.read_text(encoding='utf-8')
    a = ('Burroughs\u2019s words themselves are kept, hath and doth and thou among them, and the British spellings '
         'stand.')
    b = ('This is a modernised edition, made for clear reading and listening, not for interpretation. Thou and thee '
         'are you, hath is has, and the old endings of the verbs are the ones we use now; where a question or a '
         'command was put the old way, it is put as we would say it. Burroughs\u2019s words, his order of thought '
         'and his meaning are his own throughout. The British spellings stand.')
    if a not in t:
        sys.exit('!! About This Edition: the sentence on his words was not found')
    note.write_text(t.replace(a, b), encoding='utf-8')
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
