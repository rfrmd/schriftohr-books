import sys,re,json,collections,zipfile
sys.path.insert(0,sys.argv[1]);from align import *
S=sys.argv[1]
FORM=set('thou thee thy thine ye hath hast doth dost doest saith art wilt shalt canst wert wast hadst hadest didst didest unto whence whither wherefore wouldest shouldest couldest mightest mightst mayest beest'.split())
SHIFT=set('sensible complacency discover discovered frowardness froward conversation prevented artificially dispose naught nice physic meat propriety beholding'.split())
KEEP={'thy : they','ye : eye','darkneth : darkeneth','yeeldeth : yieldeth','thy self : thyself','least : most'}
H={'thou canst not : you cannot':'thou canst not','thy self : yourself':'thyself','thy self thy : yourself your':'thyself thy',
'gods dispose : god’s ordering':'God’s dispose','gods dispose : god’s disposal':'God’s dispose','unto gods dispose : to god’s ordering':'unto God’s dispose',
'hath it s : has its':'hath its','hath it s : has it’s':'hath it’s','hath al : has all':'hath all','hath call d : has called':'hath called','hath blest : has blessed':'hath blessed','hath gods : has god’s':'hath God’s',
'hath : which has':'which hath','thee there s : you there’s':'thee there’s','thee blest : you blessed':'thee blessed','thee object : you objection':'thee Objection',
'thy hearts : your heart’s':'thy heart’s','thy days : your day’s':'thy day’s','thy son : your sin':'thy sin','unto ans : to answer':'unto Answer','ans thou hast : answer you have':'Answer thou hast','unto them : to you':'unto thee',
'saith ely : says eli':'saith Eli','saith naamans : says naaman’s':'saith Naaman’s','saith phil : says philippians':'saith Philippians','saith saith : says':'saith','possible saith : possibly says':'possibly saith','parillus saith : farellus says':'Farellus saith','our selves saith : ourselves says':'ourselves saith',
'dishonourable unto : dishonourably to':'dishonourably unto','til thou wilt : till you will':'till thou wilt','every thing hath : everything has':'everything hath','in keeper hath : innkeeper has':'innkeeper hath','meals meat : meal’s food':'meal’s meat','art : and are':'and art',
'thou saiest : you say':'thou sayest','thou saiest thou canst not : you say you cannot':'thou sayest thou canst not','thou injoyest : you enjoy':'thou enjoyest','rejoycest : rejoice':'rejoicest','can st not thou : cannot you':'canst not thou',
'faith : says':'saith','a forehand : beforehand':'aforehand','thou : are you':'art thou','bear : bore':'bare','swear : swore':'sware','eat : ate':'eat','discover : find out':'discover',
'know : do':'Know',' : know':'','cannot : can':'Cannot',' : not':'','gives : does not give':'gives',' : do not':'',' : do you':'',
'not : ':'not','you : ':'you','he : ':'he','it : ':'it','they : ':'they','she : ':'she','in : ':'in','of : ':'of','and : ':'and','though : ':'though','who : ':'who','with : ':'with',
'be : is':'be','it s : is':'it’s','his : the':'his','i : they':'I','in : into':'in','scriptures : scripture':'Scriptures','disposed : disposes':'disposed',
'viz : that is':'viz','nylus : nile':'Nilus','catched : caught':'catched','strucken : struck':'strucken','tentation : temptation':'tentation','unsensible : insensible':'unsensible','unconstant : inconstant':'unconstant','learnedst : most learned':'learnedst','discontentedst : most discontented':'discontentedst','cheerily : cheery':'cheerly',
'hath saith : has says':'hath saith','thee saith : you says':'thee saith','thee doth : you does':'thee doth','hath discovered : has revealed':'hath discovered','hath artificially : has skilfully':'hath artificially','physic doth : medicine does':'physic doth','naught thou shouldest : worthless you should':'naught thou shouldest','unto thee : to you':'unto thee','thy dispose : your disposal':'thy dispose','buyest thy meat : buy your food':'buyest thy meat'}
ST={'do':'dost','did':'didst','had':'hadst','could':'couldst','would':'wouldst','can':'canst','should':'shouldst'}
def isform(w,newj):
    return w in FORM or w in SHIFT or (re.fullmatch(r'[a-z]{2,}eth',w) is not None) or (re.fullmatch(r'[a-z]{2,}e?st',w) is not None and w not in ('first','must','just','least','most','blest','curst','possest','priest','profest','quest','roast','tost','best','rest','st','east','midst','last','past','worst','lest','against') and newj!=w)
def decide(key,a,b):
    if key in KEEP: return None
    if key in H: return H[key]
    if key=='an : a' and False: pass
    if a and all(isform(w,' '.join(b)) for w in a): return ' '.join(a)
    return None
def run(src,dst,log):
    z=zipfile.ZipFile(src);out={};flag=[];rows=[]
    old=sections(S+'/before-modern.epub')
    for name in z.namelist():
        base=name.split('/')[-1]
        if base not in old: continue
        s=z.read(name).decode();e=split_notes(s)
        o=tokens(old[base],split_notes(old[base]));n=tokens(s,e)
        a,b,O=ops(o,n);ed=[]
        for t,i,j,x,y in O:
            oa=a[i:j];nb=b[x:y];key=' '.join(oa)+' : '+' '.join(nb)
            if oa[:1]==['st']:
                p=n[x-1][0].lower()
                if p not in ST: flag.append((base,key,'prev '+p));continue
                w=ST[p]; 
                if n[x-1][0][0].isupper(): w=w.capitalize()
                rest=' '.join(oa[1:])
                ed.append((n[x-1][1],n[x-1][2],w))
                if rest:
                    ed.append((n[x][1],n[y-1][2],rest))
                rows.append((base,key,w+(' '+rest if rest else '')));continue
            if key=='you : ' and n[x-1][0].lower()=='tender': continue   # 'tender you' stays corrected
            if key=='an : a' and n[x+1][0].lower()=='hundred': r='an'
            else: r=decide(key,oa,nb)
            if r is None: continue
            rows.append((base,key,r))
            if x==y:   # his word was dropped: put it back where it stood
                gap=old[base][o[i-1][2]:o[i][1]]
                if re.fullmatch(r'\s+',gap): ed.append((n[x-1][2],n[x-1][2],' '+r))
                else: ed.append((n[x][1],n[x][1],r+' '))
                continue
            st,en=n[x][1],n[y-1][2]
            if r=='':   # our added word comes out, with its space
                if s[en:en+1]==' ': en+=1
                ed.append((st,en,''));continue
            gaps=[s[n[q][2]:n[q+1][1]] for q in range(x,y-1)]
            if any(g.strip() for g in gaps):   # punctuation or markup between the words stays exactly as it is
                ws=r.split(' ')
                if len(ws)!=y-x: flag.append((base,key,'gap, count: '+repr(gaps)));continue
                for q,wd in zip(n[x:y],ws):
                    ed.append((q[1],q[2],wd.capitalize() if q[0][0].isupper() and wd[0].islower() else wd))
                continue
            if n[x][0][0].isupper() and r[0].islower(): r=r[0].upper()+r[1:]
            ed.append((st,en,r))
        for st,en,r in sorted(ed,reverse=True): s=s[:st]+r+s[en:]
        s=s.replace('viz, The','viz. The').replace('viz., The','viz. The')
        out[name]=s.encode()
    with zipfile.ZipFile(dst,'w') as w:
        for i in z.infolist():
            w.writestr(i,out.get(i.filename,z.read(i.filename)),compress_type=i.compress_type)
    return rows,flag
rows,flag=run(S+'/now.epub',S+'/restored.epub',None)
print('restored sites',len(rows),'flagged',len(flag))
for f in flag: print(f)
with open(S+'/restore-log.tsv','w',encoding='utf8') as f:
    for r in rows: f.write('\t'.join(r)+'\n')
# proof: what still differs from the 1649 words
old=sections(S+'/before-modern.epub');new=sections(S+'/restored.epub')
c=collections.Counter();bad=collections.Counter()
for k in sorted(new):
    o=tokens(old[k],split_notes(old[k]));n=tokens(new[k],split_notes(new[k]))
    a,b,O=ops(o,n)
    for t,i,j,x,y in O:
        key=' '.join(a[i:j])+' : '+' '.join(b[x:y]);c[key]+=1
        if any(w in FORM or w in SHIFT or re.fullmatch(r'[a-z]{2,}eth',w) for w in a[i:j]): bad[key]+=1
print('remaining differences',sum(c.values()),'distinct',len(c));print('still touching a form word:',bad.most_common(60))
open(S+'/residual.txt','w',encoding='utf8').write('\n'.join(f'{m}\t{k}' for k,m in c.most_common()))
