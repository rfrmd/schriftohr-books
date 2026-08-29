#!/usr/bin/env python3
"""Mend the breaks both witnesses share, using the book's own vocabulary.

Two OCR passes over two copies fail the same way at a line end: 'suffi- cient',
'han- som', 'ex plained'. Because they agree, collation never sees them — an
error both witnesses make is invisible to the method that compares them.

⚠️ The evidence used here is the BOOK'S OWN WORDS, not an outside text. A break
is mended only when the mended form already appears elsewhere in this book, so
nothing is imported and nothing is invented: 'explained' occurs whole a dozen
times, which is what licenses joining 'ex plained'.

    mend_text.py IN OUT [--report FILE]
"""
import re, sys, pathlib
from collections import Counter

def main():
    src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    report = None
    if '--report' in sys.argv:
        report = pathlib.Path(sys.argv[sys.argv.index('--report') + 1])
    text = src.read_text(encoding='utf-8')

    vocab = Counter(w.lower() for w in re.findall(r"[A-Za-z][A-Za-z'’-]*", text))
    def known(w, least=2):
        return vocab.get(w.lower(), 0) >= least

    fixes = []

    def mend_hyphen(m):
        a, b = m.group(1), m.group(2)
        joined, hyphened = a + b, f'{a}-{b}'
        if known(joined):
            fixes.append((m.group(0), joined, 'joined; the whole word is in this book'))
            return joined
        if known(hyphened):
            fixes.append((m.group(0), hyphened, 'hyphen kept; the compound is in this book'))
            return hyphened
        return m.group(0)

    text = re.sub(r"\b([A-Za-z]{2,})-\s+([a-z]{2,})\b", mend_hyphen, text)

    def mend_space(m):
        a, b = m.group(1), m.group(2)
        joined = a + b
        # only when the split halves are NOT both words in their own right —
        # otherwise "the re" would swallow a real phrase
        if known(joined, 3) and not (known(a, 6) and known(b, 6)):
            fixes.append((m.group(0), joined, 'space closed; the whole word is in this book'))
            return joined
        return m.group(0)

    text = re.sub(r"\b([A-Za-z]{2,})\s+([a-z]{2,})\b", mend_space, text)

    dst.write_text(text, encoding='utf-8')
    print(f'{len(fixes)} breaks mended')
    for what, _n in Counter(f[2] for f in fixes).most_common():
        print(f'   {_n:>4}  {what}')
    if report:
        with report.open('w') as f:
            f.write('was\tnow\twhy\n')
            for a, b, why in fixes:
                f.write(f'{a}\t{b}\t{why}\n')
        print(f'   every one listed in {report}')

if __name__ == '__main__':
    sys.exit(main())
