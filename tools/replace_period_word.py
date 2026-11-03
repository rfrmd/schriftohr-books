#!/usr/bin/env python3
"""Replace a period word that tools/period_words.py had explained, and take its notes out.

    tools/replace_period_word.py BOOK.epub PATTERN=NOW [PATTERN=NOW ...]

John, 2026-11-03, on Sherlock's "ejaculated": a word whose modern sense is crude or embarrassing is replaced,
not explained; a note does not stop the reader stumbling. PATTERN is a regex over the text (whole words, the
first letter's case kept); NOW is the word put in its place. The lettered note on the word goes, the aside
naming it goes, and the chapter's remaining period-word notes are lettered again in reading order. Text only:
never inside a tag; numbered footnotes are left alone. In place; every other file is copied byte for byte.
"""
import pathlib, re, sys, zipfile

LET = 'abcdefghijklmnopqrstuvwxyz'
REF = r'<a epub:type="noteref" href="#pn(?P<k>\d+)" id="pr(?P=k)" class="nref pref"><sup>[a-z]</sup></a>'


def main():
    epub = pathlib.Path(sys.argv[1])
    rules = [(re.compile(r'(?<![\w’-])(' + p + r')(?![\w-])', re.I), now)
             for p, now in (a.split('=', 1) for a in sys.argv[2:])]
    with zipfile.ZipFile(epub) as z:
        names = z.namelist()
        data = {n: z.read(n) for n in names}
        infos = {i.filename: i for i in z.infolist()}
    words = notes = 0
    for n in names:
        if not re.search(r'text/C\d\d-.*\.xhtml$', n):
            continue
        x = data[n].decode('utf-8')
        a = x.index('<body')
        head, body = x[:a], x[a:]
        k = body.find('<section epub:type="endnotes"')
        main_, tail = (body[:k], body[k:]) if k >= 0 else (body, '')
        gone = set()
        for rx, now in rules:
            # the word and its note mark, if it carries one
            def swap(m):
                nonlocal words
                words += 1
                if m.group(2):
                    gone.add(m.group(2))
                return (now[0].upper() if m.group(1)[0].isupper() else now[0]) + now[1:]
            main_ = re.sub(r'(?<=>)[^<]+', lambda t: rx.sub(lambda m: '\x03' + m.group(1) + '\x04', t.group(0)), main_)
            main_ = re.sub('\x03([^\x04]+)\x04(?:' + REF + ')?', swap, main_)
        if not gone:
            data[n] = (head + main_ + tail).encode('utf-8')
            continue
        for g in gone:
            tail, c = re.subn(r'<aside epub:type="footnote" id="pn%s" class="fn pw">.*?</aside>' % g, '', tail, flags=re.S)
            assert c == 1, (n, g)
            notes += 1
        # letters again, in reading order
        order = re.findall(REF, main_)
        rank = {old: i for i, old in enumerate(order)}
        main_ = re.sub(REF, lambda m: f'<a epub:type="noteref" href="#pn\x05{rank[m.group(1)]}" id="pr\x05{rank[m.group(1)]}" '
                       f'class="nref pref"><sup>{LET[rank[m.group(1)]]}</sup></a>', main_)
        asides = dict(re.findall(r'(<aside epub:type="footnote" id="pn(\d+)" class="fn pw">.*?</aside>)', tail, re.S)[i][::-1]
                      for i in range(len(re.findall(r'class="fn pw"', tail))))
        assert sorted(asides) == sorted(rank), (n, sorted(asides), sorted(rank))
        block = ''.join(re.sub(r'id="pn\d+"', f'id="pn\x05{rank[o]}"',
                               re.sub(r'<a href="#pr\d+">[a-z]\.</a>', f'<a href="#pr\x05{rank[o]}">{LET[rank[o]]}.</a>', asides[o]))
                        for o in order)
        tail = re.sub(r'(<hr/>)(?:<aside epub:type="footnote" id="pn\d+" class="fn pw">.*?</aside>)+', lambda m: m.group(1) + block,
                      tail, count=1, flags=re.S)
        if not order:
            tail = re.sub(r'<section epub:type="endnotes" class="notes"><hr/></section>\n?', '', tail)
        data[n] = (head + (main_ + tail).replace('\x05', '')).encode('utf-8')
    out = epub.with_suffix('.new.epub')
    with zipfile.ZipFile(out, 'w') as z:
        for n in names:
            z.writestr(infos[n], data[n], compress_type=zipfile.ZIP_STORED if n == 'mimetype' else zipfile.ZIP_DEFLATED)
    out.replace(epub)
    print(f'{epub.name}: {words} words replaced, {notes} notes taken out, letters in reading order')


if __name__ == '__main__':
    main()
