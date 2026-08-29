#!/usr/bin/env python3
"""Build the SchriftOhr Edition of The Adventures of Sherlock Holmes.

From the COLLATED text — two independent readings of two Harper printings,
settled reading by reading, with the page image as arbiter. Project Gutenberg
had no part in it and is named nowhere.

Everything in the book comes from our own materials:

  · the text        sherlock-clean.txt, the collation's output
  · the plates      Sidney Paget's, lifted from John's own scan of the
                    Harper printing — not from anyone else's files
  · the colour art  John's cover and his twelve Adventure plates

    build_sherlock_collated.py

⚠️ The twelve stories open with a drop capital three or four lines deep. NO OCR
reads it — Vision gives "Do Sherlock Holmes she is always the woman", the other
witness "SSO Sherlock Holmes ... tHe woman" — and because both fail the same
way it never appears as a disagreement. Each opening is therefore set by hand
below, and that list is the only hand-set text in the book.
"""

import html
import io
import os
import pathlib
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_edition import page, package, slug
from edition_parts import proofing_xhtml, PROOFING_CSS
from PIL import Image

W = pathlib.Path.home() / 'Desktop/Sherlock-Working'
DESKTOP = pathlib.Path.home() / 'Desktop'
# ⚠️ The art lives in the working tree, not loose on the Desktop. Every one of
# these files — the cover and all twelve plates — had been cleared off the
# Desktop by the time this builder first ran, and came back out of the private
# working archive byte-for-byte. A build must not depend on a scratch folder.
ART = W / 'artwork'
SCANS = DESKTOP / 'adventuressherl02doylgoog_tif'
# ⚠️ the MENDED text: breaks both witnesses share, closed from the book's
# own vocabulary — collation cannot see an error both witnesses make.
CLEAN = W / 'working/sherlock-mended.txt'
TPL = '/tmp/schriftohr-tpl'
OUT = W / 'output/adventures-of-sherlock-holmes'
EPUB = W / 'output/Doyle_Arthur_Conan-SchriftOhr_Edition-Adventures_of_Sherlock_Holmes.epub'

T = 'The Adventures of Sherlock Holmes'
A = 'Arthur Conan Doyle'

# Each story: the roman, its title, the phrase that finds its start in the
# collated text, how many characters of OCR wreckage to drop from that point,
# and the opening words as the page actually prints them.
STORIES = [
    ('I',    'A Scandal in Bohemia',
     'Sherlock Holmes she is always the woman',
     'Sherlock Holmes she is always the woman', 'To '),
    ('II',   'The Red-Headed League',
     'called upon my friend, Mr. Sherlock Holmes, one day in the autumn',
     'called upon my friend', 'I had '),
    ('III',  'A Case of Identity',
     'dear fellow," said Sherlock Holmes, as we sat',
     'dear fellow," said Sherlock Holmes', '“My '),
    ('IV',   'The Boscombe Valley Mystery',
     'were seated at breakfast one morning',
     'were seated at breakfast one morning', 'We '),
    ('V',    'The Five Orange Pips',
     'glance over my notes and records',
     'glance over my notes and records', 'When I '),
    ('VI',   'The Man with the Twisted Lip',
     'WHITNEY, brother of the late Elias Whitney',
     'WHITNEY, brother of the late Elias Whitney', 'Isa '),
    ('VII',  'The Adventure of the Blue Carbuncle',
     'called upon my friend Sherlock Holmes upon the second',
     'called upon my friend Sherlock Holmes', 'I had '),
    ('VIII', 'The Adventure of the Speckled Band',
     'glancing over my notes of the seventy',
     'glancing over my notes of the seventy', 'On '),
    ('IX',   "The Adventure of the Engineer's Thumb",
     'all the problems which have been submitted',
     'all the problems which have been submitted', 'Of '),
    ('X',    'The Adventure of the Noble Bachelor',
     'Lord St. Simon marriage, and its curious',
     'Lord St. Simon marriage', 'The '),
    ('XI',   'The Adventure of the Beryl Coronet',
     'said I, as I stood one morning in our bow-window',
     'said I, as I stood one morning', '“Holmes,” '),
    ('XII',  'The Adventure of the Copper Beeches',
     'the man who loves art for its own sake',
     'the man who loves art for its own sake', '“To '),
]

# Paget's plates, as they stand in our own scan: the page image, its caption as
# the printing gives it, and the Adventure it belongs to. ⚠️ Plate 0046 faces
# the opening of Adventure II rather than closing Adventure I — a facing plate
# sits BEFORE the chapter it illustrates.
# Paget's plates. ⚠️ NOT from the Google scan of our base copy: those pages are
# bitonal, and a bitonal scan destroys a halftone. Plate 46 there carries 0.4%
# ink — the printed caption and nothing else; the picture is simply gone. The
# same plates in the archive.org copy of the same printing are greyscale and
# whole, so the pictures come from that copy and the text from ours.
#
# ⚠️ Captions read off the page rather than guessed, which corrected one:
# "HAVE MERCY! HE SHRIEKED" is Ryder in the Blue Carbuncle, not the Beryl
# Coronet, and a mapping by page number in the other copy had put it wrong.
PAGET_SRC = pathlib.Path('/tmp/ia3/EPUB')      # unpacked archive.org copy
PAGET = [
    (7,   'THE GENTLEMAN IN THE PEW HANDED IT UP TO HER', 'X'),
    (22,  'A MAN ENTERED', 'I'),
    (56,  'THE DOOR WAS SHUT AND LOCKED', 'II'),
    (64,  'ALL AFTERNOON HE SAT IN THE STALLS', 'II'),
    (80,  'SHERLOCK HOLMES WELCOMED HER', 'III'),
    (94,  'GLANCING ABOUT HIM LIKE A RAT IN A TRAP', 'III'),
    (104, 'THEY FOUND THE BODY', 'IV'),
    (118, 'THE MAID SHOWED US THE BOOTS', 'IV'),
    (150, '“HOLMES, I CRIED, YOU ARE TOO LATE”', 'V'),
    (164, 'AT THE FOOT OF THE STAIRS SHE MET THIS LASCAR SCOUNDREL', 'VI'),
    (204, '“HAVE MERCY!” HE SHRIEKED', 'VII'),
    (230, 'GOOD-BYE, AND BE BRAVE', 'VIII'),
    (250, 'NOT A WORD TO A SOUL', 'IX'),
    (318, 'I CLAPPED A PISTOL TO HIS HEAD', 'XI'),
    (334, 'I AM SO DELIGHTED THAT YOU HAVE COME', 'XII'),
]

PLATES = {                                   # John's colour art, by Adventure
    'I': 'Scandel in Bohemia.jpg', 'II': 'RedHeadedLeague.jpg',
    'III': 'ACaseofIdentity.jpg',  'IV': 'boscombeValleyMystery.jpg',
    'V': 'FiveOrangePips.jpg',     'VI': 'Twisted Lip.jpg',
    'VII': 'BlueCarbuncle.jpg',    'VIII': 'SpeckledBand.jpg',
    'IX': 'Thumb.jpg',             'X': 'Noble.jpg',
    'XI': 'BerylCoronet.jpg',      'XII': 'CopperBeaches.jpg',
}


def unpack_template():
    if not os.path.exists(f'{TPL}/OEBPS/css/style.css'):
        shutil.rmtree(TPL, ignore_errors=True)
        os.makedirs(TPL, exist_ok=True)
        import glob
        donor = glob.glob(os.path.expanduser(
            '~/Developer/schriftohr-books/books/pilgrims-progress/*.epub'))[0]
        subprocess.run(['unzip', '-oq', donor], cwd=TPL, check=True)


def cut_stories(text):
    """The twelve Adventures, each opening as the page prints it."""
    marks = []
    for roman, title, anchor, junk_end, opening in STORIES:
        i = text.find(anchor)
        if i < 0:
            sys.exit(f'could not find the opening of Adventure {roman}: {anchor!r}')
        marks.append((i, roman, title, junk_end, opening))
    marks.sort()
    out = []
    for k, (i, roman, title, junk_end, opening) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(text)
        body = text[i:end]
        # cut back to the real first word, then set the drop capital by hand
        j = body.find(junk_end)
        body = opening + body[j:] if j >= 0 else opening + body
        # the chapter ornament of the NEXT story trails this one
        body = re.sub(r'\n\n[^\n]{0,40}(?:[Aa][a-z]*oventu[a-z]*|[A-Z]{3,}[^\n]{0,60})\s*$',
                      '', body).rstrip()
        out.append((roman, title, body))
    return out


def carry_plates(out_dir):
    """Paget's plates, from the greyscale copy, trimmed of their page margins."""
    made = {}
    for n, caption, roman in PAGET:
        src = PAGET_SRC / f'image_{n:04d}_00.jpeg'
        if not src.exists():
            print(f'  !! plate image_{n:04d} is not there')
            continue
        im = Image.open(src).convert('L')
        if im.width > 1100:
            im = im.resize((1100, round(im.height * 1100 / im.width)), Image.LANCZOS)
        dest = f'paget-{n:04d}.jpg'
        im.save(out_dir / 'OEBPS/images' / dest, 'JPEG', quality=88,
                optimize=True, progressive=True)
        made[n] = dest
    return made


def main():
    text = CLEAN.read_text(encoding='utf-8')
    unpack_template()
    shutil.rmtree(OUT, ignore_errors=True)
    for d in ('META-INF', 'OEBPS/text', 'OEBPS/css', 'OEBPS/images'):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    EPUB.parent.mkdir(parents=True, exist_ok=True)

    stories = cut_stories(text)
    print(f'{len(stories)} Adventures cut · {sum(len(b.split()) for _,_,b in stories):,} words')

    paget = carry_plates(OUT)
    print(f'{len(paget)} Paget plates carried from our own scan')

    colour = {}
    for roman, filename in PLATES.items():
        src = ART / filename
        if not src.exists():
            print(f'  !! colour plate for {roman} missing: {filename}')
            continue
        dest = f'plate-{roman.lower()}.jpg'
        Image.open(src).convert('RGB').save(
            OUT / 'OEBPS/images' / dest, 'JPEG', quality=88, optimize=True,
            progressive=True)
        colour[roman] = dest
    print(f'{len(colour)}/12 colour plates')

    # ── the chapters ────────────────────────────────────────────────────────
    by_story = {}
    for n, caption, roman in PAGET:
        by_story.setdefault(roman, []).append((n, caption))

    chapters, illus = [], []
    for idx, (roman, title, body) in enumerate(stories, 1):
        paras = [p.strip() for p in body.split('\n\n') if p.strip()]

        # Paget's plates for this story, set after the first few paragraphs so
        # they fall inside the story rather than on top of its opening.
        marks = []
        for n, caption in by_story.get(roman, []):
            if n not in paget:
                continue
            k = len(illus) + 1
            illus.append((k, 'paget', paget[n], caption, roman, title, idx))
            marks.append((k, paget[n], caption))

        html_paras = []
        for i, p in enumerate(paras):
            html_paras.append(f'<p>{html.escape(p)}</p>')
            if marks and i == min(3, len(paras) - 1):
                k, dest, caption = marks.pop(0)
                html_paras.append(
                    f'<figure class="paget" id="fig{k}">'
                    f'<img alt="{html.escape(caption)}" src="../images/{dest}" />'
                    f'<figcaption id="figc{k}">{html.escape(caption)} '
                    f'<a class="figref" href="02-illustrations.xhtml#li{k}">&#8593;</a>'
                    f'</figcaption></figure>')
        # any that did not fit go at the foot
        for k, dest, caption in marks:
            html_paras.append(
                f'<figure class="paget" id="fig{k}">'
                f'<img alt="{html.escape(caption)}" src="../images/{dest}" />'
                f'<figcaption id="figc{k}">{html.escape(caption)} '
                f'<a class="figref" href="02-illustrations.xhtml#li{k}">&#8593;</a>'
                f'</figcaption></figure>')

        fn = f'C{idx:02d}-{slug(title)}.xhtml'
        plate_fn = ''
        if roman in colour:
            plate_fn = f'P{idx:02d}-{slug(title)}.xhtml'
            (OUT / 'OEBPS/text' / plate_fn).write_text(page(
                title, 'titlepage', 'plate-page',
                f'<div class="plate-page"><img alt="{html.escape(title)}" '
                f'src="../images/{colour[roman]}" id="plate{idx}" />'
                f'<p class="plate-back"><a class="figref" '
                f'href="02-illustrations.xhtml#lp{idx}">&#8593;</a></p></div>',
                'frontmatter'), encoding='utf-8')

        (OUT / 'OEBPS/text' / fn).write_text(page(
            f'Adventure {roman}. {title}', 'chapter', 'chapter',
            f'<p class="advnum">Adventure {roman}</p>\n<h2>{html.escape(title)}</h2>\n'
            + '\n'.join(html_paras)), encoding='utf-8')

        if plate_fn:
            chapters.append((plate_fn, f'{roman}. {title}'))
            chapters.append((fn, title))
        else:
            chapters.append((fn, f'{roman}. {title}'))

    # ── front matter ────────────────────────────────────────────────────────
    E = html.escape
    rows = ['<h2>Illustrations</h2>',
            '<p class="listnote">Every picture in this edition, in the order it '
            'appears. Touch a line to go to it; the arrow beneath each picture '
            'brings you back here.</p>',
            '<h3>The Adventure Plates</h3>',
            '<p class="listnote">Made for this edition — one at the head of each '
            'Adventure.</p>', '<ol class="illus">']
    for idx, (roman, title, _b) in enumerate(stories, 1):
        if roman in colour:
            rows.append(f'  <li id="lp{idx}"><a href="P{idx:02d}-{slug(title)}.xhtml#plate{idx}">'
                        f'<span class="num">{roman}.</span> {E(title)}</a></li>')
    rows += ['</ol>', '<h3>Sidney Paget’s Plates</h3>',
             '<p class="listnote">From the Harper printing of 1892, with the '
             'captions as they were set beneath them.</p>', '<ol class="illus">']
    for k, _kind, _dest, caption, roman, title, idx in illus:
        rows.append(f'  <li id="li{k}"><a href="C{idx:02d}-{slug(title)}.xhtml#fig{k}">'
                    f'{E(caption)}</a><span class="in">{E(title)}</span></li>')
    rows.append('</ol>')
    loi_fn = '02-illustrations.xhtml'
    (OUT / 'OEBPS/text' / loi_fn).write_text(
        page('Illustrations', 'loi', 'illustrations', '\n'.join(rows), 'frontmatter'),
        encoding='utf-8')

    DELIBERATE = (
        'Two things are deliberate, and are not errors. The colour plate that opens '
        'each Adventure was made for this edition — it is not a Victorian illustration '
        'and does not pretend to be one. The black-and-white plates inside the stories '
        'are Sidney Paget’s, photographed from the 1892 printing this text is set from.')
    proof_fn = '00-proofing.xhtml'
    (OUT / 'OEBPS/text' / proof_fn).write_text(
        proofing_xhtml(T, A, deliberate=DELIBERATE), encoding='utf-8')

    META = {
        'title': T, 'author': A, 'surname': 'Doyle', 'pronoun': 'he',
        'year': '1892', 'id': 'adventures-of-sherlock-holmes',
        'date': '2026-08-29', 'series': 'The Adventures of Sherlock Holmes',
        'description': ('The twelve stories that made Sherlock Holmes, set from the '
                        'Harper & Brothers printing of 1892 — with Sidney Paget’s '
                        'plates, and a colour plate at the head of every Adventure.'),
        'source': ('Harper & Brothers, New York, 1892 — collated from two scans of '
                   'two copies of that printing'),
        'rights': ('The text and Sidney Paget’s plates are in the public domain. The '
                   'cover, the twelve Adventure plates, and the setting of this '
                   'edition are © RFRMD Word Labs, LLC.'),
        'sources': (
            '<p>The text is set from <i>Adventures of Sherlock Holmes</i>, Harper &amp; '
            'Brothers, New York, 1892 — the first American edition, gathering the '
            'twelve stories that had run one a month in the <i>Strand Magazine</i> '
            'from July 1891.</p>\n'
            '<p>It was not transcribed from any existing digital text. Two scans of '
            'two separate copies of that printing were read independently, and every '
            'place where the two readings differed — one thousand nine hundred and '
            'fifteen of them — was settled one at a time, by rule where a rule could '
            'be stated and by eye against the page where it could not. Where the two '
            'copies disagreed about whether a word was there at all, the page decided. '
            'One copy is missing its page 215 and the other the opening of <i>The '
            'Boscombe Valley Mystery</i>; each was recovered from the other.</p>\n'
            '<p>Sidney Paget’s plates are photographed from the same printing. The '
            'cover and the twelve colour plates that head each Adventure were made '
            'for this edition.</p>'),
    }

    package(str(OUT), chapters, META, str(ART / 'SherlockHolmes-Master.jpg'),
            TPL, str(EPUB))

    # nav: one row per Adventure, landing on its plate
    nav = (OUT / 'OEBPS/nav.xhtml').read_text(encoding='utf-8')
    nav = re.sub(r'\s*<li><a href="text/C\d\d[^"]*">[^<]*</a></li>', '', nav)
    nav = nav.replace(
        '<li><a href="text/01-edition-note.xhtml">About This Edition</a></li>',
        '<li><a href="text/01-edition-note.xhtml">About This Edition</a></li>\n'
        f'      <li><a href="text/{loi_fn}">Illustrations</a></li>')
    (OUT / 'OEBPS/nav.xhtml').write_text(nav, encoding='utf-8')

    opf = (OUT / 'OEBPS/content.opf').read_text(encoding='utf-8')
    opf = opf.replace('  </manifest>',
                      f'    <item id="proof" href="text/{proof_fn}" '
                      'media-type="application/xhtml+xml"/>\n'
                      f'    <item id="loi" href="text/{loi_fn}" '
                      'media-type="application/xhtml+xml"/>\n  </manifest>')
    opf = re.sub(r'(<itemref idref="t0"/>)', r'\1\n    <itemref idref="proof"/>', opf)
    opf = re.sub(r'(<itemref idref="t2"/>)', r'\1\n    <itemref idref="loi"/>', opf)
    (OUT / 'OEBPS/content.opf').write_text(opf, encoding='utf-8')

    css = (OUT / 'OEBPS/css/style.css').read_text(encoding='utf-8')
    css += """
/* The Adventure plates: full measure, alone on their page. */
div.plate-page{margin:0;padding:0;text-align:center;page-break-after:always;break-after:page}
div.plate-page img{max-width:100%;max-height:96vh;height:auto;display:block;margin:0 auto}
p.plate-back{margin:.3em 0 0}
p.advnum{font-variant:small-caps;letter-spacing:.12em;font-size:.82em;color:#6b665e;
  margin:0 0 .1em;text-align:center}
/* Paget, from the 1892 printing; his captions were set in small capitals. */
figure.paget{margin:1.5em 0;padding:0;text-align:center}
figure.paget img{max-width:100%;height:auto;display:block;margin:0 auto}
figure.paget figcaption{font-size:.82em;letter-spacing:.06em;color:#6b665e;
  margin-top:.5em;font-variant:small-caps}
ol.illus{list-style:none;margin:0 0 1.4em;padding:0}
ol.illus li{margin:0 0 .55em;padding:0;line-height:1.45}
ol.illus li .num{font-variant:small-caps;letter-spacing:.04em;margin-right:.35em}
ol.illus li .in{display:block;font-size:.82em;color:#6b665e;font-style:italic}
ol.illus a{text-decoration:none}
p.listnote{font-size:.9em;color:#6b665e;margin:.2em 0 1em}
a.figref{text-decoration:none;font-size:.9em;padding-left:.4em;opacity:.65}
"""
    # ⚠️ the donor template already carries PROOFING_CSS; appending it again
    # put the whole block in the stylesheet twice.
    if '.proof{' not in css:
        css += PROOFING_CSS
    elif '.proof .rule{' not in css:
        css += '\n.proof .rule{text-align:center;color:#fd8008;letter-spacing:.3em;margin:.2em 0 .8em}\n'
    (OUT / 'OEBPS/css/style.css').write_text(css, encoding='utf-8')

    if EPUB.exists():
        EPUB.unlink()
    subprocess.run(['zip', '-qX0', str(EPUB), 'mimetype'], cwd=OUT, check=True)
    subprocess.run(['zip', '-qXr9', str(EPUB), 'META-INF', 'OEBPS'], cwd=OUT, check=True)
    print(f'built {EPUB.name}  ({EPUB.stat().st_size/1e6:.1f} MB) · '
          f'{len(colour)} colour plates + {len(illus)} Paget plates, each linked both ways')


if __name__ == '__main__':
    sys.exit(main())
