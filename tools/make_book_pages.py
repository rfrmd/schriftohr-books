#!/usr/bin/env python3
"""Write the edition cards on both websites from shelf.json.

The shelf is the one place a book's title, blurb, cover and download live. The
two sites had their own hand-written copies of all of it, so publishing a book
meant editing three files and remembering to — which is how schriftohr.com came
to be showing eleven editions on the day the twelfth went up.

    make_book_pages.py [--check]

Each site keeps its own card shape and its own words around them; only the run
of cards is generated. Everything outside is left exactly as it was.
"""

import argparse
import html
import json
import pathlib
import re
import sys

SHELF = pathlib.Path(__file__).resolve().parent.parent / 'shelf.json'

WORDS = ('no', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight',
         'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen',
         'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen', 'Twenty',
         'Twenty-one', 'Twenty-two', 'Twenty-three', 'Twenty-four',
         'Twenty-five', 'Twenty-six', 'Twenty-seven', 'Twenty-eight',
         'Twenty-nine', 'Thirty')


def spell(n):
    """"Fourteen so far" reads better than "14 so far" in running prose, and
    the number has to change with the shelf either way."""
    return WORDS[n] if n < len(WORDS) else str(n)


SITES = [
    # (path, css class, how the title line reads, how the description reads)
    (pathlib.Path.home() / 'Developer/rfrmdwordlabs-web/books.html', 'card bk',
     lambda b: html.escape(b['title']),
     lambda b: f"{html.escape(b['author'])} — {html.escape(b['blurb'])}"),
    (pathlib.Path.home() / 'Developer/schriftohr-web/books.html', 'src bk',
     lambda b: f"{html.escape(b['title'])} — {html.escape(b['author'])}",
     lambda b: html.escape(b['blurb'])),
]


def cards(books, klass, title_of, desc_of, indent='    '):
    out = []
    for b in books:
        # ⚠️ A proofing copy says so on the page as well as on its cover. A
        # reader downloading from the site never sees the shelf entry.
        proof = 'proofing copy' in b.get('blurb', '').lower()
        tag = 'proofing copy — free EPUB' if proof else 'free EPUB download'
        out.append(
            f'{indent}<a class="{klass}" href="{html.escape(b["epub"])}" rel="noopener">\n'
            f'{indent}  <img class="cover" src="{html.escape(b["cover"])}" alt="" '
            f'loading="lazy" width="1074" height="1600">\n'
            f'{indent}  <span class="t">\n'
            f'{indent}    <b>{title_of(b)} <span class="host">{tag}</span></b>\n'
            f'{indent}    <span class="d">{desc_of(b)}</span>\n'
            f'{indent}  </span>\n'
            f'{indent}</a>')
    return '\n'.join(out)


def shelf_strip(books, base_indent='      '):
    """The row of cover thumbnails on a front page."""
    return '\n'.join(
        f'{base_indent}<img src="{html.escape(b["cover"])}" '
        f'alt="{html.escape(b["title"])}" loading="lazy" width="1074" height="1600">'
        for b in books)


def replace_strip(text, block):
    """Swap the images inside <a class="shelf"> and leave the anchor alone."""
    m = re.search(r'(<a class="shelf"[^>]*>)(.*?)(</a>)', text, re.S)
    if not m:
        return None, 0
    had = len(re.findall(r'<img', m.group(2)))
    return text[:m.end(1)] + '\n' + block + '\n    ' + text[m.start(3):], had


def replace_count(text, n):
    """The prose count beside the strip — "Eleven so far"."""
    pat = re.compile(r'<strong>([A-Za-z-]+) so far</strong>')
    m = pat.search(text)
    if not m:
        return text, None
    return pat.sub(f'<strong>{spell(n)} so far</strong>', text, count=1), m.group(1)


def replace_block(text, klass, block):
    """Swap the run of cards, leaving every word around them alone."""
    pattern = re.escape(f'<a class="{klass}"')
    first = re.search(pattern, text)
    if not first:
        return None, 0
    # the run ends at the last such card's </a>, before the section closes
    end_of_section = text.find('</section>', first.start())
    if end_of_section < 0:
        end_of_section = len(text)
    last_close = text.rfind('</a>', first.start(), end_of_section)
    if last_close < 0:
        return None, 0
    had = len(re.findall(pattern, text[first.start():end_of_section]))
    return text[:first.start()] + block.lstrip() + text[last_close + 4:], had



# ⚠️ The two sites are hand-copied to a hosting server, so every book we publish
# used to mean John copying three files. This script lets the page refresh its
# own list from shelf.json on GitHub Pages, which serves it with
# access-control-allow-origin: *, so a page on another domain may read it.
#
# It is an ENHANCEMENT, not a replacement. The generated cards stay in the HTML:
# the page is correct the moment it is uploaded, works with JavaScript off, and
# stays readable to a crawler. The script only steps in when the shelf has moved
# on since the upload — which means John copies files when the DESIGN changes,
# not when a book is added.
#
# ⚠️ Nothing from the JSON is written as HTML. Every value goes in through
# textContent or setAttribute, so a stray angle bracket in a blurb cannot become
# markup.
LIVE_JS = """<script>
/* Refresh the shelf from rfrmd.github.io. Static cards above are the fallback. */
(function () {
  var SRC = 'https://rfrmd.github.io/schriftohr-books/shelf.json';
  var KLASS = %(klass)r, TITLE_MODE = %(mode)r;
  function card(b) {
    var a = document.createElement('a');
    a.className = KLASS; a.href = b.epub; a.rel = 'noopener';
    var img = document.createElement('img');
    img.className = 'cover'; img.src = b.cover; img.alt = '';
    img.loading = 'lazy'; img.width = 1074; img.height = 1600;
    var t = document.createElement('span'); t.className = 't';
    var bold = document.createElement('b');
    bold.appendChild(document.createTextNode(
      TITLE_MODE === 'both' ? b.title + ' \u2014 ' + b.author : b.title));
    var host = document.createElement('span');
    host.className = 'host';
    host.textContent = /proofing copy/i.test(b.blurb || '')
      ? 'proofing copy \u2014 free EPUB' : 'free EPUB download';
    bold.appendChild(document.createTextNode(' ')); bold.appendChild(host);
    var d = document.createElement('span'); d.className = 'd';
    d.textContent = TITLE_MODE === 'both' ? b.blurb : b.author + ' \u2014 ' + b.blurb;
    t.appendChild(bold); t.appendChild(d);
    a.appendChild(img); a.appendChild(t);
    return a;
  }
  fetch(SRC).then(function (r) { return r.ok ? r.json() : null; }).then(function (j) {
    if (!j || !j.books || !j.books.length) return;
    var have = document.querySelectorAll('a.' + KLASS.split(' ').join('.'));
    if (!have.length) return;
    var same = have.length === j.books.length;
    if (same) for (var i = 0; i < have.length; i++)
      if (have[i].getAttribute('href') !== j.books[i].epub) { same = false; break; }
    if (same) return;                       /* the page is already current */
    var parent = have[0].parentNode, anchor = have[0];
    for (var k = have.length - 1; k >= 1; k--) have[k].parentNode.removeChild(have[k]);
    var frag = document.createDocumentFragment();
    j.books.forEach(function (b) { frag.appendChild(card(b)); });
    parent.replaceChild(frag, anchor);
    var strip = document.querySelector('a.shelf');
    if (strip) {
      while (strip.firstChild) strip.removeChild(strip.firstChild);
      j.books.forEach(function (b) {
        var i = document.createElement('img');
        i.src = b.cover; i.alt = b.title; i.loading = 'lazy';
        i.width = 1074; i.height = 1600; strip.appendChild(i);
      });
    }
    var W = ['no','One','Two','Three','Four','Five','Six','Seven','Eight','Nine','Ten',
             'Eleven','Twelve','Thirteen','Fourteen','Fifteen','Sixteen','Seventeen',
             'Eighteen','Nineteen','Twenty','Twenty-one','Twenty-two','Twenty-three',
             'Twenty-four','Twenty-five','Twenty-six','Twenty-seven','Twenty-eight',
             'Twenty-nine','Thirty'];
    var n = j.books.length;
    Array.prototype.forEach.call(document.querySelectorAll('strong'), function (s) {
      if (/ so far$/.test(s.textContent))
        s.textContent = (W[n] || String(n)) + ' so far';
    });
  }).catch(function () { /* leave the page as uploaded */ });
})();
</script>"""


def strip_live(text):
    return re.sub(r'\\n?<script>\\n/\\* Refresh the shelf.*?</script>', '', text, flags=re.S)


def inject_live(text, klass, mode):
    """Put the refresher just before </body>, replacing any earlier copy."""
    js = LIVE_JS % {'klass': klass, 'mode': mode}
    text = re.sub(r'<script>\n/\* Refresh the shelf.*?</script>', '', text, flags=re.S)
    if '</body>' in text:
        return text.replace('</body>', js + '\n</body>', 1)
    return text + js + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true',
                    help='report what would change; write nothing')
    ap.add_argument('--live', action='store_true',
                    help='embed the script that refreshes the shelf from GitHub '
                         '(⚠️ untested in a browser as of 2026-08-31)')
    args = ap.parse_args()

    books = json.loads(SHELF.read_text())['books']
    print(f'{len(books)} editions on the shelf')

    stale = 0

    # ⚠️ The front page carries the shelf too — a strip of covers and a count
    # in the prose. It said "Eleven so far" on the day the fourteenth went up,
    # which is the same drift the card lists had, in a place that is harder to
    # notice (John, 2026-08-29).
    front = pathlib.Path.home() / 'Developer/rfrmdwordlabs-web/index.html'
    if front.exists():
        text = strip_live(front.read_text(encoding='utf-8'))
        new, had = replace_strip(text, shelf_strip(books))
        if new is None:
            print(f'  !! no shelf strip in {front.name}')
        else:
            new, was = replace_count(new, len(books))
            same = new == text
            if args.live:
                new = inject_live(new, 'card bk', 'title')
            same = new == text
            print(f'  {front.parent.name}/{front.name}: strip {had} -> {len(books)} '
                  f'cover(s); count {was!r} -> {spell(len(books))!r}'
                  f'{"  (already current)" if same else ""}')
            if not same:
                stale += 1
                if not args.check:
                    front.write_text(new, encoding='utf-8')

    for path, klass, title_of, desc_of in SITES:
        if not path.exists():
            print(f'  !! {path} is not here'); continue
        text = strip_live(path.read_text(encoding='utf-8'))
        block = cards(books, klass, title_of, desc_of)
        new, had = replace_block(text, klass, block)
        if new is None:
            print(f'  !! no "{klass}" cards found in {path.name} — not touching it')
            continue
        if args.live:
            new = inject_live(new, klass, 'both' if 'src' in klass else 'title')
        same = new == text
        print(f'  {path.parent.name}/{path.name}: {had} card(s) -> {len(books)}'
              f'{"  (already current)" if same else ""}')
        if not same:
            stale += 1
            if not args.check:
                path.write_text(new, encoding='utf-8')
    if args.check and stale:
        print(f'{stale} page(s) out of date')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
