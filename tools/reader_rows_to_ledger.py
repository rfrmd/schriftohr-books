"""reader_rows_to_ledger.py BOOK.epub OUT.tsv ROWS... — turn readers' rows (file, text as it stands, corrected, note) into
apply_ledger rows matched in the XHTML. Three spaces in a row mean a paragraph break."""
import sys, zipfile, re, html
z = zipfile.ZipFile(sys.argv[1])
docs = {n.split('/')[-1][:-6]: z.read(n).decode() for n in z.namelist() if n.startswith('OEBPS/text/')}
GAP = r'(?:\s|<[^>]+>)+'
ok, bad = [], []
for f in sys.argv[3:]:
    for l in open(f, encoding='utf-8'):
        if not l.strip() or l.startswith('#'): continue
        c = l.rstrip('\n').split('\t')
        if len(c) < 3: bad.append(('cols', l)); continue
        key, ours, fix = c[0].replace('.xhtml', ''), c[1], c[2]; page = c[3] if len(c) > 3 else ''
        x = docs.get(key)
        if x is None: bad.append(('no chapter', l)); continue
        body = x.index('<body')
        toks = ours.split()
        pat = GAP.join(re.escape(html.escape(t, quote=False)) for t in toks)
        ms = list(re.finditer(pat, x[body:]))
        if len(ms) != 1: bad.append((f'{len(ms)} matches', l)); continue
        span = ms[0].group(0)
        gaps = re.findall(GAP, span)
        tagged = [g for g in gaps if '<' in g]
        if any(not re.fullmatch(r'\s*</p>\s*<p[^>]*>\s*', g) for g in tagged):
            bad.append(('inline markup', l + '    span: ' + span[:200])); continue
        parts = re.split(r' {3,}', fix)
        if len(parts) - 1 == len(tagged):
            new = parts[0]
            for g, p in zip(tagged, parts[1:]): new += g + p
        elif not tagged:
            new = '</p>\n<p>'.join(parts)
        else:
            bad.append((f'breaks {len(tagged)} vs {len(parts)-1}', l + '    span: ' + span[:300])); continue
        new = html.escape(new, quote=False).replace('&lt;/p&gt;\n&lt;p&gt;', '</p>\n<p>')
        # escape only the text, put the tags back
        new = re.sub(r'&lt;(/?p[^&]*)&gt;', r'<\1>', new)
        ok.append((key, span, new, page))
seen = {}
for r in ok: seen.setdefault((r[0], r[1]), []).append(r)
with open(sys.argv[2], 'w', encoding='utf-8') as o:
    o.write('# Pink 1918: our text read against the page images (four readers), 2026-11-03\n')
    for (k, s), rs in seen.items():
        if len(rs) > 1: bad.append(('dup', str(rs)))
        o.write(f'{k}\t{s.replace(chr(10), chr(92)+"n")}\t{rs[0][2].replace(chr(10), chr(92)+"n")}\tpage\tp. {rs[0][3]}\n')
print(len(ok), 'rows;', len(bad), 'to settle by hand')
for why, l in bad: print('--', why, '|', l.strip()[:400])
