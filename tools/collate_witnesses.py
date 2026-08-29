#!/usr/bin/env python3
"""Collate two independent readings of a book into one text, and a ledger of doubt.

The method, and why it is this one (John, 2026-08-29):

  · **Two witnesses, independently produced.** Two OCR passes over two different
    printings, by two different recognisers, made decades apart. Their errors are
    uncorrelated — measured on Sherlock, Apple's Vision fails on quotation marks
    and dropped initials, archive.org's 2008 pass fails on I→T — so where they
    AGREE the reading is close to certain, and where they differ you have a short
    list rather than a whole book to re-read.
  · **The page image decides.** Not a third transcription. A proofread text from
    elsewhere may flag a place worth looking at, but if it settles what our book
    says then its editorial work is in our book and the edition is not ours.
  · **Nothing disappears silently.** Every disagreement is written to a ledger
    with both readings and their context. What is accepted automatically is only
    ever what both witnesses already say.

Mechanical repair runs BEFORE comparison, or the ledger fills with noise that was
never in doubt: line-end hyphens, running heads, page numbers, quote characters.

    collate_witnesses.py --vision DIR --plain FILE --out DIR
"""

import argparse
import difflib
import pathlib
import re
import sys
from collections import Counter


# ── mechanical repair ───────────────────────────────────────────────────────────

QUOTE_MAP = {
    '«': '"', '»': '"', '“': '"', '”': '"', '‟': '"', '„': '"',
    '‘': "'", '’': "'", '‚': "'", '‛': "'", '`': "'", '´': "'",
}

def canon_quotes(s):
    for bad, good in QUOTE_MAP.items():
        s = s.replace(bad, good)
    return s


def join_hyphens(lines):
    """A word broken across a line end is one word.

    ⚠️ Both witnesses fail here identically ('ad- vice'), so it would not show up
    as a disagreement — it would sail through as agreed nonsense. Repair first.
    Only join when the next line starts lower-case: 'Saxe-\\nCoburg' is a real
    hyphen and must survive.
    """
    out = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        while line.endswith('-') and i + 1 < len(lines):
            nxt = lines[i + 1].lstrip()
            if not nxt or not nxt[0].islower():
                break
            head, _, _ = line.rpartition('-')
            word = re.search(r'(\S+)$', head)
            tail = re.match(r"([A-Za-z'’]+)", nxt)
            if not word or not tail:
                break
            line = head + tail.group(1)
            lines[i + 1] = nxt[len(tail.group(1)):].lstrip()
            if lines[i + 1]:
                break
            i += 1
        out.append(line)
        i += 1
    return out


# ── the witnesses ───────────────────────────────────────────────────────────────

def read_vision(directory, zone=0.085, repeats=5):
    """Vision's pages, with the furniture dropped by what it IS, not where it sits.

    ⚠️ A fixed top margin is a text-eater. Measured over these 355 pages the
    running head sits at y≈0.039 and the page number BESIDE it at the same
    height — but the first line of body text can begin as high as 0.067, and a
    7% margin swallowed it. The margin that clears the furniture also clears
    prose, on some pages and not others, which is the worst kind of bug: it
    loses a line here and there and the text still reads.

    So the book is asked what its own running heads are. Every line in the top
    zone is censused; a line whose text recurs at the top of `repeats` pages or
    more is furniture — twelve story titles and the book's own name will each
    appear dozens of times, while a line of Doyle's prose appears once. Bare
    numerals and roman numerals go too. Everything dropped is returned, so it
    can be read back and checked.
    """
    from collections import Counter

    pages_raw = []
    for tsv in sorted(pathlib.Path(directory).glob('*.tsv')):
        rows = []
        for row in tsv.read_text(encoding='utf-8').splitlines():
            parts = row.split('\t')
            if len(parts) == 4:
                rows.append((parts[0], float(parts[1]), float(parts[2]), float(parts[3])))
        pages_raw.append(rows)

    def norm(s):
        return re.sub(r'[^a-z]', '', s.lower())

    census = Counter()
    for rows in pages_raw:
        for text, top, bottom, _ in rows:
            if top < zone or bottom > 1 - zone:
                n = norm(text)
                if n:
                    census[n] += 1
    heads = {n for n, c in census.items() if c >= repeats}

    NUMBERISH = re.compile(r"^[\s\d IlOSB!$|.,;:_\-—~'’`()\[\]]*$")
    ROMAN = re.compile(r'^[\s.,;:_\-]*[IVXLC]{1,7}[\s.,;:_\-]*$', re.I)

    pages, dropped = [], []
    for rows in pages_raw:
        keep = []
        for text, top, bottom, _ in rows:
            in_zone = top < zone or bottom > 1 - zone
            if in_zone and (norm(text) in heads or NUMBERISH.match(text)
                            or ROMAN.match(text)):
                dropped.append(text)
                continue
            keep.append(text)
        pages.append(join_hyphens(keep))
    return pages, dropped


RUNNING_HEAD = re.compile(
    r'^[\s_\-.]*[A-Z][A-Z\s\'’.,;:_\-]{6,60}?[\s.,;:_\-]*[0-9IlOS!$|]{1,4}[\s.,;:_\-]*$')

def read_plain(path):
    """A full-text file (archive.org's _djvu.txt), furniture stripped by pattern.

    Its running heads are 'THE RED-HEADED LEAGUE 43' — the title, then a page
    number the OCR has often mangled into 'II', '4S', '$7', '29!'. Match the
    SHAPE, not the digits.
    """
    lines = pathlib.Path(path).read_text(encoding='utf-8', errors='replace').splitlines()
    keep, dropped = [], []
    for line in lines:
        s = line.strip()
        if not s:
            keep.append('')
            continue
        if RUNNING_HEAD.match(s) or re.fullmatch(r'[\s\d IlOS!$|._\-]{1,12}', s):
            dropped.append(s)
            continue
        keep.append(s)
    return join_hyphens(keep), dropped


# ── comparison ──────────────────────────────────────────────────────────────────

WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'\-]*")

def tokens(text):
    """Words only. Punctuation and quoting are compared separately — they are the
    noisiest class in both witnesses and would drown the real disagreements."""
    return WORD.findall(canon_quotes(text))


def collate(a_words, b_words, a_name, b_name, context=6):
    sm = difflib.SequenceMatcher(None,
                                 [w.lower() for w in a_words],
                                 [w.lower() for w in b_words], autojunk=False)
    agreed = 0
    rows = []
    for tag, a1, a2, b1, b2 in sm.get_opcodes():
        if tag == 'equal':
            agreed += a2 - a1
            continue
        rows.append({
            'kind': tag,
            a_name: ' '.join(a_words[a1:a2]),
            b_name: ' '.join(b_words[b1:b2]),
            'before': ' '.join(a_words[max(0, a1 - context):a1]),
            'after': ' '.join(a_words[a2:a2 + context]),
        })
    return agreed, rows, sm.ratio()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vision', required=True, help='directory of Vision .txt/.tsv pages')
    ap.add_argument('--plain', required=True, help='a full-text file (e.g. _djvu.txt)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--zone', type=float, default=0.085,
                    help='fraction of the page treated as margin for the census')
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    pages, v_dropped = read_vision(args.vision, args.zone)
    v_text = '\n'.join('\n'.join(p) for p in pages)
    p_lines, p_dropped = read_plain(args.plain)
    p_text = '\n'.join(p_lines)

    (out / 'witness-a-vision.txt').write_text(v_text, encoding='utf-8')
    (out / 'witness-b-plain.txt').write_text(p_text, encoding='utf-8')

    A, B = tokens(v_text), tokens(p_text)
    print(f'witness A (Vision) : {len(pages):>4} pages · {len(A):>7,} words · '
          f'{len(v_dropped):,} furniture lines dropped')
    print(f'witness B (plain)  : {len(p_lines):>4} lines · {len(B):>7,} words · '
          f'{len(p_dropped):,} furniture lines dropped')

    agreed, rows, ratio = collate(A, B, 'vision', 'plain')
    print(f'\nagreement: {ratio*100:.1f}%  ({agreed:,} words both witnesses read the same)')
    print(f'in doubt : {len(rows):,} places')

    # The ledger, and a census of the disagreement shapes — the census is what
    # makes this tractable, because most disagreements are the SAME disagreement.
    with (out / 'disagreements.tsv').open('w', encoding='utf-8') as f:
        f.write('n\tkind\tvision\tplain\tbefore\tafter\n')
        for n, r in enumerate(rows, 1):
            f.write(f"{n}\t{r['kind']}\t{r['vision']}\t{r['plain']}\t"
                    f"{r['before']}\t{r['after']}\n")

    census = Counter((r['vision'].lower(), r['plain'].lower()) for r in rows)
    with (out / 'census.tsv').open('w', encoding='utf-8') as f:
        f.write('count\tvision\tplain\n')
        for (v, p), c in census.most_common():
            f.write(f'{c}\t{v}\t{p}\n')
    top = census.most_common(12)
    covered = sum(c for _, c in top)
    print(f'\nthe 12 commonest shapes account for {covered:,} of {len(rows):,} '
          f'({100*covered/max(1,len(rows)):.0f}%):')
    for (v, p), c in top:
        print(f'   {c:>5}  {v[:34]!r:38} vs {p[:34]!r}')
    print(f'\nwritten to {out}/')


if __name__ == '__main__':
    sys.exit(main())
