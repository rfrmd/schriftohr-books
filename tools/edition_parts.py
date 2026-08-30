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
