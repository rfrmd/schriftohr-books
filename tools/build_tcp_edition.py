import re, html, json, os, sys, shutil, subprocess, uuid
sys.path.insert(0, os.path.expanduser('~/Developer/schriftohr-books/tools'))
from PIL import Image
from tei_reader import open_cap
from edition_parts import cover_xhtml, proofing_xhtml, PROOFING_CSS, SCRIPT_CSS
W=os.path.expanduser('~/Desktop/Reformed-Shelf-Working/02-owen-mortification')
TPL='/private/tmp/claude-501/-Users-johnwest-Developer-schriftohr/6c0e5e0e-5ab4-4c3b-a6f4-cca64a136103/scratchpad/tpl'
OUT=f'{W}/output/mortification-of-sin'
xml=open(f'{W}/source/A53715-EEBO-TCP-1668-keyed.xml',encoding='utf-8',errors='ignore').read()
led=json.load(open(f'{W}/working/gap-ledger.json'))
readings={g['n']: g['reading'] for g in led['final'] if g.get('reading')}

gk=json.load(open(f'{W}/working/greek.json',encoding='utf-8'))['gaps']
GK0,GK1,HB0,HB1,PH0,PH1='\ue000','\ue001','\ue002','\ue003','\ue004','\ue005'

body=xml[xml.find('<text'):]
# A gap is the WHOLE element, placeholder glyph and all. Replacing only the
# opening tag left 〈◊〉 and 〈 in non-Latin alphabet 〉 loose in the text, where a
# later sweep called every one of them Greek — including the illegible words.
GAP=re.compile(r'<gap\b[^>]*/>|<gap\b[^>]*>.*?</gap>', re.S)
cnt=[0]
def _tok(m):
    cnt[0]+=1
    # Whether the gap sits INSIDE a word decides whether its reading may absorb
    # the letters beside it. Decided here, on the XML, because flattening turns
    # </gap> into a space and hides the join.
    pre =re.sub(r'<[^>]+>','', body[max(0,m.start()-60):m.start()])
    post=re.sub(r'<[^>]+>','', body[m.end():m.end()+60])
    L='1' if re.search(r'[A-Za-zſ]$', pre) else '0'
    R='1' if re.match(r'[A-Za-zſ]', post) else '0'
    P='1' if re.search(r'extent="1 letter"', m.group(0)) else '0'
    return f'⟦{"F" if "foreign" in m.group(0) else "G"}{cnt[0]}:{L}{R}{P}⟧'
body=GAP.sub(_tok, body)

# Owen's margin — mostly the Scripture he is leaning on — was being flattened
# into the middle of his sentence ("as the Judgement of another, Rom. 1.26. a
# greater for the punishment of a less"). It is a note, and is set as one.
NOTEREF=re.compile(r'⟦N\d+⟧')
NOTES=[]
def _note(m):
    NOTES.append(m.group(1))
    return f'⟦N{len(NOTES)}⟧'
body=re.sub(r'<note\b[^>]*>(.*?)</note>', _note, body, flags=re.S)

def totext(x):
    # The printer's glyphs, before the generic strip — which turns a tag into a
    # SPACE and so put one through the middle of a word ("Ʋ pon the Eruption").
    # An end-of-line hyphen must REJOIN the word: as a space it made "princi pal".
    x=re.sub(r'<g ref="char:cmbAbbrStroke">[^<]*</g>(?=m)', 'm', x)
    x=re.sub(r'<g ref="char:cmbAbbrStroke">[^<]*</g>', 'n', x)
    x=re.sub(r'<g ref="char:EOLhyphen"\s*/?>(?:</g>)?', '', x)
    x=re.sub(r'<g ref="char:V">[^<]*</g>', 'U', x)   # the 17th-c. capital U, cut as a V
    x=re.sub(r'<g ref="char:punc">[^<]*</g>', '', x) # a mark the keyers could not identify
    x=re.sub(r'<g [^>]*>([^<]*)</g>', r'\1', x)      # any other glyph: the character, not a space
    x=re.sub(r'<g [^>]*/?>', '', x)
    x=re.sub(r'<pb[^>]*/?>',' ', x); x=re.sub(r'<[^>]+>',' ', x)
    return re.sub(r'\s+',' ', html.unescape(x).replace('ſ','s')).strip()

def _foreign(m):
    e=gk.get(m.group(1))
    if not (e and e.get('t')): return '[Greek]'
    a,z=(HB0,HB1) if e.get('script')=='hbo' else (GK0,GK1)
    # The word is no use to a reader who cannot read the script, and none at
    # all to the ear. Say how it sounds.
    ph=f" {PH0}({e['ph']}){PH1}" if e.get('ph') else ''
    return a+e['t']+z+ph

def _damaged(m):
    left, sp, n = m.group(1) or '', m.group(2), int(m.group(3))
    L, R, P     = m.group(4)=='1', m.group(5)=='1', m.group(6)=='1'
    right       = m.group(7) or ''
    # Where the gap opened the match, the space before it still has to be kept.
    lead = ' ' if (sp and not left) else ''
    # A single damaged letter standing between two intact words is a punctuation
    # mark, not a missing word. Collating it against its neighbours produced
    # "no good thing and and it hinders" and "for the most part amongst .".
    if P and not (L or R):
        return lead + ' '.join(x for x in (left, right) if x)
    rd = readings.get(n)
    if rd is None:
        if L or R: return lead + left + '[…]' + right
        return lead + ' '.join(x for x in (left, '[…]', right) if x)
    # The reading is the WHOLE word. It absorbs the broken fragments beside it —
    # and nothing else: a gap between two intact words used to swallow both
    # ("the [gap] substance" came out as bare "the").
    return lead + ' '.join(x for x in (('' if L else left), rd, ('' if R else right)) if x)

def resolve(t):
    t=re.sub(r'⟦F(\d+):\d\d\d⟧', _foreign, t)
    t=re.sub(r'([A-Za-z]*)(\s*)⟦G(\d+):(\d)(\d)(\d)⟧[•▫▪\s]*([A-Za-z]*)', _damaged, t)
    t=t.replace('•','')
    return re.sub(r'\s+',' ',t).strip()

ROM=['I','II','III','IV','V','VI','VII','VIII','IX','X','XI','XII','XIII','XIV']
divs=re.findall(r'<div\d?[^>]*>(.*?)</div\d?>', body, re.S)
chapters=[]; preface=None
for d in divs:
    head=re.search(r'<head[^>]*>(.*?)</head>', d, re.S)
    arg=re.search(r'<argument[^>]*>(.*?)</argument>', d, re.S)
    title=totext(head.group(1)) if head else ''
    if 'Catalogue' in title: continue
    # the argument carries its own <p>; strip it before reading the body,
    # or it appears twice — once as the head-note and once as chapter one
    d_body=re.sub(r'<argument[^>]*>.*?</argument>', '', d, flags=re.S)
    paras=[resolve(totext(p)) for p in re.findall(r'<p\b[^>]*>(.*?)</p>', d_body, re.S)]
    paras=[p for p in paras if p]
    words=sum(len(p.split()) for p in paras)
    if words<400: continue
    m=re.match(r'CHAP\.?\s*([IVXL]+)', title, re.I)
    if m: chapters.append({'num':m.group(1).upper(),
                           'argument':resolve(totext(arg.group(1))) if arg else '',
                           'paras':paras})
    elif preface is None: preface={'paras':paras}

shutil.rmtree(OUT, ignore_errors=True)
for d in ('META-INF','OEBPS/text','OEBPS/css','OEBPS/images'): os.makedirs(f'{OUT}/{d}')
shutil.copy(f'{TPL}/OEBPS/css/style.css', f'{OUT}/OEBPS/css/style.css')
open(f'{OUT}/OEBPS/css/style.css','a').write(
 '\n/* The printer\'s argument at each chapter head, as 1668 set it. */\n'
 '.argument{font-style:italic;text-align:left;text-indent:0;margin:0 1.2em 1.6em;\n'
 '          font-size:.94em;border-left:2px solid #bbb;padding-left:.8em}\n'
 '/* Owen\'s margin, kept as notes at the foot of the chapter. */\n'
 '.nref{text-decoration:none;font-size:.8em;vertical-align:super;line-height:0}\n'
 '.notes{font-size:.9em;color:#555;margin-top:2.4em}\n'
 '.notes hr{border:0;border-top:1px solid #ccc;width:35%;margin:0 0 .9em}\n'
 '.fn p{text-indent:0;margin:.35em 0}\n'
 '.fn a{text-decoration:none;color:#777}\n'+PROOFING_CSS+SCRIPT_CSS)
for m_ in ('publisher-mark.png','publisher-mark-dark.png'):
    shutil.copy(f'{TPL}/OEBPS/images/{m_}', f'{OUT}/OEBPS/images/{m_}')
Image.open(os.path.expanduser('~/Desktop/Owen-MortificationofSin.png')).convert('RGB').save(
    f'{OUT}/OEBPS/images/cover.jpg','JPEG',quality=90,optimize=True,progressive=True)

def page(title, et, cls, inner, bt='bodymatter'):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
      'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n'
      f'<head><title>{html.escape(title)}</title><meta charset="utf-8"/>'
      '<link rel="stylesheet" type="text/css" href="../css/style.css"/></head>\n'
      f'<body epub:type="{bt}"><section epub:type="{et}" class="{cls}">\n{inner}\n</section></body></html>\n')
def E(s, seen=None):
    s=html.escape(s)
    def _ref(m):
        n=int(m.group(1))
        if seen is not None: seen.append(n)
        return (f'<a epub:type="noteref" href="#fn{n}" id="fr{n}" class="nref">'
                f'<sup>{n}</sup></a>')
    s=re.sub(r'\s*⟦N(\d+)⟧', _ref, s)
    s=s.replace(GK0,'<span xml:lang="grc" lang="grc" class="gk">').replace(GK1,'</span>')
    s=s.replace(HB0,'<span xml:lang="hbo" lang="hbo" dir="rtl" class="hb">').replace(HB1,'</span>')
    return s.replace(PH0,'<span class="ph">').replace(PH1,'</span>')
def notes_block(seen):
    """Owen's margin, gathered at the foot of the chapter that refers to it."""
    if not seen: return ''
    return ('\n<section epub:type="endnotes" class="notes"><hr/>\n'+'\n'.join(
      f'<aside epub:type="footnote" id="fn{n}" class="fn">'
      f'<p><a href="#fr{n}">{n}.</a> {E(resolve(totext(NOTES[n-1])))}</p></aside>'
      for n in seen)+'\n</section>')

files=[]
T='The Mortification of Sin in Believers'
_cw,_ch=Image.open(f'{OUT}/OEBPS/images/cover.jpg').size
open(f'{OUT}/OEBPS/text/cover.xhtml','w',encoding='utf-8').write(cover_xhtml(_cw,_ch))
files.append(('cover.xhtml','Cover'))
open(f'{OUT}/OEBPS/text/00-proofing.xhtml','w',encoding='utf-8').write(
    proofing_xhtml(T,'John Owen'))
files.append(('00-proofing.xhtml','Proofing Copy'))
open(f'{OUT}/OEBPS/text/00-title.xhtml','w',encoding='utf-8').write(page(T,'titlepage','titlepage',
 f'<h1>{T}</h1>\n<h2>The Necessity, Nature, and Means of It</h2>\n<p><strong>John Owen</strong></p>\n'
 '<p>The SchriftOhr Edition</p>\n<p>Developed by RFRMDWordLabs, LLC</p>\n'
 '<p>For the benefit of readers, prayerfully, to the glory of God.</p>\n'
 '<p class="publisher-mark"><img src="../images/publisher-mark.png" alt="RFRMD Word Labs, LLC"/></p>','frontmatter'))
files.append(('00-title.xhtml',T))
open(f'{OUT}/OEBPS/text/01-edition-note.xhtml','w',encoding='utf-8').write(page(
 'About This Edition','preamble','preamble','<h2>About This Edition</h2>\n'
 f'<p>This is the SchriftOhr edition of <i>{T}</i>, prepared by RFRMDWordLabs, LLC. '
 'Owen\u2019s text is given as he wrote it \u2014 not modernised, abridged, or rewritten. The '
 'seventeenth-century spelling stands, save that the long <i>\u017f</i> is set as <i>s</i> and words '
 'broken across a line are rejoined.</p>\n'
 '<p>Where the page was damaged past reading, the word is supplied where it can be established '
 'and marked <i>[\u2026]</i> where it cannot.</p>\n'
 '<p>The Greek Owen quotes is set as he quoted it, with how it sounds in brackets after it, '
 'so the word can be read aloud by anyone. One marginal note, Greek alone and past recovery, '
 'is marked <i>[Greek]</i>.</p>\n'
 '<p>The argument standing at the head of each chapter is the printer\u2019s own, as 1668 set it.</p>',
 'frontmatter'))
files.append(('01-edition-note.xhtml','About This Edition'))
if preface:
    open(f'{OUT}/OEBPS/text/02-preface.xhtml','w',encoding='utf-8').write(page(
      'To the Reader','preface','preamble',
      (lambda _s: '<h2>To the Reader</h2>\n'+'\n'.join(f'<p>{E(x,_s)}</p>' for x in
        ([open_cap(preface['paras'][0])]+preface['paras'][1:] if preface['paras'] else []))
       + notes_block(_s))([]),'frontmatter'))
    files.append(('02-preface.xhtml','To the Reader'))
for i,c in enumerate(chapters,1):
    t=f'Chapter {c["num"]}'
    inner=f'<h2>{t}</h2>\n'
    if c['argument']:
        _arg=NOTEREF.sub('', E(c['argument']))     # the head-note takes no note of its own
        inner+=f'<p class="argument">{_arg}</p>\n'
    _ps=list(c['paras'])
    if _ps: _ps[0]=open_cap(_ps[0])          # the printer's opening flourish
    seen=[]
    inner+='\n'.join(f'<p>{E(p, seen)}</p>' for p in _ps)
    inner+=notes_block(seen)
    fn=f'C{i:02d}.xhtml'
    open(f'{OUT}/OEBPS/text/{fn}','w',encoding='utf-8').write(page(t,'chapter','chapter',inner))
    files.append((fn,t))
open(f'{OUT}/OEBPS/text/97-sources.xhtml','w',encoding='utf-8').write(page(
 'Sources and Acknowledgements','preamble','preamble','<h2>Sources and Acknowledgements</h2>\n'
 '<p>John Owen published <i>Of the Mortification of Sin in Believers</i> in 1656; this edition '
 'follows the printing of 1668 (Wing O787; ESTC R214591). Owen died in 1683, and his text has long '
 'been in the public domain.</p>\n'
 '<p>Our text descends from the <i>Early English Books Online Text Creation Partnership</i>, whose '
 'keyers typed it by hand from images of the 1668 pages. The Partnership has waived every right '
 'it holds in that work under the <i>CC0 1.0 Public Domain Dedication</i>. Freely given, and '
 'gratefully used.</p>\n'
 '<p>The arrangement of this edition is the work of RFRMDWordLabs, LLC. No claim is made upon the '
 'text.</p>\n<p><i>Soli Deo gloria.</i></p>','backmatter'))
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
f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid" xml:lang="en-GB">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="uid">urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL,"schriftohr:mortification-of-sin")}</dc:identifier>
    <dc:title>{T}</dc:title>
    <dc:creator id="author">John Owen</dc:creator>
    <meta refines="#author" property="role" scheme="marc:relators">aut</meta>
    <dc:language>en-GB</dc:language>
    <dc:publisher>SchriftOhr / RFRMDWordLabs, LLC</dc:publisher>
    <dc:description>A reading edition of Owen's 1668 treatise, from the EEBO-TCP keyed transcription, set with its chapter arguments and cleared of the scan's lacunae.</dc:description>
    <dc:source>EEBO-TCP A53715 (Wing O787), the 1668 printing, CC0</dc:source>
    <dc:rights>Owen's text is in the public domain.</dc:rights>
    <dc:date>2026-08-22</dc:date>
    <meta property="dcterms:modified">2026-08-22T00:00:00Z</meta>
    <meta name="cover" content="cover-img"/>
  </metadata>
  <manifest>
{chr(10).join(man)}
  </manifest>
  <spine>
{chr(10).join(spine)}
  </spine>
</package>
''')
open(f'{OUT}/META-INF/container.xml','w',encoding='utf-8').write(
 '<?xml version="1.0" encoding="utf-8"?>\n<container version="1.0" '
 'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n  <rootfiles>\n'
 '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
 '  </rootfiles>\n</container>\n')
open(f'{OUT}/mimetype','w').write('application/epub+zip')
name='Owen_John-SchriftOhr_Edition-Mortification_of_Sin.epub'
ep=f'{W}/output/{name}'
if os.path.exists(ep): os.remove(ep)
subprocess.run(['zip','-qX0',ep,'mimetype'],cwd=OUT,check=True)
subprocess.run(['zip','-qXr9',ep,'META-INF','OEBPS'],cwd=OUT,check=True)
print(f'{len(chapters)} chapters + preface · {os.path.getsize(ep)//1024} KB')
