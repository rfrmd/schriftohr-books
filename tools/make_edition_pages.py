#!/usr/bin/env python3
"""Write one page per edition on schriftohr.com, from shelf.json, the publisher's log and the book file itself
(John, 2026-11-04): the card is the way in, the page says what the book is and how it was made, and offers
Read now (schriftohr.app, no account) and Download.

    make_edition_pages.py

Every word about a book comes from the book or the shelf, so a page cannot drift from what it describes.
Writes schriftohr-web/editions/<id>.html; run it again whenever a book changes. Reads the footer version from
schriftohr-web/index.html. A book's faithful copy (listed_with) gets its page too, and each links to the other.
"""
import html
import json
import pathlib
import re
import zipfile
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = ROOT.parent / 'schriftohr-web'
OUT = SITE / 'editions'
PREFIX = 'https://rfrmd.github.io/schriftohr-books/'
READ = 'https://schriftohr.app/#/edition/'
E = html.escape

# Pages of a book that are not its contents.
NOT_CONTENTS = re.compile(
    r'^(cover|title|title page|about this (copy|edition)|this book is made|how these books are made|'
    r'sources( and acknowledgements)?|words brought forward|why we make|frontispiece|illustrations|'
    r'closing|back cover|notes?$|contents$|the contents$)', re.I)


def read_book(path):
    z = zipfile.ZipFile(path)
    names = z.namelist()

    def page(tail):
        for n in names:
            if n.endswith(tail):
                return z.read(n).decode('utf-8')
        return ''

    return z, names, page


def contents(page, title):
    nav = page('nav.xhtml')
    m = re.search(r'<nav[^>]*epub:type="toc"[^>]*>(.*?)</nav>', nav, re.S) or re.search(r'<nav[^>]*>(.*?)</nav>', nav, re.S)
    items = []
    for t in re.findall(r'<a [^>]*>(.*?)</a>', m.group(1) if m else '', re.S):
        t = html.unescape(re.sub('<[^>]+>', '', t)).strip()
        if not t or NOT_CONTENTS.match(t) or t.split(':')[0].strip().lower() == title.split(':')[0].strip().lower():
            continue
        items.append(t)
    # Chapter numbers alone tell a reader nothing but the count.
    bare = [i for i in items if re.fullmatch(r'Chapter \d+', i)]
    if items and len(bare) == len(items):
        return f'{len(items)} chapters.', []
    return '', items


def paragraphs(xhtml):
    body = re.sub(r'<head>.*?</head>', '', xhtml, flags=re.S)
    out = []
    for p in re.findall(r'<p\b[^>]*>(.*?)</p>', body, re.S):
        p = re.sub(r'</?(?:a|span|sup|img)\b[^>]*>', '', p).strip()
        if re.sub('<[^>]+>', '', p).strip():
            out.append(p)
    return out


def when(d):
    y, m, day = map(int, d.split('-'))
    return date(y, m, day).strftime('%-d %B %Y')


def footer_version():
    m = re.search(r'schriftohr\.com v([\d.]+)', (SITE / 'index.html').read_text(encoding='utf-8'))
    return m.group(1)


def css_query():
    m = re.search(r'so\.css\?v=([\d.]+)', (SITE / 'index.html').read_text(encoding='utf-8'))
    return m.group(1)


def page_for(b, partner, log, ver, cssv):
    z, names, page = read_book(ROOT / b['epub'][len(PREFIX):])
    title, author = E(b['title']), E(b['author'])
    url = f'https://schriftohr.com/editions/{b["id"]}.html'
    desc = b['blurb'].replace('Proofing copy: corrections welcome.', '').strip()
    count, items = contents(page, b['title'])
    about = paragraphs(page('edition-note.xhtml'))
    sources = [p for p in paragraphs(page('sources.xhtml')) if 'Soli Deo' not in p]
    made = ''.join(f'    <p>{p}</p>\n' for p in about)
    src = ''.join(f'    <p>{p}</p>\n' for p in sources)
    other = ''
    if partner:
        family = b.get('listed_with') is None
        word = 'Original edition' if family else 'Family Edition'
        other = f'      <a class="ghost" href="{partner["id"]}.html">{word}</a>\n'
    toc = ''
    if items:
        lis = ''.join(f'      <li>{E(i)}</li>\n' for i in items)
        if len(items) > 24:
            toc = f'  <section>\n    <details>\n    <summary><h2>Contents</h2></summary>\n    <ul class="toc">\n{lis}    </ul>\n    </details>\n  </section>\n'
        else:
            toc = f'  <section>\n    <h2>Contents</h2>\n    <ul class="toc">\n{lis}    </ul>\n  </section>\n'
    elif count:
        toc = f'  <section>\n    <h2>Contents</h2>\n    <p>{count}</p>\n  </section>\n'
    changes = ''
    if log:
        rows = ''.join(f'    <p><strong>{when(e["date"])}.</strong> {E(e["text"])}</p>\n' for e in log)
        changes = f'  <section>\n    <h2>What has changed</h2>\n{rows}  </section>\n'
    source_block = f'  <section>\n    <h2>Sources</h2>\n{src}  </section>\n' if src else ''
    made_block = f'  <section>\n    <h2>How this edition was made</h2>\n{made}  </section>\n' if made else ''
    short = E(desc[:155].rsplit(' ', 1)[0] + '…' if len(desc) > 155 else desc)
    stamp = f'Build {E(b["build"])}.' if b.get('build') else ''
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} by {author}: free to read and keep</title>
<meta name="description" content="{short}">
<link rel="canonical" href="{url}">
<link rel="icon" href="../favicon.png">
<link rel="apple-touch-icon" href="../apple-touch-icon.png">
<meta property="og:title" content="{title} by {author}">
<meta property="og:description" content="{short}">
<meta property="og:image" content="{E(b["cover"])}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image">
<link rel="stylesheet" href="../so.css?v={cssv}">
</head>
<body>
<header class="bar page" id="bar">
  <div class="wrap">
    <a class="brand" href="../"><img src="../logo-icon.png" alt="" width="34" height="34">SchriftOhr</a>
    <nav>
      <a href="../guide.html">Guide</a>
      <a href="../books.html#editions">Books</a>
      <a href="../support.html" class="opt">Support</a>
    </nav>
  </div>
</header>

<main class="narrow doc edition">
  <div class="ed-top">
    <img class="ed-cover" src="{E(b["cover"])}" alt="Cover of {title}" width="1074" height="1600">
    <div class="ed-head">
      <h1>{title}</h1>
      <p class="ed-by">{author}</p>
      <p class="ed-free">Free. No account, no tracking, yours to keep.</p>
      <div class="ed-go">
      <a class="go-read" href="{READ}{b["id"]}">Read now</a>
      <a class="ghost" href="{E(b["epub"])}" rel="noopener">Download EPUB</a>
{other}      </div>
    </div>
  </div>
  <p class="ed-desc">{E(desc)}</p>
{toc}{made_block}{source_block}{changes}  <p class="ed-stamp"><a href="../books.html#editions">All the editions</a>. {stamp}</p>
</main>

<footer class="foot">
  <div class="wrap">
    <nav>
      <a href="../">schriftohr.com</a>
      <a href="https://apps.apple.com/app/id6789832705" rel="noopener">App Store</a>
      <a href="../guide.html">How to use</a>
      <a href="../books.html">Where to find books</a>
      <a href="../support.html">Support</a>
      <a href="../privacy-policy.html">Privacy</a>
      <a href="../age-suitability.html">Age suitability</a>
    </nav>
    <p><a href="https://rfrmdwordlabs.com">© 2026 RFRMD Word Labs LLC</a> <span class="ver">· schriftohr.com v{ver}</span></p>
  </div>
</footer>

<script src="../so.js?v=2.0.5"></script>
</body>
</html>
'''


def main():
    books = json.loads((ROOT / 'shelf.json').read_text(encoding='utf-8'))['books']
    logs = json.loads((ROOT / 'editions-log.json').read_text(encoding='utf-8'))['books']
    by = {b['id']: b for b in books}
    orig = {b['listed_with']: b for b in books if b.get('listed_with')}
    ver, cssv = footer_version(), css_query()
    OUT.mkdir(exist_ok=True)
    for b in books:
        partner = by.get(b.get('listed_with')) or orig.get(b['id'])
        (OUT / f'{b["id"]}.html').write_text(page_for(b, partner, logs.get(b['id']), ver, cssv), encoding='utf-8')
    print(f'{len(books)} pages in {OUT}')


if __name__ == '__main__':
    main()
