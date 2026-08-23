#!/usr/bin/env python3
"""Build the SchriftOhr Edition of Brooks, Precious Remedies (1658).

The 1658 printer arranges the book by DEVICE: Brooks states one of
Satan's devices, answers it with a train of remedies, and the last
paragraph of that train announces the next device. So the divisions in
the file do not fall where the chapters do — a chapter begins at each
device statement, wherever it sits.

The four Parts are Brooks's own: devices to draw the soul to sin, to
keep it from holy duties, to keep it doubting, and against several
sorts of men.
"""
import sys, os, re, html, json, shutil, subprocess, uuid
sys.path.insert(0, os.path.expanduser('~/Developer/schriftohr-books/tools'))
from tei_reader import sections, words, open_cap, GK0, GK1, HB0, HB1, PH0, PH1, NR0, NR1
from edition_parts import cover_xhtml, proofing_xhtml, PROOFING_CSS, SCRIPT_CSS
from PIL import Image

W   = os.path.expanduser('~/Desktop/Reformed-Shelf-Working/04-brooks-precious-remedies')
TPL = '/private/tmp/claude-501/-Users-johnwest-Developer-schriftohr/6c0e5e0e-5ab4-4c3b-a6f4-cca64a136103/scratchpad/tpl'
OUT = f'{W}/output/precious-remedies'
T   = 'Precious Remedies Against Satan’s Devices'
AUTHOR = 'Thomas Brooks'

led    = json.load(open(f'{W}/working/gap-ledger.json'))
gapmap = {g['n']: g['reading'] for g in led['final'] if g.get('reading')}
greek  = json.load(open(f'{W}/working/greek.json', encoding='utf-8'))['gaps']
NOTES  = []
FRONT, secs = sections(f'{W}/source/A77614-EEBO-TCP-1658-keyed.xml', gapmap, greek,
                       NOTES, want_front=True)

# --- the stream, in the order the book is read -----------------------------
def stream(node, out):
    out.extend(node['paras'])
    for s in node['subs']:
        if s['head']:
            out.append(s['head'] if s['head'].endswith(('.', ':')) else s['head'] + '.')
        stream(s, out)
    return out

PARTS = [
 ('I',  'Satan’s Devices to Draw the Soul to Sin'),
 ('II', 'Satan’s Devices to Keep Souls from Holy Duties'),
 ('III','Satan’s Devices to Keep Souls in a Sad and Doubting Condition'),
 ('IV', 'Satan’s Devices Against Several Sorts of Men'),
]
ORDW = ['','First','Second','Third','Fourth','Fifth','Sixth','Seventh','Eighth',
        'Ninth','Tenth','Eleventh','Twelfth']
# 1658 spells them as it pleases — "sixt", "fift", and "twel[…]th" where the
# page is damaged — so the ordinal is matched loosely and read from its stem.
ORD = {'first':1,'second':2,'third':3,'fourth':4,'fift':5,'fifth':5,'sixt':6,'sixth':6,
       'seventh':7,'eighth':8,'eight':8,'ninth':9,'tenth':10,'eleventh':11,'twelfth':12}
DEVICE = re.compile(
  r'^\s*(?:Now\s+the|His|The)\s+([A-Za-z\[\]\u2026]+?)\s+[Dd]evice\b(.*)$', re.S)
# Part IV runs by the sort of men Satan is at work upon, not by numbered device
CLASS = re.compile(r'^\s*(Secondly|Thirdly|Lastly)\b[^.]{0,80}?Satan hath his [Dd]evices\b', re.I|re.S)
# Brooks names these four himself, in the text and in his own running heads.
CLOSERS = [
 (re.compile(r'^\s*I\s+Shall begin with the honourable', re.I),
  'Satan’s Devices Against the Great and Honourable'),
 (re.compile(r'^\s*And now to prevent Objections', re.I),
  'Propositions Concerning Satan and His Devices'),
 (re.compile(r'^\s*THe first Reason is', re.I), 'The Reasons of the Point'),
 (re.compile(r'^\s*IF Satan hath such a world of devices', re.I), 'The Use of the Point'),
]

def ordinal(word):
    w = re.sub(r'[^a-z]', '', word.lower())
    if w in ORD: return ORD[w]
    for k, v in ORD.items():                      # "twel…th" → twelfth
        if w and (w.startswith(k[:3]) and w.endswith(k[-2:])): return v
    return None

def plain(t):
    """A title carries no note of its own — a reference mark left in one nested
    an <a> inside the contents' own link, and the entry vanished from the nav."""
    return re.sub(NR0 + r'\d+' + NR1, '', t)


def clause_of(stmt, nxt):
    """Brooks's own words for what the device IS — never invented.

    He writes it two ways: '…is, by painting sin with vertues colours' in the
    same sentence, or '…is,' with the device standing in the paragraph after.
    """
    m = re.search(r'\bis,?\s*$', stmt)
    text = nxt if m else re.split(r'\bis,\s*', stmt, maxsplit=1)[-1]
    if text is stmt or text == stmt:
        text = re.split(r'\bis,?\s+', stmt, maxsplit=1)[-1]
    text = plain(text)
    text = re.sub(r'^(?:BY|By|by)\s+', 'By ', text.strip())
    text = re.split(r'[;.]|\s\(', text)[0].strip().rstrip(',')
    text = re.sub(r'\s*\[[^\]]*\]\s*', ' ', text).strip()      # a mark is no title
    if len(text) > 76:
        text = text[:76].rsplit(' ', 1)[0] + '…'
    return (text[0].upper() + text[1:]) if text else ''

def stream(node, out):
    out.extend(node['paras'])
    for s_ in node['subs']:
        if s_['head']:
            out.append(s_['head'] if s_['head'].endswith(('.', ':', ',')) else s_['head'] + '.')
        stream(s_, out)
    return out

chapters = []
for pi, sec in enumerate(secs):
    roman, ptitle = PARTS[pi]
    body = stream(sec, [])
    bag, cur = [], {'title': None, 'paras': []}
    for i, p in enumerate(body):
        nxt = body[i+1] if i+1 < len(body) else ''
        head = None
        m = DEVICE.match(p)
        if m and ordinal(m.group(1)):
            n = ordinal(m.group(1))
            c = clause_of(p, nxt)
            head = f'The {ORDW[n]} Device' + (f' — {c}' if c else '')
        elif pi == 3 and CLASS.match(p):
            who = re.search(r'[Dd]evices\s+to\s+(?:ensnare\s+and\s+)?destroy\s+([^,;.]+)', p)
            head = 'Satan’s Devices Against ' + (plain(who.group(1)).strip().title() if who else 'Others')
        elif pi == 3:
            for rx, name in CLOSERS:
                if rx.match(p): head = name; break
        if head:
            if cur['paras']: bag.append(cur)
            cur = {'title': head, 'paras': [p]}
        else:
            cur['paras'].append(p)
    if cur['paras']: bag.append(cur)
    if pi == 0 and bag and not bag[0]['title']:
        bag[0]['title'] = 'The Text Opened'
    for b in bag:
        chapters.append((roman, ptitle, b['title'] or ptitle, b['paras']))

# --- set it ---------------------------------------------------------------
shutil.rmtree(OUT, ignore_errors=True)
for d in ('META-INF','OEBPS/text','OEBPS/css','OEBPS/images'): os.makedirs(f'{OUT}/{d}')
shutil.copy(f'{TPL}/OEBPS/css/style.css', f'{OUT}/OEBPS/css/style.css')
open(f'{OUT}/OEBPS/css/style.css','a').write(
 '\n/* Brooks runs by Part and Device; keep both visible. */\n'
 '.parthd{text-align:center;font-variant:small-caps;letter-spacing:.06em;color:#777;\n'
 '        font-size:.86em;margin:0 0 .4em;text-indent:0}\n'
 '/* Brooks\'s margin, kept as notes at the foot of the chapter. */\n'
 '.nref{text-decoration:none;font-size:.8em;vertical-align:super;line-height:0}\n'
 '.notes{font-size:.9em;color:#555;margin-top:2.4em}\n'
 '.notes hr{border:0;border-top:1px solid #ccc;width:35%;margin:0 0 .9em}\n'
 '.fn p{text-indent:0;margin:.35em 0}\n'
 '.fn a{text-decoration:none;color:#777}\n' + PROOFING_CSS + SCRIPT_CSS)
for m in ('publisher-mark.png','publisher-mark-dark.png'):
    shutil.copy(f'{TPL}/OEBPS/images/{m}', f'{OUT}/OEBPS/images/{m}')
Image.open(os.path.expanduser('~/Desktop/Brooks-PreciousRemedies.png')).convert('RGB').save(
    f'{OUT}/OEBPS/images/cover.jpg','JPEG',quality=90,optimize=True,progressive=True)

def E(s, notes_seen=None):
    s=html.escape(s)
    # Brooks's margin, set as a real note: readers that can, pop it up; readers
    # that cannot, find it at the foot of the chapter. Either way it is out of
    # the middle of his sentence, where flattening had put it.
    def _ref(m):
        n=int(m.group(1))
        if notes_seen is not None: notes_seen.append(n)
        return (f'<a epub:type="noteref" href="#fn{n}" id="fr{n}" class="nref">'
                f'<sup>{n}</sup></a>')
    # the mark hugs the word it belongs to; the margin left a space there
    s=re.sub(r'\s*'+NR0+r'(\d+)'+NR1, _ref, s)
    s=s.replace(GK0,'<span xml:lang="grc" lang="grc" class="gk">').replace(GK1,'</span>')
    s=s.replace(HB0,'<span xml:lang="hbo" lang="hbo" dir="rtl" class="hb">').replace(HB1,'</span>')
    return s.replace(PH0,'<span class="ph">').replace(PH1,'</span>')

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
 f'<h1>{E(T)}</h1>\n<h2>Or, Salve for Believers and Unbelievers’ Sores</h2>\n'
 f'<p><strong>{E(AUTHOR)}</strong></p>\n<p>The SchriftOhr Edition</p>\n'
 '<p>Developed by RFRMDWordLabs, LLC</p>\n'
 '<p>For the benefit of readers, prayerfully, to the glory of God.</p>\n'
 '<p class="publisher-mark"><img src="../images/publisher-mark.png" alt="RFRMD Word Labs, LLC"/></p>','frontmatter'))
files.append(('00-title.xhtml',T))
open(f'{OUT}/OEBPS/text/01-edition-note.xhtml','w',encoding='utf-8').write(page(
 'About This Edition','preamble','preamble','<h2>About This Edition</h2>\n'
 f'<p>This is the SchriftOhr edition of <i>{E(T)}</i>, prepared by RFRMDWordLabs, LLC. '
 'Brooks’s text is given as he wrote it — not modernised, abridged, or rewritten. The '
 'seventeenth-century spelling stands, save that the long <i>ſ</i> is set as <i>s</i> and '
 'words broken across a line are rejoined.</p>\n'
 '<p>Where the page was damaged past reading, the word is supplied where it can be established '
 'and marked <i>[…]</i> where it cannot.</p>\n'
 '<p>The Greek and Hebrew Brooks quotes are set as he quoted them, with how each sounds in '
 'brackets after it, so the word can be read aloud by anyone. Where he leaves a word unexplained '
 'and no printing sets the script, it is marked <i>[Greek]</i>.</p>\n'
 '<p>The chapters are the book’s own: Brooks states a device of Satan, answers it with his '
 'remedies, and the close of that train announces the next. Each device begins a chapter, and '
 'the title is Brooks’s own sentence, cut short.</p>','frontmatter'))
files.append(('01-edition-note.xhtml','About This Edition'))

# Brooks's own front matter — the dedication to his people at Margarets, and
# his word to the reader. The 1658 contents table is dropped; this edition
# has its own.
for k,(fn,ttl) in enumerate([('02-epistle.xhtml','The Epistle Dedicatory'),
                             ('03-to-the-reader.xhtml','A Word to the Reader')]):
    node=[f for f in FRONT if f['head'] and 'CONTENTS' not in f['head'].upper()]
    if k>=len(node): continue
    n=node[k]; ps=list(n['paras'])
    if ps: ps[0]=open_cap(ps[0])
    seen=[]
    inner=f'<h2>{E(ttl)}</h2>\n'+'\n'.join(f'<p>{E(x, seen)}</p>' for x in ps)
    if seen:
        inner+='\n<section epub:type="endnotes" class="notes"><hr/>\n'+'\n'.join(
            f'<aside epub:type="footnote" id="fn{n_}" class="fn">'
            f'<p><a href="#fr{n_}">{n_}.</a> {E(NOTES[n_-1])}</p></aside>' for n_ in seen)+'\n</section>'
    open(f'{OUT}/OEBPS/text/{fn}','w',encoding='utf-8').write(
        page(ttl,'preface','preamble',inner,'frontmatter'))
    files.append((fn,ttl))

last_part=None
for i,(roman, ptitle, ctitle, paras) in enumerate(chapters,1):
    inner=''
    if roman!=last_part:
        inner+=f'<p class="parthd">Part {roman} · {E(ptitle)}</p>\n'; last_part=roman
    inner+=f'<h2>{E(ctitle)}</h2>\n'
    ps=list(paras)
    if ps: ps[0]=open_cap(ps[0])
    seen=[]
    inner+='\n'.join(f'<p>{E(p, seen)}</p>' for p in ps)
    if seen:
        inner+='\n<section epub:type="endnotes" class="notes"><hr/>\n'+'\n'.join(
            f'<aside epub:type="footnote" id="fn{n}" class="fn">'
            f'<p><a href="#fr{n}">{n}.</a> {E(NOTES[n-1])}</p></aside>' for n in seen)+'\n</section>'
    fn=f'C{i:02d}.xhtml'
    open(f'{OUT}/OEBPS/text/{fn}','w',encoding='utf-8').write(page(ctitle,'chapter','chapter',inner))
    files.append((fn,ctitle))

open(f'{OUT}/OEBPS/text/97-sources.xhtml','w',encoding='utf-8').write(page(
 'Sources and Acknowledgements','preamble','preamble','<h2>Sources and Acknowledgements</h2>\n'
 '<p>Thomas Brooks published <i>Precious Remedies Against Satan’s Devices</i> in 1652; this '
 'edition follows the printing of 1658 (Wing B4954; Thomason E1426_1). Brooks died in 1680, and '
 'his text has long been in the public domain.</p>\n'
 '<p>Our text descends from the <i>Early English Books Online Text Creation Partnership</i>, '
 'whose keyers typed it by hand from images of the 1658 pages. The Partnership has waived every '
 'right it holds in that work under the <i>CC0 1.0 Public Domain Dedication</i>. Freely given, '
 'and gratefully used.</p>\n'
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
 f'    <dc:identifier id="bookid">urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, "schriftohr:brooks-precious-remedies")}</dc:identifier>\n'
 f'    <dc:title>{E(T)}</dc:title>\n    <dc:creator>{E(AUTHOR)}</dc:creator>\n'
 '    <dc:language>en-GB</dc:language>\n'
 '    <dc:publisher>RFRMD Word Labs LLC</dc:publisher>\n'
 '    <dc:description>A reading edition of Brooks’s Precious Remedies, from the EEBO-TCP '
 'keyed transcription of the 1658 printing.</dc:description>\n'
 '    <meta property="dcterms:modified">2026-08-23T00:00:00Z</meta>\n'
 '  </metadata>\n  <manifest>\n'+'\n'.join(man)+'\n  </manifest>\n  <spine>\n'+'\n'.join(spine)+
 '\n  </spine>\n</package>\n')
open(f'{OUT}/META-INF/container.xml','w',encoding='utf-8').write(
 '<?xml version="1.0" encoding="utf-8"?>\n<container version="1.0" '
 'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n  <rootfiles>\n'
 '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
 '  </rootfiles>\n</container>\n')

name='Brooks_Thomas-SchriftOhr_Edition-Precious_Remedies.epub'
ep=f'{W}/output/{name}'
if os.path.exists(ep): os.remove(ep)
open(f'{OUT}/mimetype','w').write('application/epub+zip')
subprocess.run(['zip','-X0q',ep,'mimetype'], cwd=OUT, check=True)
subprocess.run(['zip','-Xr9Dq',ep,'META-INF','OEBPS'], cwd=OUT, check=True)
shutil.copy(ep, os.path.expanduser(f'~/Desktop/{name}'))
print(f'{len(chapters)} chapters · {sum(len(" ".join(p).split()) for _,_,_,p in chapters):,} words '
      f'· {os.path.getsize(ep)//1024} KB')
