#!/usr/bin/env python3
"""Repair the two faults that stop Apple Books opening our editions.

⚠️ THE COVER IS AN SVG. Every SchriftOhr cover page wraps the cover image in
an <svg> so it scales to any screen. EPUB requires a content document that
uses SVG to say so in the manifest — `properties="svg"` — and Apple Books
does not merely warn about the omission: it refuses the whole book, on the
iPhone and iPad, with "not formatted properly". Fourteen of the sixteen
published editions carried this, which means most of the shelf would not
open on a phone. Sherlock and Glory of Christ were built after the covers
changed and are clean.

The second fault is smaller: an anchor inside the "landmarks" nav with no
epub:type. That is a parse error in the navigation document.

This is surgery on a finished book, not a rebuild — same reasoning as
restamp_proof.py. The text is not re-derived and the chapters are not re-cut;
only content.opf and nav.xhtml are touched.

    fix_epub_validity.py BOOK.epub [BOOK.epub ...] [--check]
"""

import argparse
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

# what a content document may contain that the manifest has to declare
FEATURES = (
    ('svg', re.compile(r'<svg[\s>]|<[a-zA-Z]+:svg[\s>]')),
    ('mathml', re.compile(r'<math[\s>]|<[a-zA-Z]+:math[\s>]')),
    ('scripted', re.compile(r'<script[\s>]|\son[a-z]+\s*=')),
)


def fix(path, check=False):
    work = pathlib.Path(tempfile.mkdtemp(prefix='fixepub-'))
    subprocess.run(['unzip', '-qq', str(path), '-d', str(work)], check=True)
    opf_path = next(work.rglob('*.opf'))
    root = opf_path.parent
    opf = opf_path.read_text(encoding='utf-8')
    changed = []

    # ── declare what each document actually uses ────────────────────────────
    for m in list(re.finditer(r'<item\b[^>]*?/>', opf)):
        tag = m.group(0)
        href = re.search(r'href="([^"]+)"', tag)
        if not href or not href.group(1).endswith(('.xhtml', '.html')):
            continue
        doc = root / href.group(1)
        if not doc.exists():
            continue
        body = doc.read_text(encoding='utf-8', errors='replace')
        have = set(re.search(r'properties="([^"]*)"', tag).group(1).split()) \
            if 'properties="' in tag else set()
        want = {name for name, pat in FEATURES if pat.search(body)}
        missing = want - have
        if not missing:
            continue
        props = ' '.join(sorted(have | want))
        if 'properties="' in tag:
            new = re.sub(r'properties="[^"]*"', f'properties="{props}"', tag)
        else:
            new = tag[:-2].rstrip() + f' properties="{props}"/>'
        opf = opf.replace(tag, new, 1)
        changed.append(f'{href.group(1)}: declared {" ".join(sorted(missing))}')

    # ── a paragraph may not hold paragraphs ────────────────────────────────
    # ⚠️ One book sets a list — stolen goods, an inscription — as a run of
    # <p class="tN"> wrapped in a bare <p>. Nested paragraphs are not legal
    # and the reader rejects the file. The wrapper is doing a block's job, so
    # it becomes a <div>; nothing inside it changes.
    for doc in sorted(root.rglob('*.xhtml')):
        body = doc.read_text(encoding='utf-8')
        out = []
        hit = 0
        for line in body.split('\n'):
            if re.match(r'^<p[^>]*>\s*<p[\s>]', line) and line.rstrip().endswith('</p>'):
                inner = re.sub(r'^<p[^>]*>', '', line.rstrip())[:-4]
                line = '<div class="block">' + inner + '</div>'
                hit += 1
            out.append(line)
        if hit:
            doc.write_text('\n'.join(out), encoding='utf-8')
            changed.append(f'{doc.name}: {hit} nested paragraph(s) unwrapped')

    # ── every landmark must say what it points at ──────────────────────────
    nav = None
    for cand in root.rglob('*.xhtml'):
        t = cand.read_text(encoding='utf-8', errors='replace')
        if 'epub:type="landmarks"' in t:
            nav = cand; break
    if nav is not None:
        t = nav.read_text(encoding='utf-8')
        m = re.search(r'(<nav[^>]*epub:type="landmarks".*?</nav>)', t, re.S)
        if m:
            block = m.group(1)
            fixed = block
            for a in re.finditer(r'<a (?![^>]*epub:type)([^>]*href="([^"]+)")[^>]*>', block):
                target = a.group(2).split('#')[0]
                doc = root / target
                kind = 'bodymatter'
                if doc.exists():
                    s = re.search(r'<section[^>]*epub:type="([^"]+)"',
                                  doc.read_text(encoding='utf-8', errors='replace'))
                    # a landmark names a place in the book; the page already
                    # says what it is, so take its word rather than invent one
                    if s and s.group(1) not in ('frontmatter', 'bodymatter', 'backmatter'):
                        kind = s.group(1)
                fixed = fixed.replace(a.group(0),
                                      a.group(0).replace('<a ', f'<a epub:type="{kind}" ', 1), 1)
                changed.append(f'landmark {target}: epub:type="{kind}"')
            if fixed != block:
                nav.write_text(t.replace(block, fixed), encoding='utf-8')

    if not changed:
        print(f'  {path.name}: already valid')
        shutil.rmtree(work, ignore_errors=True)
        return False
    if check:
        print(f'  {path.name}: would fix {len(changed)} —')
        for c in changed: print(f'      {c}')
        shutil.rmtree(work, ignore_errors=True)
        return True

    opf_path.write_text(opf, encoding='utf-8')
    tmp = work.parent / (path.name + '.tmp')
    subprocess.run(['zip', '-qX0', str(tmp), 'mimetype'], cwd=work, check=True)
    subprocess.run(['zip', '-qXr9', str(tmp), '.', '-x', 'mimetype', '-x', '.DS_Store'],
                   cwd=work, check=True)
    shutil.move(str(tmp), path)
    shutil.rmtree(work, ignore_errors=True)
    print(f'  {path.name}: fixed {len(changed)} — ' + '; '.join(changed[:3]))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('epubs', nargs='+')
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    n = sum(fix(pathlib.Path(e), args.check) for e in args.epubs)
    print(f'{n} book(s) {"would be " if args.check else ""}changed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
