#!/usr/bin/env python3
"""Modernise the spelling of The Rare Jewel of Christian Contentment (John, 2026-11-02: "Yes, modernise").

Burroughs's words stay his (hath, doth, thou, saith, spake, builded, catched, contentation); only their 1649
spelling is brought forward, so the book reads easily and the voice says each word rightly: waies becomes ways,
injoy enjoy, businesse business, yeers years, i'le I'll, and slips of the printer or the keyer are mended
(grashppers, conntentment). British spellings stay (honour, labour), as in the other Editions.

    tools/modernise_rare_jewel.py BOOK.epub OUT.epub

Reads books/rare-jewel-of-christian-contentment/spelling-map.tsv (each old spelling and its modern form, every
one read by hand). Changes whole words in the text only: never inside the Greek or Hebrew or their pronunciations
(class gk, hb, ph), never in markup. A word keeps its capital. Prints how many words changed.
"""
import collections, html, pathlib, re, shutil, sys, tempfile, zipfile

HERE = pathlib.Path(__file__).resolve().parent
MAP = HERE.parent / 'books/rare-jewel-of-christian-contentment/spelling-map.tsv'
BUILD = '2026-11-02.1'
SKIP = re.compile(r'<(span|i|b)\b[^>]*class="(?:gk|hb|ph)"[^>]*>.*?</\1>', re.S)
NOTE_OLD = ('The seventeenth-century spelling stands, save that the long <i>ſ</i> is set as <i>s</i> and words '
            'broken across a line are rejoined.')
NOTE_NEW = ('The spelling has been brought up to date, so that the book reads easily and sounds right when read '
            'aloud: waies is ways, injoy is enjoy, yeers is years. Burroughs’s words themselves are kept, hath and '
            'doth and thou among them, and the British spellings stand. Words broken across a line are rejoined.')


# Possessives the 1649 page sets without an apostrophe, where the capital makes them certain (gods, lowercase, is
# the heathen gods and stays).
CASED = {'Gods': 'God\u2019s', 'Christs': 'Christ\u2019s', 'Davids': 'David\u2019s', 'Jobs': 'Job\u2019s'}
PHRASES = [('his fathers house', 'his father\u2019s house'), ('my fathers house', 'my father\u2019s house'),
           ('the fathers love', 'the father\u2019s love'), ('is not acquainted with</p>', 'is not acquainted with.</p>')]


def load():
    m = {}
    for line in MAP.read_text(encoding='utf-8').splitlines():
        if line.startswith('#') or not line.strip():
            continue
        old, new = line.split('\t')
        m[old] = new
    return m


def main():
    src, dst = sys.argv[1], sys.argv[2]
    M = load()
    word = re.compile(r"(?<![\w’'])([A-Za-z][A-Za-z’']*[A-Za-z]|[A-Za-z])(?![\w’'])")
    work = pathlib.Path(tempfile.mkdtemp())
    with zipfile.ZipFile(src) as z:
        z.extractall(work)
    T = work / 'OEBPS/text'
    count = collections.Counter()

    def fix(m):
        w = m.group(0)
        key = w.lower().replace('’', "'")
        new = CASED.get(w) or M.get(key)
        if new is None:
            return w
        if "'" in new and '’' in w:
            new = new.replace("'", '’')
        elif "'" in key and "'" not in new and '’' in w:
            pass
        if w[0].isupper() and new[0].islower():
            new = new[0].upper() + new[1:]
        if w.isupper() and len(w) > 1:
            new = new.upper()
        count[(key, new.lower())] += 1
        return new

    def text_only(seg):
        # change text between tags, leave tags alone
        # the text as read (the book stores apostrophes as &#x27;), changed, and set back in safe form
        return re.sub(r'(?<=>)[^<]+|^[^<]+',
                      lambda t: html.escape(word.sub(fix, html.unescape(t.group(0))), quote=False), seg)

    for f in sorted(T.glob('*.xhtml')):
        if not re.match(r'(S\d\d|90-|02-to-the-reader)', f.name):
            continue
        x = f.read_text(encoding='utf-8')
        a = x.index('<body')
        body, out, pos = x[a:], [], 0
        for m in SKIP.finditer(body):
            out.append(text_only(body[pos:m.start()])); out.append(m.group(0)); pos = m.end()
        out.append(text_only(body[pos:]))
        y = ''.join(out)
        for o, n in PHRASES:
            y = y.replace(o, n)
        f.write_text(x[:a] + y, encoding='utf-8')

    note = T / '01-edition-note.xhtml'
    t = note.read_text(encoding='utf-8')
    if NOTE_OLD not in t:
        sys.exit('!! About This Edition: the spelling sentence was not found')
    t = t.replace(NOTE_OLD, NOTE_NEW)
    for o, n in [('as 1649 printed it \u2014 not modernised, abridged, or rewritten', 'as 1649 printed it, not abridged or rewritten'),
                 ('after the Rare Jewel \u2014 a sermon', 'after the Rare Jewel: a sermon')]:
        if o not in t:
            sys.exit(f'!! About This Edition: {o[:40]!r} not found')
        t = t.replace(o, n)
    note.write_text(t, encoding='utf-8')
    p = T / '00-proofing.xhtml'; t = p.read_text(encoding='utf-8')
    t2 = re.sub(r'build \d{4}-\d\d-\d\d(?:\.\d+)?', f'build {BUILD}', t)
    p.write_text(t2, encoding='utf-8')
    opf = work / 'OEBPS/content.opf'; o = opf.read_text(encoding='utf-8')
    opf.write_text(re.sub(r'(<meta property="dcterms:modified">)[^<]*', r'\g<1>' + BUILD[:10] + 'T00:00:00Z', o),
                   encoding='utf-8')

    out = pathlib.Path(dst)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, 'w') as z:
        z.write(work / 'mimetype', 'mimetype', compress_type=zipfile.ZIP_STORED)
        for q in sorted(work.rglob('*')):
            if q.is_file() and q.name != 'mimetype':
                z.write(q, q.relative_to(work).as_posix(), compress_type=zipfile.ZIP_DEFLATED)
    shutil.rmtree(work)
    print(f'{sum(count.values())} words changed, {len(count)} spellings; wrote {out}')


if __name__ == '__main__':
    main()
