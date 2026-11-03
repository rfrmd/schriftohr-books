#!/usr/bin/env python3
"""Close the old printer's space before a stop (the 1668 page sets "you shall live ; and"), in place.

    tools/tighten_punct.py BOOK.epub [--files REGEX]

Text only, in the author's documents only, never inside the Greek or Hebrew or their sounds. A space before
; : , . ? ! goes, and a space after an opening bracket or before a closing one. The words are not touched: the
script proves the letters of every document are the same before and after.
"""
import argparse, html, pathlib, re, tempfile, zipfile

SKIP = re.compile(r'<(span|i|b)\b[^>]*class="(?:gk|hb|ph)"[^>]*>.*?</\1>', re.S)
AUTHOR = r'/(C\d\d|S\d\d|P\d\d|02-preface|02-to-the-reader)[^/]*\.xhtml$'


def tighten(t):
    t = re.sub(r'(?<=\S) +(?=[;:,.?!](?:\s|$|[”’)<]))', '', t)
    t = re.sub(r'\( +', '(', t)
    return re.sub(r'(?<=\S) +\)', ')', t)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('epub'); ap.add_argument('--files', default=AUTHOR)
    a = ap.parse_args()
    epub = pathlib.Path(a.epub)
    with zipfile.ZipFile(epub) as z:
        infos = z.infolist(); data = {i.filename: z.read(i.filename) for i in infos}
    n = 0
    for name in data:
        if not re.search(a.files, name):
            continue
        x = data[name].decode('utf-8'); b = x.index('<body'); body = x[b:]
        def text_only(seg):
            return re.sub(r'(?<=>)[^<]+|^[^<]+', lambda t: html.escape(tighten(html.unescape(t.group(0))), quote=False), seg)
        out, pos = [], 0
        for m in SKIP.finditer(body):
            out.append(text_only(body[pos:m.start()])); out.append(m.group(0)); pos = m.end()
        out.append(text_only(body[pos:]))
        new = x[:b] + ''.join(out)
        if re.sub(r'\s', '', new) != re.sub(r'\s', '', x):
            raise SystemExit(f'{name}: more than spaces changed; nothing written')
        n += len(x) - len(new); data[name] = new.encode('utf-8')
    tmp = pathlib.Path(tempfile.mkstemp(suffix='.epub', dir=epub.parent)[1])
    with zipfile.ZipFile(tmp, 'w') as out:
        for i in infos:
            out.writestr(i, data[i.filename],
                         compress_type=zipfile.ZIP_STORED if i.filename == 'mimetype' else zipfile.ZIP_DEFLATED)
    tmp.replace(epub)
    print(f'{epub.name}: {n} stray spaces closed')


if __name__ == '__main__':
    main()
