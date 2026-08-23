#!/usr/bin/env python3
"""Build the SchriftOhr Edition of Pink's Sovereignty of God.

The one book on this shelf with no keyed transcription behind it: the
source is a scan of the Bible Truth Depot printing at Swengel, and the
text comes from the scan's own OCR layer, which keeps what the page-by-page
epub threw away — line breaks, blank lines between paragraphs, and the
running heads standing on their own lines.

⚠️ Build from THIS printing, not a later one. The 1961 Banner of Truth
edition is abridged — whole chapters and appendices cut — and that editing
is in copyright. This printing carries three appendices; the fourth
(1 John 2:2) belongs to a later edition and is not here.

The editorial work, in order: throw away the running heads and the
scanner's noise, rejoin the words the compositor broke at the line end,
gather the lines back into Pink's paragraphs, and cut at his own chapter
titles — which survive the OCR cleanly even where "CHAPTER SEVEN" comes
through as "GHAPTER SEVEN,".
"""
import re, os, html, json, uuid, shutil, subprocess, sys
sys.path.insert(0, os.path.expanduser('~/Developer/schriftohr-books/tools'))
from edition_parts import cover_xhtml, proofing_xhtml, PROOFING_CSS, SCRIPT_CSS
from PIL import Image

W   = os.path.expanduser('~/Desktop/Reformed-Shelf-Working/01-pink-sovereignty')
TPL = '/private/tmp/claude-501/-Users-johnwest-Developer-schriftohr/6c0e5e0e-5ab4-4c3b-a6f4-cca64a136103/scratchpad/tpl'
OUT = f'{W}/output/sovereignty-of-god'
T   = 'The Sovereignty of God'
AUTHOR = 'Arthur W. Pink'

CORR = json.load(open(f'{W}/working/corrections.json', encoding='utf-8'))
raw = open(f'{W}/source/sovereigntyofgod00pink_0_djvu.txt',
           encoding='utf-8', errors='replace').read().split('\n')

# Pink's own divisions. Matched on the title line, which the OCR reads
# cleanly; the "CHAPTER N" line above it often does not survive at all.
PARTS = [
 ('front', 'Foreword to the First Edition',  'FOREWORD TO THE FIRST EDITION'),
 ('front', 'Foreword to the Second Edition', 'FOREWORD TO THE SECOND EDITION'),
 ('front', 'Introduction',                   'INTRODUCTION'),
 ('ch', 'God’s Sovereignty Defined',                  'GOD’S SOVEREIGNTY DEFINED'),
 ('ch', 'The Sovereignty of God in Creation',         'THE SOVEREIGNTY OF GOD IN CREATION'),
 ('ch', 'The Sovereignty of God in Administration',   'THE SOVEREIGNTY OF GOD IN ADMINISTRATION'),
 ('ch', 'The Sovereignty of God in Salvation',        'THE SOVEREIGNTY OF GOD IN SALVATION'),
 ('ch', 'The Sovereignty of God in Reprobation',      'THE SOVEREIGNTY OF GOD IN REPROBATION'),
 ('ch', 'The Sovereignty of God in Operation',        'THE SOVEREIGNTY OF GOD IN OPERATION'),
 ('ch', 'God’s Sovereignty and the Human Will',       'GOD’S SOVEREIGNTY AND THE HUMAN WILL'),
 ('ch', 'God’s Sovereignty and Human Responsibility', 'GOD’S SOVEREIGNTY AND HUMAN RESPONSIBILITY'),
 ('ch', 'God’s Sovereignty and Prayer',               'GOD’S SOVEREIGNTY AND PRAYER'),
 ('ch', 'Our Attitude Toward God’s Sovereignty',      'OUR ATTITUDE TOWARD GOD’S SOVEREIGNTY'),
 ('ch', 'Difficulties and Objections',                'DIFFICULTIES AND OBJECTIONS'),
 ('ch', 'The Value of This Doctrine',                 'VALUE OF THIS DOCTRINE'),
 ('back', 'Conclusion',                        'CONCLUSION'),
 ('back', 'Appendix I — The Will of God',      'THE WILL OF GOD'),
 ('back', 'Appendix II — The Case of Adam',    'THE CASE OF ADAM'),
 ('back', 'Appendix III — The Meaning of “Kosmos” in John 3:16',
                                               'THE MEANING OF “KOSMOS” IN JOHN 3:16'),
]
# where the book stops and the publisher's advertisements begin
END = next(i for i, l in enumerate(raw) if 'BY ARTHUR W. PINK' in l and i > 11800)

def norm(s):
    return re.sub(r'[^A-Z0-9]+', ' ', s.upper().replace('’', "'").replace("'", '')).strip()

starts, at = [], 0
for kind, title, key in PARTS:
    k = norm(key)
    for i in range(at, END):
        if norm(raw[i]) == k and len(raw[i].strip()) < 70:
            starts.append((i, kind, title)); at = i + 1; break
    else:
        raise SystemExit(f'could not find the opening of “{title}”')
print(f'  {len(starts)} divisions located, lines {starts[0][0]}–{END}')

RUNHEAD = re.compile(r'^\s*(?:\d{1,3}\s+)?[A-Z][A-Z’\'\.\- ]{5,60}?(?:\s+\d{1,3})?\s*$')
PAGENUM = re.compile(r'^\s*\d{1,3}\s*$')

APPLIED = set()

def wordish(s):
    """What share of a line's tokens are actual words.

    A blank page or a plate leaves the scanner talking to itself — pages of
    "= - ae ; it At ane : J : :" — and those lines score near zero where real
    prose scores above a half. Nothing else separates them as cleanly.
    """
    toks = s.split()
    if not toks: return 0.0
    return sum(1 for t in toks
               if re.fullmatch(r"[A-Za-z][A-Za-z’'\-]{2,}[.,;:!?”’)]*", t)) / len(toks)

def is_noise(s):
    if not s or not any(c.isalpha() for c in s): return True
    if len(s) < 24 and len(re.findall(r"[A-Za-z’']{3,}", s)) < 2: return True
    return wordish(s) < 0.40

IA_NOTICE = re.compile(r'(Digitized by the Internet Archive|with funding from|'
                       r'Princeton Theological Seminary|https?\s*://archive\.org)', re.I)

def paragraphs(lo, hi, key='', drop_head=True):
    out, cur = [], []
    body = raw[lo:hi]
    if drop_head: body = body[1:]                       # the title line itself
    for l in body:
        s = l.rstrip()
        if not s.strip():
            # A blank line only ends a paragraph when the paragraph has ended:
            # around a large opening initial the scanner leaves gaps mid-sentence.
            if cur and re.search(r'[.!?”’]$', cur[-1]):
                out.append(cur); cur = []
            continue
        if PAGENUM.match(s) or (RUNHEAD.match(s) and re.search(r'\d', s)):
            continue                                    # a running head, not text
        # The divisional half-title, repeated on the chapter's first text page.
        # Its roman numeral rarely survives the OCR — I reads as l, VII as Vil,
        # XI as Xl — so it is caught by the title, not by the numeral.
        if key and len(s) < len(key) + 20:
            a, b = set(norm(s).split()), set(norm(key).split())
            if b and len(a & b) / len(b) >= 0.6:
                continue                                # the divisional half-title
        if IA_NOTICE.search(s):
            continue                                    # the scanner's own notice
        if is_noise(s.strip()):
            continue
        cur.append(s.strip())
    if cur: out.append(cur)
    paras = []
    for block in out:
        t = ''
        for line in block:
            if t.endswith('-') and not t.endswith('--'):
                t = t[:-1] + line                       # the compositor's line-end break
            elif t:
                t += ' ' + line
            else:
                t = line
        t = re.sub(r'\s+', ' ', t).strip()
        t = re.sub(r'\s+([,;.!?:])', r'\1', t)          # OCR spacing before punctuation
        t = t.replace('‘‘', '“').replace('’’', '”')
        if len(t.split()) >= 3: paras.append(t)
    # Every correction is recorded in working/corrections.json, with what settled it.
    fixed = []
    for t in paras:
        for c in CORR['openings']:
            if c['find'] in t:
                t = t.replace(c['find'], c['reads']); APPLIED.add(c['find'])
        for c in CORR['sweeps']:
            t2 = re.sub(c['find'], c['reads'], t)
            if t2 != t: APPLIED.add(c['find'])
            t = t2
        fixed.append(t)
    return fixed


divisions = []
for k, (i, kind, title) in enumerate(starts):
    key = PARTS[k][2]
    end = starts[k+1][0] if k+1 < len(starts) else END
    ps = paragraphs(i, end, key)
    divisions.append((kind, title, ps))
    print(f'    {kind:5} {sum(len(p.split()) for p in ps):7,}w  {title[:52]}')

# --- set it ---------------------------------------------------------------
shutil.rmtree(OUT, ignore_errors=True)
for d in ('META-INF','OEBPS/text','OEBPS/css','OEBPS/images'): os.makedirs(f'{OUT}/{d}')
shutil.copy(f'{TPL}/OEBPS/css/style.css', f'{OUT}/OEBPS/css/style.css')
open(f'{OUT}/OEBPS/css/style.css','a').write(
 '\n/* Pink sets a text under each chapter title. */\n'
 '.epigraph{font-style:italic;text-align:center;text-indent:0;margin:0 1.4em 1.8em;\n'
 '          font-size:.95em}\n' + PROOFING_CSS + SCRIPT_CSS)
for m_ in ('publisher-mark.png','publisher-mark-dark.png'):
    shutil.copy(f'{TPL}/OEBPS/images/{m_}', f'{OUT}/OEBPS/images/{m_}')
Image.open(os.path.expanduser('~/Desktop/Pink_AW-Sovereignty_of_God.png')).convert('RGB').save(
    f'{OUT}/OEBPS/images/cover.jpg','JPEG',quality=90,optimize=True,progressive=True)

E = html.escape
def page(title, et, cls, inner, bt='bodymatter'):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
      'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n'
      f'<head><title>{E(title)}</title><meta charset="utf-8"/>'
      '<link rel="stylesheet" type="text/css" href="../css/style.css"/></head>\n'
      f'<body epub:type="{bt}"><section epub:type="{et}" class="{cls}">\n{inner}\n</section></body></html>\n')

files=[]
_cw,_ch = Image.open(f'{OUT}/OEBPS/images/cover.jpg').size
open(f'{OUT}/OEBPS/text/cover.xhtml','w',encoding='utf-8').write(cover_xhtml(_cw,_ch))
files.append(('cover.xhtml','Cover'))
open(f'{OUT}/OEBPS/text/00-proofing.xhtml','w',encoding='utf-8').write(proofing_xhtml(T, AUTHOR))
files.append(('00-proofing.xhtml','Proofing Copy'))
open(f'{OUT}/OEBPS/text/00-title.xhtml','w',encoding='utf-8').write(page(T,'titlepage','titlepage',
 f'<h1>{E(T)}</h1>\n<p><strong>{E(AUTHOR)}</strong></p>\n<p>The SchriftOhr Edition</p>\n'
 '<p>Developed by RFRMDWordLabs, LLC</p>\n'
 '<p>For the benefit of readers, prayerfully, to the glory of God.</p>\n'
 '<p class="publisher-mark"><img src="../images/publisher-mark.png" alt="RFRMD Word Labs, LLC"/></p>','frontmatter'))
files.append(('00-title.xhtml',T))
open(f'{OUT}/OEBPS/text/01-edition-note.xhtml','w',encoding='utf-8').write(page(
 'About This Edition','preamble','preamble','<h2>About This Edition</h2>\n'
 f'<p>This is the SchriftOhr edition of <i>{E(T)}</i>, prepared by RFRMDWordLabs, LLC. '
 'Pink’s text is given as he wrote it — not modernised, abridged, or rewritten.</p>\n'
 '<p>Alone among the books on this shelf, this one has no hand-typed transcription behind it: '
 'the text was read off the printed page by machine, and machines misread. We have set the '
 'chapters, rejoined the words the printer broke across a line, and cleared away the running '
 'heads and page numbers the scanner mistook for text. <b>If you find a word that reads oddly, '
 'it is worth reporting</b> — see the note at the front.</p>\n'
 '<p>Pink revised this book across several editions, and later ones are shorter. This is the '
 'longer, earlier text, with the three appendices it carried.</p>','frontmatter'))
files.append(('01-edition-note.xhtml','About This Edition'))

n=2
for kind, title, ps in divisions:
    inner=f'<h2>{E(title)}</h2>\n'
    body=list(ps)
    # Pink heads each chapter with a text of Scripture; keep it as an epigraph
    if kind=='ch' and body and len(body[0].split())<70 and body[0].lstrip().startswith(('“','_“','"')):
        inner+=f'<p class="epigraph">{E(body.pop(0))}</p>\n'
        if body and len(body[0].split())<8:
            inner+=f'<p class="epigraph">{E(body.pop(0))}</p>\n'
    inner+='\n'.join(f'<p>{E(p)}</p>' for p in body)
    fn = f'{n:02d}-{re.sub(chr(0x2014),"",re.sub(r"[^a-z0-9]+","-",title.lower())).strip("-")[:40]}.xhtml'
    et = {'front':'preface','ch':'chapter','back':'afterword'}[kind]
    bt = {'front':'frontmatter','ch':'bodymatter','back':'backmatter'}[kind]
    open(f'{OUT}/OEBPS/text/{fn}','w',encoding='utf-8').write(
        page(title, et, 'chapter' if kind=='ch' else 'preamble', inner, bt))
    files.append((fn,title)); n+=1

open(f'{OUT}/OEBPS/text/97-sources.xhtml','w',encoding='utf-8').write(page(
 'Sources and Acknowledgements','preamble','preamble','<h2>Sources and Acknowledgements</h2>\n'
 '<p>Arthur W. Pink first published <i>The Sovereignty of God</i> in 1918, printed by the Bible '
 'Truth Depot of Swengel, Pennsylvania. This edition follows that printing, which has long been '
 'in the public domain in the United States.</p>\n'
 '<p>Our text was taken from the <i>Internet Archive</i>’s scan of a library copy '
 '(<i>sovereigntyofgod00pink_0</i>), and set from its text layer. Later editions of this book '
 'were revised and shortened by other hands; none of that editing is here.</p>\n'
 '<p>The arrangement of this edition is the work of RFRMDWordLabs, LLC. No claim is made upon '
 'the text.</p>\n<p><i>Soli Deo gloria.</i></p>','backmatter'))
files.append(('97-sources.xhtml','Sources and Acknowledgements'))

open(f'{OUT}/OEBPS/nav.xhtml','w',encoding='utf-8').write(
 '<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
 'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n<head><title>Contents</title>'
 '<meta charset="utf-8"/></head><body>\n<nav epub:type="toc" role="doc-toc" id="toc"><h1>Contents</h1><ol>\n'
 +'\n'.join(f'      <li><a href="text/{f}">{E(t)}</a></li>' for f,t in files[1:])+'\n</ol></nav>\n</body></html>\n')
man=['    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
     '    <item id="css" href="css/style.css" media-type="text/css"/>',
     '    <item id="cover-img" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>',
     '    <item id="pm" href="images/publisher-mark.png" media-type="image/png"/>',
     '    <item id="pmd" href="images/publisher-mark-dark.png" media-type="image/png"/>']
spine=[]
for i,(f,t) in enumerate(files):
    man.append(f'    <item id="t{i}" href="text/{f}" media-type="application/xhtml+xml"/>')
    spine.append(f'    <itemref idref="t{i}"/>')
open(f'{OUT}/OEBPS/content.opf','w',encoding='utf-8').write(
 '<?xml version="1.0" encoding="utf-8"?>\n<package xmlns="http://www.idpf.org/2007/opf" '
 'version="3.0" unique-identifier="bookid" xml:lang="en-GB">\n'
 '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
 f'    <dc:identifier id="bookid">urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL,"schriftohr:pink-sovereignty")}</dc:identifier>\n'
 f'    <dc:title>{E(T)}</dc:title>\n    <dc:creator>{E(AUTHOR)}</dc:creator>\n'
 '    <dc:language>en-GB</dc:language>\n    <dc:publisher>RFRMD Word Labs LLC</dc:publisher>\n'
 '    <dc:description>A reading edition of Pink’s Sovereignty of God, from the 1918 Bible Truth '
 'Depot printing.</dc:description>\n'
 '    <meta property="dcterms:modified">2026-08-23T00:00:00Z</meta>\n'
 '  </metadata>\n  <manifest>\n'+'\n'.join(man)+'\n  </manifest>\n  <spine>\n'+'\n'.join(spine)+
 '\n  </spine>\n</package>\n')
open(f'{OUT}/META-INF/container.xml','w',encoding='utf-8').write(
 '<?xml version="1.0" encoding="utf-8"?>\n<container version="1.0" '
 'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n  <rootfiles>\n'
 '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
 '  </rootfiles>\n</container>\n')
name='Pink_Arthur_W-SchriftOhr_Edition-Sovereignty_of_God.epub'
ep=f'{W}/output/{name}'
os.makedirs(f'{W}/output', exist_ok=True)
if os.path.exists(ep): os.remove(ep)
open(f'{OUT}/mimetype','w').write('application/epub+zip')
subprocess.run(['zip','-X0q',ep,'mimetype'], cwd=OUT, check=True)
subprocess.run(['zip','-Xr9Dq',ep,'META-INF','OEBPS'], cwd=OUT, check=True)
shutil.copy(ep, os.path.expanduser(f'~/Desktop/{name}'))
unused = [c['find'][:44] for c in CORR['openings'] + CORR['sweeps'] if c['find'] not in APPLIED]
print(f'  corrections: {len(APPLIED)} of {len(CORR["openings"])+len(CORR["sweeps"])} applied')
for u in unused: print(f'    ⚠️  never matched: {u}')
print(f'{len(divisions)} divisions · {sum(len(" ".join(p).split()) for _,_,p in divisions):,} words '
      f'· {os.path.getsize(ep)//1024} KB')
