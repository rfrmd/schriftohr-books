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
from edition_parts import stamp_proof_cover


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('epub')
    ap.add_argument('--source', default='')
    ap.add_argument('--out', default='')
    ap.add_argument('--no-band', action='store_true')
    ap.add_argument('--at', type=float, default=0.425)
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
