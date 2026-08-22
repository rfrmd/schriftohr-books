#!/usr/bin/env python3
"""Build a SchriftOhr Edition from a Project Gutenberg epub.

The editorial acts, in order: read the source in its own spine order,
cut it into real chapters, throw away the apparatus of the scan (page
numbers mid-sentence, Gutenberg's boilerplate and logo), reflow the
hard-wrapped lines, and set the result in the house style.

Every image in the source is ACCOUNTED FOR — kept and reported, or
dropped and reported. Nothing disappears silently.
"""
import re, os, html, glob, uuid, shutil, zipfile, subprocess, unicodedata
from PIL import Image

def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s.lower())).strip('-')

def flatten(x):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', x))).strip()

def spine_docs(src):
    """Reading order as the source itself declares it — never a filename sort."""
    opf = glob.glob(f'{src}/**/content.opf', recursive=True)[0]
    base = os.path.dirname(opf)
    s = open(opf, encoding='utf-8').read()
    man = {i: h for i, h in re.findall(r'<item id="([^"]+)"[^>]*href="([^"]+)"', s)}
    man.update({i: h for h, i in re.findall(r'<item[^>]*href="([^"]+)"[^>]*id="([^"]+)"', s)})
    order = [man[i] for i in re.findall(r'idref="([^"]+)"', s) if i in man]
    if not order:                                     # some PG epubs omit the spine
        docs = glob.glob(f'{base}/*-h-*.htm.xhtml')
        docs.sort(key=lambda p: int(re.search(r'-h-(\d+)\.htm', p).group(1)))
        return [os.path.relpath(d, base) for d in docs], base
    return order, base

CHAPTER_HEAD = re.compile(r'^(?:CHAPTER\s+)?([IVXL]+|\d+)\.?\s*(.*)$', re.I)

def body_of(doc):
    m = re.search(r'<body[^>]*>(.*)</body>', doc, re.S | re.I)
    return m.group(1) if m else doc

def clean(b, imgmap, kept):
    b = re.sub(r'<div class="pb"[^>]*>.*?</div>', '', b, flags=re.S)
    b = re.sub(r'\[\d+\]', '', b)
    b = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', b, flags=re.S)
    b = re.sub(r'</?span[^>]*>', '', b)
    out = []
    for m in re.finditer(r'<(p|blockquote|div|figure|h[3-6])\b[^>]*>(.*?)</\1>', b, flags=re.S):
        tag, inner = m.group(1), re.sub(r'\s+', ' ', m.group(2)).strip()
        img = re.search(r'<img[^>]*src="([^"]+)"', inner)
        if img:
            name = os.path.basename(img.group(1))
            if name in imgmap:                        # a plate the book owns
                kept.add(name)
                out.append(f'<figure><img alt="" src="../images/{imgmap[name]}" /></figure>')
            continue
        if not flatten(inner):
            continue
        out.append(f'<p>{inner}</p>' if tag in ('p', 'div') else f'<{tag}>{inner}</{tag}>')
    return '\n'.join(out)

def page(title, et, cls, inner, bt='bodymatter'):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n'
            f'<head><title>{html.escape(title)}</title><meta charset="utf-8"/>'
            '<link rel="stylesheet" type="text/css" href="../css/style.css"/></head>\n'
            f'<body epub:type="{bt}"><section epub:type="{et}" class="{cls}">\n{inner}\n'
            '</section></body></html>\n')

def build(src, out, meta, cover, tpl, plates=()):
    """plates: source image basenames to carry into the edition as its own art."""
    shutil.rmtree(out, ignore_errors=True)
    for d in ('META-INF', 'OEBPS/text', 'OEBPS/css', 'OEBPS/images'):
        os.makedirs(f'{out}/{d}')
    docs, base = spine_docs(src)

    all_imgs = {os.path.basename(p) for p in
                glob.glob(f'{base}/*.jpg') + glob.glob(f'{base}/*.jpeg') + glob.glob(f'{base}/*.png')}
    imgmap = {}
    for name in plates:
        match = next((i for i in all_imgs if i.endswith(name)), None)
        if match:
            dest = slug(name.rsplit('.', 1)[0]) + '.jpg'
            Image.open(f'{base}/{match}').convert('RGB').save(
                f'{out}/OEBPS/images/{dest}', 'JPEG', quality=88, optimize=True)
            imgmap[match] = dest

    kept, chapters = set(), []
    for d in docs:
        p = os.path.join(base, d.split('#')[0])
        if not os.path.exists(p):
            continue
        raw = open(p, encoding='utf-8', errors='ignore').read()
        if 'PROJECT GUTENBERG LICENSE' in raw.upper():
            continue
        b = body_of(raw)
        for m in re.finditer(r'<h[12][^>]*>(.*?)</h[12]>', b, re.S | re.I):
            head = flatten(m.group(1))
            cm = CHAPTER_HEAD.match(head)
            if not cm or 'gutenberg' in head.lower():
                continue
            rest = b[m.end():]
            nxt = re.search(r'<h[12][^>]*>', rest)
            body = rest[:nxt.start()] if nxt else rest
            num, name = cm.group(1).upper(), cm.group(2).strip()
            title = f'Chapter {num}' + (f': {name}' if name else '')
            fn = f'C{len(chapters)+1:02d}' + (f'-{slug(name)}' if name else '') + '.xhtml'
            open(f'{out}/OEBPS/text/{fn}', 'w', encoding='utf-8').write(
                page(title, 'chapter', 'chapter',
                     f'<h2>{html.escape(title)}</h2>\n{clean(body, imgmap, kept)}'))
            chapters.append((fn, title))

    report = {'source_images': sorted(all_imgs), 'carried': sorted(imgmap.values()),
              'used_in_text': sorted(kept), 'chapters': len(chapters)}
    return chapters, report
