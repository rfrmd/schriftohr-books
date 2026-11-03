#!/usr/bin/env python3
"""Put back the paragraph breaks lost between sentences, read from another copy of the same text.

    tools/restore_breaks.py BOOK.epub REFERENCE.epub [--dry]

Sherlock Holmes, 2026-11-03: correct_sherlock.py's paragraph pass (11-01) took its breaks from the indents of the
1892 page, and where the indent was not seen it took the book's own break out. That ran 532 speeches into the
speech before them: "“No.” “Then, what clue ...”" in one paragraph, a new speaker the voice cannot hear. Our own
earlier copies ran them together too (the collation of 09-29), so the breaks are read from Project Gutenberg's
text (#1661), which gives every speaker his paragraph; only the break is taken, never a word. A reference break
comes back where the word before it
ends a sentence (. ! ? or a closing quotation mark after one, or a dash); a break inside a sentence was a page
turn, and stays out. Chapters are matched word for word; nothing but the break is changed.
"""
import difflib, pathlib, re, sys, unicodedata, zipfile


def nw(w):
    w = unicodedata.normalize('NFKD', w.lower())
    return re.sub(r'[^a-z0-9]', '', w)


ENDS = re.compile(r'([.!?]["”’\']*|[”’]|—|--)$')


def paragraphs(x, any_p=False):
    b = x.index('<body')
    rx = r'<p\b[^>]*>(.*?)</p>' if any_p else r'<p>(.*?)</p>'
    return [(m.start(1) + 0, m.end(1), m.group(1)) for m in re.finditer(rx, x[b:], re.S)], b


def reference(path):
    """Every paragraph of the reference in reading order, its markup and entities stripped."""
    import html
    z = zipfile.ZipFile(path)
    opf = next(n for n in z.namelist() if n.endswith('.opf'))
    o = z.read(opf).decode('utf-8')
    base = opf.rsplit('/', 1)[0] + '/' if '/' in opf else ''
    items = dict(re.findall(r'<item\b[^>]*?id="([^"]+)"[^>]*?href="([^"]+)"', o))
    items.update({k: v for v, k in re.findall(r'<item\b[^>]*?href="([^"]+)"[^>]*?id="([^"]+)"', o)})
    out = []
    for idref in re.findall(r'<itemref\b[^>]*idref="([^"]+)"', o):
        x = z.read(base + items[idref]).decode('utf-8', 'ignore')
        if '<body' not in x:
            continue
        ps, _ = paragraphs(x, any_p=True)
        out += [(0, 0, html.unescape(re.sub(r'<[^>]+>', ' ', t))) for _, _, t in ps]
    return out


def words_of(paras):
    out = []                    # (paragraph index, offset of the word in the paragraph text, raw, normalised)
    for k, (_, _, t) in enumerate(paras):
        for m in re.finditer(r'\S+', t):
            out.append((k, m.start(), m.group(0), nw(m.group(0))))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dry = '--dry' in sys.argv
    epub, earlier = map(pathlib.Path, args)
    with zipfile.ZipFile(epub) as z:
        names = z.namelist()
        data = {n: z.read(n) for n in names}
        infos = {i.filename: i for i in z.infolist()}
    old_p = reference(earlier)
    old_w = [w for w in words_of(old_p) if w[3]]
    total = 0
    for n in names:
        if not re.search(r'text/C\d\d-.*\.xhtml$', n):
            continue
        x = data[n].decode('utf-8')
        new_p, nb = paragraphs(x)
        new_w = [w for w in words_of(new_p) if w[3]]
        sm = difflib.SequenceMatcher(None, [w[3] for w in old_w], [w[3] for w in new_w], autojunk=False)
        splits = {}             # paragraph index -> offsets in its text to break before
        for blk in sm.get_matching_blocks():
            for j in range(1, blk.size):
                o_prev, o = old_w[blk.a + j - 1], old_w[blk.a + j]
                w_prev, w = new_w[blk.b + j - 1], new_w[blk.b + j]
                if o[0] != o_prev[0] and w[0] == w_prev[0] and ENDS.search(w_prev[2]):
                    splits.setdefault(w[0], []).append(w[1])
        if not splits:
            continue
        out, last = [], 0
        for k, (s, e, t) in enumerate(new_p):
            if k not in splits:
                continue
            if '<' in t:
                print(f'{n}: paragraph {k + 1} carries markup; left whole', file=sys.stderr)
                continue
            pieces, a = [], 0
            for off in sorted(splits[k]):
                pieces.append(t[a:off].rstrip()); a = off
            pieces.append(t[a:])
            out.append((nb + s, nb + e, '</p>\n<p>'.join(pieces)))
            total += len(pieces) - 1
        for s, e, t in reversed(out):
            x = x[:s] + t + x[e:]
        print(f'{n.rsplit("/", 1)[-1][:3]}: {sum(len(v) for v in splits.values())} breaks put back')
        data[n] = x.encode('utf-8')
    if dry:
        print(f'dry run: {total} breaks'); return
    tmp = epub.with_suffix('.new.epub')
    with zipfile.ZipFile(tmp, 'w') as z:
        for n in names:
            z.writestr(infos[n], data[n], compress_type=zipfile.ZIP_STORED if n == 'mimetype' else zipfile.ZIP_DEFLATED)
    tmp.replace(epub)
    print(f'{epub.name}: {total} paragraph breaks put back')


if __name__ == '__main__':
    main()
