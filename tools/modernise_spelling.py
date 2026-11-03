#!/usr/bin/env python3
"""Modernise the spelling of an Edition from its hand-read spelling map (the Rare Jewel method, made general).

    tools/modernise_spelling.py BOOK.epub MAP.tsv [--possessive Name ...]

The author's words stay his: only their old spelling is brought forward (wayes ways, onely only, perswade
persuade), so the book reads easily and the voice says each word rightly. MAP.tsv holds `old<TAB>modern`, every
row read by hand. Whole words only, in the text only: never inside the Greek or Hebrew or their sounds
(class gk, hb, ph), never in markup, never in our own front and back pages (only the author's chapters and
prefaces: C01.., S01.., P01.., 02-preface, 02-to-the-reader, 90-...). A word keeps its capital.
--possessive gives names whose bare genitive the old page sets without an apostrophe (Gods, Christs, Davids);
the capital makes them certain, so "Gods" becomes "God's" and the lower-case "gods" is left alone.
Prints how many words changed, and stops if a map row is never used (a stale row is a wrong row).
"""
import argparse, collections, html, pathlib, re, tempfile, zipfile

SKIP = re.compile(r'<(span|i|b)\b[^>]*class="(?:gk|hb|ph)"[^>]*>.*?</\1>', re.S)
AUTHOR = re.compile(r'/(C\d\d|S\d\d|P\d\d|02-preface|02-to-the-reader|9\d-(?!sources|why|closing|words))[^/]*\.xhtml$')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('epub'); ap.add_argument('map')
    ap.add_argument('--possessive', nargs='*', default=[])
    ap.add_argument('--files', help='regex for the author\'s documents, where the default does not fit (Glory of Christ: 03-i-01 ...)')
    a = ap.parse_args()
    M = {}
    for line in pathlib.Path(a.map).read_text(encoding='utf-8').splitlines():
        if line.strip() and not line.startswith('#'):
            old, new = line.split('\t')[:2]
            M[old.lower().replace('’', "'")] = new
    cased = {n + 's': n + '’s' for n in a.possessive}
    word = re.compile(r"(?<![\w’'])([A-Za-z][A-Za-z’']*[A-Za-z]|[A-Za-z])(?![\w’'])")
    count = collections.Counter()

    def fix(m):
        w = m.group(0)
        if w in cased:
            count[w] += 1
            return cased[w]
        key = w.lower().replace('’', "'")
        new = M.get(key)
        if new is None:
            return w
        new = new.replace("'", '’')
        if w[0].isupper() and new[0].islower():
            new = new[0].upper() + new[1:]
        if w.isupper() and len(w) > 1:
            new = new.upper()
        count[key] += 1
        return new

    def text_only(seg):
        return re.sub(r'(?<=>)[^<]+|^[^<]+',
                      lambda t: html.escape(word.sub(fix, html.unescape(t.group(0))), quote=False), seg)

    epub = pathlib.Path(a.epub)
    with zipfile.ZipFile(epub) as z:
        infos = z.infolist(); data = {i.filename: z.read(i.filename) for i in infos}
    for name in data:
        if not (re.search(a.files, name) if a.files else AUTHOR.search(name)):
            continue
        x = data[name].decode('utf-8'); b = x.index('<body')
        body, out, pos = x[b:], [], 0
        for m in SKIP.finditer(body):
            out.append(text_only(body[pos:m.start()])); out.append(m.group(0)); pos = m.end()
        out.append(text_only(body[pos:]))
        data[name] = (x[:b] + ''.join(out)).encode('utf-8')
    unused = [k for k in M if count[k] == 0]
    if unused:
        raise SystemExit(f'{pathlib.Path(a.map).name}: never used {unused}; nothing written')
    tmp = pathlib.Path(tempfile.mkstemp(suffix='.epub', dir=epub.parent)[1])
    with zipfile.ZipFile(tmp, 'w') as out:
        for i in infos:
            out.writestr(i, data[i.filename],
                         compress_type=zipfile.ZIP_STORED if i.filename == 'mimetype' else zipfile.ZIP_DEFLATED)
    tmp.replace(epub)
    print(f'{epub.name}: {sum(count.values())} words changed, {len(count)} spellings')


if __name__ == '__main__':
    main()
