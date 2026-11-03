"""set_footnotes.py BOOK.epub SPEC.tsv — set the 1918 footnotes, run into Pink's text by the page reading, as notes.
SPEC rows: file key TAB marker (unique text containing the one * where the reference goes) TAB note start (unique
text beginning with the note's *, or + then the note's text to add a note the reading lost) TAB note end (unique
text closing the note; empty for an added note). A row with note start '-' only removes a stray * at the marker."""
import sys, zipfile, re, pathlib, tempfile, collections
epub = pathlib.Path(sys.argv[1])
with zipfile.ZipFile(epub) as z:
    infos = z.infolist(); data = {i.filename: z.read(i.filename) for i in infos}
spec = collections.defaultdict(list)
for l in open(sys.argv[2], encoding='utf-8'):
    if l.strip() and not l.startswith('#'):
        c = l.rstrip('\n').split('\t'); spec[c[0]].append(c[1:4] + [''] * (3 - len(c[1:4])))
def once(x, s, what):
    if x.count(s) != 1: sys.exit(f'{what}: {x.count(s)} times: {s[:70]}')
    return x.index(s)
total = 0
for key, rows in spec.items():
    name = f'OEBPS/text/{key}.xhtml'; x = data[name].decode()
    notes = []
    for marker, start, end in rows:
        if start == '-':
            x = x.replace(marker, marker.replace('*', '', 1), 1) if x.count(marker) == 1 else sys.exit(f'marker: {marker}')
            continue
        if start.startswith('+'):
            text = start[1:]
        else:
            s = once(x, start, 'note start'); e = x.index(end, s) + len(end)
            if x.count(end, s) < 1: sys.exit(f'note end: {end}')
            text = x[s + 1:e].strip()
            if '<' in text: sys.exit(f'note crosses markup: {text[:200]}')
            before, after = x[:s], x[e:]
            m = re.match(r'</p>\s*', after)
            if before.endswith('<p>') and m:
                before = before[:-3]; after = after[m.end():]           # the note was a paragraph of its own
            elif re.match(r'</p>\s*<p>', after) and not re.match(r'</p>\s*<p>\d+\.|</p>\s*<p>[A-Z]', after):
                after = re.sub(r'^</p>\s*<p>', '', after)              # the note fell inside a sentence: rejoin it
            elif after.startswith('</p>'):
                before = before.rstrip(' ')
            if before.endswith(' ') and after.startswith(' '):
                after = after[1:]
            x = before + after
        notes.append((marker, text))
    # number in reading order, put the references in, append the notes
    order = sorted(notes, key=lambda n: once(x, n[0], 'marker'))
    asides = []
    for i, (marker, text) in enumerate(order, 1):
        p = once(x, marker, 'marker') + marker.index('*')
        x = x[:p] + f'<a epub:type="noteref" href="#fn{i}" id="fr{i}" class="nref"><sup>{i}</sup></a>' + x[p + 1:]
        asides.append(f'<aside epub:type="footnote" id="fn{i}" class="fn"><p><a href="#fr{i}">{i}.</a> {text}</p></aside>')
    if asides:
        x = x.replace('</section></body>', '<section epub:type="endnotes" class="footnotes"><hr/>\n' + '\n'.join(asides)
                      + '\n</section>\n</section></body>', 1) if '</section></body>' in x else sys.exit(f'{key}: no end')
    total += len(asides); data[name] = x.encode()
tmp = pathlib.Path(tempfile.mkstemp(suffix='.epub', dir=epub.parent)[1])
with zipfile.ZipFile(tmp, 'w') as out:
    for i in infos:
        out.writestr(i, data[i.filename], compress_type=zipfile.ZIP_STORED if i.filename == 'mimetype' else zipfile.ZIP_DEFLATED)
tmp.replace(epub); print(f'{epub.name}: {total} notes set')
