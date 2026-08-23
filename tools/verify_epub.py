#!/usr/bin/env python3
"""Structural and textual check on a built SchriftOhr Edition.

Run it on every rebuild. It reads the EPUB the way a reader does — spine
order, manifest completeness, every referenced file present — and then
sweeps the text for the marks that mean the pipeline leaked: placeholder
glyphs, doubled fragments, tag debris.
"""
import re, sys, zipfile, html
from collections import Counter

LEAKS = {
 '〈':'TCP bracket placeholder', '◊':'illegible-word lozenge',
 'ſ':'long s', 'Ʋ':'V-form capital U', '▪':'unidentified punc mark',
 '▫':'unidentified punc mark', '̄':'combining abbreviation stroke',
 '⟦':'internal gap token', '⟧':'internal gap token',
 '':'unresolved Greek sentinel', '':'unresolved reading sentinel',
 '•':'gap bullet',
}

def check(path):
    z = zipfile.ZipFile(path); names = set(z.namelist())
    print(f'\n=== {path.split("/")[-1]}  ({z.fp.seek(0,2) or len(z.read(z.namelist()[0])) and 0 or 0})')
    bad = []
    # 1. mimetype must be first and STORED
    info = z.infolist()
    if info[0].filename != 'mimetype' or info[0].compress_type != zipfile.ZIP_STORED:
        bad.append('mimetype is not the first, stored entry')
    if z.read('mimetype') != b'application/epub+zip':
        bad.append('mimetype content wrong')
    # 2. container -> opf
    c = z.read('META-INF/container.xml').decode()
    opf_path = re.search(r'full-path="([^"]+)"', c).group(1)
    if opf_path not in names: bad.append(f'container points at missing {opf_path}')
    opf = z.read(opf_path).decode()
    base = opf_path.rsplit('/',1)[0]
    man = dict(re.findall(r'<item id="([^"]+)"\s+href="([^"]+)"', opf))
    spine = re.findall(r'<itemref idref="([^"]+)"', opf)
    for ref in spine:
        if ref not in man: bad.append(f'spine references unknown item {ref}')
    for i,h in man.items():
        full = f'{base}/{h}' if base else h
        if full not in names: bad.append(f'manifest item {i} missing file {h}')
    # A nav entry with a tag inside its own <a> is invalid, and the entry is
    # lost to anything reading the contents.
    nav = [f'{base}/{h}' if base else h for i,h in man.items()
           if re.search(rf'id="{re.escape(i)}"[^>]*properties="[^"]*nav', opf)]
    for n in nav:
        body = z.read(n).decode('utf-8','replace')
        if re.search(r'<a\b[^>]*>[^<]*<a\b', body): bad.append('nested <a> in the nav document')
        entries = len(re.findall(r'<li>', body))
        if entries and entries < len(spine) - 2:
            bad.append(f'nav lists {entries} entries for {len(spine)} spine documents')
    if not re.search(r'properties="cover-image"', opf): bad.append('no cover-image property')
    if not re.search(r'properties="nav"', opf): bad.append('no nav document')
    # 3. every internal link resolves
    docs = [f'{base}/{man[r]}' if base else man[r] for r in spine if r in man]
    for d in docs:
        body = z.read(d).decode('utf-8', 'replace')
        for href in re.findall(r'(?:href|xlink:href|src)="([^"#]+)"', body):
            if re.match(r'[a-z]+:', href): continue      # mailto:, http:, data:
            tgt = f'{d.rsplit("/",1)[0]}/{href}'
            while '/../' in tgt: tgt = re.sub(r'[^/]+/\.\./', '', tgt, count=1)
            if tgt not in names: bad.append(f'{d.split("/")[-1]} links to missing {href}')
    # 4. every note reference must land on a note
    refs, bodies = set(), set()
    for d in docs:
        b = z.read(d).decode('utf-8','replace')
        refs   |= set(re.findall(r'epub:type="noteref"\s+href="#([^"]+)"', b))
        bodies |= set(re.findall(r'epub:type="footnote"\s+id="([^"]+)"', b))
    if refs - bodies: bad.append(f'{len(refs-bodies)} note references with no note')
    if bodies - refs: bad.append(f'{len(bodies-refs)} notes nothing refers to')

    # 5. text sweep
    # The edition note and the proofing page quote the marks on purpose
    # ("the long ſ is set as s", "marked […]"); they are not leaks.
    text = []
    for d in docs:
        if re.search(r'(proofing|edition-note|cover)\.xhtml$', d): continue
        b = z.read(d).decode('utf-8','replace')
        b = re.sub(r'<[^>]+>', ' ', b)
        text.append(html.unescape(b))
    T = '\n'.join(text)
    leaks = Counter()
    for ch, what in LEAKS.items():
        n = T.count(ch)
        if n: leaks[what] += n
    # doubled fragments: "ababased", "lealeast"
    # A fragment left beside its reading makes a word that occurs once and
    # repeats its own opening ('ababased', 'lealeast'). 'murmuring' repeats a
    # stem too, but it is a real word and occurs many times — so require the
    # word to be a hapax AND to collapse to a word the book uses elsewhere.
    freq = Counter(w.lower() for w in re.findall(r'\b[A-Za-z]+\b', T))
    dbl = []
    for w in {w for w in re.findall(r'\b[A-Za-z]{6,}\b', T)}:
        m = re.match(r'^([A-Za-z]{2,5})\1', w)
        if not m or freq[w.lower()] > 1: continue
        if freq.get(w.lower()[len(m.group(1)):], 0) > 0: dbl.append(w)
    words = len(T.split())
    print(f'  {len(docs)} spine docs · {words:,} words')
    print(f'  marks: […]={T.count("[…]")}  [Greek]={T.count("[Greek]")}  '
          f'Greek spans={len(re.findall(chr(0x1F00)+"-"+chr(0x1FFF), T)) or sum(1 for _ in re.finditer(r"[ἀ-ῼΑ-ω]+", T))}')
    if leaks:
        for what, n in leaks.items(): print(f'  ⚠️  {n} × {what}')
    if dbl:
        c = Counter(dbl)
        print(f'  ⚠️  {len(dbl)} doubled-stem words: {[w for w,_ in c.most_common(6)]}')
    if bad:
        for b in bad: print(f'  ✗ {b}')
    else:
        print('  ✓ structure clean')
    return not bad and not leaks

if __name__ == '__main__':
    ok = all([check(p) for p in sys.argv[1:]])
    sys.exit(0 if ok else 1)
