#!/usr/bin/env python3
"""Build the SchriftOhr Edition of Charnock's Existence and Attributes of God.

Two volumes in one, fourteen Discourses, some six hundred thousand words.
The source is Project Gutenberg 53527, proofread by Distributed
Proofreaders from the nineteenth-century edition — already in modern
spelling, and, unlike the keyed EEBO texts, carrying its Greek and Hebrew.

A Discourse can run across three of the source's files; the chapters here
follow Charnock's divisions, not the file boundaries. The footnotes, which
the source keeps in one table at the back, are set at the foot of the
chapter that calls them.
"""
import re, os, html, glob, uuid, shutil, subprocess, sys
sys.path.insert(0, os.path.expanduser('~/Developer/schriftohr-books/tools'))
from edition_parts import cover_xhtml, proofing_xhtml, PROOFING_CSS, SCRIPT_CSS
from greek_sound import gloss
from PIL import Image

W   = os.path.expanduser('~/Desktop/Reformed-Shelf-Working/05-charnock-attributes')
SRC = '/tmp/chk/OEBPS'
TPL = '/private/tmp/claude-501/-Users-johnwest-Developer-schriftohr/6c0e5e0e-5ab4-4c3b-a6f4-cca64a136103/scratchpad/tpl'
OUT = f'{W}/output/existence-and-attributes'
T   = 'The Existence and Attributes of God'
AUTHOR = 'Stephen Charnock'

opf = open(f'{SRC}/content.opf', encoding='utf-8').read()
# the source writes href before id; read either order
man = dict(re.findall(r'<item\s+[^>]*id="([^"]+)"[^>]*href="([^"]+)"', opf))
man.update({i: h for h, i in re.findall(r'<item\s+href="([^"]+)"[^>]*id="([^"]+)"', opf)})
spine = [man[r] for r in re.findall(r'idref="([^"]+)"', opf) if r in man]

def read(p):  return open(f'{SRC}/{p}', encoding='utf-8', errors='ignore').read()
def body_of(d):
    m = re.search(r'<body[^>]*>(.*)</body>', d, re.S)
    return m.group(1) if m else d
def flat(x): return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', x))).strip()

# --- the footnote table at the back ---------------------------------------
NOTES = {}
for f in spine:
    if not f.endswith('-31.htm.xhtml'): continue
    for m in re.finditer(r'<tr id="fn_(\d+)">.*?class="ft_text">(.*?)</td>', read(f), re.S):
        NOTES[int(m.group(1))] = re.sub(r'\s+', ' ', m.group(2)).strip()
print(f'  {len(NOTES)} footnotes read from the back of the source')

# --- clean one run of source html into our own paragraphs -----------------
GK0, GK1 = '\ue000', '\ue001'
HB0, HB1 = '\ue002', '\ue003'

def _greek_span(m):
    """The word as Charnock set it, and how it sounds — the house manner."""
    word = m.group(1)
    g = gloss(word)
    return (f'<span xml:lang="grc" lang="grc" class="gk">{word}</span>'
            + (f' <span class="ph">({g})</span>' if g else ''))

def clean(b, seen):
    b = re.sub(r'<div class="section"[^>]*>|</div>', '', b)
    b = re.sub(r'<h[12][^>]*>.*?</h[12]>', '', b, flags=re.S)     # our own heads replace them
    b = re.sub(r'<a class="anchor pginternal" href="[^"]*#pg_[^"]*"[^>]*></a>', '', b)
    b = re.sub(r'<a[^>]*id="pg_[^"]*"[^>]*></a>', '', b)
    # ⚠️ Mark the note references, unwrap every anchor, and only THEN write the
    # real <a>. Writing it first and excluding it from the unwrap looked safe
    # and was not: the source carries anchors with no closing tag, and the
    # unwrap's non-greedy (.*?)</a> reached past them to eat the note
    # reference's own </a>, leaving four pages that a reader opens to an error.
    def _ref(m):
        n = int(m.group(1)); seen.append(n)
        return f'\ue008{n}\ue009'
    b = re.sub(r'<a[^>]*href="[^"]*-31\.htm[^"]*#fn_(\d+)"[^>]*>[^<]*</a>', _ref, b)
    b = re.sub(r'<a\b[^>]*>(.*?)</a>', r'\1', b, flags=re.S)
    b = re.sub(r'</?a\b[^>]*/?>', '', b)          # anything unclosed, or an orphan close
    # Mark the two scripts BEFORE the general span strip — a span made here
    # and stripped two lines later leaves the Greek unglossed and unstyled.
    b = re.sub(r'<span lang="he">([^<]+)</span>', lambda m: HB0 + m.group(1) + HB1, b)
    b = re.sub(r'<span lang="grc">([^<]+)</span>', lambda m: GK0 + m.group(1) + GK1, b)
    b = re.sub(r'<span class="txt_sc">([^<]*)</span>', r'\1', b)
    b = re.sub(r'</?span[^>]*>', '', b)
    # The source sometimes marks only part of a word — "ἀπ᾽ α<span>ἰῶ</span>νος".
    # Pull the loose letters into the marked run before anything else, or the
    # sweep below wraps a run inside a run.
    b = re.sub(r'([ἀ-῿Ἀ-ῼ᾽\u02bc\u2019]*)' + GK0 + r'([^' + GK1 + r']*)' + GK1
               + r'([ἀ-῿Ἀ-ῼ᾽\u02bc\u2019]*)',
               lambda m: GK0 + m.group(1) + m.group(2) + m.group(3) + GK1, b)
    # anything Greek the source left unmarked, in the stretches between
    BARE = re.compile(r'([ἀ-῿Ἀ-ῼ]{2,}(?:[ \u00b7][ἀ-῿Ἀ-ῼ᾽\u02bc\u2019]+)*)')
    parts = re.split('(' + GK0 + r'[^' + GK1 + r']*' + GK1 + ')', b)
    b = ''.join(x if x.startswith(GK0) else BARE.sub(lambda m: GK0+m.group(1)+GK1, x)
                for x in parts)
    b = re.sub(GK0 + r'([^' + GK1 + r']*)' + GK1, _greek_span, b)
    b = re.sub(HB0 + r'([^' + HB1 + r']*)' + HB1,
               lambda m: f'<span xml:lang="hbo" lang="hbo" dir="rtl" class="hb">{m.group(1)}</span>', b)
    b = re.sub(r'<(em|i|cite)[^>]*>', '<i>', b); b = re.sub(r'</(em|i|cite)>', '</i>', b)
    b = re.sub('\ue008(\\d+)\ue009',
               lambda m: (f'<a epub:type="noteref" href="#fn{m.group(1)}" '
                          f'id="fr{m.group(1)}" class="nref"><sup>{m.group(1)}</sup></a>'), b)
    out = []
    for m in re.finditer(r'<(p|blockquote|h[3-6])\b[^>]*>(.*?)</\1>', b, flags=re.S):
        tag, inner = m.group(1), re.sub(r'\s+', ' ', m.group(2)).strip()
        if not flat(inner): continue
        out.append(f'<p>{inner}</p>' if tag == 'p' else f'<{tag}>{inner}</{tag}>')
    return '\n'.join(out)

# --- cut the source into Charnock's own divisions -------------------------
DROP = ('-28.htm', '-29.htm', '-30.htm', '-31.htm', '-32.htm', '-33.htm',
        '-14.htm', 'wrap0000')     # index, scripture table, notes, licence, vol-II contents
chapters, front = [], []
for f in spine:
    if any(d in f for d in DROP): continue
    doc = read(f)
    if f.endswith('-0.htm.xhtml'):
        b = body_of(doc)
        i = b.find('LIFE AND CHARACTER OF CHARNOCK')
        j = b.find('TO THE READER.')
        front.append(('The Life and Character of Charnock',
                      'By William Symington, D.D.', b[b.rfind('<h2', 0, i):j]))
        front.append(('To the Reader', '', b[b.rfind('<h2', 0, j):]))
        continue
    head = re.search(r'<h2[^>]*>(.*?)</h2>', doc, re.S)
    title = flat(head.group(1)) if head else ''
    m = re.match(r'DISCOURSE\s+([IVXL]+)\.?\s*(.*)$', title, re.I)
    if m:
        name = m.group(2).strip().rstrip('.')
        name = name[0] + name[1:].lower() if name else ''
        name = re.sub(r'\bgod\b', 'God', name, flags=re.I)
        name = re.sub(r"\bgod’s\b", 'God’s', name, flags=re.I)
        chapters.append({'num': m.group(1).upper(), 'title': name, 'docs': [f]})
    elif chapters:
        chapters[-1]['docs'].append(f)                     # a Discourse continued
print(f'  {len(chapters)} Discourses, {sum(len(c["docs"]) for c in chapters)} source files')

# --- set it ---------------------------------------------------------------
shutil.rmtree(OUT, ignore_errors=True)
for d in ('META-INF','OEBPS/text','OEBPS/css','OEBPS/images'): os.makedirs(f'{OUT}/{d}')
shutil.copy(f'{TPL}/OEBPS/css/style.css', f'{OUT}/OEBPS/css/style.css')
open(f'{OUT}/OEBPS/css/style.css','a').write(
 '\n/* Charnock quotes his fathers and schoolmen in the margin; set at the foot. */\n'
 '.nref{text-decoration:none;font-size:.8em;vertical-align:super;line-height:0}\n'
 '.notes{font-size:.9em;color:#555;margin-top:2.4em}\n'
 '.notes hr{border:0;border-top:1px solid #ccc;width:35%;margin:0 0 .9em}\n'
 '.fn p{text-indent:0;margin:.35em 0}\n.fn a{text-decoration:none;color:#777}\n'
 'blockquote{margin:1em 1.6em;font-size:.97em}\n' + PROOFING_CSS + SCRIPT_CSS)
for m_ in ('publisher-mark.png','publisher-mark-dark.png'):
    shutil.copy(f'{TPL}/OEBPS/images/{m_}', f'{OUT}/OEBPS/images/{m_}')
Image.open(os.path.expanduser('~/Desktop/Charnock-ExistenceOfGod.png')).convert('RGB').save(
    f'{OUT}/OEBPS/images/cover.jpg','JPEG',quality=90,optimize=True,progressive=True)

def page(title, et, cls, inner, bt='bodymatter'):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
      'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n'
      f'<head><title>{html.escape(title)}</title><meta charset="utf-8"/>'
      '<link rel="stylesheet" type="text/css" href="../css/style.css"/></head>\n'
      f'<body epub:type="{bt}"><section epub:type="{et}" class="{cls}">\n{inner}\n</section></body></html>\n')

def notes_block(seen):
    seen = sorted(set(seen))
    if not seen: return ''
    return ('\n<section epub:type="endnotes" class="notes"><hr/>\n' + '\n'.join(
      f'<aside epub:type="footnote" id="fn{n}" class="fn">'
      f'<p><a href="#fr{n}">{n}.</a> {NOTES.get(n, "")}</p></aside>' for n in seen)
      + '\n</section>')

files=[]
_cw,_ch = Image.open(f'{OUT}/OEBPS/images/cover.jpg').size
open(f'{OUT}/OEBPS/text/cover.xhtml','w',encoding='utf-8').write(cover_xhtml(_cw,_ch))
files.append(('cover.xhtml','Cover'))
open(f'{OUT}/OEBPS/text/00-proofing.xhtml','w',encoding='utf-8').write(proofing_xhtml(T, AUTHOR))
files.append(('00-proofing.xhtml','Proofing Copy'))
open(f'{OUT}/OEBPS/text/00-title.xhtml','w',encoding='utf-8').write(page(T,'titlepage','titlepage',
 f'<h1>{html.escape(T)}</h1>\n<h2>Fourteen Discourses, in Two Volumes</h2>\n'
 f'<p><strong>{html.escape(AUTHOR)}</strong></p>\n<p>The SchriftOhr Edition</p>\n'
 '<p>Developed by RFRMDWordLabs, LLC</p>\n'
 '<p>For the benefit of readers, prayerfully, to the glory of God.</p>\n'
 '<p class="publisher-mark"><img src="../images/publisher-mark.png" alt="RFRMD Word Labs, LLC"/></p>','frontmatter'))
files.append(('00-title.xhtml',T))
open(f'{OUT}/OEBPS/text/01-edition-note.xhtml','w',encoding='utf-8').write(page(
 'About This Edition','preamble','preamble','<h2>About This Edition</h2>\n'
 f'<p>This is the SchriftOhr edition of <i>{html.escape(T)}</i>, prepared by RFRMDWordLabs, LLC. '
 'Charnock’s text is given as he wrote it — not modernised, abridged, or rewritten.</p>\n'
 '<p>The chapters are his own fourteen Discourses. Charnock quotes the Greek and Hebrew '
 'constantly; the Greek is followed by how it sounds, in brackets, so it can be read aloud by '
 'anyone. The Hebrew is set without vowel points in the source, as it was printed, and so is '
 'given without a sound.</p>\n'
 '<p>His references — to the fathers, the schoolmen, and the classical writers — stood in the '
 'margin. They are set at the foot of the chapter that calls them.</p>\n'
 '<p>Two tables in the source index the printed pages of the volumes they were made for, and '
 'are left out: an ebook has no such pages, and the search finds what they were for.</p>','frontmatter'))
files.append(('01-edition-note.xhtml','About This Edition'))

for k,(ttl, sub, raw) in enumerate(front, 2):
    seen=[]
    inner=f'<h2>{html.escape(ttl)}</h2>\n' + (f'<p class="parthd">{html.escape(sub)}</p>\n' if sub else '')
    inner+=clean(raw, seen) + notes_block(seen)
    fn=f'{k:02d}-{re.sub(r"[^a-z]+","-",ttl.lower()).strip("-")}.xhtml'
    open(f'{OUT}/OEBPS/text/{fn}','w',encoding='utf-8').write(page(ttl,'preface','preamble',inner,'frontmatter'))
    files.append((fn,ttl))

for i,c in enumerate(chapters,1):
    ttl=f'Discourse {c["num"]} — {c["title"]}' if c['title'] else f'Discourse {c["num"]}'
    seen=[]
    inner=f'<h2>{html.escape(ttl)}</h2>\n' + '\n'.join(clean(body_of(read(d)), seen) for d in c['docs'])
    inner+=notes_block(seen)
    fn=f'D{i:02d}.xhtml'
    open(f'{OUT}/OEBPS/text/{fn}','w',encoding='utf-8').write(page(ttl,'chapter','chapter',inner))
    files.append((fn,ttl))

open(f'{OUT}/OEBPS/text/97-sources.xhtml','w',encoding='utf-8').write(page(
 'Sources and Acknowledgements','preamble','preamble','<h2>Sources and Acknowledgements</h2>\n'
 '<p>Stephen Charnock died in 1680, and these Discourses were gathered from his papers and '
 'published in 1682. This edition follows the two-volume nineteenth-century printing, with the '
 'life of Charnock by William Symington.</p>\n'
 '<p>Our text descends from <i>Project Gutenberg</i> ebook 53527, proofread by the volunteers '
 'of <i>Distributed Proofreaders</i> from scans of that printing. Freely given, and gratefully '
 'used.</p>\n'
 '<p>The arrangement of this edition is the work of RFRMDWordLabs, LLC. No claim is made upon '
 'the text.</p>\n<p><i>Soli Deo gloria.</i></p>','backmatter'))
files.append(('97-sources.xhtml','Sources and Acknowledgements'))

E=html.escape
open(f'{OUT}/OEBPS/nav.xhtml','w',encoding='utf-8').write(
 '<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
 'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n<head><title>Contents</title>'
 '<meta charset="utf-8"/></head><body>\n<nav epub:type="toc" role="doc-toc" id="toc"><h1>Contents</h1><ol>\n'
 +'\n'.join(f'      <li><a href="text/{f}">{E(t)}</a></li>' for f,t in files[1:])+'\n</ol></nav>\n</body></html>\n')
man_=['    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
      '    <item id="css" href="css/style.css" media-type="text/css"/>',
      '    <item id="cover-img" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>',
      '    <item id="pm" href="images/publisher-mark.png" media-type="image/png"/>',
      '    <item id="pmd" href="images/publisher-mark-dark.png" media-type="image/png"/>']
spine_=[]
for i,(f,t) in enumerate(files):
    man_.append(f'    <item id="t{i}" href="text/{f}" media-type="application/xhtml+xml"/>')
    spine_.append(f'    <itemref idref="t{i}"/>')
open(f'{OUT}/OEBPS/content.opf','w',encoding='utf-8').write(
 '<?xml version="1.0" encoding="utf-8"?>\n<package xmlns="http://www.idpf.org/2007/opf" '
 'version="3.0" unique-identifier="bookid" xml:lang="en-GB">\n'
 '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
 f'    <dc:identifier id="bookid">urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL,"schriftohr:charnock-attributes")}</dc:identifier>\n'
 f'    <dc:title>{E(T)}</dc:title>\n    <dc:creator>{E(AUTHOR)}</dc:creator>\n'
 '    <dc:language>en-GB</dc:language>\n    <dc:publisher>RFRMD Word Labs LLC</dc:publisher>\n'
 '    <dc:description>A reading edition of Charnock’s fourteen Discourses on the existence and '
 'attributes of God, from the Distributed Proofreaders transcription.</dc:description>\n'
 '    <meta property="dcterms:modified">2026-08-23T00:00:00Z</meta>\n'
 '  </metadata>\n  <manifest>\n'+'\n'.join(man_)+'\n  </manifest>\n  <spine>\n'+'\n'.join(spine_)+
 '\n  </spine>\n</package>\n')
open(f'{OUT}/META-INF/container.xml','w',encoding='utf-8').write(
 '<?xml version="1.0" encoding="utf-8"?>\n<container version="1.0" '
 'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n  <rootfiles>\n'
 '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
 '  </rootfiles>\n</container>\n')
name='Charnock_Stephen-SchriftOhr_Edition-Existence_and_Attributes_of_God.epub'
ep=f'{W}/output/{name}'
if os.path.exists(ep): os.remove(ep)
open(f'{OUT}/mimetype','w').write('application/epub+zip')
subprocess.run(['zip','-X0q',ep,'mimetype'], cwd=OUT, check=True)
subprocess.run(['zip','-Xr9Dq',ep,'META-INF','OEBPS'], cwd=OUT, check=True)
shutil.copy(ep, os.path.expanduser(f'~/Desktop/{name}'))
print(f'{len(chapters)} Discourses + {len(front)} front pieces · {os.path.getsize(ep)//1024} KB')
