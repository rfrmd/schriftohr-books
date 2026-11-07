#!/usr/bin/env python3
"""Front matter every SchriftOhr Edition shares.

The cover is set as a full-page SVG rather than a bare <img>: a plain image
is scaled by each reader's own rules and can land small and centred on a
field of white. The SVG viewBox makes it fill the page everywhere.

The proofing notice rides in front of the title page while a book is still
being read for errors. It carries a build stamp so a report can be tied to
the exact copy it came from — remove the page (drop `proofing=` from the
builder) when the edition is ready to publish.
"""
import html, os
from datetime import date

XHTML_OPEN = ('<?xml version="1.0" encoding="utf-8"?>\n'
              '<html xmlns="http://www.w3.org/1999/xhtml" '
              'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n')

def cover_xhtml(width, height, src='../images/cover.jpg'):
    return (XHTML_OPEN +
      '<head><title>Cover</title><meta charset="utf-8"/>\n'
      '<style>html,body{margin:0;padding:0;height:100%}\n'
      'body{background:#000}\n'
      'svg{display:block;width:100%;height:100%}</style></head>\n'
      '<body epub:type="frontmatter"><section epub:type="cover" class="cover">\n'
      '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"\n'
      f'     version="1.1" width="100%" height="100%" viewBox="0 0 {width} {height}"\n'
      '     preserveAspectRatio="xMidYMid meet">\n'
      # BOTH href and xlink:href: the first is SVG 2, the second SVG 1.1, and
      # readers are split between them — with only xlink some draw nothing at
      # all, and the book appears to open on its title page.
      f'  <image width="{width}" height="{height}" href="{src}" xlink:href="{src}"/>\n'
      '</svg>\n</section></body></html>\n')

SCRIPT_CSS = """
/* Greek and Hebrew, restored where the keyers left the page blank, each
   followed by how it sounds — for the reader who does not read the script,
   and for the voice reading the book aloud. */
.gk{font-family:"GFS Didot","New Athena Unicode","Palatino Linotype",Palatino,serif}
.hb{font-family:"SBL Hebrew","Ezra SIL","Times New Roman",serif;font-size:1.06em}
.ph{font-size:.9em;color:#6b665e;font-style:normal}
"""

PROOFING_CSS = """
.proof hr.rule{border:0;border-top:2px solid #fd8008;margin:1em 0 1.1em}
/* The proofing notice. Loud on purpose: this copy is not for keeping.
   .note is the same box for a published edition — the orange is the house
   mark and stays; only the words change. */
/* two-thirds size and never split, so it stays on one page in every reader (John, 2026-10-29) */
.proof{border:2px solid #fd8008;border-radius:10px;padding:1.2em 1.1em;margin:1.5em 0;font-size:67%;break-inside:avoid;page-break-inside:avoid}
.proof h1{font-size:1.25em;letter-spacing:.14em;text-align:center;color:#fd8008;
          margin:0 0 .8em;text-transform:uppercase}
.proof p{text-indent:0;margin:.75em 0;font-size:.97em;text-align:left}
.proof .stamp{font-size:.84em;color:#777;text-align:center;margin-top:1.2em;
              border-top:1px solid #ddd;padding-top:.7em}
/* the published note likewise: two-thirds size and never split, one page in every reader (John, 2026-11-03) */
.note{border:2px solid #fd8008;border-radius:10px;padding:1.2em 1.1em;margin:1.5em 0;font-size:67%;break-inside:avoid;page-break-inside:avoid}
.note h1{font-size:1.25em;letter-spacing:.14em;text-align:center;color:#fd8008;
         margin:0 0 .8em;text-transform:uppercase}
.note p{text-indent:0;margin:.75em 0;font-size:.97em;text-align:left}
.note .stamp{font-size:.84em;color:#777;text-align:center;margin-top:1.2em;
             border-top:1px solid #ddd;padding-top:.7em}
"""


def corrections_xhtml(title, author, build=None, contact='john@rfrmdwordlabs.com'):
    """The published edition's version of the same invitation.

    A finished book should not tell its reader it is unfinished, but it can
    still ask to be told when something is wrong — every one of these is set
    from a scan or builds on another's transcription, and errors survive either way
    (John, 2026-09-24: the old sentence was not true of the transcription-built books).
    """
    E = html.escape
    build = build or date.today().isoformat()
    return (XHTML_OPEN +
      '<head><title>About This Copy</title><meta charset="utf-8"/>'
      '<link rel="stylesheet" type="text/css" href="../css/style.css"/></head>\n'
      '<body epub:type="frontmatter"><section epub:type="preamble" class="preamble">\n'
      '<div class="note">\n'
      '<h1>About This Copy</h1>\n'
      '<p>This is a <i>SchriftOhr Edition</i>: a book long out of copyright, set again '
      'with care — for reading on a page, and for listening to aloud. It is free, and '
      'yours to keep and to pass on.</p>\n'
      '<p>Every edition here begins either with a scan of an old printing or with a '
      'transcription that others made before us. The Sources and Acknowledgements at the '
      'back say which, and name them. Errors can survive either way. If something reads wrongly — a misprint, a word that sits oddly, a chapter '
      'that begins in the wrong place — we would be glad to be told. Note the chapter and '
      'the sentence around it and send it to '
      f'<a href="mailto:{contact}">{contact}</a>. Small things are worth reporting; they '
      'are how the next printing gets better.</p>\n'
      f'<p class="stamp">{E(title)} &#183; {E(author)}<br/>'
      f'SchriftOhr Edition &#183; build {E(build)}</p>\n'
      '</div>\n</section></body></html>\n')

def proofing_xhtml(title, author, build=None, contact='john@rfrmdwordlabs.com',
                   deliberate=None):
    """`deliberate`: the "these are not errors" paragraph, when a book needs
    its own. The default speaks of seventeenth-century spelling and damaged
    pages, which is true of the Reformed shelf and of nothing else — a Doyle
    proofing copy that warned about long-s would be telling the reader a
    falsehood about the book in their hands."""
    E = html.escape
    build = build or date.today().isoformat()
    note = deliberate or (
        'Two things are deliberate, and are not errors. The seventeenth-century '
        'spelling stands as the author wrote it. And where the original page was '
        'damaged past reading, a word that could not be established is marked '
        '<i>[&#8230;]</i>.')
    return (XHTML_OPEN +
      '<head><title>Proofing Copy</title><meta charset="utf-8"/>'
      '<link rel="stylesheet" type="text/css" href="../css/style.css"/></head>\n'
      '<body epub:type="frontmatter"><section epub:type="preamble" class="preamble">\n'
      '<div class="proof">\n'
      '<h1>Proofing Copy</h1>\n'
      # ⚠️ The orange box is CSS, and SchriftOhr's own reader takes only bold and
      # italic from a book's stylesheet — borders and colour live in publisher
      # view alone. So the notice must also announce itself in ways that survive
      # any renderer: a rule made of characters, and BOLD on the sentence that
      # matters (John, 2026-08-29: "where is the orange proofing page it looks
      # like text").
      '<hr class="rule"/>\n'
      '<p><strong>This edition is not finished. It is circulated for reading and '
      'correction — please read and enjoy, but rather than pass it on, ask others '
      'to acquire it from us as we may have updated and improved the edition.'
      '</strong></p>\n'
      '<p>If something reads wrongly — a misprint, a word that sits oddly, a chapter '
      'that begins in the wrong place, a heading out of order — note the chapter and '
      'the sentence around it and send it to '
      f'<a href="mailto:{contact}">{contact}</a>. Small things are worth reporting; '
      'they are exactly what this copy is for.</p>\n'
      f'<p>{note}</p>\n'
      f'<p class="stamp">{E(title)} &#183; {E(author)}<br/>'
      f'SchriftOhr Edition &#183; build {E(build)}</p>\n'
      '</div>\n</section></body></html>\n')


# ── the proof band ──────────────────────────────────────────────────────────

PROOF_ORANGE = (253, 128, 8)

def stamp_proof_cover(src, dst, label='PROOFING COPY', at=0.425, quality=90):
    """Band a cover so a proof is obvious on a shelf of finished books.

    ⚠️ The orange notice inside a proof is no use where a reader chooses what
    to open. A proofing copy sitting in a library grid beside published
    editions looks exactly like one of them — John, 2026-08-29, of the Sherlock
    cover: "it just doesn't have the orange bordered proof copy on it."

    ⚠️ NOT ACROSS THE FOOT. That is where the publisher's mark sits, and the
    first attempt put the band straight over the RFRMD Word Labs logo. `at`
    is the band's centre as a fraction of the height; the default sits it in
    the upper-middle, which on these covers is the quietest ground and still
    reads at thumbnail size.
    """
    from PIL import Image, ImageDraw, ImageFont

    im = Image.open(src).convert('RGB')
    W, H = im.size
    band_h = max(44, round(H * 0.070))
    y0 = max(0, round(H * at - band_h / 2))
    y1 = min(H, y0 + band_h)
    pad = round(W * 0.035)

    layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle([pad, y0, W - pad, y1], fill=(18, 18, 20, 232),
                outline=PROOF_ORANGE + (255,), width=max(3, round(W * 0.005)))

    size = round(band_h * 0.46)
    font = None
    for path in ('/System/Library/Fonts/Supplemental/Arial Bold.ttf',
                 '/System/Library/Fonts/Supplemental/Georgia Bold.ttf'):
        try:
            font = ImageFont.truetype(path, size); break
        except OSError:
            continue
    text = ' '.join(label.upper())          # letter-spaced, like the notice
    if font:
        box = d.textbbox((0, 0), text, font=font)
        d.text(((W - (box[2] - box[0])) / 2, (y0 + y1) / 2 - (box[3] - box[1]) / 2 - box[1]),
               text, font=font, fill=PROOF_ORANGE + (255,))
    else:
        d.text((pad + 12, y0 + band_h / 3), text, fill=PROOF_ORANGE + (255,))

    out = Image.alpha_composite(im.convert('RGBA'), layer).convert('RGB')
    out.save(dst, 'JPEG', quality=quality, optimize=True, progressive=True)
    return out.size


def closing_xhtml(title='How These Books Are Made', portions=None):
    """The last written page: how an edition is made, and the hope.

    ⚠️ John, 2026-08-30: the closing COVER carries why these old books are worth the
    effort, so this page does not repeat it. John, 2026-11-03: plain and true of every
    book on the shelf, not bigger than we are; what was done to one book is said in its
    own About This Edition, so this page makes no promise a book does not keep.
    """
    P = '<p>%s</p>\n'
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
      '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
      'xml:lang="en-GB" lang="en-GB">\n<head><title>' + html.escape(title) + '</title>'
      '<meta charset="utf-8"/><link rel="stylesheet" type="text/css" href="../css/style.css"/>'
      '</head>\n<body epub:type="backmatter"><section epub:type="afterword" class="preamble">\n'
      '<h2>' + html.escape(title) + '</h2>\n'
      + P % ('The leaf after this one says why we make them. This page says how.')
      + '<h3>How an edition comes to be</h3>\n'
      + P % ('Each book starts as a <b>proofing copy</b> and is read for errors, by us and by '
             'readers who write in. When that is done it is issued as an edition, with the '
             'corrections in.')
      + '<h3>What was done to this book</h3>\n'
      + P % ('Its own <b>About This Edition</b>, at the front, says which printing it was set '
             'from, what was changed and what was left alone.')
      + P % ('Some books are set as their printer set them, cleared of the errors that came '
             'with putting them into digital form. Others are also <b>lightly modernised</b>: '
             'old spellings and forms brought up to date, so the book reads easily and sounds '
             'right when read aloud. A modernised book says what was changed.')
      + '<h3>Reading it in portions</h3>\n'
      + P % (portions or ('We break a book only where the author does. Where he says \u201cI shall do these '
             'three things\u201d, we set a heading there and list it in the contents. Where he '
             'marks nothing, we add nothing, so one chapter may have several headings and the '
             'next none.'))
      + '<h3>Spelling</h3>\n'
      + P % ('Where an author wrote English spelling (<i>Saviour</i>, <i>honour</i>, '
             '<i>labour</i>), we keep it. Where a book is set in American spelling, or has its '
             'old spellings brought up to date, its About This Edition says so.')
      + '<h3>How we keep them faithful</h3>\n<ul>\n'
      + '<li>We say what we set from, and where it was found.</li>\n'
      + '<li>Where more than one copy survives, we read one against another.</li>\n'
      + '<li>Where a word was lost or misread, we put it right from the printed page.</li>\n'
      + '<li>Nothing is invented. Where a page is lost and no copy settles it, the book says so.</li>\n'
      + '<li>Nothing is cut. No chapter is left out and nothing is summarised.</li>\n</ul>\n'
      + '<h3>What we hope of it</h3>\n'
      + P % ('That it reaches people, grows their love for the Lord, and increases their joy '
             'in reading.')
      + P % ('If you find something wrong in it, we would rather know.')
      + '</section></body></html>\n')


def heard_xhtml(title='This Book Is Made to Be Heard', greek=True, figures=True, refs=True, notes=False, latin=False, scan=True):
    """A short note at the FRONT. John, 2026-08-30: the explanation belongs in a
    foreword as well as at the back, so a reader meeting a phonetic gloss on page three
    need not reach the last page to learn why it is there. John, 2026-11-03: it says
    only what this book does, so each part is given or left out by the builder."""
    P = '<p>%s</p>\n'
    body = P % ('It is set to be read aloud as well as read, and a few things in it are there '
                'for that reason.')
    if greek:
        body += P % ('Every Greek and Hebrew word carries its sound beside it, because a voice '
                     'cannot read those alphabets.')
    if latin:
        body += P % ('The Greek and Hebrew words are given in Latin letters, because a voice '
                     'cannot read those alphabets.')
    if figures:
        body += P % ('Chapters are numbered 1, 2, 3 rather than I, II, III, because a voice '
                     'meeting \u201cChapter II\u201d may say anything at all.')
    if refs:
        body += P % ('Abbreviations and Scripture references are written out in full, so the '
                     'voice reads them as words.')
    if notes:
        body += P % ('Notes are set apart, where you can tap them, so the voice does not read '
                     'them in the middle of a sentence.')
    if scan:
        body += P % ('What the scan left behind, page numbers and running heads in the middle of '
                     'a sentence, is cleared away, so the voice reads only the book.')
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
      '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n'
      '<head><title>' + html.escape(title) + '</title><meta charset="utf-8"/>'
      '<link rel="stylesheet" type="text/css" href="../css/style.css"/></head>\n'
      '<body epub:type="frontmatter"><section epub:type="preface" class="preamble">\n'
      '<h2>' + html.escape(title) + '</h2>\n'
      + body + '</section></body></html>\n')
