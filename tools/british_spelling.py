#!/usr/bin/env python3
"""Put a book back into its author's British spelling, in place (John, 2026-11-04).

    british_spelling.py BOOK.epub MAP.tsv

MAP rows are american TAB british, every pair checked against the author's own printing. Whole words only, in the
text of the chapters and never inside a tag, keeping capitals. Prints what changed and any like word the map missed.
"""
import collections, pathlib, re, sys, zipfile

epub, mapfile = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
MAP = {}
for line in mapfile.read_text(encoding='utf-8').splitlines():
    if line.strip() and not line.startswith('#'):
        a, b = line.split('\t')[:2]
        MAP[a] = b
WORD = re.compile(r'\b(' + '|'.join(sorted(map(re.escape, MAP), key=len, reverse=True)) + r')\b', re.I)
STEMS = re.compile(r'\b\w*(?:color|labor(?!ious)|honor(?!ary)|favor|neighbor|harbor|vigor(?!ous)|humor(?!ous)|odor(?!if)|flavor|savor|armor|endeavor|splendor|valor|vapor(?!ous)|behavior|fiber|center|defense|offense|pretense|plow|traveler|traveled|marvel[eo]|skillful)\w*\b', re.I)
done = collections.Counter()


def case(old, new):
    return new.capitalize() if old[0].isupper() else new


def text(part):
    def swap(m):
        done[m.group(1).lower()] += 1
        return case(m.group(1), MAP[m.group(1).lower()])
    return WORD.sub(swap, part)


with zipfile.ZipFile(epub) as z:
    names = z.namelist()
    infos = {i.filename: i for i in z.infolist()}
    data = {n: z.read(n) for n in names}
left = collections.Counter()
for n in names:
    if re.search(r'/C\d\d[^/]*\.xhtml$', n):
        parts = re.split(r'(<[^>]+>)', data[n].decode('utf-8'))
        parts = [p if p.startswith('<') else text(p) for p in parts]
        s = ''.join(parts)
        data[n] = s.encode('utf-8')
        for p in parts:
            if not p.startswith('<'):
                left.update(w.lower() for w in STEMS.findall(p))
out = epub.with_suffix('.new.epub')
with zipfile.ZipFile(out, 'w') as z:
    for n in names:
        z.writestr(infos[n], data[n], compress_type=zipfile.ZIP_STORED if n == 'mimetype' else zipfile.ZIP_DEFLATED)
out.replace(epub)
print(f'{epub.name}: {sum(done.values())} words respelt, {len(done)} forms')
if left:
    print('  like words not in the map:', dict(left))
