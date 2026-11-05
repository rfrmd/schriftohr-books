import sys,re,zipfile,xml.dom.minidom as X,html
S,E=sys.argv[1:3]
G={'meat':'food of any kind','sensible of':'feeling, keenly aware of','froward':'stubborn, perverse','dispose':'ordering, disposal','physic':'medicine','naught':'worthless, bad','discover':'reveal, make known','discovered':'revealed, made known','nice':'fastidious, hard to please','complacency':'delight','prevented':'anticipated, went before','conversation':'conduct, way of life','beholding to':'beholden to, indebted to','frowardness':'stubbornness, perversity','propriety':'ownership','artificially':'skilfully'}
z=zipfile.ZipFile(S+'/restored.epub');out={};flips=0
def flip(m):
    global flips;flips+=1
    return f'<i>{m.group(1)}</i>: {G[m.group(1)]}.'
for i in z.infolist():
    d=z.read(i.filename)
    if i.filename.endswith('.xhtml'):
        d=re.sub(r'Burroughs wrote <i>([^<]+)</i>\.',flip,d.decode()).encode()
    out[i.filename]=d
s=out['OEBPS/text/96-words.xhtml'].decode().replace('Words Brought Forward','Words That Have Changed')
a=s.index('<p>A few of');b=s.index('</table>')
rows=''.join(f'<tr><td><i>{k}</i></td><td>{v}</td></tr>' for k,v in sorted(G.items()))
s=s[:a]+'<p>A few of Burroughs’s words have changed their meaning since 1649. His word stands in the text, and a lettered note at its first use in each sermon says what it meant. These are the words.</p><table class="words"><tr><th>He wrote</th><th>It meant</th></tr>'+rows+s[b:]
out['OEBPS/text/96-words.xhtml']=s.encode()
t=out['OEBPS/nav.xhtml'].decode();out['OEBPS/nav.xhtml']=t.replace('Words Brought Forward','Words That Have Changed').encode()
s=out['OEBPS/text/01-edition-note.xhtml'].decode()
m=re.search(r'<p>This is the SchriftOhr edition.*?</p>',s,re.S);assert m
new=('<p>This is the SchriftOhr edition of <i>The Rare Jewel of Christian Contentment</i>, the Classic Version, prepared by RFRMD Word Labs LLC. '
'Burroughs’s text is given in his own words, as he preached it and as 1649 printed it, not abridged or rewritten. His old forms stand (thou, hath, doth, saith), and Scripture stands as he printed it. '
'The spelling has been brought up to date, so that the book reads easily and sounds right when read aloud: waies is ways, injoy is enjoy, yeers is years. The punctuation has been made clear, and some long sentences are divided by it; references and abbreviations are written out. '
'Misprints, words the printer dropped or doubled, and a few wrong references have been put right. A few words whose meaning has changed since 1649 are explained in a lettered note; they are listed at the back under Words That Have Changed. '
'The British spellings stand. Words broken across a line are rejoined.</p>')
out['OEBPS/text/01-edition-note.xhtml']=(s[:m.start()]+new+s[m.end():]).encode()
print('notes turned',flips)
for n,d in out.items():
    if n.endswith(('.xhtml','.opf')): X.parseString(d)
with zipfile.ZipFile(E,'w') as w:
    for i in z.infolist(): w.writestr(i,out[i.filename],compress_type=i.compress_type)
# proof: the punctuation is untouched by the restoring
sys.path.insert(0,S)
from align import sections,split_notes
import collections
A=sections(S+'/now.epub');B=sections(E);tot=0
def marks(s):
    s=s[:split_notes(s)];s=re.sub(r'<[^>]+>','',s);s=html.unescape(s)
    return re.findall(r"[,.;:?!()\[\]]",s)
import difflib
for k in sorted(A):
    a,b=marks(A[k]),marks(B[k])
    if a!=b:
        d=[o for o in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes() if o[0]!='equal']
        print(k,'punctuation differs',[(o[0],a[o[1]:o[2]],b[o[3]:o[4]]) for o in d][:12]);tot+=len(d)
print('punctuation differences',tot)
