#!/usr/bin/env python3
"""Resolve the <gap> marks in an EEBO-TCP text.

John's rule (2026-08-22): infer from context, and check a later
printing. Never fill silently — every resolution is written to a
ledger that ships with the working files, so any reading can be
challenged later.

A gap that sits inside a word is strongly constrained: the letters on
either side plus the keyer's own letter-count usually leave exactly one
English word. Those we propose automatically. Gaps that swallow whole
words, and Greek or Hebrew left untyped, are listed for a human and for
collation against a later edition.
"""
import re, html, json, os

def lexicon(*texts):
    """The book is its own dictionary — and a better one than a word list.

    A word Owen uses elsewhere is a far likelier reading than a
    curiosity like 'proamnion' that happens to fit the letter count.
    Comparison copies of the same work widen it further.
    """
    freq = {}
    for t in texts:
        for w in re.findall(r"[A-Za-z]{2,}", t.replace('\u017f', 's').lower()):
            freq[w] = freq.get(w, 0) + 1
    return freq

WORDLIST = {w.strip().lower() for w in open('/usr/share/dict/words')} \
           if os.path.exists('/usr/share/dict/words') else set()

def flat(x):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', x)))

def extent_len(extent):
    m = re.match(r'(\d+)\s+letter', extent or '')
    return int(m.group(1)) if m else None

def gaps(xml):
    body = xml[xml.find('<text'):]
    parts = re.split(r'(<gap[^>]*/?>)', body)
    out = []
    for i, p in enumerate(parts):
        if not p.startswith('<gap'):
            continue
        reason = (re.search(r'reason="([^"]*)"', p) or [None, '?'])[1]
        extent = (re.search(r'extent="([^"]*)"', p) or [None, '?'])[1]
        before = flat(parts[i-1])
        after  = flat(parts[i+1]) if i+1 < len(parts) else ''
        out.append({'n': len(out)+1, 'reason': reason, 'extent': extent,
                    'before': before[-70:], 'after': after[:70]})
    return out

def propose(g, freq):
    """Only where the gap sits inside a word and its length is known."""
    if 'foreign' in g['reason'] or extent_len(g['extent']) is None:
        return None
    # A gap only continues a word when no space separates them. Without
    # this the previous word gets glued on and 'all |alse' never resolves.
    b = g['before'].rstrip('\u2022 ')
    head = re.search(r'([A-Za-z]+)$', b) if not re.search(r'\s[\u2022 ]*$', g['before']) else None
    a = re.sub(r'^[\u2022\s]+', '', g['after'])
    tail = re.match(r'([A-Za-z]+)', a) if not re.match(r'^\s', g['after'].lstrip('\u2022')) or True else None
    h = (head.group(1) if head else '').lower().replace('\u017f', 's')
    t = (tail.group(1) if tail else '').lower().replace('\u017f', 's')
    if not h and not t:
        return None
    n = extent_len(g['extent'])
    pat = re.compile(rf'^{re.escape(h)}.{{{n}}}{re.escape(t)}$')
    seen = sorted({w for w in freq if pat.match(w)}, key=lambda w: -freq[w])
    if seen and (len(seen) == 1 or freq[seen[0]] >= 3 * max(1, freq[seen[1]] if len(seen) > 1 else 0)):
        return seen[0]                      # the book's own usage decides
    if seen:
        return {'candidates': [(w, freq[w]) for w in seen[:5]]}
    listed = sorted({w for w in WORDLIST if pat.match(w)})
    return {'candidates': [(w, 0) for w in listed[:5]]} if listed else None

def report(xml_path, out_dir, label, compare=None):
    xml = open(xml_path, encoding='utf-8', errors='ignore').read()
    own = flat(xml[xml.find('<text'):])
    freq = lexicon(own, *[open(c, encoding='utf-8', errors='ignore').read()
                          for c in (compare or [])])
    gs = gaps(xml)
    resolved, review = [], []
    for g in gs:
        p = propose(g, freq)
        if isinstance(p, str):
            g['proposed'] = p
            resolved.append(g)
        else:
            g['candidates'] = p.get('candidates') if isinstance(p, dict) else None
            review.append(g)
    os.makedirs(out_dir, exist_ok=True)
    json.dump({'text': label, 'total': len(gs), 'proposed': len(resolved),
               'for_review': len(review), 'resolved': resolved, 'review': review},
              open(f'{out_dir}/gap-ledger.json', 'w'), indent=2)
    return len(gs), len(resolved), len(review)

if __name__ == '__main__':
    import sys
    print(report(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ''))


# ---------------------------------------------------------------------------
# Collation against a later printing.
#
# Inference from the book's own vocabulary is good but not sufficient: for
# Owen's opening gap it proposed 'provision', and the later printing reads
# 'promotion'. So the second half of John's rule does real work — where a
# later edition can be found, it decides, and the inference is only a
# fallback for readings the later edition does not cover.
# ---------------------------------------------------------------------------

def norm(t):
    return re.sub(r'[^a-z ]', ' ', re.sub(r'\s+', ' ',
                  t.replace('ſ', 's').lower())).split()

def collate(g, later_words, index, window=5):
    """Find this gap's context in the later printing and read what stands there."""
    before = norm(g['before'])[-window:]
    after = norm(re.sub(r'^[•\s]+', '', g['after']))[:2]
    if len(before) < 3:
        return None
    key = tuple(before[-3:])
    for pos in index.get(key, ())[:40]:
        nxt = later_words[pos + 1: pos + 4]
        if not nxt:
            continue
        # the word standing where the gap is; confirm the text resumes as we expect
        if after and after[0] not in ('', None):
            tail = after[0]
            cand = nxt[0]
            if cand.endswith(tail) or tail.endswith(cand) or cand == tail:
                return cand
            if len(nxt) > 1 and nxt[1] == tail:
                return cand
        else:
            return nxt[0]
    return None

def build_index(words):
    idx = {}
    for i in range(len(words) - 2):
        idx.setdefault(tuple(words[i:i+3]), []).append(i + 2)
    return idx
