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
import re, html, json, os, unicodedata
import itertools, string

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
    """The context around a gap, normalised the way the built page is.

    ⚠️ These two have to agree. A context left as the file writes it keeps the
    printer's marks — the abbreviation stroke over a vowel, the V-form capital
    U — and neither is a letter, so the fragment beside a gap reads as empty
    and the gap looks like a whole missing word. 'Multi ama_ veritatem' could
    not be matched at all until this was fixed.
    """
    x = re.sub(r'<g ref="char:cmbAbbrStroke">[^<]*</g>(?=m)', 'm', x)
    x = re.sub(r'<g ref="char:cmbAbbrStroke">[^<]*</g>', 'n', x)
    x = re.sub(r'<g ref="char:EOL[^"]*"\s*/?>(?:</g>)?', '', x)
    x = re.sub(r'<g ref="char:V">[^<]*</g>', 'U', x)
    x = re.sub(r'<g ref="char:punc">[^<]*</g>', '', x)
    x = re.sub(r'<g [^>]*>([^<]*)</g>', r'\1', x)
    x = re.sub(r'<[^>]+>', '', x)
    x = html.unescape(x).replace('\u017f', 's').replace('\u01b2', 'U')
    x = unicodedata.normalize('NFC', x)
    return re.sub(r'\s+', ' ', x)

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

def fold(w):
    """Flatten the spellings a printing may vary without changing the word.

    Between 1658 and 1866 the same word is set 'sinne'/'sin', 'wee'/'we',
    'vpon'/'upon', 'mercie'/'mercy'. Folding u/v and i/j together, collapsing
    doubled letters and settling the -ie/-y ending puts them on one form, so a
    stem can be taken from either and still match.
    """
    w = w.lower().replace('\u017f', 's')
    w = re.sub(r'ie$', 'y', w)
    w = w.replace('v', 'u').replace('j', 'i').replace('y', 'i')
    w = re.sub(r'(.)\1+', r'\1', w)
    return w

def stem(w):
    """Enough of a word to survive three centuries of spelling drift:
    'wayes'/'ways', 'mortifie'/'mortify', 'shew'/'show' all share a head."""
    return fold(w)[:4]

def candidates(g, later_words, index, after_index, fits):
    """Every word the later printing offers for this gap, best first.

    One key in one place is brittle: the words before a gap may be mangled in
    the scan, or too few, or the gap may sit at the head of a paragraph. So the
    text is keyed from BOTH sides and at two widths, every match is collected,
    and the word that turns up most often — among those that actually fit the
    letters on the page — is the reading.
    """
    before = norm(g['before'])
    after  = norm(re.sub(r'^[\u2022\s]+', '', g['after']))
    continues = not re.search(r'\s[\u2022 ]*$', g['before'])
    tail_frag = after[0] if (after and not re.match(r'^[\u2022\s]*\s', g['after'])) else ''
    complete = before[:-1] if continues else before
    tail     = after[1:] if tail_frag else after

    found = {}
    def offer(w):
        if w and fits(g, w):
            found[w] = found.get(w, 0) + 1

    for width in (3, 2):
        if len(complete) >= width:
            key = tuple(stem(x) for x in complete[-width:])
            for pos in index.get(key, ())[:80]:
                if pos + 1 < len(later_words):
                    offer(later_words[pos + 1])
        if len(tail) >= width:
            key = tuple(stem(x) for x in tail[:width])
            for pos in after_index.get(key, ())[:80]:
                if pos - 1 >= 0:
                    offer(later_words[pos - 1])
    if not found:
        return []
    return sorted(found, key=lambda w: (fit_rank(g, w), -found[w]))


def collate(g, later_words, index, after_index=None):
    """The single best reading the later printing offers, or None."""
    def _any(_g, _w): return True
    c = candidates(g, later_words, index, after_index or {}, _any)
    return c[0] if c else None


def build_index(words):
    """Key: the stems of three words. Value: where the third of them sits."""
    idx = {}
    for i in range(len(words) - 2):
        idx.setdefault(tuple(stem(w) for w in words[i:i+3]), []).append(i + 2)
        idx.setdefault(tuple(stem(w) for w in words[i:i+2]), []).append(i + 1)
    return idx


def build_after_index(words):
    """The same, keyed on three words and pointing at the FIRST of them, so a
    gap can be read backwards from the words that follow it."""
    idx = {}
    for i in range(len(words) - 2):
        idx.setdefault(tuple(stem(w) for w in words[i:i+3]), []).append(i)
        idx.setdefault(tuple(stem(w) for w in words[i:i+2]), []).append(i)
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


def readings_of(g):
    """The ways this gap's surroundings can be read, likeliest first.

    Flattening the page puts a space between the gap and whatever follows it,
    so the letters after a gap may be the REST OF THE DAMAGED WORD ('app_ar' —
    appear) or an INTACT NEIGHBOUR ('if h_ should' — he). Nothing in the
    flattened text tells the two apart, so both are tried, and the reading that
    makes a word the author actually uses is the one that stands.
    """
    lf, rf = fragments(g)
    # The same space that hides a following fragment hides a preceding one:
    # "Multi aman ⟦⟧ veritatem" is amant, with the gap joined to the word
    # before it. So the word before is offered as a fragment too.
    before = g.get('before', '').replace('\u017f', 's')
    m = re.search(r'([A-Za-z]+)[\s\u2022]*$', before)
    pw = m.group(1) if (m and not lf) else ''
    # Fullest use of the page first. Where nothing survives joined to the gap
    # on the left, the word standing before it is still a better reading than
    # none — "the ham ⟦⟧er" is hammer, not "the ham her".
    pairs = []
    if lf:
        pairs += [(lf, rf), (lf, '')]
    if pw:
        pairs += [(pw, rf), (pw, '')]
    if rf:
        pairs += [('', rf)]
    seen, out = set(), []
    for pair in pairs:
        if pair not in seen and any(pair):
            seen.add(pair); out.append(pair)
    return out


def fit_rank(g, word):
    """Which reading of the surroundings this word satisfies — 0 is the fullest.

    Ranking matters as much as fitting. Where the page reads 'si_s chiefe',
    both 'sits' (using the letters on both sides) and 'is' (using only those
    after) fit; the first uses more of what survived and is the better reading.
    """
    if not word:
        return None
    w = word.lower()
    n = extent_len(g.get('extent'))
    for i, (lf, rf) in enumerate(readings_of(g)):
        lo, hi = lf.lower(), rf.lower()
        if lo and not w.startswith(lo):
            continue
        if hi and not w.endswith(hi):
            continue
        if n:
            if len(w) != len(lo) + n + len(hi):
                continue
        elif len(w) <= len(lo) + len(hi):
            continue
        return i
    return None


def fits(g, word):
    """Does this word fit the letters the page still shows, and the count the
    keyer made of what is missing?"""
    return fit_rank(g, word) is not None


def construct(g, freq, later_word=None, max_letters=3, bigrams=None):
    """Build the word the page had, from the letters it still has.

    The strongest constraint on a damaged word is not a later printing but the
    page itself: the letters standing on either side, and the number the keyer
    counted missing. Filling those in gives a small closed set of candidates —
    26 for one missing letter — and two things choose between them: the book's
    own vocabulary, which is in the author's spelling, and the later printing,
    which read the page we cannot.

    This is what taking the later printing's word wholesale could not do. Its
    'Chrysostom' does not fit a page reading 'Chrysost_me'; but of the 26 words
    that DO fit, only 'Chrysostome' is that word in 1658 dress.
    """
    n = extent_len(g.get('extent'))
    if not n or n > max_letters:
        return None, None
    # Read the page as fully as it can be read first. Only if the fullest
    # reading makes no word the author ever uses is a partial one tried —
    # otherwise 'he' gets seated in "thou hast do_e this", where the letters
    # on both sides plainly say 'done'.
    blocked = False
    for rank, (lf, rf) in enumerate(readings_of(g)):
        word, why, had_known = _construct_one(g, freq, later_word, n, lf, rf,
                                              bigrams, rank, blocked)
        if word:
            return word, why
        if rank == 0 and had_known:
            blocked = True
    return None, None


def _construct_one(g, freq, later_word, n, lf, rf, bigrams, rank=0, blocked=False):
    lo, hi = (lf or '').lower(), (rf or '').lower()
    fits = [lo + ''.join(c) + hi
            for c in itertools.product(string.ascii_lowercase, repeat=n)]
    known = [w for w in fits if freq.get(w)]
    if later_word:
        target = fold(later_word)
        same = [w for w in fits if fold(w) == target]
        if len(same) == 1:
            return _cased(same[0], lf), 'the letters on the page, read as the later printing has it', True
        if same:                                   # several fold alike: the book decides
            best = max(same, key=lambda w: freq.get(w, 0))
            if freq.get(best):
                return _cased(best, lf), 'the letters on the page, and the author\'s own spelling', bool(known)
    # A word standing a few words away is the strongest signal of all: a
    # damaged word often repeats one the author has just used, and a repeated
    # phrase carries its own answer — "migremus hinc, migr_mus hinc".
    # ⚠️ These last three are guesses, not readings, and they are only allowed
    # on the FULLEST use of the page. Let them run on a partial reading and
    # they seat 'he' in "thou hast do_e this", where the letters on both sides
    # plainly say 'done'.
    if rank > 0 and blocked:
        return None, None, bool(known)
    # ⚠️ A reading that throws away letters the page still shows is not a
    # reading. Where 'Ign' stands before the damage, only a printing that read
    # the page may set a word ignoring it — never a guess from the English
    # lexicon, which offered 'that' for Latin 'Ignorat'.
    if rank > 0 and fragments(g)[0] and not lf:
        return None, None, bool(known)
    near = set(norm(g.get('before', '') + ' ' + g.get('after', '')))
    close = [w for w in fits if w in near and len(w) > 2]
    if len(close) == 1:
        return _cased(close[0], lf), 'the letters on the page, and the same word standing beside the gap', bool(known)
    if len(known) == 1:
        return _cased(known[0], lf), 'the letters on the page, and the only word the author uses that fits', bool(known)
    if known and bigrams is not None:
        # ⚠️ Raw frequency is the wrong judge here. 'sin' outnumbers 'sun' in
        # this book many times over, so it wins every s_n gap — including "the
        # body of the S_n", where the page means the sun. What settles it is
        # whether the author ever puts THIS word next to THESE neighbours.
        pre = norm(g['before'])[-1:] or ['']
        post = norm(re.sub(r'^[\u2022\s]+', '', g['after']))[:1] or ['']
        def ctx(w):
            return (bigrams.get((pre[0], w), 0) + bigrams.get((w, post[0]), 0))
        ranked = sorted(known, key=lambda w: (-ctx(w), -freq[w]))
        best, rest = ranked[0], ranked[1:]
        if ctx(best) and (not rest or ctx(best) >= 2 * max(1, ctx(rest[0]))):
            return _cased(best, lf), 'the letters on the page, and the company the author keeps for that word', bool(known)
    return None, None, bool(known)


def _cased(word, lf):
    """Keep the capital the page still shows."""
    if lf and lf[0].isupper():
        return word[0].upper() + word[1:]
    return word


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
    if not fits(g, r):
        g['reading'] = None
        g['source'] = f'rejected — does not fit the letters on the page'
        return g
    # Which way the surroundings read is settled by the reading itself: it
    # absorbs a fragment only where it actually begins or ends with it.
    R = r.lower()
    lf, rf = fragments(g)
    if lf and not R.startswith(lf.lower()):
        lf = ''
    if rf and not (R.endswith(rf.lower()) and len(R) > len(rf)):
        rf = ''
    g['absorb_left']  = bool(lf)
    g['absorb_right'] = bool(rf)
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
