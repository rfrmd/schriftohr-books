#!/usr/bin/env python3
"""Draft a modernising ledger for a finished Edition (John, 2026-11-02: modernise for the reader by default).

    tools/modern_pass_ledger.py BOOK.epub RULES.tsv OUT.tsv

RULES.tsv rows: kind TAB pattern TAB replacement TAB where
  kind    word (an old word given by its sense), join (a hyphenated compound now one word), us (British to American)
  pattern a regex matched against whole words in the text (never inside a tag)
  where   all, or narration (outside quotation marks only, so a character's own speech keeps its voice)

Writes one apply_ledger.py row per instance: chapter, was, now, evidence, note. `was` is widened with the words
around it until it occurs once in its chapter file. Nothing is changed here; the ledger is read, then applied.
"""
import html, pathlib, re, sys, zipfile


def spans(body):
    """Text runs of a chapter body with their offsets, outside tags, skipping footnote sections."""
    cut = body.find('<section epub:type="footnotes"')
    end = cut if cut >= 0 else len(body)
    for m in re.finditer(r'>([^<]+)<', body[:end]):
        yield m.start(1), m.group(1)


def in_dialogue(body, pos):
    text = re.sub(r'<[^>]+>', '', body[:pos])
    para = text[text.rfind('\n') + 1:] if '\n' in text else text
    return para.count('“') > para.count('”')


def main():
    epub, rules_p, out_p = map(pathlib.Path, sys.argv[1:4])
    rules = []
    for line in rules_p.read_text(encoding='utf-8').splitlines():
        if line.strip() and not line.startswith('#'):
            kind, pat, rep, where = line.split('\t')
            rules.append((kind, re.compile(r'(?<![\w’-])' + pat + r'(?![\w-])'), rep, where))
    z = zipfile.ZipFile(epub)
    rows = []
    for n in sorted(z.namelist()):
        m = re.search(r'text/(C\d\d)-', n)
        if not m:
            continue
        ch, doc = m.group(1), z.read(n).decode('utf-8')
        start = doc.index('<body')
        body = doc[start:]
        taken = []
        for off, run in spans(body):
            for kind, rx, rep, where in rules:
                for w in rx.finditer(run):
                    a, b = off + w.start(), off + w.end()
                    if any(a < y and x < b for x, y in taken):
                        continue
                    if where == 'narration' and in_dialogue(body, a):
                        continue
                    word = w.group(0)
                    new = w.expand(rep)
                    if word[0].isupper() and new[:1].islower():
                        new = new[0].upper() + new[1:]
                    # widen inside this text run until unique in the chapter file
                    lo, hi = a, b
                    while doc.count(body[lo:hi]) != 1 and (lo > off or hi < off + len(run)):
                        lo, hi = max(off, lo - 6), min(off + len(run), hi + 6)
                    was = body[lo:hi]
                    if doc.count(was) != 1:
                        print(f'{ch}: "{word}" not unique even across its run; skipped', file=sys.stderr)
                        continue
                    now = body[lo:a] + new + body[b:hi]
                    taken.append((a, b))
                    rows.append((ch, was, now, kind, f'{word} -> {new}'))
    # rows widened to the same span would collide: keep the first, report the rest
    seen, kept = set(), []
    for r in rows:
        key = (r[0], r[1])
        if key in seen:
            print(f'{r[0]}: overlapping span for {r[4]}; run again after applying', file=sys.stderr)
            continue
        seen.add(key)
        kept.append(r)
    with out_p.open('w', encoding='utf-8') as o:
        o.write('# chapter\twas\tnow\tkind\tnote\n')
        for r in kept:
            o.write('\t'.join(r) + '\n')
    print(f'{out_p.name}: {len(kept)} rows')


if __name__ == '__main__':
    main()
