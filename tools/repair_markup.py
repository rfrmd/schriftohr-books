#!/usr/bin/env python3
"""Repair markup a reader cannot parse, in a finished EPUB.

Found by John, 2026-08-23, reading Charnock: four pages opened to an error
box instead of the text. The verifier had said "structure clean" because it
stripped tags with a regex and never asked a parser. It asks now, and the
same question found two of the eleven published editions broken as well.

Two faults, both from the builders and both since fixed there:

  · a page marker written `<a id="Page_9" title="9">` with no closing tag,
    left standing when the surrounding links were unwrapped;
  · a stanza, which arrives as nested <div>s, wrapped in a <p> — giving
    `<p><div><div><div>text</p>`.

Repairing the finished file rather than rebuilding is deliberate: these were
set from several different sources, and re-deriving their text to fix their
wrapper would risk the text.

    python3 repair_markup.py <epub> [<epub> …]
"""
import re, sys, os, zipfile, shutil
import xml.etree.ElementTree as ET

VERSE_CSS = """
/* A stanza quoted in the text. */
p.verse{text-indent:0;margin:.15em 0 .15em 1.6em;font-size:.97em}
p.verse:first-of-type{margin-top:1em}
"""

def repair_doc(s):
    fixed = s
    # an anchor that nothing closes, and any orphan close
    if len(re.findall(r'<a\b', fixed)) != len(re.findall(r'</a>', fixed)):
        fixed = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', fixed, flags=re.S)
        fixed = re.sub(r'</?a\b[^>]*/?>', '', fixed)
    # a stanza's nested divs, wrapped in a paragraph
    def _verse(m):
        return '<p class="verse">' + m.group(1) + '</p>'
    fixed = re.sub(r'<p><div class="poetry"[^>]*>\s*(?:<div class="verse"[^>]*>\s*)?'
                   r'(?:<div class="line[^"]*"[^>]*>\s*)?(.*?)</p>', _verse, fixed, flags=re.S)
    # the rest of that stanza is already separate paragraphs; mark them too,
    # as far as the closing quotation mark that ends it
    out, in_verse = [], False
    for part in re.split(r'(<p[^>]*>.*?</p>)', fixed, flags=re.S):
        if part.startswith('<p'):
            if 'class="verse"' in part:
                in_verse = True
            elif in_verse:
                if re.search(r'[”"]\s*</p>$', part):
                    in_verse = False
                part = part.replace('<p>', '<p class="verse">', 1)
        out.append(part)
    return ''.join(out)

def repair(path):
    z = zipfile.ZipFile(path); names = z.namelist()
    out, touched = {}, []
    for n in names:
        if not n.endswith('.xhtml'): continue
        s = z.read(n).decode('utf-8')
        try:
            ET.fromstring(s.encode('utf-8')); continue     # already fine
        except ET.ParseError:
            pass
        f = repair_doc(s)
        try:
            ET.fromstring(f.encode('utf-8'))
        except ET.ParseError as e:
            print(f'  ✗ {n.split("/")[-1]} still will not parse: {e}')
            continue
        out[n] = f.encode('utf-8'); touched.append(n.split('/')[-1])
    if not touched:
        print(f'  {os.path.basename(path)}: nothing to repair'); return False
    css = next((n for n in names if n.endswith('.css')), None)
    if css and b'p.verse{' not in z.read(css):
        out[css] = z.read(css) + VERSE_CSS.encode('utf-8')
    tmp = path + '.new'
    with zipfile.ZipFile(tmp, 'w') as w:
        w.writestr(zipfile.ZipInfo('mimetype'), 'application/epub+zip',
                   compress_type=zipfile.ZIP_STORED)
        for n in names:
            if n == 'mimetype': continue
            w.writestr(n, out.get(n, z.read(n)), compress_type=zipfile.ZIP_DEFLATED)
    z.close(); shutil.move(tmp, path)
    print(f'  {os.path.basename(path)}: repaired {len(touched)} pages — {", ".join(touched)}')
    return True

if __name__ == '__main__':
    n = sum(bool(repair(p)) for p in sys.argv[1:])
    print(f'{n} edition(s) repaired')
