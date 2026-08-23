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

def stem(w):
    """Enough of a word to survive three centuries of spelling drift:
    'wayes'/'ways', 'mortifie'/'mortify', 'shew'/'show' all share a head."""
    return w[:4]

def collate(g, later_words, index):
    """Read what the later printing has where this gap stands.

    Keyed on word stems, because exact keys do not survive the drift
    between a 1668 printing and a modern one.

    ⚠️ Two traps, both of which produced wrong readings before:
      · The word carrying the gap may be split ("pro|on"). Its leading
        fragment is NOT a word — keying on it means 'pro' never matches
        'prom', and the gap that proves this whole method (promotion)
        goes unread. Build the key from complete words only.
      · The answer is then always the word AFTER the key, and where the
        gap continues a word that answer must start with the fragment.
    """
    before = norm(g['before'])
    after = norm(re.sub(r'^[\u2022\s]+', '', g['after']))
    continues = not re.search(r'\s[\u2022 ]*$', g['before'])
    frag = before[-1] if continues and before else ''
    complete = before[:-1] if continues else before
    if len(complete) < 3:
        return None
    key = tuple(stem(w) for w in complete[-3:])
    for pos in index.get(key, ())[:60]:
        at = pos + 1
        if at >= len(later_words):
            continue
        cand = later_words[at]
        if frag and not cand.startswith(frag[:3]):
            continue
        if frag and len(cand) <= len(frag):
            continue
        nxt = later_words[at + 1] if at + 1 < len(later_words) else ''
        if after and not (stem(nxt) == stem(after[0]) or cand.endswith(after[0])):
            continue
        return cand
    return None

def build_index(words):
    idx = {}
    for i in range(len(words) - 2):
        idx.setdefault(tuple(stem(w) for w in words[i:i+3]), []).append(i + 2)
    return idx


def _edit(a, b):
    """Levenshtein distance — small and exact, no dependency."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j-1] + 1, prev[j-1] + (ca != cb)))
        prev = cur
    return prev[-1]


def decide(inferred, later):
    """Which reading stands, when the two methods differ.

    The later printing normally wins — it read the page we cannot. But
    not when the only difference is that a modern editor respelled the
    word: this is a 1668 text, so 'wayes' stands and 'ways' does not.
    """
    if not later:
        return inferred, 'inferred from the text'
    if not inferred:
        return later, 'later printing'
    if inferred == later:
        return inferred, 'both agree'
    a, b = inferred, later
    # "Respelling" means ONE letter's difference — wayes/ways. It does not
    # mean sharing a prefix: provision and promotion share 'pro' and are
    # different words, and treating them as variants kept the wrong reading.
    if _edit(a, b) <= 1 and a[:2] == b[:2]:
        return inferred, 'later printing modernised the spelling; period form kept'
    return later, 'later printing (inference differed)'



def fragments(g):
    """The letters the damage left standing on either side of a gap.

    Returned as (left, right) — either may be ''. A fragment counts only
    when it is joined to the gap: a word with a space between it and the
    damage is an intact neighbour, not a fragment.
    """
    before = g.get('before', '').replace('ſ', 's')
    after  = g.get('after',  '').replace('ſ', 's')
    lf = ''
    if not re.search(r'\s[\u2022\s]*$', before):
        m = re.search(r'([A-Za-z]+)$', before)
        lf = m.group(1) if m else ''
    m = re.match(r'^[\u2022\s]*([A-Za-z]+)', after)
    rf = m.group(1) if m else ''
    return lf, rf


def validate(g):
    """A settled reading has to fit the letters still on the page.

    The collator matches on stems, so it can hand back a word that does not
    actually continue the fragment — 'curistas' where the page reads
    'currist‸'. A reading that cannot be reconciled with the surviving
    letters is not a reading, and the gap stays marked.

    It also records which side the reading may absorb. 'but' continues 'bu'
    but does not run on into 'then': the page reads 'but then', two words,
    and absorbing both would have swallowed one of them.
    """
    r = g.get('reading')
    if not r:
        return g
    lf, rf = fragments(g)
    R = r.lower()
    if lf and not R.startswith(lf.lower()):
        g['reading'] = None
        g['source'] = f'rejected — does not continue "{lf}"'
        return g
    g['absorb_left']  = bool(lf)
    g['absorb_right'] = bool(rf) and R.endswith(rf.lower()) and len(R) > len(rf)
    # The page's own capital survives in the fragment; keep it. Where no
    # fragment survives, an opening bracket or a full stop says the word
    # began a name or a sentence.
    if (lf and lf[0].isupper()) or \
       (not lf and re.search(r'[.?!(\u201c"]\s*[\u2022\s]*$', g.get('before', ''))):
        g['reading'] = r[0].upper() + r[1:]
    return g


def apply_readings(xml, ledger_final, unresolved_mark='▫'):
    """Substitute settled readings into the text.

    Gaps arrive in document order, so they map onto the split in order.
    Where a gap continues a word, the fragment on either side is already
    part of the reading, so the fragments are consumed with it.
    """
    body_at = xml.find('<text')
    head, body = xml[:body_at], xml[body_at:]
    parts = re.split(r'(<gap[^>]*/?>)', body)
    readings = {g['n']: g for g in ledger_final}
    n = 0
    out = [parts[0]]
    for i in range(1, len(parts), 2):
        n += 1
        g = readings.get(n)
        nxt = parts[i+1] if i+1 < len(parts) else ''
        if g and g.get('reading'):
            # drop the fragment already spoken for, on both sides
            if not re.search(r'\s[• ]*$', flat(out[-1])):
                out[-1] = re.sub(r'[A-Za-z]+$', '', out[-1].rstrip('• '))
            nxt = re.sub(r'^[•\s]*[A-Za-z]+', '', nxt, count=1) \
                  if re.match(r'^[•\s]*[A-Za-z]', nxt) else nxt
            out.append(g['reading'])
        else:
            out.append(unresolved_mark)
        out.append(nxt)
    return head + ''.join(out)
