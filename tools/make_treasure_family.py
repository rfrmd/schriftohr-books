#!/usr/bin/env python3
"""Front and back pages of the Treasure Island Family Edition, after the text ledger.
   make_treasure_family.py BOOK.epub BUILD COVER.jpg CLOSING.jpg"""
import json,re,sys,uuid,zipfile,datetime,os
from xml.sax.saxutils import escape
e,B,COVER,CLOSE=sys.argv[1:5]
z=zipfile.ZipFile(e); names=z.namelist(); infos={i.filename:i for i in z.infolist()}; data={n:z.read(n) for n in names}; z.close()
def one(rx,new,s):
    s,n=re.subn(rx,new,s,flags=re.S); assert n==1,(rx,n); return s
def ed(n,f): data[n]=f(data[n].decode()).encode()
def title(s):
    s=one(r'<p><strong>Robert Louis Stevenson</strong></p>\n(<p>Illustrated by Louis Rhead</p>)\n<p>The SchriftOhr Edition</p>',r'<p><strong>The SchriftOhr Family Edition</strong></p>\n<p>Based on the beloved classic by Robert Louis Stevenson</p>\n\1',s)
    return s.replace('Reissued September 2026','First issued November 2026')
ed('OEBPS/text/00-title.xhtml',title)
def note(s):
    s=one(r'<p>This is the SchriftOhr edition of <em>Treasure Island</em>, prepared by RFRMD Word Labs LLC\.</p>\n<p>Stevenson’s text is given in his own words, complete\. Where a convention of the page would slow a reader or trip the voice, it has been brought up to date; nothing has been rewritten, and his sailors keep their own way of speaking\.',
      '<p>This is the SchriftOhr Family Edition of <em>Treasure Island</em>, prepared by RFRMD Word Labs LLC and based on the beloved classic by Robert Louis Stevenson. Our faithful edition stands beside it on the shelf, for anyone who wants the book as Stevenson wrote it.</p>\n<p>The story and its people are his. The wording is not always his, and we say below where it differs. Where a convention of the page would slow a reader or trip the voice, it has been brought up to date.',s)
    add=('<p>Earlier printings of this book carried words and remarks, about race above all, that were neither edifying to a reader nor kind to the people in the story. In this edition they have been reworded. Where the story could stand as the author told it, it does; where a remark could not be mended, a kinder and more fitting one stands in its place. The pirates keep their oaths and their rough talk, because they are pirates, and they are not men to copy.</p>\n'
         '<p>A few phrases about salvation and prayer now follow historic Christian teaching. Salvation is God’s work from first to last.</p>\n')
    return one(r'(</section></body></html>)',lambda m:add+m.group(1),s)
ed('OEBPS/text/01-edition-note.xhtml',note)
def copy(s):
    s=one(r'<p>This is a <i>SchriftOhr Edition</i>: a book long out of copyright, set again with care — for reading on a page, and for listening to aloud\.','<p>This is a <i>SchriftOhr Family Edition</i>: based on a book long out of copyright, reworded where it needed it, and set again with care for reading on a page and for listening to aloud.',s)
    s=one(r'If something reads wrongly — (a misprint.*?the wrong place) — we would',r'If something reads wrongly (\1), we would',s)
    return one(r'Treasure Island &#183; Robert Louis Stevenson<br/>SchriftOhr Edition &#183; build [0-9.-]+',f'Treasure Island &#183; Robert Louis Stevenson<br/>SchriftOhr Family Edition &#183; build {B}',s)
ed('OEBPS/text/00-proofing.xhtml',copy)
ed('OEBPS/text/97-sources.xhtml',lambda s:one(r'This edition’s arrangement and its treatment of the illustrations are the work of','This Family Edition’s arrangement and rewording, and its treatment of the illustrations, are the work of',s))
def why(s):
    s=one(r'(<p>Its own <b>About This Edition</b>, at the front, says which printing it was set from, what was changed and what was left alone\.</p>)',lambda m:m.group(1)+'\n<p>This book is a <b>SchriftOhr Family Edition</b>: based on the classic, with some words, remarks and teaching reworded.</p>',s)
    s=one(r'<h3>How we keep them faithful</h3>','<h3>How we keep it honest</h3>',s)
    return one(r'<li>Nothing is invented\. Where a page is lost and no copy settles it, the book says so\.</li>\n<li>Nothing is cut\. No chapter is left out and nothing is summarised\.</li>','<li>Where we have changed the author’s words, we say so. No chapter is left out and nothing is summarised.</li>',s)
ed('OEBPS/text/98-why.xhtml',why)
blurb=[b for b in json.load(open('shelf.json'))['books'] if b['id']=='treasure-island'][0]['blurb']
def opf(s):
    s=one(r'(<dc:identifier id="uid">)urn:uuid:[^<]+',lambda m:m.group(1)+'urn:uuid:'+str(uuid.uuid4()),s)
    s=one(r'<dc:title>[^<]+','<dc:title>Treasure Island: Family Edition',s)
    s=one(r'<dc:description>.*?</dc:description>',lambda m:'<dc:description>'+escape('The SchriftOhr Family Edition, based on the beloved classic by Robert Louis Stevenson. '+blurb)+'</dc:description>',s)
    return one(r'(<meta property="dcterms:modified">)[^<]+',lambda m:m.group(1)+datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),s)
ed('OEBPS/content.opf',opf)
data['OEBPS/images/cover.jpg']=open(COVER,'rb').read()
data['OEBPS/images/closing-cover.jpg']=open(CLOSE,'rb').read()
with zipfile.ZipFile(e+'.new','w') as w:
    for n in names: w.writestr(infos[n],data[n],compress_type=zipfile.ZIP_STORED if n=='mimetype' else zipfile.ZIP_DEFLATED)
os.replace(e+'.new',e); print('front set',B,'|',blurb[:60])
