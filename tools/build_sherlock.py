#!/usr/bin/env python3
"""Build the SchriftOhr Edition of The Adventures of Sherlock Holmes.

The source is Project Gutenberg 48320 — the ILLUSTRATED text, carrying
Sidney Paget's drawings from the Strand Magazine, where these twelve
stories first appeared between 1891 and 1892. Doyle is long out of
copyright and the Paget plates with him; the clearance rule (pre-1929,
or a keyed transcription of one) is satisfied twice over.

Two things make this edition its own, and both are John's:

  · a colour plate at the head of every Adventure, drawn for this
    edition — twelve of them, one per story;
  · the cover.

Paget's fifteen in-text illustrations are carried through as they stand.
What is dropped is the apparatus: Gutenberg's logo, the two decorative
drop-caps, and the source's own cover page.

⚠️ The generic splitter in build_edition cannot cut this book. Its
CHAPTER_HEAD wants "CHAPTER IV" or a bare numeral; Doyle's headings read
"Adventure IV THE BOSCOMBE VALLEY MYSTERY", and the first one has the
book's title run into it. Hence a builder of its own — the same reason
Charnock has one.

    python3 build_sherlock.py
"""
import re, os, html, glob, shutil, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_edition import flatten, body_of, clean, page, package, slug
from edition_parts import proofing_xhtml, PROOFING_CSS
from PIL import Image

DESKTOP = os.path.expanduser('~/Desktop')
SRC     = '/tmp/sherlock-src/OEBPS'
TPL     = '/tmp/schriftohr-tpl'
WORK    = os.path.expanduser('~/Desktop/Sherlock-Working')
OUT     = f'{WORK}/output/adventures-of-sherlock-holmes'
EPUB    = (f'{WORK}/output/'
           'Doyle_Arthur_Conan-SchriftOhr_Edition-Adventures_of_Sherlock_Holmes.epub')

T = 'The Adventures of Sherlock Holmes'
A = 'Arthur Conan Doyle'

# John's plates, by the Adventure they head. The two misspelled filenames
# ("Scandel", "Beaches") are his; mapped by intent, not by spelling, so
# nothing has to be renamed on the Desktop.
PLATES = {
    'I':   'Scandel in Bohemia.jpg',   'II':   'RedHeadedLeague.jpg',
    'III': 'ACaseofIdentity.jpg',      'IV':   'boscombeValleyMystery.jpg',
    'V':   'FiveOrangePips.jpg',       'VI':   'Twisted Lip.jpg',
    'VII': 'BlueCarbuncle.jpg',        'VIII': 'SpeckledBand.jpg',
    'IX':  'Thumb.jpg',                'X':    'Noble.jpg',
    'XI':  'BerylCoronet.jpg',         'XII':  'CopperBeaches.jpg',
}

SMALL = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'in', 'of', 'on',
         'or', 'the', 'to', 'with', 'from', 'into', 'nor', 'per', 'via'}


def titled(shout):
    """"THE MAN WITH THE TWISTED LIP" -> "The Man with the Twisted Lip"."""
    words = shout.split()
    out = []
    for i, w in enumerate(words):
        parts = w.split('-')                       # RED-HEADED -> Red-Headed
        done = []
        for p in parts:
            low = p.lower()
            first_or_last = (i == 0 or i == len(words) - 1)
            done.append(low if (low in SMALL and not first_or_last and len(parts) == 1)
                        else low[:1].upper() + low[1:])
        out.append('-'.join(done))
    return ' '.join(out)


def unpack():
    """Source and template, both from epubs we already have."""
    shutil.rmtree('/tmp/sherlock-src', ignore_errors=True)
    os.makedirs('/tmp/sherlock-src', exist_ok=True)
    subprocess.run(['unzip', '-oq', f'{DESKTOP}/TheAdventuresofSherlockHolmes.epub'],
                   cwd='/tmp/sherlock-src', check=True)
    # The house style — stylesheet and publisher marks — is not kept loose in
    # the repo; it lives inside the editions already published. Borrow it from
    # one, so this book cannot drift from the shelf it joins.
    if not os.path.exists(f'{TPL}/OEBPS/css/style.css'):
        shutil.rmtree(TPL, ignore_errors=True)
        os.makedirs(TPL, exist_ok=True)
        donor = glob.glob(os.path.expanduser(
            '~/Developer/schriftohr-books/books/pilgrims-progress/*.epub'))[0]
        subprocess.run(['unzip', '-oq', donor], cwd=TPL, check=True)


def chapters_from_source(out):
    """Twelve Adventures, in the source's own spine order.

    Every image is accounted for: Paget's plates are carried and reported,
    the apparatus is dropped and reported.
    """
    docs = sorted(glob.glob(f'{SRC}/*-h-[0-9].htm.xhtml'),
                  key=lambda p: int(re.search(r'-h-(\d)\.', p).group(1)))

    # Paget's own illustrations, carried at the size the source holds them.
    imgmap, kept = {}, set()
    for p in sorted(glob.glob(f'{SRC}/*illus*.jpg')):
        name = os.path.basename(p)
        dest = re.sub(r'^\d+_', '', name)
        Image.open(p).convert('RGB').save(
            f'{out}/OEBPS/images/{dest}', 'JPEG', quality=88, optimize=True)
        imgmap[name] = dest

    # John's plates, one per Adventure.
    plate_dest = {}
    for roman, filename in PLATES.items():
        src = f'{DESKTOP}/{filename}'
        if not os.path.exists(src):
            print(f'  !! plate for Adventure {roman} missing: {filename}')
            continue
        dest = f'plate-{roman.lower()}.jpg'
        Image.open(src).convert('RGB').save(
            f'{out}/OEBPS/images/{dest}', 'JPEG', quality=88, optimize=True,
            progressive=True)
        plate_dest[roman] = dest

    def figure_spans(b):
        """Every figure div, with its true closing tag.

        ⚠️ NOT a regex. `<div class="fig…">.*?</div>\\s*</div>` looks right and
        is a text-eater: a figure with no caption has only ONE closing div, so
        the non-greedy match runs on to the next figure's pair and swallows
        every paragraph in between. Count the depth instead.
        """
        spans = []
        for m in re.finditer(r'<div class="fig[^"]*"[^>]*>', b):
            depth, i = 1, m.end()
            while depth and i < len(b):
                nxt = re.search(r'<div\b[^>]*>|</div>', b[i:])
                if not nxt:
                    break
                depth += 1 if nxt.group().startswith('<div') else -1
                i += nxt.end()
            if depth == 0:
                spans.append((m.start(), i))
        return spans

    def protect_figures(b, chapter_figs):
        """Lift Paget's plates out of PG's markup before `clean` can lose them.

        ⚠️ The source sets an illustration as
            <div class="figcenter"><a id/><img/><div class="caption">…</div></div>
        and `clean` skips any div holding another block — so the picture was
        dropped and the caption alone survived as a stray line of small caps.
        An illustrated edition with captions and no illustrations.

        Each figure becomes a token in a paragraph of its own, which `clean`
        carries through untouched, and is put back afterwards with its caption
        intact — which the generic figure branch would also have thrown away.
        """
        out, last = [], 0
        for begin, end in figure_spans(b):
            block = b[begin:end]
            out.append(b[last:begin])
            last = end
            img = re.search(r'<img[^>]*src="([^"]+)"', block)
            name = os.path.basename(img.group(1)) if img else None
            if not name or name not in imgmap:
                continue                      # apparatus: drop it, keep the prose
            cap = re.search(r'<div class="caption"[^>]*>(.*?)</div>', block, re.S)
            kept.add(name)
            chapter_figs.append((imgmap[name], flatten(cap.group(1)) if cap else ''))
            out.append(f'<p>@@FIG{len(chapter_figs) - 1}@@</p>')
        out.append(b[last:])
        return ''.join(out)

    def restore_figures(xhtml, chapter_figs):
        for i, (dest, cap) in enumerate(chapter_figs):
            caption = f'<figcaption>{html.escape(cap)}</figcaption>' if cap else ''
            xhtml = xhtml.replace(
                f'<p>@@FIG{i}@@</p>',
                f'<figure class="paget"><img alt="{html.escape(cap)}" '
                f'src="../images/{dest}" />{caption}</figure>')
        return xhtml

    head = re.compile(r'Adventure\s+([IVX]+)\s+(.*)$', re.S)
    chapters, seen, budget = [], [], []

    # ⚠️ ONE STREAM, not one pass per file. Gutenberg splits this book across
    # four files WITHOUT regard to the stories: -h-1 opens mid-way through
    # Adventure III, -h-2 mid-VI, -h-3 mid-X. Cutting each file separately
    # therefore threw away the tail of every Adventure that crosses a
    # boundary — three whole endings, and the two Paget plates standing in
    # them. Join the bodies in spine order and cut the book, not the files.
    b = ''.join(
        body_of(open(d, encoding='utf-8', errors='ignore').read())
        for d in docs
        if not re.search(r'<h[12][^>]*>\s*THE FULL PROJECT GUTENBERG',
                         open(d, encoding='utf-8', errors='ignore').read(), re.I))
    if True:
        for m in re.finditer(r'<h2[^>]*>(.*?)</h2>', b, re.S | re.I):
            # ⚠️ The first heading carries the book's title run into it:
            # "ADVENTURES OF SHERLOCK HOLMES Adventure I A SCANDAL IN BOHEMIA".
            hm = head.search(flatten(m.group(1)))
            if not hm:
                continue
            roman, shout = hm.group(1).upper(), hm.group(2).strip()
            rest = b[m.end():]
            nxt = re.search(r'<h2[^>]*>', rest)
            body = rest[:nxt.start()] if nxt else rest

            chapter_figs = []
            body = protect_figures(body, chapter_figs)

            title = f'Adventure {roman}: {titled(shout)}'
            fn = f'C{len(chapters)+1:02d}-{slug(titled(shout))}.xhtml'
            plate = ''
            if roman in plate_dest:
                plate = (f'<figure class="plate"><img alt="" '
                         f'src="../images/{plate_dest[roman]}" /></figure>\n')
            open(f'{out}/OEBPS/text/{fn}', 'w', encoding='utf-8').write(
                restore_figures(
                    page(title, 'chapter', 'chapter',
                         f'{plate}<h2>{html.escape(title)}</h2>\n'
                         f'{clean(body, imgmap, kept)}'),
                    chapter_figs))
            chapters.append((fn, title))
            seen.append(roman)
            # ⚠️ Nothing disappears silently. Count the words the source holds
            # for this Adventure against the words the edition kept; captions
            # and page furniture account for a little, a text-eating bug for a
            # lot. This is the check that caught the regex above.
            got_words = len(flatten(open(f'{out}/OEBPS/text/{fn}',
                                         encoding='utf-8').read()).split())
            budget.append((title, got_words))

    dropped = sorted({os.path.basename(p) for p in glob.glob(f'{SRC}/*.jpg')}
                     - set(imgmap))
    plain = [re.sub(r'^\d+_', '', d) for d in dropped]
    print(f'  chapters: {len(chapters)}  ({", ".join(seen)})')
    print(f'  Paget illustrations carried: {len(imgmap)}, used in text: {len(kept)}')
    print(f'  plates: {len(plate_dest)}/12')
    print(f'  source images dropped (apparatus): {len(dropped)} — {", ".join(plain)}')
    unused = sorted(set(imgmap) - kept)
    if unused:
        print(f'  !! carried but never referenced: {len(unused)}')
    # Every word of the book from the first Adventure onward, captions and
    # page furniture aside — the honest denominator.
    # ⚠️ Not `<h2[^>]*>[^<]*Adventure` — the first heading carries markup
    # inside it, so a character class that forbids '<' never reaches the word
    # and the denominator comes out zero.
    first = next((m for m in re.finditer(r'<h2[^>]*>(.*?)</h2>', b, re.S)
                  if head.search(flatten(m.group(1)))), None)
    tail = re.sub(r'<div class="caption"[^>]*>.*?</div>', ' ',
                  b[first.start():], flags=re.S) if first else ''
    total_src = len(flatten(tail).split())
    total_got = sum(g for _, g in budget)
    share = 100 * total_got / max(1, total_src)
    print(f'  words: {total_got:,} kept of {total_src:,} in source ({share:.1f}%)')
    if share < 98:
        print(f'  !! {total_src - total_got:,} words of the book did not '
              f'reach the edition')
    return chapters


META = {
    'title': T,
    'author': A,
    'surname': 'Doyle',
    'pronoun': 'he',
    'year': '1892',
    'id': 'adventures-of-sherlock-holmes',
    'date': '2026-08-29',
    'series': 'The Adventures of Sherlock Holmes',
    'description': (
        'The twelve stories that made Sherlock Holmes, as they ran in the Strand '
        'Magazine between 1891 and 1892 — with Sidney Paget’s illustrations, and a '
        'colour plate at the head of every Adventure.'),
    'source': 'Project Gutenberg 48320 (Adventures of Sherlock Holmes, Illustrated)',
    'rights': ('The text and Sidney Paget’s illustrations are in the public domain. '
               'The cover, the twelve Adventure plates, and the arrangement of this '
               'edition are © RFRMD Word Labs, LLC.'),
    'sources': (
        '<p>The text is Project Gutenberg 48320, <i>Adventures of Sherlock Holmes</i>, '
        'Illustrated — prepared by Distributed Proofreaders from the 1892 George Newnes '
        'volume that gathered the twelve stories out of the <i>Strand Magazine</i>, where '
        'they had appeared one a month from July 1891.</p>\n'
        '<p>The fifteen drawings in the text are Sidney Paget’s, from the same printing. '
        'Paget gave Holmes the face the world settled on, and the deerstalker he is '
        'never once described as wearing.</p>\n'
        '<p>The cover and the twelve colour plates that head each Adventure were made '
        'for this edition and are not part of the public-domain source.</p>'),
}

DELIBERATE = (
    'Two things are deliberate, and are not errors. The colour plate that opens each '
    'Adventure was made for this edition — it is not a Victorian illustration, and is '
    'not trying to pass as one. The black-and-white drawings inside the stories are '
    'Sidney Paget’s own, from the <i>Strand</i>, and are reproduced as they stand.')


def main():
    print(f'=== {T} ===')
    unpack()
    shutil.rmtree(OUT, ignore_errors=True)
    for d in ('META-INF', 'OEBPS/text', 'OEBPS/css', 'OEBPS/images'):
        os.makedirs(f'{OUT}/{d}', exist_ok=True)
    os.makedirs(os.path.dirname(EPUB), exist_ok=True)

    chapters = chapters_from_source(OUT)
    if len(chapters) != 12:
        print(f'  !! expected 12 Adventures, cut {len(chapters)} — stopping')
        return 1

    # The proofing notice rides in front of the title page until John has read
    # it through; drop this block to publish.
    proof_fn = '00-proofing.xhtml'
    open(f'{OUT}/OEBPS/text/{proof_fn}', 'w', encoding='utf-8').write(
        proofing_xhtml(T, A, deliberate=DELIBERATE))

    package(OUT, chapters, META, f'{DESKTOP}/SherlockHolmes-Master.jpg', TPL, EPUB)

    # package() writes the manifest without knowing about the proofing page, so
    # thread it in behind the cover — the house order: cover, proofing, title.
    opf = open(f'{OUT}/OEBPS/content.opf', encoding='utf-8').read()
    opf = opf.replace('  </manifest>',
                      f'    <item id="proof" href="text/{proof_fn}" '
                      'media-type="application/xhtml+xml"/>\n  </manifest>')
    opf = re.sub(r'(<itemref idref="t0"/>)', r'\1\n    <itemref idref="proof"/>', opf)
    open(f'{OUT}/OEBPS/content.opf', 'w', encoding='utf-8').write(opf)

    css = open(f'{OUT}/OEBPS/css/style.css', encoding='utf-8').read()
    if '.plate' not in css:
        css += ('\n/* The Adventure plates: full measure, and alone on their line. */\n'
                'figure.plate{margin:0 0 1.2em;padding:0}\n'
                'figure.plate img{width:100%;height:auto;display:block}\n'
                '/* Paget, from the Strand — his captions were set in small caps. */\n'
                'figure.paget{margin:1.4em 0;padding:0;text-align:center}\n'
                'figure.paget img{max-width:100%;height:auto;display:block;margin:0 auto}\n'
                'figure.paget figcaption{font-size:.82em;letter-spacing:.06em;\n'
                '  color:#6b665e;margin-top:.5em;font-variant:small-caps}\n')
    open(f'{OUT}/OEBPS/css/style.css', 'w', encoding='utf-8').write(css + PROOFING_CSS)

    os.remove(EPUB)
    subprocess.run(['zip', '-qX0', EPUB, 'mimetype'], cwd=OUT, check=True)
    subprocess.run(['zip', '-qXr9', EPUB, 'META-INF', 'OEBPS'], cwd=OUT, check=True)
    print(f'  built {EPUB}  ({os.path.getsize(EPUB)/1e6:.1f} MB)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
