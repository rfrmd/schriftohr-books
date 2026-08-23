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

def _tag(el):
    return el.tag.replace(TEI, '')

def text_of(el, gapmap=None, counter=None):
    """Flatten one element to reading text.

    · char:EOLhyphen / EOLunhyphen rejoin a word split across lines —
      they must contribute NOTHING, not a space, or 'principal' becomes
      'princi pal'.
    · <gap> becomes its settled reading, or a visible mark.
    · <pb> is a page turn: a space.
    """
    out = []
    def walk(e):
        t = _tag(e)
        if t == 'g':
            ref = e.get('ref', '')
            if 'EOL' in ref:
                pass                     # rejoin the word
            elif ref == 'char:punc':
                out.append('·')
            else:
                out.append(e.text or '')
        elif t == 'gap':
            if counter is not None:
                counter[0] += 1
                r = (gapmap or {}).get(counter[0])
                out.append(r if r else ('[Greek]' if 'foreign' in (e.get('reason') or '')
                                        else '[…]'))
            else:
                out.append('[…]')
        elif t == 'pb':
            out.append(' ')
        elif t == 'note':
            pass                          # marginal notes handled separately
        else:
            if e.text:
                out.append(e.text)
        for kid in e:
            walk(kid)
            if kid.tail:
                out.append(kid.tail)
    if el.text:
        out.append(el.text)
    for kid in el:
        walk(kid)
        if kid.tail:
            out.append(kid.tail)
    s = html.unescape(''.join(out)).replace('ſ', 's')
    return re.sub(r'\s+', ' ', s).strip()

def sections(xml_path, gapmap=None):
    """Top-level divisions of <body>, each with its nested subsections."""
    root = ET.parse(xml_path).getroot()
    body = root.find(f'.//{TEI}body')
    counter = [0]
    # count gaps in document order across the WHOLE text, so numbering
    # matches the ledger built from the raw file
    def collect(el, depth=0):
        node = {'head': '', 'argument': '', 'paras': [], 'subs': []}
        for kid in el:
            t = _tag(kid)
            if t == 'head' and not node['head']:
                node['head'] = text_of(kid, gapmap, counter)
            elif t == 'argument':
                node['argument'] = text_of(kid, gapmap, counter)
            elif t in ('p', 'lg', 'l', 'q'):
                s = text_of(kid, gapmap, counter)
                if s:
                    node['paras'].append(s)
            elif t.startswith('div'):
                node['subs'].append(collect(kid, depth + 1))
            elif t in ('list', 'item', 'opener', 'closer', 'trailer', 'label', 'byline'):
                s = text_of(kid, gapmap, counter)
                if s:
                    node['paras'].append(s)
        return node
    return [collect(d) for d in body if _tag(d).startswith('div')]

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
