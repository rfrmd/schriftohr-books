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
.proof{border:2px solid #fd8008;border-radius:10px;padding:1.2em 1.1em;margin:2.2em 0}
.proof h1{font-size:1.25em;letter-spacing:.14em;text-align:center;color:#fd8008;
          margin:0 0 .8em;text-transform:uppercase}
.proof p{text-indent:0;margin:.75em 0;font-size:.97em;text-align:left}
.proof .stamp{font-size:.84em;color:#777;text-align:center;margin-top:1.2em;
              border-top:1px solid #ddd;padding-top:.7em}
.note{border:2px solid #fd8008;border-radius:10px;padding:1.2em 1.1em;margin:2.2em 0}
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
    from a scan or an old printing, and errors survive that.
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
      '<p>Every edition here begins with a scan or an old printing, and errors survive '
      'that. If something reads wrongly — a misprint, a word that sits oddly, a chapter '
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


def closing_xhtml(title='Why We Make These Books'):
    """The last page of every edition: why the book exists, and the rules we keep.

    John, 2026-08-30. A proofing copy is a STAGE, not an apology — it ends, after
    the readers have had it, in an initial edition. And every book says on its own
    front matter what was done to its text, because the shelf will hold both plain
    transcriptions and, in time, faithful modernised editions, and a reader is
    owed the difference.
    """
    P = ('<p>%s</p>\n')
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
      '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
      'xml:lang="en-GB" lang="en-GB">\n<head><title>' + html.escape(title) + '</title>'
      '<meta charset="utf-8"/><link rel="stylesheet" type="text/css" href="../css/style.css"/>'
      '</head>\n<body epub:type="backmatter"><section epub:type="afterword" class="preamble">\n'
      '<h2>' + html.escape(title) + '</h2>\n'
      + P % ('What we are after is a faithful text: the author\u2019s own words, set from a '
             'printing we can name, and set out to be read.')
      + P % ('These were written by brothers from another age \u2014 men who thought long and '
             'hard about God and wrote down what they found. The depth of the thinking and the '
             'distance of the years both make them heavy going in places. We think they are '
             'worth the effort, if they draw heart and mind to consider our need of a Saviour.')
      + P % ('So they are set for reading together. A chapter is broken where the author '
             'himself breaks it, which gives a group somewhere to stop and something to take '
             'up; and the point of the talk is never the book but the God it is about \u2014 '
             'the most glorious God, our Saviour.')
      + '<h3>Reading it in portions</h3>\n'
      + P % ('A book like this is not read at a sitting, and where it breaks decides '
             'whether a group can use it. So the divisions matter, and we take them '
             'seriously.')
      + P % ('We divide only where the author divides. Where he says \u201cI shall do '
             'these three things\u201d, or \u201cthe second thing proposed is\u201d, we '
             'set a heading there and give it a place in the contents. The break then '
             'falls where his own thought turns \u2014 which is also where a reader can '
             'stop and a group can begin talking.')
      + P % ('Where he signposts nothing, we add nothing. That is why one chapter may be '
             'opened into six passages and the next not divided at all. It is not '
             'inconsistency. It is the author\u2019s own shape, and imposing a tidier one '
             'would mean deciding for him where his argument turns.')
      + P % ('The same divisions serve a reader alone. A chapter too long to hold is a '
             'chapter that gets set down.')
      + '<h3>How an edition comes to be</h3>\n'
      + P % ('Every book here begins as a <b>proofing copy</b>. That is not an apology, it is '
             'a stage. The text has been set with care and now wants other eyes on it. Readers '
             'who find an error tell us, and we correct it.')
      + P % ('When that has run its course the book is issued as an <b>initial edition</b> '
             '\u2014 the same work, settled, with the corrections in and the proofing notice '
             'gone.')
      + '<h3>What was done to this book</h3>\n'
      + P % ('<b>Every edition states, on its own front matter, what was done to its text.</b> '
             'Not in general terms: which printing, what was changed, what was left alone, and '
             'what could not be recovered.')
      + P % ('We begin with <b>straightforward transcription</b> \u2014 the author\u2019s '
             'words as he set them, cleared of what the passage into digital form left behind, '
             'and nothing more.')
      + P % ('In time we hope to offer <b>faithful modernised editions</b> as well: the same '
             'work brought forward in spelling and in the conventions of the page, for a reader '
             'who would otherwise set it down. Where a book has been modernised it says so, and '
             'says what was changed. It will not be silent about it, and it will not be '
             'abridged.')
      + '<h3>A word on spelling</h3>\n'
      + P % ('We keep English spelling \u2014 <i>Saviour</i>, <i>honour</i>, <i>labour</i> '
             '\u2014 because that is how these authors wrote and how their printers set them. '
             'Where we bring a spelling forward it is because the word itself has changed, '
             'never to suit a different country.')
      + '<h3>How we keep them faithful</h3>\n<ol>\n'
      + '<li><b>We name what we set from.</b> Every edition says which printing, and where that '
        'printing was found.</li>\n'
      + '<li><b>Where two copies survive, we collate them</b> \u2014 and record every place '
        'they differ, with the reason one was preferred.</li>\n'
      + '<li><b>Scripture is left exactly as it was printed</b>, capitals, spelling and all. '
        'Those words are not ours to modernise.</li>\n'
      + '<li><b>The author\u2019s own English is left alone.</b> We may correct his spelling; '
        'we do not rewrite him. <i>Thou</i>, <i>hath</i> and <i>doth</i> stand.</li>\n'
      + '<li><b>Nothing is invented.</b> Where the page is lost and no witness settles it, the '
        'edition says so. A book that quietly fills its holes with something plausible reads '
        'better and is worth less.</li>\n'
      + '<li><b>A heading we add stands only where the author announces the division '
        'himself.</b> Where he divides nothing, we add nothing.</li>\n'
      + '<li><b>Nothing is abridged.</b> No chapter cut, nothing summarised, nothing left out '
        'because it is difficult.</li>\n</ol>\n'
      + P % ('If you find something wrong, we would rather know.')
      + '</section></body></html>\n')

def heard_xhtml(title='This Book Is Made to Be Heard'):
    """A short note at the FRONT. John, 2026-08-30: the explanation belongs in a
    foreword as well as at the back — a reader meeting a phonetic gloss on page three
    should not have to reach the last page to learn why it is there."""
    P = '<p>%s</p>\n'
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
      '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n'
      '<head><title>' + html.escape(title) + '</title><meta charset="utf-8"/>'
      '<link rel="stylesheet" type="text/css" href="../css/style.css"/></head>\n'
      '<body epub:type="frontmatter"><section epub:type="preface" class="preamble">\n'
      '<h2>' + html.escape(title) + '</h2>\n'
      + P % ('It is set to be read aloud as well as read, and some of what is in it is '
             'here for no other reason.')
      + P % ('Every Greek and Hebrew word carries its sound beside it, because a '
             'narrator can read neither alphabet. Chapters are numbered 1, 2, 3 rather '
             'than I, II, III, because a voice meeting \u201cChapter II\u201d may say '
             'anything at all. Abbreviations are written out, and Scripture references '
             'are resolved, because a listener cannot turn back to a footnote.')
      + P % ('None of it shows on the page. It shows when the book is spoken.')
      + '</section></body></html>\n')
