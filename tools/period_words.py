#!/usr/bin/env python3
"""Period words kept as the author wrote them, each explained in a lettered note on its first use in a chapter.

    tools/period_words.py BOOK.epub PERIOD.tsv

John, 2026-11-03, on Sherlock's "slavey": spellings are corrected, but a word whose meaning belongs to its period,
above all one that looks like another word, stays in the text and is explained, "so that the reader ... is both
educated and shown the original text correctly." (tools/shifted_words.py, which put the modern word in the text,
is the earlier treatment.)

PERIOD.tsv rows: pattern (regex, whole words, matched without regard to case) TAB the word as the note names it TAB
the gloss. The note reads "<i>word</i>: gloss". Letters, so a word note is told at a glance from a numbered
footnote. Text only: never inside a tag, a heading or a note. The chapter's notes go in an endnotes section at its
foot, which the voice steps over. In place; every other file is copied byte for byte.
"""
import html, pathlib, re, sys, zipfile

LET = 'abcdefghijklmnopqrstuvwxyz'
CSS = ('\n.nref{text-decoration:none;font-size:.8em;vertical-align:super;line-height:0}\n'
       '.notes{font-size:.9em;color:#555;margin-top:2.4em}\n'
       '.notes hr{border:0;border-top:1px solid #ccc;width:35%;margin:0 0 .9em}\n'
       '.fn p{text-indent:0;margin:.35em 0}\n.fn a{text-decoration:none;color:#777}\n')


def main():
    epub, table = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    rows = []
    for line in table.read_text(encoding='utf-8').splitlines():
        if line.strip() and not line.startswith('#'):
            pat, word, gloss = line.split('\t')
            rows.append((re.compile(r'(?<![\w’-])(?:' + pat + r')(?![\w-])', re.I), word, gloss))
    with zipfile.ZipFile(epub) as z:
        names = z.namelist()
        data = {n: z.read(n) for n in names}
        infos = {i.filename: i for i in z.infolist()}
    total = 0
    for n in names:
        if not re.search(r'text/C\d\d-.*\.xhtml$', n):
            continue
        x = data[n].decode('utf-8')
        if 'class="fn pw"' in x:
            sys.exit(f'{n}: already carries period-word notes')
        a = x.index('<body')
        body = x[a:]
        cuts = [k for k in (body.find('<section epub:type="footnotes"'), body.find('<section epub:type="endnotes"')) if k >= 0]
        k = min(cuts) if cuts else -1
        main_, tail = (body[:k], body[k:]) if k >= 0 else (body, '')
        notes, seen = [], set()

        def paragraph(p):
            def textnode(t):
                s = html.unescape(t.group(0))
                for rx, word, gloss in rows:
                    if word in seen:
                        continue
                    m = rx.search(s)
                    if not m:
                        continue
                    seen.add(word)
                    notes.append((word, gloss))
                    s = s[:m.end()] + '\x01%d\x02' % (len(notes) - 1) + s[m.end():]
                return html.escape(s, quote=False)
            return re.sub(r'(?<=>)[^<]+', textnode, p.group(0))
        # paragraphs only: headings, captions and figures keep their words bare
        main_ = re.sub(r'<p\b[^>]*>.*?</p>', paragraph, main_, flags=re.S)
        main_ = re.sub('\x01(\\d+)\x02', lambda m: (
            f'<a epub:type="noteref" href="#pn{m.group(1)}" id="pr{m.group(1)}" class="nref pref">'
            f'<sup>{LET[int(m.group(1))]}</sup></a>'), main_)
        if notes:
            asides = ''.join(f'<aside epub:type="footnote" id="pn{i}" class="fn pw"><p><a href="#pr{i}">{LET[i]}.</a> '
                             f'<i>{html.escape(w)}</i>: {html.escape(g)}</p></aside>'
                             for i, (w, g) in enumerate(notes))
            section = f'<section epub:type="endnotes" class="notes"><hr/>{asides}</section>\n'
            if tail:
                tail = section + tail
            else:
                if main_.count('</section></body>') != 1:
                    sys.exit(f'{n}: cannot find the end of the chapter')
                main_ = main_.replace('</section></body>', section + '</section></body>')
        total += len(notes)
        data[n] = (x[:a] + main_ + tail).encode('utf-8')
    css = next(n for n in names if n.endswith('style.css'))
    if b'.nref{' not in data[css]:
        data[css] += CSS.encode('utf-8')
    out = epub.with_suffix('.new.epub')
    with zipfile.ZipFile(out, 'w') as z:
        for n in names:
            z.writestr(infos[n], data[n], compress_type=zipfile.ZIP_STORED if n == 'mimetype' else zipfile.ZIP_DEFLATED)
    out.replace(epub)
    print(f'{epub.name}: {total} period words explained')


if __name__ == '__main__':
    main()
