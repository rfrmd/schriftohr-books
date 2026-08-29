#!/usr/bin/env python3
"""Settle the disagreements a rule can settle, and say why for each one.

Every rule here is conservative and reversible: it writes a decision AND the
reason, so a decision can be argued with later. Anything a rule cannot reach is
left for a person — which is the point. A tool that guesses to look helpful
would put errors into the book with no record that a guess was made.

    auto_decide.py --ledger disagreements.tsv --out decisions-auto.tsv \\
                   [--residual residual.tsv]
"""

import argparse
import csv
import pathlib
import re
import sys

DICT = pathlib.Path('/usr/share/dict/words')
SINGLE = {'a', 'i', 'o'}
VOCAB = ({w.strip().lower() for w in DICT.open() if w.strip()} if DICT.exists() else set())


def is_english(phrase):
    ws = [w.strip("'") for w in re.findall(r"[A-Za-z']+", phrase.lower())]
    ws = [w for w in ws if w]
    if not ws:
        return False
    return all((w in SINGLE) if len(w) == 1 else (w in VOCAB) for w in ws)


# Words this book uses that a general dictionary does not know. Without these,
# the "only one side is English" rule silently favours the wrong witness.
BOOK_WORDS = {
    'holmes', 'watson', 'lestrade', 'baker', 'sherlock', 'moriarty', 'mycroft',
    'boscombe', 'mccarthy', 'turner', 'openshaw', 'roylott', 'stoner', 'rucastle',
    'hunter', 'ryder', 'horner', 'baynes', 'hosmer', 'angel', 'windibank',
    'sutherland', 'wilson', 'spaulding', 'merryweather', 'jabez', 'saxe',
    'coburg', 'aldersgate', 'norbury', 'stoke', 'moran', 'adler', 'irene',
    'godfrey', 'norton', 'bohemia', 'ormstein', 'briony', 'serpentine',
    'stangerson', 'whitney', 'boone', 'clair', 'lascar', 'swandam', 'cornelius',
    'toller', 'fowler', 'carruthers', 'walsall', 'hampshire', 'hereford',
    'ross', 'duncan', 'morris', 'breckinridge', 'oakshott', 'peterson',
    'ballarat', 'lone', 'star', 'pondicherry', 'dundee', 'sholto',
}


def better(vision, plain):
    """Return (chosen, reason) or (None, None) when no rule applies."""
    v, p = vision.strip(), plain.strip()
    lv, lp = v.lower(), p.lower()

    if not v and not p:
        return None, None

    # ── the book's own proper names, which the dictionary lacks ──────────────
    def bookish(s):
        ws = [w.strip("'").lower() for w in re.findall(r"[A-Za-z']+", s)]
        return bool(ws) and all(w in VOCAB or w in BOOK_WORDS or
                                (len(w) == 1 and w in SINGLE) for w in ws)

    bv, bp = bookish(v), bookish(p)
    if v and p and bv != bp:
        return (v, 'only this witness reads words the book uses') if bv else \
               (p, 'only this witness reads words the book uses')

    # ── a spurious space inside one word ────────────────────────────────────
    if v and p and re.sub(r'\s+', '', lv) == re.sub(r'\s+', '', lp):
        # ⚠️ Which side has the spurious space? Ask whether the JOINED form is
        # a word. 'tempera ment' joins to 'temperament' and the space is
        # debris; "You'lldo" is not a word and the SPACE is what was lost.
        joined = [x for x in (v, p) if ' ' not in x]
        spaced = [x for x in (v, p) if ' ' in x]
        if joined and spaced:
            if is_english(joined[0].replace('-', '')):
                return joined[0], 'the joined form is a word; the space was debris'
            return spaced[0], 'the joined form is not a word; a space was lost'

    # ── hyphen or dash? let the witnesses tell you which ────────────────────
    # ⚠️ Not "prefer the hyphenated form". The 1892 setting uses an em dash
    # freely — "observer—excellent for drawing the veil" — and this scan glues
    # a dash into a hyphen while the archive scan renders it as a space. So the
    # SHAPE of the disagreement says which mark the page carries:
    #   this=A-B, other=A B  -> the page has a DASH; neither witness has it
    #   this=A B, other=A-B  -> the page has a real hyphen (great-coat)
    # Getting this backwards welds two words into a compound Doyle never wrote.
    if v and p and lv.replace('-', ' ') == lp.replace('-', ' ') and lv != lp:
        if '-' in v and '-' not in p:
            return v.replace('-', '\u2014'), 'the page has a dash here, not a hyphen'
        if '-' in p and '-' not in v:
            return p, 'the printing hyphenates this'

    # ⚠️ NO AUTOMATIC RULE FOR QUOTE MARKS. There was one here, preferring the
    # bare word — and it stripped real quotation marks: the page reads
    # "'P,' of course, stands for 'Papier.'", where that trailing mark closes a
    # quotation and is not debris. Vision does attach junk quotes, but the two
    # cases cannot be told apart without looking, so they go to review.

    # ── the archive scan's systematic letter confusions ─────────────────────
    # Measured on this book: it reads I as T, y as v, h as b, r as t.
    SWAPS = [('t', 'i'), ('v', 'y'), ('b', 'h'), ('l', 'i'), ('j', 'i')]
    if v and p and len(lv) == len(lp):
        diffs = [(a, b) for a, b in zip(lv, lp) if a != b]
        if len(diffs) == 1:
            a, b = diffs[0]
            if (b, a) in SWAPS and is_english(v) and not is_english(p):
                return v, f'archive scan reads {b!r} for {a!r}; this is the word'
            if (a, b) in SWAPS and is_english(p) and not is_english(v):
                return p, f'this scan reads {a!r} for {b!r}; the other is the word'

    # ── the archive scan reads a capital I as T at the head of a word ───────
    # 'TI'/'IT' for 'I', "Tt's" for "It's", "T've" for "I've". Measured 209
    # times in this book; it is the single commonest thing wrong with it.
    if v and p and lp.replace('t', 'i', 1) == lv and p[:1].upper() == 'T':
        return v, "archive scan reads T for I at the head of a word"
    if v and p and re.fullmatch(r'[TI]{1,2}', p) and v == 'I':
        return v, "archive scan reads T for I at the head of a word"

    # ── a word broken at a line end, joined by one witness only ─────────────
    # 'suffi' / 'suffi-' with 'cient' following; 'Water- 1o0' / 'Waterloo'.
    # Keep whichever form lets the joiner finish the word: the fully joined one
    # if a witness managed it, otherwise the hyphenated fragment, which the
    # final join pass completes against the token that follows.
    if v and p:
        jv, jp = re.sub(r'-\s*', '', lv), re.sub(r'-\s*', '', lp)
        sv, sp = re.sub(r'\s+', '', jv), re.sub(r'\s+', '', jp)
        if sv == sp and sv:
            whole = [x for x in (v, p) if '-' not in x and ' ' not in x]
            if whole:
                return whole[0], 'the same word, joined'
        if lv.rstrip('-') == lp.rstrip('-') and lv != lp:
            return (v, 'broken at a line end; keep the hyphen for the join pass') \
                if v.endswith('-') else \
                (p, 'broken at a line end; keep the hyphen for the join pass')

    # ── a run of capitals on one side and nothing on the other ──────────────
    # A running head the inline stripper did not reach. It is page furniture,
    # not a phrase one witness lost.
    if bool(v) != bool(p):
        lone = (v or p)
        caps = [w for w in lone.split() if re.match(r'^[^a-z]*[A-Z][^a-z]*$', w)]
        if len(lone.split()) >= 2 and len(caps) >= max(2, len(lone.split()) - 1):
            return '', 'a run of capitals on one side only; page furniture'

    # ── a lone stray mark against nothing ───────────────────────────────────
    # One witness picked up a page-number fragment or a speck; the other saw
    # nothing there. A single character that is not a word is not text.
    if bool(v) != bool(p):
        lone = (v or p)
        # ⚠️ DIGITS AND MARKS ONLY. This rule used to delete any lone
        # character that was not a word, and a lone LETTER is often text: the
        # Bohemia note is read as "a large E with a small g, a P, and a large
        # G with a small t". It would have quietly deleted four letters out of
        # the passage that explains the monogram (John's own pass, 2026-08-29).
        if re.fullmatch(r"[0-9]['’]?|[^\w\s]", lone):
            return '', 'a lone digit or mark on one side only; not text'

    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ledger', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--residual', default='')
    args = ap.parse_args()

    rows = list(csv.DictReader(open(args.ledger), delimiter='\t'))
    decided, left = [], []
    for r in rows:
        v, p = r['vision'].strip(), r['plain'].strip()
        if v and p and is_english(v) != is_english(p):
            decided.append((r, v if is_english(v) else p, 'only this witness reads English'))
            continue
        pick, why = better(v, p)
        if pick is not None:
            decided.append((r, pick, why))
        else:
            left.append(r)

    with open(args.out, 'w', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['id', 'chosen', 'reason', 'vision', 'plain', 'before', 'after'])
        for r, pick, why in decided:
            w.writerow([r['n'], pick, why, r['vision'], r['plain'], r['before'], r['after']])

    if args.residual:
        with open(args.residual, 'w', newline='') as f:
            w = csv.writer(f, delimiter='\t')
            w.writerow(['n', 'vision', 'plain', 'before', 'after'])
            for r in left:
                w.writerow([r['n'], r['vision'], r['plain'], r['before'], r['after']])

    print(f'{len(rows):,} disagreements')
    print(f'  {len(decided):,} settled by rule')
    print(f'  {len(left):,} left for a person')
    from collections import Counter
    for why, n in Counter(w for _, _, w in decided).most_common():
        print(f'     {n:>5}  {why}')


if __name__ == '__main__':
    sys.exit(main())
