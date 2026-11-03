#!/usr/bin/env python3
"""Words whose meaning has moved: the modern word in the text, a lettered note on its first use in each chapter.

    tools/shifted_words.py BOOK.epub SHIFTED.tsv AUTHOR

The Rare Jewel's treatment (tools/rare_jewel_modern_forms.py, John 2026-11-02), for any finished Edition.
SHIFTED.tsv rows: pattern (regex, whole words, matched without regard to case) TAB modern word TAB the word the
author wrote. The note reads "<AUTHOR> wrote <i>word</i>." Letters, so a word note is told at a glance from a
numbered footnote. Text only: never inside a tag or a note. The chapter's notes go in an endnotes section at its
foot, which the voice steps over. In place; every other file is copied byte for byte.
"""
import html, pathlib, re, sys, zipfile

LET = 'abcdefghijklmnopqrstuvwxyz'
CSS = ('\n.nref{text-decoration:none;font-size:.8em;vertical-align:super;line-height:0}\n'
       '.notes{font-size:.9em;color:#555;margin-top:2.4em}\n'
       '.notes hr{border:0;border-top:1px solid #ccc;width:35%;margin:0 0 .9em}\n'
       '.fn p{text-indent:0;margin:.35em 0}\n.fn a{text-decoration:none;color:#777}\n')


def main():
    epub, table, author = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
    rows = []
    for line in table.read_text(encoding='utf-8').splitlines():
        if line.strip() and not line.startswith('#'):
            pat, rep, old_w = line.split('\t')
            rows.append((re.compile(r'\b' + pat + r'\b', re.I), rep, old_w))
    with zipfile.ZipFile(epub) as z:
        names = z.namelist()
        data = {n: z.read(n) for n in names}
        infos = {i.filename: i for i in z.infolist()}
    total = 0
    for n in names:
        if not re.search(r'text/C\d\d-.*\.xhtml$', n):
            continue
        x = data[n].decode('utf-8')
        a = x.index('<body')
        body = x[a:]
        k = body.find('<section epub:type="footnotes"')
        main_, tail = (body[:k], body[k:]) if k >= 0 else (body, '')
        notes, seen, count = [], set(), [0]

        def textnode(t):
            s = html.unescape(t.group(0))
            for rx, rep, old_w in rows:
                def one(m):
                    count[0] += 1
                    new = rep[0].upper() + rep[1:] if m.group(0)[0].isupper() else rep
                    if old_w in seen:
                        return new
                    seen.add(old_w)
                    notes.append(old_w)
                    return new + '\x01%d\x02' % (len(notes) - 1)
                s = rx.sub(one, s)
            return html.escape(s, quote=False)
        main_ = re.sub(r'(?<=>)[^<]+', textnode, main_)
        main_ = re.sub('\x01(\\d+)\x02', lambda m: (
            f'<a epub:type="noteref" href="#wn{m.group(1)}" id="wr{m.group(1)}" class="nref wref">'
            f'<sup>{LET[int(m.group(1))]}</sup></a>'), main_)
        if notes:
            asides = ''.join(f'<aside epub:type="footnote" id="wn{i}" class="fn wn"><p><a href="#wr{i}">{LET[i]}.</a> '
                             f'{html.escape(author)} wrote <i>{html.escape(w)}</i>.</p></aside>'
                             for i, w in enumerate(notes))
            section = f'<section epub:type="endnotes" class="notes"><hr/>{asides}</section>\n'
            if tail:
                tail = section + tail
            else:
                if main_.count('</section></body>') != 1:
                    sys.exit(f'{n}: cannot find the end of the chapter')
                main_ = main_.replace('</section></body>', section + '</section></body>')
        total += count[0]
        data[n] = (x[:a] + main_ + tail).encode('utf-8')
    css = next(n for n in names if n.endswith('style.css'))
    if b'.nref{' not in data[css]:
        data[css] += CSS.encode('utf-8')
    out = epub.with_suffix('.new.epub')
    with zipfile.ZipFile(out, 'w') as z:
        for n in names:
            z.writestr(infos[n], data[n], compress_type=zipfile.ZIP_STORED if n == 'mimetype' else zipfile.ZIP_DEFLATED)
    out.replace(epub)
    print(f'{epub.name}: {total} words given their modern word')


if __name__ == '__main__':
    main()
