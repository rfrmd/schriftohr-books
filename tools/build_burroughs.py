import sys, os, re, html, json, shutil, subprocess, uuid
sys.path.insert(0, os.path.expanduser('~/Developer/schriftohr-books/tools'))
from tei_reader import sections, words, open_cap
from PIL import Image
W=os.path.expanduser('~/Desktop/Reformed-Shelf-Working/03-burroughs-rare-jewel')
TPL='/private/tmp/claude-501/-Users-johnwest-Developer-schriftohr/6c0e5e0e-5ab4-4c3b-a6f4-cca64a136103/scratchpad/tpl'
OUT=f'{W}/output/rare-jewel'
led=json.load(open(f'{W}/working/gap-ledger.json'))
gapmap={g['n']: g['reading'] for g in led['final'] if g.get('reading')}
secs=sections(f'{W}/source/A30598-EEBO-TCP-1649-keyed.xml', gapmap)
rj, duty = secs[0], secs[1]

shutil.rmtree(OUT, ignore_errors=True)
for d in ('META-INF','OEBPS/text','OEBPS/css','OEBPS/images'): os.makedirs(f'{OUT}/{d}')
shutil.copy(f'{TPL}/OEBPS/css/style.css', f'{OUT}/OEBPS/css/style.css')
open(f'{OUT}/OEBPS/css/style.css','a').write(
 '\n/* Burroughs preaches in heads and sub-heads; keep his scaffolding visible. */\n'
 'h3{text-align:left;font-size:1em;margin:1.8em 0 .5em;font-weight:600}\n')
for m in ('publisher-mark.png','publisher-mark-dark.png'):
    shutil.copy(f'{TPL}/OEBPS/images/{m}', f'{OUT}/OEBPS/images/{m}')
Image.open(os.path.expanduser('~/Desktop/Burroughs-RareJewel.png')).convert('RGB').save(
    f'{OUT}/OEBPS/images/cover.jpg','JPEG',quality=90,optimize=True,progressive=True)
E=lambda s: html.escape(s)
def page(title, et, cls, inner, bt='bodymatter'):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
      'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n'
      f'<head><title>{E(title)}</title><meta charset="utf-8"/>'
      '<link rel="stylesheet" type="text/css" href="../css/style.css"/></head>\n'
      f'<body epub:type="{bt}"><section epub:type="{et}" class="{cls}">\n{inner}\n</section></body></html>\n')
def render(node, level=3, first=True):
    out=[]
    for i,p in enumerate(node['paras']):
        # A sermon opens with its text and then its exposition, and the
        # flourish can sit on either. FINIS is a closing, not an opening,
        # and keeps its capitals.
        if first and i < 3 and p.strip() != 'FINIS.':
            p = open_cap(p)
        out.append(f'<p>{E(p)}</p>')
    for s in node['subs']:
        if s['head']: out.append(f'<h{level}>{E(s["head"])}</h{level}>')
        out.append(render(s, min(level+1,6)))
    return '\n'.join(out)

T='The Rare Jewel of Christian Contentment'
files=[]
open(f'{OUT}/OEBPS/text/cover.xhtml','w',encoding='utf-8').write(
 '<?xml version="1.0" encoding="utf-8"?>\n<html xmlns="http://www.w3.org/1999/xhtml" '
 'xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="en-GB" lang="en-GB">\n<head><title>Cover</title>'
 '<meta charset="utf-8"/><style>body{margin:0;padding:0}img{max-width:100%;height:auto;display:block;'
 'margin:0 auto}</style></head>\n<body epub:type="frontmatter"><section epub:type="cover">'
 '<img src="../images/cover.jpg" alt="Cover"/></section></body></html>\n')
files.append(('cover.xhtml','Cover'))
open(f'{OUT}/OEBPS/text/00-title.xhtml','w',encoding='utf-8').write(page(T,'titlepage','titlepage',
 f'<h1>{T}</h1>\n<h2>Wherein is shewed the Excellent Temper of a Christian</h2>\n'
 '<p><strong>Jeremiah Burroughs</strong></p>\n<p>The SchriftOhr Edition</p>\n'
 '<p>Developed by RFRMDWordLabs, LLC</p>\n'
 '<p>For the benefit of readers, prayerfully, to the glory of God.</p>\n'
 '<p class="publisher-mark"><img src="../images/publisher-mark.png" alt="RFRMD Word Labs, LLC"/></p>','frontmatter'))
files.append(('00-title.xhtml',T))
open(f'{OUT}/OEBPS/text/01-edition-note.xhtml','w',encoding='utf-8').write(page(
 'About This Edition','preamble','preamble','<h2>About This Edition</h2>\n'
 f'<p>This is the SchriftOhr edition of <i>{T}</i>, prepared by RFRMDWordLabs, LLC. Burroughs’s '
 'text is given as he preached and as 1649 printed it. Nothing has been modernised, abridged, or '
 'rewritten; the seventeenth-century spelling stands, save that the long <i>ſ</i> is set as '
 '<i>s</i> and words broken across a line are rejoined.</p>\n'
 '<p>The text descends from a transcription keyed by hand from the 1649 pages. Where the page '
 'defeated the keyer, the reading has been recovered from the context and checked against a later '
 'printing; every such decision is recorded, and none was made silently. Passages left in Greek are '
 'marked <i>[Greek]</i>, and readings still unsettled <i>[…]</i>, rather than guessed at.</p>\n'
 '<p>The volume of 1649 carried a second work after the Rare Jewel — a sermon on Exodus 14:13, '
 '<i>The Saints’ Duty in Times of Extremity</i>. It is kept here, where its printer put it.</p>',
 'frontmatter'))
files.append(('01-edition-note.xhtml','About This Edition'))

# Sermon I is the work's own opening matter; II-XI are its subsections
_p=list(rj['paras']); _p[0]=open_cap(_p[0]) if _p else ''
inner=f'<h2>Sermon I</h2>\n'+'\n'.join(f'<p>{E(x)}</p>' for x in _p)
open(f'{OUT}/OEBPS/text/S01.xhtml','w',encoding='utf-8').write(page('Sermon I','chapter','chapter',inner))
files.append(('S01.xhtml','Sermon I'))
for i,s in enumerate(rj['subs'], start=2):
    # .title() lowercases roman numerals — 'SERMON II.' became 'Sermon Ii'
    raw=re.sub(r'\.$','', s['head']).strip()
    m=re.match(r'(?i)^sermon\s+([IVXL]+)$', raw)
    title=f'Sermon {m.group(1).upper()}' if m else (raw or f'Sermon {i}')
    fn=f'S{i:02d}.xhtml'
    open(f'{OUT}/OEBPS/text/{fn}','w',encoding='utf-8').write(
        page(title,'chapter','chapter',f'<h2>{E(title)}</h2>\n{render(s)}'))
    files.append((fn,title))
DT="The Saints' Duty in Times of Extremity"
open(f'{OUT}/OEBPS/text/90-saints-duty.xhtml','w',encoding='utf-8').write(
    page(DT,'chapter','chapter',f'<h2>{E(DT)}</h2>\n<p class="argument">A sermon on Exodus 14:13, '
         'printed with the Rare Jewel in 1649.</p>\n'+render(duty)))
files.append(('90-saints-duty.xhtml',DT))
open(f'{OUT}/OEBPS/text/97-sources.xhtml','w',encoding='utf-8').write(page(
 'Sources and Acknowledgements','preamble','preamble','<h2>Sources and Acknowledgements</h2>\n'
 f'<p>Jeremiah Burroughs died in 1646; <i>{T}</i> was printed in 1649 for Peter Cole (Wing B6103; '
 'ESTC R32016), and his text has long been in the public domain.</p>\n'
 '<p>Our text descends from the <i>Early English Books Online Text Creation Partnership</i>, whose '
 'keyers typed it by hand from images of the 1649 pages rather than passing them through a machine. '
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
    <dc:identifier id="uid">urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL,"schriftohr:rare-jewel")}</dc:identifier>
    <dc:title>{T}</dc:title>
    <dc:creator id="author">Jeremiah Burroughs</dc:creator>
    <meta refines="#author" property="role" scheme="marc:relators">aut</meta>
    <dc:language>en-GB</dc:language>
    <dc:publisher>SchriftOhr / RFRMDWordLabs, LLC</dc:publisher>
    <dc:description>A reading edition of Burroughs's sermons on contentment, from the EEBO-TCP keyed transcription of the 1649 printing.</dc:description>
    <dc:source>EEBO-TCP A30598 (Wing B6103), the 1649 printing, CC0</dc:source>
    <dc:rights>Burroughs's text is in the public domain.</dc:rights>
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
name='Burroughs_Jeremiah-SchriftOhr_Edition-Rare_Jewel_of_Christian_Contentment.epub'
ep=f'{W}/output/{name}'
if os.path.exists(ep): os.remove(ep)
subprocess.run(['zip','-qX0',ep,'mimetype'],cwd=OUT,check=True)
subprocess.run(['zip','-qXr9',ep,'META-INF','OEBPS'],cwd=OUT,check=True)
print(f'{len(files)-4} sermons + the bound-in sermon · {os.path.getsize(ep)//1024} KB')
