#!/usr/bin/env python3
"""Respell eye-dialect in a finished EPUB's chapters, in place.

    tools/respell_dialect.py BOOK.epub MAP.tsv

John, 2026-11-03: "spell the words correctly, you can use apostrophes to contract if it is beneficial for the
portrayal of an education level or age." So "de", "dat", "fergit", "eddication" become "the", "that", "forget",
"education", while real contractions that carry a speaker's voice ("ain't", "'em", "'bout", "goin'") stay.

MAP.tsv: one `was<TAB>now` per line, whole words, matched without regard to case (the first letter's case is kept).
A word followed by ’s or ’ll is still matched ("Dat’s" -> "That’s"). Only text between tags changes; markup never.
Prints a count per word, and stops if a word in the map is never found (a stale map is a wrong map).
"""
import pathlib, re, sys, tempfile, zipfile


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    epub, mapfile = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    pairs = []
    for line in mapfile.read_text(encoding='utf-8').splitlines():
        if line.strip() and not line.startswith('#'):
            was, now = line.split('\t')[:2]
            pairs.append((was, now))
    alt = '|'.join(re.escape(w) for w, _ in sorted(pairs, key=lambda p: -len(p[0])))
    word = re.compile(rf"(?<![\w’'\-])({alt})(?=(?:’(?:s|ll|d|re|ve))?(?![\w\-]))", re.I)
    table = {w.lower(): n for w, n in pairs}
    counts = {w.lower(): 0 for w, _ in pairs}

    def fix(m):
        w = m.group(1)
        n = table[w.lower()]
        counts[w.lower()] += 1
        return n[0].upper() + n[1:] if w[0].isupper() else n

    with zipfile.ZipFile(epub) as z:
        infos = z.infolist()
        data = {i.filename: z.read(i.filename) for i in infos}
    for name in data:
        if re.search(r'/text/C\d\d[^/]*\.xhtml$', name):
            parts = re.split(r'(<[^>]+>)', data[name].decode('utf-8'))
            parts = [p if p.startswith('<') else word.sub(fix, p) for p in parts]
            data[name] = ''.join(parts).encode('utf-8')
    missing = [w for w, c in counts.items() if c == 0]
    if missing:
        sys.exit(f'{mapfile.name}: never found {missing}; nothing written')
    tmp = pathlib.Path(tempfile.mkstemp(suffix='.epub', dir=epub.parent)[1])
    with zipfile.ZipFile(tmp, 'w') as out:
        for i in infos:
            out.writestr(i, data[i.filename], compress_type=zipfile.ZIP_STORED if i.filename == 'mimetype' else zipfile.ZIP_DEFLATED)
    tmp.replace(epub)
    print(f'{epub.name}: ' + ', '.join(f'{w} {c}' for w, c in counts.items()))


if __name__ == '__main__':
    main()
