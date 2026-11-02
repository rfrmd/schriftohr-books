#!/usr/bin/env python3
"""Correct the SchriftOhr Edition of The Adventures of Sherlock Holmes (John, 2026-11-01).

The shelf book carried the collation's leftovers: misread figures ("the 2oth of March, I888I"), words one scan
misread and the other could not check, dialogue run together into one paragraph, paragraphs broken at page
turns, stray spaces inside the punctuation, and straight quotation marks. Every correction here is read off our
own scan of the 1892 Harper printing (witness A in the private archive), never taken from another edition.

    tools/correct_sherlock.py BOOK.epub OUT.epub [--ledger sherlock-corrections.tsv]

Four passes, in this order, each on the twelve Adventures only:
  1. paragraphs   - a paragraph begins where the 1892 page indents a line. Witness A's per-line geometry gives
                    the indents; our words are aligned to witness A's, so each indented line marks a break
                    before the word it starts with. Breaks the page does not have are taken out.
  2. spacing      - no space before , ; : ? ! or a closing quotation mark, none after an opening one.
  3. the ledger   - sherlock-corrections.tsv: was, now, page, why. Each "was" must occur exactly once in its
                    Adventure; a ledger line that matches nothing or twice stops the build.
  4. quotation marks - curly, opening or closing by position; apostrophes curly.
"""
import argparse, collections, difflib, glob, html, os, pathlib, re, shutil, subprocess, sys, tempfile, unicodedata, zipfile

HERE = pathlib.Path(__file__).resolve().parent
ARCHIVE = pathlib.Path(os.environ.get('SHERLOCK_ARCHIVE', HERE.parent.parent / 'schriftohr-editions-working/books/06-sherlock-holmes'))
WITNESS_A = ARCHIVE / 'witness-a-google'


def nw(w):
    w = unicodedata.normalize('NFKD', w.lower())
    return re.sub(r'[^a-z0-9]', '', w)


# ── witness A: its words in page order, and the paragraph starts its indents show ──────────────────────
def witness_a():
    lines = []                      # (page, y0, x0, x1, text) with Vision's split segments joined
    for f in sorted(WITNESS_A.glob('*.tsv')):
        pg = int(re.search(r'_(\d+)\.tsv', f.name).group(1))
        segs = []
        for l in f.read_text(encoding='utf-8').splitlines():
            p = l.split('\t')
            if len(p) >= 6:
                segs.append((float(p[1]), float(p[4]), float(p[5]), p[0]))
        segs.sort()
        rows = []
        for y0, x0, x1, t in segs:  # one printed line can come back as two segments
            if rows and abs(rows[-1][0] - y0) < 0.006:
                r = rows[-1]
                parts = sorted([(r[1], r[3]), (x0, t)])
                rows[-1] = (r[0], min(r[1], x0), max(r[2], x1), ' '.join(s for _, s in parts))
            else:
                rows.append((y0, x0, x1, t))
        lines += [(pg,) + r for r in rows]
    words, starts = [], set()
    for k, (pg, y0, x0, x1, t) in enumerate(lines):
        near = [l[2] for l in lines[max(0, k - 5):k + 6] if l[0] == pg and l[3] - l[2] > 0.5]
        margin = sorted(near)[len(near) // 2] if near else x0     # the page's left edge here (pages are skewed)
        indented = x0 - margin > 0.012 and x0 - margin < 0.15
        # ...and only after a line that ends a sentence: lines wrapping round a drop capital are indented too
        prev = next((l for l in reversed(lines[max(0, k - 12):k]) if l[1] > 0.06), None)   # not a running head
        if indented and prev and re.search(r'[A-Za-z0-9,;-]$', prev[4].strip()):
            indented = False
        first = True
        for w in t.split():
            n = nw(w)
            if not n:
                continue
            if first and indented:
                starts.add(len(words))
            words.append(n)
            first = False
    return words, starts


# ── the book: each Adventure as its paragraphs, with the plates kept in place ─────────────────────────
PARA = re.compile(r'<p>(.*?)</p>|(<figure\b.*?</figure>)', re.S)


def read_chapter(x):
    a = x.index('</h2>') + len('</h2>')
    b = x.rindex('</section>')
    items = []
    for m in PARA.finditer(x[a:b]):
        items.append(('p', html.unescape(m.group(1))) if m.group(1) is not None else ('fig', m.group(2)))
    return x[:a], items, x[b:]


def write_chapter(head, items, tail):
    def one(k, v):
        if k == 'fig':
            return v
        m = re.fullmatch(r'§ ([IVX]+)', v)     # a story's numbered part, as the page sets it
        return f'<h3 class="part">{m.group(1)}</h3>' if m else f'<p>{html.escape(v)}</p>'
    body = ''.join('\n' + one(k, v) for k, v in items)
    return head + body + '\n' + tail


# ── pass 1: paragraphs from the page ─────────────────────────────────────────────────────────────────
def repara(chapters, A, starts):
    tokens = []                     # (chapter, item index, word, normalised)
    for ch, (_, items, _) in chapters.items():
        for k, (kind, v) in enumerate(items):
            if kind == 'p':
                for w in v.split():
                    tokens.append((ch, k, w, nw(w)))
    ours = [t[3] for t in tokens]
    keep = [i for i, n in enumerate(ours) if n]
    sm = difflib.SequenceMatcher(None, [ours[i] for i in keep], A, autojunk=False)
    to_a = {}
    for b in sm.get_matching_blocks():
        for j in range(b.size):
            to_a[keep[b.a + j]] = b.b + j
    from_a = {v: k for k, v in to_a.items()}
    breaks = set()                  # token indexes that begin a paragraph, by the page
    for s in starts:
        # the first word of the indented line, or the first one of it that aligned
        for d in range(0, 3):
            if s + d in from_a:
                breaks.add(from_a[s + d] - d)
                break
    known = sorted(to_a)            # where the page can speak; elsewhere the book's own breaks stand
    def covered(i):
        return any(abs(x - i) < 12 for x in known[max(0, bisect(known, i) - 3):bisect(known, i) + 3])
    out, stats = {}, collections.Counter()
    for ch, (head, items, tail) in chapters.items():
        idx = [i for i, t in enumerate(tokens) if t[0] == ch]
        new, cur, prev_item = [], [], None
        figs_after = collections.defaultdict(list)       # plates follow the word they followed
        last_word = None
        for k, (kind, v) in enumerate(items):
            if kind == 'fig':
                figs_after[last_word].append(v)
            else:
                ws = [i for i in idx if tokens[i][1] == k]
                if ws:
                    last_word = ws[-1]
        first = True
        for i in idx:
            old_break = tokens[i][1] != prev_item
            prev_item = tokens[i][1]
            if first:
                brk = True
            elif covered(i):
                brk = i in breaks
            else:
                brk = old_break
            if brk and cur:
                new.append(('p', ' '.join(cur))); cur = []
            stats['break kept' if brk and old_break else 'break added' if brk else 'break removed' if old_break else 'same'] += 1
            cur.append(tokens[i][2])
            first = False
            for f in figs_after.get(i, []):
                new.append(('p', ' '.join(cur))); cur = []
                new.append(('fig', f))
        if cur:
            new.append(('p', ' '.join(cur)))
        for f in figs_after.get(None, []):
            new.insert(0, ('fig', f))
        out[ch] = (head, [x for x in new if x[0] == 'fig' or x[1].strip()], tail)
    return out, stats


def bisect(a, x):
    import bisect as b
    return b.bisect_left(a, x)


# ── pass 2: spacing ─────────────────────────────────────────────────────────────────────────────────
def spacing(t):
    t = re.sub(r'\s+([,;:?!])', r'\1', t)
    t = re.sub(r'(\w)\s+\.(?!\.)', r'\1.', t)
    t = re.sub(r'(^|[\s(—])" (?=[A-Za-z])', r'\1"', t)        # an opening quotation mark, then a stray space
    t = re.sub(r"(^|[\s\"—])' (?=[A-Za-z])", r"\1'", t)
    t = re.sub(r'\s{2,}', ' ', t)
    return t.strip()


# ── pass 4: quotation marks ─────────────────────────────────────────────────────────────────────────
def curly(t):
    out, open_d = [], False
    for k, c in enumerate(t):
        prev = t[k - 1] if k else ' '
        nxt = t[k + 1] if k + 1 < len(t) else ' '
        if c == '"':
            opening = prev in ' \n(—[' or (prev in "'‘" and k > 1 and t[k - 2] in ' \n')
            if prev.isspace() or k == 0:
                opening = True
            elif prev == '—' and (nxt.isspace() or k + 1 == len(t)):
                opening = False
            elif nxt.isspace() or nxt in ',.;:?!—)' or k + 1 == len(t):
                opening = False
            out.append('“' if opening else '”')
        elif c == "'":
            if prev == '—' and (nxt.isspace() or nxt in '"”'):
                out.append('’')
            elif (k == 0 or prev in ' \n(—“"') and not re.match(r"(?:tis|twas|em|82|83|84|85|86|87|88|89|90|91|9\d|8\d)\b", t[k + 1:k + 5]):
                out.append('‘')
            else:
                out.append('’')
        else:
            out.append(c)
    return ''.join(out)


def carry_quotes(text):
    """A paragraph break moved by pass 1 can strand the next paragraph's opening quotation mark at the end of the
    one before ('rely on you." "' / 'But what is it'). Carried over only when that evens both paragraphs. Runs where
    the ledger says @carry, so every ledger row is written against the text it is applied to."""
    ps = text.split(' ¶ ')
    for x in range(len(ps) - 1):
        P, Q = ps[x], ps[x + 1]
        m = re.search(r' ("\'?|\')$', P)
        if m and P.count('"') % 2 and Q.count('"') % 2 and re.match(r"[A-Za-z']", Q):
            ps[x] = P[:m.start()].rstrip(); ps[x + 1] = m.group(1) + Q
    return ' ¶ '.join(ps)


# The wording of a proofread copy (John, 2026-11-01): say what was done and that it was done with care, without
# claiming perfection; name the printing; say plainly that no one else's edition was used. No em dashes.
STAMP_DATE = '2026-11-02'
NOTICE = """<div class="proof">
<h1>A Proofread Copy</h1>
<hr class="rule"/>
<p><strong>This copy has been read against the 1892 printing and corrected.</strong> We have taken care over it, but no reading catches everything. If something still reads wrongly (a misprint, a word that sits oddly, a paragraph that breaks in the wrong place) note the Adventure and the sentence around it and send it to <a href="mailto:john@rfrmdwordlabs.com">john@rfrmdwordlabs.com</a>.</p>
<p>Please point friends to the SchriftOhr shelf rather than passing this file on, so that they receive the latest corrections.</p>
<p>Two things are deliberate. The colour plate that opens each Adventure was made for this edition; it is not a Victorian illustration and does not pretend to be one. The black-and-white plates inside the stories are Sidney Paget\u2019s, photographed from the 1892 printing this text is set from.</p>
<p class="stamp">The Adventures of Sherlock Holmes &#183; Arthur Conan Doyle<br/>SchriftOhr Edition &#183; proofread __DATE__</p>
</div>"""
NOTES = {
    '00-title.xhtml': [
        ('<p class="reissue">Reissued September 2026</p>', '<p class="reissue">Proofread and corrected November 2026</p>'),
        ('<p class="proofing-line"><strong>This edition is not finished.</strong> It is circulated for reading and correction.</p>\n', ''),
    ],
    '01-edition-note.xhtml': [
        ('Doyle\u2019s text is given as he wrote it in 1892. Nothing has been modernised, abridged, or rewritten. The work here has been to clear away what had gathered around the text in its passage into digital form \u2014 the page numbers scattered mid-sentence, the broken lines, the apparatus of the scan \u2014 so that the book reads cleanly on a screen and reads aloud cleanly to a listener.',
         'Doyle\u2019s text is given as the Harper printing of 1892 set it, as nearly as we have been able to make it. Nothing has been modernised, abridged, or rewritten. Our work has been to clear away what gathered around the text on its way into digital form, such as page numbers in mid-sentence, broken lines and the marks of the scan, so that the book reads cleanly on a screen and aloud to a listener.'),
    ],
    '97-sources.xhtml': [
        ('New York, 1892 \u2014 the first American edition,', 'New York, 1892, the first American edition,'),
        (None, '<p>We worked from our own scans of two copies of that printing, read them independently, and compared the readings. Where they differed, or where a word looked doubtful, the page image decided. Our copy lacks its page 215 and the other copy the opening of <i>The Boscombe Valley Mystery</i>; each supplied what the other lacked. A few slips of the 1892 printer, such as \u201cparalled\u201d for \u201cparallel\u201d, are corrected.</p>\n<p>No other edition or digital text was copied in making this one. Our aim is a book that is true to its printing and good to read. We have taken care, and we are grateful to readers who tell us where we have fallen short.</p>'),
    ],
}


def reword(work):
    t = work / 'OEBPS/text'
    proof = (t / '00-proofing.xhtml').read_text(encoding='utf-8')
    proof = re.sub(r'<div class="proof">.*?</div>', NOTICE.replace('__DATE__', STAMP_DATE).replace('\\u2019', '\u2019'), proof, flags=re.S)
    (t / '00-proofing.xhtml').write_text(proof.replace('<title>Proofing Copy</title>', '<title>A Proofread Copy</title>'), encoding='utf-8')
    for name, edits in NOTES.items():
        x = (t / name).read_text(encoding='utf-8')
        for old, new in edits:
            if old is None:      # the second paragraph of Sources, replaced whole
                x, n = re.subn(r'<p>It was not transcribed from any existing digital text\..*?</p>', new, x, flags=re.S)
            else:
                n = x.count(old); x = x.replace(old, new)
            if n != 1:
                sys.exit(f'!! reword: {name}: {(old or "Sources para 2")[:50]!r} matched {n} times')
        (t / name).write_text(x, encoding='utf-8')
    nav = work / 'OEBPS/nav.xhtml'
    nv = nav.read_text(encoding='utf-8')
    assert nv.count('>Proofing Copy</a>') == 1
    nav.write_text(nv.replace('>Proofing Copy</a>', '>A Proofread Copy</a>'), encoding='utf-8')
    # the one straight apostrophe in a title, set by the builder
    for f in list(t.glob('*.xhtml')) + [nav, work / 'OEBPS/content.opf']:
        y = f.read_text(encoding='utf-8')
        z = y.replace("Engineer's", 'Engineer\u2019s').replace('Engineer&#x27;s', 'Engineer\u2019s').replace('Engineer&#39;s', 'Engineer\u2019s')
        if z != y:
            f.write_text(z, encoding='utf-8')
    opf = work / 'OEBPS/content.opf'
    o = opf.read_text(encoding='utf-8')
    o = re.sub(r'(<meta property="dcterms:modified">)[^<]*', r'\g<1>' + STAMP_DATE + 'T00:00:00Z', o)
    opf.write_text(o, encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('book'); ap.add_argument('out')
    ap.add_argument('--ledger', default=str(HERE.parent / 'books/adventures-of-sherlock-holmes/sherlock-corrections.tsv'))
    ap.add_argument('--no-curly', action='store_true')
    ap.add_argument('--dump', help='write each Adventure as plain paragraphs into this folder')
    a = ap.parse_args()
    work = pathlib.Path(tempfile.mkdtemp())
    with zipfile.ZipFile(a.book) as z:
        z.extractall(work)
    files = sorted((work / 'OEBPS/text').glob('C[0-9][0-9]-*.xhtml'))
    chapters = {f.name: read_chapter(f.read_text(encoding='utf-8')) for f in files}

    A, starts = witness_a()
    chapters, st = repara(chapters, A, starts)
    print(f'paragraphs: {dict(st)}')

    for ch, (h, items, t) in chapters.items():
        chapters[ch] = (h, [(k, spacing(v) if k == 'p' else v) for k, v in items], t)

    # The ledger works on each Adventure as one string, paragraphs joined by " ¶ " and each plate standing as
    # [[PLATE n]], so a line can also make or remove a paragraph break.
    led = pathlib.Path(a.ledger)
    joined = {}
    for ch, (h, items, t) in chapters.items():
        joined[ch] = ' ¶ '.join(v if k == 'p' else f'[[PLATE {i}]]' for i, (k, v) in enumerate(items))
    n = 0
    if led.exists():
        for l in led.read_text(encoding='utf-8').splitlines()[1:]:
            if not l.strip() or l.startswith('#'):
                continue
            if l.strip() == '@carry':
                joined = {k: carry_quotes(v) for k, v in joined.items()}
                continue
            ch, was, now = l.split('\t')[:3]
            f = next((c for c in chapters if c.startswith(ch + '-')), None)
            if not f:
                sys.exit(f'!! ledger: no Adventure {ch}')
            c = joined[f].count(was)
            if c != 1:
                sys.exit(f'!! ledger: {was!r} occurs {c} times in {f}')
            joined[f] = joined[f].replace(was, now)
            n += 1
    print(f'ledger: {n} corrections')
    for ch, (h, items, t_) in chapters.items():   # a ledger row must never take a plate with it
        want = sorted(f'[[PLATE {i}]]' for i, (k, _) in enumerate(items) if k == 'fig')
        got = sorted(re.findall(r'\[\[PLATE \d+\]\]', joined[ch]))
        if want != got:
            sys.exit(f'!! ledger: {ch} had plates {want}, now {got}')
    for ch, (h, items, t) in chapters.items():
        new = []
        for part in joined[ch].split(' ¶ '):
            m = re.fullmatch(r'\[\[PLATE (\d+)\]\]', part.strip())
            new.append(items[int(m.group(1))] if m else ('p', part.strip()))
        chapters[ch] = (h, [x for x in new if x[0] == 'fig' or x[1]], t)


    if a.dump:   # each Adventure as the ledger sees it: paragraphs joined by " ¶ ", plates as [[PLATE n]]
        d = pathlib.Path(a.dump); d.mkdir(parents=True, exist_ok=True)
        for ch, (h, items, t) in chapters.items():
            (d / (ch[:3] + '.txt')).write_text(
                ' ¶ '.join(v if k == 'p' else f'[[PLATE {i}]]' for i, (k, v) in enumerate(items)), encoding='utf-8')

    for ch, (h, items, t) in chapters.items():
        if not a.no_curly:
            items = [(k, curly(v) if k == 'p' and not v.startswith('§ ') else v) for k, v in items]
        (work / 'OEBPS/text' / ch).write_text(write_chapter(h, items, t), encoding='utf-8')

    reword(work)
    css = work / 'OEBPS/css/style.css'
    if 'h3.part' not in css.read_text(encoding='utf-8'):
        css.write_text(css.read_text(encoding='utf-8') + '\n/* A story told in numbered parts: the numeral alone, centred. */\n'
                       'h3.part{text-align:center;font-weight:normal;letter-spacing:.1em;margin:1.6em 0 .8em;page-break-after:avoid;break-after:avoid}\n',
                       encoding='utf-8')

    out = pathlib.Path(a.out)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, 'w') as z:
        z.write(work / 'mimetype', 'mimetype', compress_type=zipfile.ZIP_STORED)
        for p in sorted(work.rglob('*')):
            if p.is_file() and p.name != 'mimetype':
                z.write(p, p.relative_to(work).as_posix(), compress_type=zipfile.ZIP_DEFLATED)
    shutil.rmtree(work)
    print(f'wrote {out}')


if __name__ == '__main__':
    main()
