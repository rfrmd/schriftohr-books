#!/usr/bin/env python3
"""Move a finished proofing copy to a published Edition, in place (John, 2026-11-03).

    tools/publish_proof.py BOOK.epub BUILD

The orange "Proofing Copy" (or "A Proofread Copy") page becomes the published "About This Copy" note
(edition_parts.corrections_xhtml), its Contents entry is renamed, and the title page's "This edition is not
finished" line goes. Title, author and identifier stay, so a reader's place and notes carry over and the shelf can
offer this copy as an update. Every other file is copied byte for byte.
"""
import pathlib, re, sys, tempfile, zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from edition_parts import corrections_xhtml


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    epub, build = pathlib.Path(sys.argv[1]), sys.argv[2]
    with zipfile.ZipFile(epub) as z:
        infos = z.infolist()
        data = {i.filename: z.read(i.filename) for i in infos}
    proof = data['OEBPS/text/00-proofing.xhtml'].decode()
    if 'class="proof"' not in proof:
        sys.exit(f'{epub.name}: not a proofing copy')
    stamp = re.search(r'<p class="stamp">(.*?) &#183; (.*?)<br/>', proof)
    title, author = (re.sub(r'<[^>]+>', '', s) for s in stamp.groups())
    import html
    data['OEBPS/text/00-proofing.xhtml'] = corrections_xhtml(html.unescape(title), html.unescape(author), build).encode()
    nav = data['OEBPS/nav.xhtml'].decode()
    nav, n = re.subn(r'(<a href="text/00-proofing\.xhtml">)(?:Proofing Copy|A Proofread Copy|A Proofing Copy)(</a>)',
                     r'\1About This Copy\2', nav)
    if n != 1:
        sys.exit(f'{epub.name}: Contents entry not found')
    data['OEBPS/nav.xhtml'] = nav.encode()
    title_page = data['OEBPS/text/00-title.xhtml'].decode()
    title_page = re.sub(r'\n?<p class="proofing-line">.*?</p>', '', title_page)
    data['OEBPS/text/00-title.xhtml'] = title_page.encode()
    tmp = pathlib.Path(tempfile.mkstemp(suffix='.epub', dir=epub.parent)[1])
    with zipfile.ZipFile(tmp, 'w') as out:
        for i in infos:
            out.writestr(i, data[i.filename],
                         compress_type=zipfile.ZIP_STORED if i.filename == 'mimetype' else zipfile.ZIP_DEFLATED)
    tmp.replace(epub)
    print(f'{epub.name}: published as build {build} ({title} · {author})')


if __name__ == '__main__':
    main()
