#!/usr/bin/env python3
"""Apply a was/now corrections ledger to a finished EPUB, in place.

    tools/apply_ledger.py BOOK.epub LEDGER.tsv

Each ledger row is: chapter (C01, C02 ..., or a page's file name such as 01-edition-note) TAB was TAB now TAB evidence TAB note. Lines starting with # are
comments; a literal \\n in `now` is a line break. `was` must occur exactly once in that chapter's XHTML, or the run
stops before anything is written. Every other file in the EPUB is copied byte for byte.
"""
import pathlib, sys, tempfile, zipfile


def rows(ledger):
    for n, line in enumerate(ledger.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip() or line.startswith('#'):
            continue
        cells = line.split('\t')
        if len(cells) < 3:
            sys.exit(f'{ledger.name}:{n}: fewer than three columns')
        yield n, cells[0].strip(), cells[1].replace('\\n', '\n'), cells[2].replace('\\n', '\n')


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    epub, ledger = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    with zipfile.ZipFile(epub) as z:
        names = z.namelist()
        data = {n: z.read(n) for n in names}
        infos = {i.filename: i for i in z.infolist()}
    chapters = {}
    for n in names:
        base = n.rsplit('/', 1)[-1]
        if base[:1] == 'C' and base[1:3].isdigit() and base.endswith('.xhtml'):
            chapters[base[:3]] = n
        elif base.endswith('.xhtml'):
            chapters[base[:-6]] = n   # a front or back page, named by its file: 01-edition-note
    texts = {k: data[v].decode('utf-8') for k, v in chapters.items()}
    count = 0
    for n, ch, was, now in rows(ledger):
        if ch not in texts:
            sys.exit(f'{ledger.name}:{n}: no chapter {ch}')
        k = texts[ch].count(was)
        if k != 1:
            sys.exit(f'{ledger.name}:{n}: {ch} holds "{was[:60]}" {k} times')
        texts[ch] = texts[ch].replace(was, now)
        count += 1
    for k, v in chapters.items():
        data[v] = texts[k].encode('utf-8')
    out = epub.with_suffix('.new.epub')
    with zipfile.ZipFile(out, 'w') as z:
        for n in names:
            z.writestr(infos[n], data[n], compress_type=zipfile.ZIP_STORED if n == 'mimetype' else zipfile.ZIP_DEFLATED)
    out.replace(epub)
    print(f'{epub.name}: {count} corrections applied')


if __name__ == '__main__':
    main()
