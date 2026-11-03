#!/usr/bin/env python3
"""Sherlock Holmes (John, 2026-11-03): each Paget drawing beside the scene it shows, and every part of a story named.

    tools/sherlock_pictures_parts.py BOOK.epub

- The fifteen drawings sat near each story's head, where the 1892 page fell, a scene or more before the moment
  they draw ("A MAN ENTERED", the masked King, stood where Holmes first greets Watson). Each now follows the
  paragraph holding the words its caption names.
- A Scandal in Bohemia's parts: the 1892 page sets "I" under the title as well as II and III; our copy had lost
  the first. All three are set apart as "Part I", "Part II", "Part III" (the voice says "Part two"; a bare "II"
  was heard as "eye eye").
Run after tools/restore_breaks.py, so each phrase finds one paragraph. In place.
"""
import html, pathlib, re, sys, zipfile

# figure id -> words in the paragraph it follows
SCENES = {
    'fig1': 'A man entered who could hardly',
    'fig2': 'the door was shut and locked',
    'fig3': 'sat in the stalls',
    'fig4': 'the boy in buttons entered',
    'fig5': 'shouted Mr. Windibank, turning white',
    'fig6': 'they found the dead body stretched out',
    'fig7': 'showed us the boots which her master',
    'fig8': '“Holmes,” I cried, “you are too late.”',
    'fig9': 'Convinced that something was amiss with him',
    'fig10': 'Ryder threw himself down suddenly upon the rug',
    'fig11': 'No, I do not think so. I think that there was probably',
    'fig12': 'And not a word to a soul.’ He looked',
    'fig13': 'She dropped her bouquet as we went towards the vestry',
    'fig14': 'Precisely. It was I. I found that I had my man',
    'fig15': 'I am so delighted that you have come,” she said',
}
# two speeches the reference text did not part
SPLITS = [('“You have a clew?” “I have them', '“You have a clew?”</p>\n<p>“I have them'),
          ('“Did you observe the color?” “Yes, I saw', '“Did you observe the color?”</p>\n<p>“Yes, I saw')]


def main():
    epub = pathlib.Path(sys.argv[1])
    with zipfile.ZipFile(epub) as z:
        names = z.namelist()
        data = {n: z.read(n) for n in names}
        infos = {i.filename: i for i in z.infolist()}
    moved, split = 0, 0
    for n in names:
        if not re.search(r'text/C\d\d-.*\.xhtml$', n):
            continue
        x = data[n].decode('utf-8')
        for was, now in SPLITS:
            if x.count(was) == 1:
                x = x.replace(was, now); split += 1
        if 'scandal-in-bohemia' in n:
            for k in ('II', 'III'):
                assert x.count(f'<h3 class="part">{k}</h3>') == 1, k
                x = x.replace(f'<h3 class="part">{k}</h3>', f'<h3 class="part">Part {k}</h3>')
            assert x.count('<h2>A Scandal in Bohemia</h2>') == 1
            x = x.replace('<h2>A Scandal in Bohemia</h2>', '<h2>A Scandal in Bohemia</h2>\n<h3 class="part">Part I</h3>')
        for fig in re.findall(r'<figure class="paget" id="(fig\d+)">.*?</figure>', x, re.S):
            m = re.search(r'\n?<figure class="paget" id="%s">.*?</figure>' % fig, x, re.S)
            block = m.group(0).lstrip('\n')
            rest = x[:m.start()] + x[m.end():]
            want = SCENES[fig]
            hits = [p for p in re.finditer(r'<p>(.*?)</p>', rest, re.S) if want in html.unescape(p.group(1))]
            if len(hits) != 1:
                sys.exit(f'{n}: {fig} finds {len(hits)} paragraphs for "{want}"')
            e = hits[0].end()
            x = rest[:e] + '\n' + block + rest[e:]
            moved += 1
        data[n] = x.encode('utf-8')
    if split != len(SPLITS):
        sys.exit(f'{split} of {len(SPLITS)} speeches parted')
    out = epub.with_suffix('.new.epub')
    with zipfile.ZipFile(out, 'w') as z:
        for n in names:
            z.writestr(infos[n], data[n], compress_type=zipfile.ZIP_STORED if n == 'mimetype' else zipfile.ZIP_DEFLATED)
    out.replace(epub)
    print(f'{epub.name}: {moved} drawings placed at their scenes, {split} speeches parted, Parts I-III named')


if __name__ == '__main__':
    main()
