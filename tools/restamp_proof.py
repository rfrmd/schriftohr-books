#!/usr/bin/env python3
"""Band a built edition's cover as a proofing copy, and record its source.

Surgery on a finished book, not a rebuild. The text is not re-derived, the
chapters are not re-cut; only the cover image is banded and `dc:source` set
where the builder left it empty. A rebuild would re-run every editorial
decision for the sake of a metadata field, and every re-run is a chance to
change something nobody asked to change.

    restamp_proof.py BOOK.epub [--source "..."] [--out OUT.epub] [--no-band]
"""

import argparse
import io
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from edition_parts import stamp_proof_cover, proofing_xhtml


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('epub')
    ap.add_argument('--source', default='')
    ap.add_argument('--out', default='')
    ap.add_argument('--no-band', action='store_true')
    ap.add_argument('--at', type=float, default=0.425)
    ap.add_argument('--refresh-notice', action='store_true',
                    help="rewrite the proofing page with the current wording")
    args = ap.parse_args()

    src = pathlib.Path(args.epub)
    out = pathlib.Path(args.out) if args.out else src
    work = pathlib.Path(tempfile.mkdtemp(prefix='restamp-'))
    subprocess.run(['unzip', '-qq', str(src), '-d', str(work)], check=True)

    changed = []

    # ── the source line ─────────────────────────────────────────────────────
    opf = next(work.rglob('*.opf'))
    text = opf.read_text(encoding='utf-8')
    if args.source:
        if re.search(r'<dc:source>.*?</dc:source>', text, re.S):
            was = re.search(r'<dc:source>(.*?)</dc:source>', text, re.S).group(1)
            if was.strip() != args.source:
                text = re.sub(r'<dc:source>.*?</dc:source>',
                              f'<dc:source>{args.source}</dc:source>', text, flags=re.S)
                changed.append(f'source set ({"was empty" if not was.strip() else "replaced"})')
        else:
            text = text.replace('</metadata>',
                                f'    <dc:source>{args.source}</dc:source>\n  </metadata>')
            changed.append('source added')
        opf.write_text(text, encoding='utf-8')

    # ── the proofing notice ────────────────────────────────────────────────
    # ⚠️ A book built before the wording changed keeps the old words forever.
    # Setting a source does not touch the notice, and neither does anything
    # else short of a rebuild — so the notice is rewritten here from the
    # current text, with this book's own title and author.
    if args.refresh_notice:
        page = None
        for cand in work.rglob('*proofing*.xhtml'):
            page = cand; break
        if page is None:
            print('  !! no proofing page in this book')
        else:
            import xml.sax.saxutils as _s
            meta = opf.read_text(encoding='utf-8')
            def dc(tag):
                m = re.search(rf'<dc:{tag}[^>]*>(.*?)</dc:{tag}>', meta, re.S)
                return _s.unescape(m.group(1)).strip() if m else ''
            was = page.read_text(encoding='utf-8')
            # keep whatever "these are deliberate" paragraph the book already
            # carries — it is per-book and says true things about THIS text
            keep = re.search(r'<p>(Two things are deliberate.*?)</p>', was, re.S)
            page.write_text(
                proofing_xhtml(dc('title'), dc('creator'),
                               deliberate=keep.group(1) if keep else None),
                encoding='utf-8')
            changed.append('proofing notice rewritten')
            # ⚠️ The page is not the whole notice. A book built before the rule
            # became an <hr> carries CSS that styles a run of em-dashes and says
            # nothing about hr, so the new rule would come out as the reader's
            # default hairline instead of the house orange.
            for css in work.rglob('*.css'):
                s = css.read_text(encoding='utf-8')
                if '.proof' not in s: continue
                s2 = re.sub(r'\.proof \.rule\{[^}]*\}',
                            '.proof hr.rule{border:0;border-top:2px solid #fd8008;'
                            'margin:1em 0 1.1em}', s)
                if 'hr.rule' not in s2:
                    s2 += ('\n.proof hr.rule{border:0;border-top:2px solid #fd8008;'
                           'margin:1em 0 1.1em}\n')
                if s2 != s:
                    css.write_text(s2, encoding='utf-8')
                    changed.append('proofing stylesheet updated')

    # ── the cover ───────────────────────────────────────────────────────────
    if not args.no_band:
        covers = [p for p in work.rglob('*')
                  if p.suffix.lower() in ('.jpg', '.jpeg', '.png')
                  and 'cover' in p.name.lower()]
        if not covers:
            print('  !! no cover image found; not banding')
        else:
            cover = max(covers, key=lambda p: p.stat().st_size)
            stamp_proof_cover(cover, cover if cover.suffix.lower() in ('.jpg', '.jpeg')
                              else cover.with_suffix('.jpg'), at=args.at)
            if cover.suffix.lower() == '.png':
                # the manifest names the file; keep the name, write JPEG bytes
                shutil.move(cover.with_suffix('.jpg'), cover)
            changed.append(f'cover banded ({cover.name})')

    # ── seal it back up, mimetype first and stored ──────────────────────────
    tmp = work.parent / (out.name + '.tmp')
    if tmp.exists():
        tmp.unlink()
    subprocess.run(['zip', '-qX0', str(tmp), 'mimetype'], cwd=work, check=True)
    subprocess.run(['zip', '-qXr9', str(tmp), '.', '-x', 'mimetype', '-x', '.DS_Store'],
                   cwd=work, check=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(tmp), out)
    shutil.rmtree(work, ignore_errors=True)

    print(f'  {out.name}: ' + ('; '.join(changed) if changed else 'nothing to change'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
