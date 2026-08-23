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
      f'  <image width="{width}" height="{height}" xlink:href="{src}"/>\n'
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
/* The proofing notice. Loud on purpose: this copy is not for keeping. */
.proof{border:2px solid #fd8008;border-radius:10px;padding:1.2em 1.1em;margin:2.2em 0}
.proof h1{font-size:1.25em;letter-spacing:.14em;text-align:center;color:#fd8008;
          margin:0 0 .8em;text-transform:uppercase}
.proof p{text-indent:0;margin:.75em 0;font-size:.97em;text-align:left}
.proof .stamp{font-size:.84em;color:#777;text-align:center;margin-top:1.2em;
              border-top:1px solid #ddd;padding-top:.7em}
"""

def proofing_xhtml(title, author, build=None, contact='john@rfrmdwordlabs.com'):
    E = html.escape
    build = build or date.today().isoformat()
    return (XHTML_OPEN +
      '<head><title>Proofing Copy</title><meta charset="utf-8"/>'
      '<link rel="stylesheet" type="text/css" href="../css/style.css"/></head>\n'
      '<body epub:type="frontmatter"><section epub:type="preamble" class="preamble">\n'
      '<div class="proof">\n'
      '<h1>Proofing Copy</h1>\n'
      '<p>This edition is not finished. It is circulated for reading and correction '
      'only — please do not pass it on.</p>\n'
      '<p>If something reads wrongly — a misprint, a word that sits oddly, a chapter '
      'that begins in the wrong place, a heading out of order — note the chapter and '
      'the sentence around it and send it to '
      f'<a href="mailto:{contact}">{contact}</a>. Small things are worth reporting; '
      'they are exactly what this copy is for.</p>\n'
      '<p>Two things are deliberate, and are not errors. The seventeenth-century '
      'spelling stands as the author wrote it. And where the original page was damaged '
      'past reading, a word that could not be established is marked '
      '<i>[&#8230;]</i>.</p>\n'
      f'<p class="stamp">{E(title)} &#183; {E(author)}<br/>'
      f'SchriftOhr Edition &#183; build {E(build)}</p>\n'
      '</div>\n</section></body></html>\n')
