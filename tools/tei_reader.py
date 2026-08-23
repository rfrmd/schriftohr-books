#!/usr/bin/env python3
"""Read a TEI text the way it is actually built — as a tree.

Regex found Burroughs' 'Rare Jewel' section to be 16,880 words because
it counted the nested Pleas and Directions inside it twice. Divisions
nest; only a parser sees that. This also keeps the seventeenth-century
printer's own furniture: the line-break hyphens that must rejoin words,
and the abbreviation strokes.
"""
import re, html
import xml.etree.ElementTree as ET

TEI = '{http://www.tei-c.org/ns/1.0}'

# The printer's running head in the margin — "2 Remedy.", "3. Device." — set
# there to help a reader find his place. It repeats the sentence beside it, so
# it is furniture, not text, and it is dropped. Everything else in the margin
# (Scripture references, Latin tags, the stories Brooks hangs on the page) is
# the book, and becomes a note.
RUNNING_HEAD = re.compile(
    r'^\s*\d+\s*\.?\s*(Remed(y|ie)|Device|Proposition|Reason|Use|Observation)s?\b\.?\s*$',
    re.I)

def _tag(el):
    return el.tag.replace(TEI, '')

# Private-use marks that survive the flattening and are resolved at the end
# (RD) or turned into markup by the builder (GK/HB).
RD0, RD1 = '\ue020', '\ue021'          # a settled reading, still to absorb its fragments
GK0, GK1 = '\ue000', '\ue001'          # Greek
HB0, HB1 = '\ue002', '\ue003'          # Hebrew
PH0, PH1 = '\ue004', '\ue005'          # how it sounds, set beside it
NR0, NR1 = '\ue006', '\ue007'          # a reference to a note in the margin
STROKE   = '\ue010'                     # the printer's abbreviation stroke

def text_of(el, gapmap=None, counter=None, greek=None, notes=None):
    """Flatten one element to reading text.

    · char:EOLhyphen / EOLunhyphen rejoin a word split across lines —
      they must contribute NOTHING, not a space, or 'principal' becomes
      'princi pal'.
    · <gap> becomes its settled reading, or a visible mark. Its own
      placeholder bullets are NOT text: walking into them printed
      'ababased• sed' where the reading was 'abased'.
    · <pb> is a page turn: a space.
    """
    out = []
    outs = [out]                       # a stack, so a note's words go to the note
    def cur():
        return outs[-1]
    def walk(e):
        t = _tag(e)
        if t == 'g':
            ref = e.get('ref', '')
            if 'EOL' in ref:
                return                   # rejoin the word
            if ref == 'char:punc':
                return                   # a mark the keyers could not identify
            if ref == 'char:V':
                cur().append('U')        # the 17th-c. capital U, cut as a V-form
                return
            if ref == 'char:cmbAbbrStroke':
                cur().append(STROKE)
                return
            cur().append(e.text or '')
            return
        elif t == 'gap':
            n = None
            if counter is not None:
                counter[0] += 1
                n = counter[0]
            if 'foreign' in (e.get('reason') or ''):
                g = (greek or {}).get(str(n))
                if g and g.get('t'):
                    a, z = (HB0, HB1) if g.get('script') == 'hbo' else (GK0, GK1)
                    cur().append(a + g['t'] + z)
                    # The word is no use to a reader who cannot read the script,
                    # and none at all to the ear. Say how it sounds.
                    if g.get('ph'):
                        cur().append(' ' + PH0 + '(' + g['ph'] + ')' + PH1)
                else:
                    cur().append('[Greek]')
            else:
                r = (gapmap or {}).get(n)
                cur().append(RD0 + r + RD1 if r else '[…]')
            return                        # never walk into the placeholder
        elif t == 'pb':
            cur().append(' ')
            return
        elif t == 'note':
            # The note's words belong to the note, not to the sentence it sits
            # beside. Its gaps still count, so gap numbering stays in document
            # order; only the text is diverted.
            buf = []
            outs.append(buf)
            if e.text:
                buf.append(e.text)
            for kid in e:
                walk(kid)
                if kid.tail:
                    buf.append(kid.tail)
            outs.pop()
            txt = _settle(''.join(buf))
            if notes is not None and txt and not RUNNING_HEAD.match(txt):
                notes.append(txt)
                cur().append(NR0 + str(len(notes)) + NR1)
            return
        else:
            if e.text:
                cur().append(e.text)
        for kid in e:
            walk(kid)
            if kid.tail:
                cur().append(kid.tail)
    if el.text:
        out.append(el.text)
    for kid in el:
        walk(kid)
        if kid.tail:
            out.append(kid.tail)
    return _settle(''.join(out))

def _settle(s):
    """Finish a flattened run: expand the printer's marks, seat the readings."""
    s = html.unescape(s).replace('ſ', 's')
    # The stroke over a vowel stands for a following n — or m where the word
    # wants one (cōmit = commit). The book's own spelling settles every case:
    # mannage 15/1, manner 33/1, condition 290, than 288, commit 5.
    s = re.sub(STROKE + '(?=m)', 'm', s)
    s = s.replace(STROKE, 'n')
    # A settled reading is the WHOLE word. It absorbs the fragments the damage
    # left directly beside it — and nothing else, since an intact neighbour is
    # always separated by a space.
    s = re.sub(r'[A-Za-z]*' + RD0 + r'(.*?)' + RD1 + r'[A-Za-z]*',
               lambda m: m.group(1), s)
    return re.sub(r'\s+', ' ', s).strip()

def sections(xml_path, gapmap=None, greek=None, notes=None, want_front=False):
    """Top-level divisions of <body>, each with its nested subsections.

    ⚠️ Gap numbering runs from <text>, not from <body> — the ledger is built by
    reading the raw file, and its first gap is the first in the whole text.
    Brooks has ten in his front matter, so starting the count at <body> put
    every reading in the book ten places out: 'an easie work' came out as
    'Eusebius easie work'.
    """
    root = ET.parse(xml_path).getroot()
    text = root.find(f'.//{TEI}text') or root
    body = root.find(f'.//{TEI}body')
    counter = [0]
    front_secs = []
    # count gaps in document order across the WHOLE text, so numbering
    # matches the ledger built from the raw file
    def collect(el, depth=0):
        node = {'head': '', 'argument': '', 'paras': [], 'subs': []}
        for kid in el:
            t = _tag(kid)
            if t == 'head' and not node['head']:
                node['head'] = text_of(kid, gapmap, counter, greek, notes)
            elif t == 'argument':
                node['argument'] = text_of(kid, gapmap, counter, greek, notes)
            elif t in ('p', 'lg', 'l', 'q'):
                s = text_of(kid, gapmap, counter, greek, notes)
                if s:
                    node['paras'].append(s)
            elif t.startswith('div'):
                node['subs'].append(collect(kid, depth + 1))
            elif t in ('list', 'item', 'opener', 'closer', 'trailer', 'label', 'byline'):
                s = text_of(kid, gapmap, counter, greek, notes)
                if s:
                    node['paras'].append(s)
        return node
    # walk <front> first so its gaps are counted, keeping the numbering in
    # step with the ledger; keep its divisions only if the caller wants them
    for part in text:
        t = _tag(part)
        if t == 'front':
            front_secs = [collect(d) for d in part if _tag(d).startswith('div')]
        elif t == 'body':
            out = [collect(d) for d in part if _tag(d).startswith('div')]
        elif t == 'back':
            for d in part:
                if _tag(d).startswith('div'):
                    collect(d)                 # counted, not returned
    return (front_secs, out) if want_front else out

def words(node):
    n = sum(len(p.split()) for p in node['paras'])
    return n + sum(words(s) for s in node['subs'])


def open_cap(text):
    """Undo the printer's opening flourish.

    A seventeenth-century chapter begins with a large initial and the
    next letter or two set to match it, which a transcription renders
    as 'THat', 'HAving', 'EIghthly' — or the whole first word in
    capitals, 'THE', 'NOW'. Both are the same convention, and both look
    like errors on a screen. Reduce the first word to ordinary
    capitalisation; the flourish belongs to the page, not the text.

    Only ever applied to the FIRST word of an opening paragraph.
    """
    m = re.match(r'([A-Z]{2,})([a-z]*)(?=\b)', text)
    if not m:
        return text
    word = m.group(0)
    if len(word) < 2:
        return text
    fixed = word[0] + word[1:].lower()
    return fixed + text[m.end():]
