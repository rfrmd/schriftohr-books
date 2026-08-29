#!/usr/bin/env python3
"""Fold every decision back into one clean text.

The base is the Harper scan read by Vision, because that is the printing this
edition is set from. The other witness never supplies the text wholesale — it
supplies READINGS, one at a time, each one decided by a rule that states its
reason or by a person looking at the page. Where a decision says something
neither witness read, that is what goes in.

    apply_decisions.py --vision DIR --plain FILE --decisions A.tsv B.tsv \\
                       --start "..." --end "..." --out clean.txt

⚠️ Splices are applied by CHARACTER SPAN into the base text, back to front, not
by rebuilding from tokens. Rebuilding from tokens would produce a book with no
punctuation, no quotation marks and no paragraphs — the comparison is done on
bare words precisely so that punctuation cannot drown the real disagreements,
and that stripped stream must never become the book.

⚠️ Paragraphs come from the INDENT of the first line, measured per page. There
is no blank line on a printed page; a global margin is no use either, because
each scan is cropped and skewed differently. See `paragraphs`.
"""

import argparse
import csv
import difflib
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from collate_witnesses import (read_vision, read_plain, tokens, canon_quotes,
                               trim_to_body, join_hyphens, WORD)


def base_text(vision_dir, zone=0.085, indent=0.018, repeats=5):
    """The Harper scan as continuous prose, with its paragraphs restored.

    ⚠️ This strips furniture ITSELF rather than filtering raw lines against
    `read_vision`'s output. The first version matched raw text against records
    that `join_hyphens` had already rewritten, so every line whose word had
    been joined failed to match and was dropped — twelve thousand words gone,
    silently, and the word count was the only thing that said so.
    """
    from collections import Counter

    pages = []
    for tsv in sorted(pathlib.Path(vision_dir).glob('*.tsv')):
        rows = []
        for row in tsv.read_text(encoding='utf-8').splitlines():
            p = row.split('\t')
            if len(p) >= 6:
                rows.append((p[0], float(p[1]), float(p[2]), float(p[4])))
        if rows:
            pages.append((tsv.stem, rows))

    def norm(s):
        return re.sub(r'[^a-z]', '', s.lower())

    census = Counter()
    for _stem, rows in pages:
        for text, top, bottom, _x in rows:
            if top < zone or bottom > 1 - zone:
                if norm(text):
                    census[norm(text)] += 1
    heads = {n for n, c in census.items() if c >= repeats}
    # ⚠️ The OTHER witness's inline-head stripper needs this census. When this
    # function was rewritten to strip its own furniture it stopped calling
    # read_vision, the census went unset, and the stripper silently ran with an
    # empty list — leaving forty-odd running heads welded to real words in the
    # ledger, each looking like a textual disagreement.
    base_text.heads = [h for h in heads if len(h) >= 10]
    NUMBERISH = re.compile(r"^[\s\d IlOSB!$|.,;:_\-—~'’`()\[\]]*$")
    ROMAN = re.compile(r'^[\s.,;:_\-]*[IVXLC]{1,7}[\s.,;:_\-]*$', re.I)

    lines, margins, first = [], [], True
    for _stem, rows in pages:
        body = [r for r in rows if zone < r[1] < 1 - zone]
        xs = sorted(r[3] for r in (body or rows))
        margin = xs[int(len(xs) * 0.20)] if xs else 0
        for text, top, bottom, x in rows:
            in_zone = top < zone or bottom > 1 - zone
            if in_zone and (norm(text) in heads or NUMBERISH.match(text)
                            or ROMAN.match(text)):
                continue
            lines.append((text, x, top))
            margins.append(margin)

    # ⚠️ A PARAGRAPH INDENT IS ONE LINE, NOT A RUN. A chapter opens with a drop
    # capital three or four lines deep, and every line beside it starts to the
    # right of the margin — so "indented means new paragraph" broke the first
    # sentence of every story into four paragraphs. A real indent is a line
    # that is indented while the line BEFORE it was not.
    marked, prev_ind = [], True
    for i, (text, x, top) in enumerate(lines):
        page_margin = margins[i]
        ind = x > page_margin + indent
        marked.append((text, ind and not prev_ind))
        prev_ind = ind

    buf = []
    for text, new_para in marked:
        piece = text.rstrip()
        if not piece:
            continue
        if not buf:
            buf.append(piece)
        elif new_para:
            buf.append('\n\n' + piece)
        elif buf[-1].endswith('-') and piece[:1].islower():
            buf[-1] = buf[-1][:-1]
            buf.append(piece)
        else:
            buf.append(' ' + piece)
    return ''.join(buf)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vision', required=True)
    ap.add_argument('--plain', required=True)
    ap.add_argument('--decisions', nargs='+', required=True)
    ap.add_argument('--start', default='')
    ap.add_argument('--end', default='')
    ap.add_argument('--out', required=True)
    ap.add_argument('--ledger-out', default='',
                    help='write THIS pass\'s own disagreement ledger, so the\n                          decision tools and the applier share one stream')
    args = ap.parse_args()

    text = base_text(args.vision)

    # The token stream the ledger was built on, but WITH character spans.
    canon = canon_quotes(text)
    matches = list(WORD.finditer(canon))
    A_all = [m.group() for m in matches]
    A, offset = trim_to_body(A_all, args.start, args.end)
    spans = [(m.start(), m.end()) for m in matches][offset:offset + len(A)]

    # the other witness, the same way collate_witnesses reads it
    p_lines, _ = read_plain(args.plain, getattr(base_text, 'heads', []))
    B, _ = trim_to_body(tokens('\n'.join(p_lines)), args.start, args.end)

    sm = difflib.SequenceMatcher(None, [w.lower() for w in A],
                                 [w.lower() for w in B], autojunk=False)
    edits, B_at, n = [], {}, 0
    for tag, a1, a2, b1, b2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        n += 1
        edits.append((n, a1, a2))
        B_at[n] = B[b1:b2]

    # ⚠️ Decisions are looked up by the READING they settle, not by the row
    # number they were recorded against. The ledger and this pass build their
    # token streams by slightly different routes, so the numbering need not
    # agree — and a decision applied to the wrong place is worse than one not
    # applied at all. The pair is the identity; the id is a convenience.
    by_pair = {}
    for path in args.decisions:
        for r in csv.DictReader(open(path), delimiter='\t'):
            by_pair[(r['vision'].strip(), r['plain'].strip())] = r['chosen']

    decided = {}
    for n, a1, a2 in edits:
        key = (' '.join(A[a1:a2]).strip(), ' '.join(B_at[n]).strip())
        if key in by_pair:
            decided[n] = by_pair[key]

    if args.ledger_out:
        with open(args.ledger_out, 'w', newline='') as f:
            w = csv.writer(f, delimiter='\t')
            w.writerow(['n', 'kind', 'vision', 'plain', 'before', 'after'])
            for n, a1, a2 in edits:
                w.writerow([n, 'diff', ' '.join(A[a1:a2]), ' '.join(B_at[n]),
                            ' '.join(A[max(0, a1 - 6):a1]), ' '.join(A[a2:a2 + 6])])
        print(f'ledger of this pass -> {args.ledger_out} ({len(edits):,} rows)')

    missing = [n for n, _, _ in edits if n not in decided]
    if missing:
        print(f'⚠️ {len(missing)} disagreements have no decision; leaving the '
              f'base reading at each: {missing[:8]}')

    # ⚠️ BACK TO FRONT. Every splice shifts the offsets after it.
    applied = deleted = inserted = 0
    for n, a1, a2 in sorted(edits, key=lambda e: -e[1]):
        if n not in decided:
            continue
        chosen = decided[n]
        if a1 < a2:
            lo, hi = spans[a1][0], spans[a2 - 1][1]
            # ⚠️ ABSORB THE STRAY MARKS EITHER SIDE. The token pattern matches
            # ASCII letters only, so a mis-read accent sitting against a word
            # is outside the span: replacing 'bhorrent' with 'abhorrent' left
            # the stranded mark behind and produced 'äabhorrent'. Any non-ASCII
            # letter-ish character touching the span belongs to the same word.
            while lo > 0 and text[lo-1] not in ' \n' and ord(text[lo-1]) > 127:
                lo -= 1
            while hi < len(text) and text[hi] not in ' \n' and ord(text[hi]) > 127:
                hi += 1
        else:                                   # nothing here in the base
            lo = hi = spans[a1][0] if a1 < len(spans) else len(text)
        if not chosen.strip():
            # take the space with it, or the deletion leaves a double gap
            while hi < len(text) and text[hi] == ' ':
                hi += 1
            text = text[:lo] + text[hi:]
            deleted += 1
        elif a1 == a2:
            text = text[:lo] + chosen + ' ' + text[lo:]
            inserted += 1
        else:
            text = text[:lo] + chosen + text[hi:]
            applied += 1

    # ⚠️ TRIM THE OUTPUT, not only the comparison. The anchors bound the token
    # stream so the two witnesses' front matter could not be collated against
    # each other; the TEXT still carried Google's scanning notice and the
    # library's stamps until they were cut here too.
    if args.start:
        i = text.find(args.start.split()[0])
        m = re.search(re.escape(args.start.split()[0]) + r'.{0,80}?'
                      + re.escape(args.start.split()[-1]), text, re.S)
        if m:
            text = text[m.start():]
    if args.end:
        m = None
        for m in re.finditer(re.escape(args.end.split()[-1]), text):
            pass
        if m:
            text = text[:m.end()] + '.'

    # ⚠️ A plate's caption sometimes lands mid-sentence: the money just
    # "SHERLOCK HOLMES WELCOMED HER" while I am staying with them. It is set
    # wholly in capitals and interrupts a lower-case clause, which is what
    # tells it apart from a letter's salutation — "MY DEAR MR. SHERLOCK
    # HOLMES," is capitals too, but it OPENS a quotation rather than cutting
    # one in half.
    def drop_caption(m):
        before, cap, after = m.group(1), m.group(2), m.group(3)
        if len(cap.split()) < 3:
            return m.group(0)
        return before + after
    text, n_caps = re.subn(
        r'([a-z,;] )[“"”]([A-Z][A-Z \'’.!?,-]{10,60})[”"“](?= [a-z])',
        lambda m: m.group(1), text)
    if n_caps:
        print(f'{n_caps} plate caption(s) removed from mid-sentence')

    # ── plate captions still standing in the prose ─────────────────────────
    # ⚠️ A caption interrupts a sentence and is set wholly in capitals, usually
    # inside quotation marks: ...the money just "SHERLOCK HOLMES WELCOMED HER"
    # while I am staying with them. The quotes are part of it, which is what an
    # earlier rule missed — its lookbehind wanted a letter before the capitals
    # and found the opening quote instead.
    #
    # A letter's salutation is capitals too ("MY DEAR MR. SHERLOCK HOLMES,") but
    # OPENS a quotation rather than cutting one in half, so it is spared.
    def caption(m):
        run = m.group('run')
        if len(run.split()) < 3:
            return m.group(0)
        if re.search(r'\bDEAR\b|\bMR\b|\bMRS\b|\bMADAM\b', run):
            return m.group(0)
        return ' '

    text, n_run = re.subn(
        # ⚠️ \s in the run class, not a bare space: the caption can straddle a
        # paragraph break — "SHERLOCK HOLMES WELCOMED\n\nHER" — and a
        # single-line pattern cannot see it at all.
        r'(?<=[a-z,;] )["“”\u2018\u2019\']*(?P<run>[A-Z][A-Z\'\u2019.,!?\s-]{12,90}?)'
        r'["“”\u2018\u2019\']*(?=\s+[a-z])',
        caption, text)
    if n_run:
        print(f'{n_run} plate caption(s) removed from mid-sentence')

    # ── the marks Vision cannot read ────────────────────────────────────────
    # It renders the 1892 quotation marks as guillemets and specks. These are
    # not readings in doubt — neither witness disagrees about them — so they
    # are normalised rather than adjudicated.
    MARKS = {'«': '"', '»': '"', '‹': "'", '›': "'", '•': '', '¡': '', '¿': '',
             'т': 't', 'о': 'o', 'п': 'n', 'д': 'd', 'е': 'e', 'а': 'a',
             'с': 'c', 'р': 'p', 'у': 'y', 'х': 'x', 'ơ': 'o'}
    fixed = 0
    for bad, good in MARKS.items():
        if bad in text:
            fixed += text.count(bad)
            text = text.replace(bad, good)
    if fixed:
        print(f'{fixed} mis-read marks normalised')

    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()

    pathlib.Path(args.out).write_text(text + '\n', encoding='utf-8')
    paras = text.count('\n\n') + 1
    print(f'{len(edits):,} disagreements · {applied:,} replaced · '
          f'{deleted:,} deleted · {inserted:,} inserted')
    print(f'{len(text.split()):,} words · {paras:,} paragraphs -> {args.out}')


if __name__ == '__main__':
    sys.exit(main())
