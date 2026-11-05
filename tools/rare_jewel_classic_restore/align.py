import zipfile,re,html,difflib
MAPF='/Volumes/data/Developer/schriftohr-books/books/rare-jewel-of-christian-contentment/spelling-map.tsv'
M={}
for l in open(MAPF,encoding='utf8'):
    if l.startswith('#') or not l.strip(): continue
    a,b=l.rstrip('\n').split('\t');M[a]=b
SKIP=re.compile(r'<(span|i|b)\b[^>]*class="(?:gk|hb|ph)"[^>]*>.*?</\1>|<a\b[^>]*noteref.*?</a>|<sup\b.*?</sup>|<[^>]+>|&[#\w]+;',re.S)
W=re.compile(r"[A-Za-z][A-Za-z’']*")
def sections(p):
    z=zipfile.ZipFile(p);o={}
    for n in z.namelist():
        b=n.split('/')[-1]
        if re.match(r'(S\d\d|02-to|90-).*\.xhtml',b): o[b]=z.read(n).decode()
    return o
def split_notes(s):
    "body end: where the word-notes block starts, if any"
    m=re.search(r'<(section|aside|div)\b[^>]*(?:wnotes|footnotes|endnotes|word-?notes)[^>]*>',s)
    return m.start() if m else len(s)
def tokens(s,end=None):
    end=len(s) if end is None else end
    t=[];pos=0
    for m in SKIP.finditer(s,0,end):
        for w in W.finditer(s,pos,m.start()): t.append((w.group(),w.start(),w.end()))
        pos=m.end()
    for w in W.finditer(s,pos,end): t.append((w.group(),w.start(),w.end()))
    return t
def norm(x):
    x=x.lower().replace("'", '’')
    return M.get(x.replace('’',"'"),x).lower().replace("'", '’')
def ops(old,new):
    a=[norm(x[0]) for x in old];b=[x[0].lower().replace("'", '’') for x in new]
    return a,b,[o for o in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes() if o[0]!='equal']
