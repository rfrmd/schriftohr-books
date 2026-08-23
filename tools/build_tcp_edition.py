import re, html, json, os, sys, shutil, subprocess, uuid
sys.path.insert(0, os.path.expanduser('~/Developer/schriftohr-books/tools'))
from PIL import Image
from tei_reader import open_cap
W=os.path.expanduser('~/Desktop/Reformed-Shelf-Working/02-owen-mortification')
TPL='/private/tmp/claude-501/-Users-johnwest-Developer-schriftohr/6c0e5e0e-5ab4-4c3b-a6f4-cca64a136103/scratchpad/tpl'
OUT=f'{W}/output/mortification-of-sin'
xml=open(f'{W}/source/A53715-EEBO-TCP-1668-keyed.xml',encoding='utf-8',errors='ignore').read()
led=json.load(open(f'{W}/working/gap-ledger.json'))
readings={g['n']: g['reading'] for g in led['final'] if g.get('reading')}

body=xml[xml.find('<text'):]
cnt=[0]
body=re.sub(r'<gap[^>]*/?>', lambda m: (cnt.__setitem__(0,cnt[0]+1) or f'⟦G{cnt[0]}⟧'), body)

def totext(x):
    # An end-of-line hyphen must REJOIN the word, not split it: turning
    # this tag into a space produced "princi pal".
    x=re.sub(r'<g ref="char:EOLhyphen"\s*/?>', '', x)
    x=re.sub(r'<g [^>]*/?>', '', x)
    x=re.sub(r'<pb[^>]*/?>',' ', x); x=re.sub(r'<[^>]+>',' ', x)
    return re.sub(r'\s+',' ', html.unescape(x).replace('ſ','s')).strip()

def resolve(t):
    t=re.sub(r'([A-Za-z]*)\s*⟦G(\d+)⟧[•\s]*([A-Za-z]*)',
             lambda m: readings.get(int(m.group(2))) or (m.group(1)+'[…]'+m.group(3)), t)
    t=re.sub(r'⟦G(\d+)⟧', lambda m: readings.get(int(m.group(1))) or '[…]', t)
    t=t.replace('•','')
    t=re.sub(r'〈[^〉]*〉','[Greek]', t)
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
 '          font-size:.94em;border-left:2px solid #bbb;padding-left:.8em}\n')
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
E=lambda s: html.escape(s)
files=[]
open(f'{OUT}/OEBPS/text/cover.xhtml','w',encoding='utf-8').write(
 '<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
 'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n<head><title>Cover</title>'
 '<meta charset="utf-8"/><style>body{margin:0;padding:0}img{max-width:100%;height:auto;display:block;'
 'margin:0 auto}</style></head>\n<body epub:type="frontmatter"><section epub:type="cover">'
 '<img src="../images/cover.jpg" alt="Cover"/></section></body></html>\n')
files.append(('cover.xhtml','Cover'))
T='The Mortification of Sin in Believers'
open(f'{OUT}/OEBPS/text/00-title.xhtml','w',encoding='utf-8').write(page(T,'titlepage','titlepage',
 f'<h1>{T}</h1>\n<h2>The Necessity, Nature, and Means of It</h2>\n<p><strong>John Owen</strong></p>\n'
 '<p>The SchriftOhr Edition</p>\n<p>Developed by RFRMDWordLabs, LLC</p>\n'
 '<p>For the benefit of readers, prayerfully, to the glory of God.</p>\n'
 '<p class="publisher-mark"><img src="../images/publisher-mark.png" alt="RFRMD Word Labs, LLC"/></p>','frontmatter'))
files.append(('00-title.xhtml',T))
open(f'{OUT}/OEBPS/text/01-edition-note.xhtml','w',encoding='utf-8').write(page(
 'About This Edition','preamble','preamble','<h2>About This Edition</h2>\n'
 f'<p>This is the SchriftOhr edition of <i>{T}</i>, prepared by RFRMDWordLabs, LLC. '
 'Owen’s text is given as he wrote it. Nothing has been modernised, abridged, or rewritten; '
 'the seventeenth-century spelling stands, save that the long <i>ſ</i> is set as <i>s</i>.</p>\n'
 '<p>The text descends from a transcription keyed by hand from the 1668 printing. Where the page '
 'defeated the keyer, the reading has been recovered from the context and checked against a later '
 'printing, and every such decision is recorded — none was made silently. Passages the keyers left '
 'in Greek are marked <i>[Greek]</i>, and the few readings still unsettled are marked '
 '<i>[…]</i> rather than guessed at.</p>\n'
 '<p>The argument standing at the head of each chapter is the printer’s own, as 1668 set it.</p>',
 'frontmatter'))
files.append(('01-edition-note.xhtml','About This Edition'))
if preface:
    open(f'{OUT}/OEBPS/text/02-preface.xhtml','w',encoding='utf-8').write(page(
      'To the Reader','preface','preamble',
      '<h2>To the Reader</h2>\n'+'\n'.join(f'<p>{E(x)}</p>' for x in
        ([open_cap(preface['paras'][0])]+preface['paras'][1:] if preface['paras'] else [])),'frontmatter'))
    files.append(('02-preface.xhtml','To the Reader'))
for i,c in enumerate(chapters,1):
    t=f'Chapter {c["num"]}'
    inner=f'<h2>{t}</h2>\n'
    if c['argument']: inner+=f'<p class="argument">{E(c["argument"])}</p>\n'
    _ps=list(c['paras'])
    if _ps: _ps[0]=open_cap(_ps[0])          # the printer's opening flourish
    inner+='\n'.join(f'<p>{E(p)}</p>' for p in _ps)
    fn=f'C{i:02d}.xhtml'
    open(f'{OUT}/OEBPS/text/{fn}','w',encoding='utf-8').write(page(t,'chapter','chapter',inner))
    files.append((fn,t))
open(f'{OUT}/OEBPS/text/97-sources.xhtml','w',encoding='utf-8').write(page(
 'Sources and Acknowledgements','preamble','preamble','<h2>Sources and Acknowledgements</h2>\n'
 '<p>John Owen published <i>Of the Mortification of Sin in Believers</i> in 1656; this edition '
 'follows the printing of 1668 (Wing O787; ESTC R214591). Owen died in 1683, and his text has long '
 'been in the public domain.</p>\n'
 '<p>Our text descends from the <i>Early English Books Online Text Creation Partnership</i>, whose '
 'keyers typed it by hand from images of the 1668 pages rather than passing them through a machine. '
 'The Partnership has waived every right it holds in that work under the <i>CC0 1.0 Public Domain '
 'Dedication</i>. Freely given, and gratefully used.</p>\n'
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
