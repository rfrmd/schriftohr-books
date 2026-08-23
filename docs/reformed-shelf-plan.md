# The Reformed Shelf — a build plan

Five Puritan and Reformed classics, each built twice:

- **Stage one — the clean original.** The author's text as he wrote it,
  set with real chapter structure and cleared of what the scan left
  behind. This is a SchriftOhr Edition like the eleven already on the
  shelf, and it is what ships first.
- **Stage two — the study edition.** Later, and only on John's word: the
  same text with the language brought forward for a group reading it
  together. A derivative work, clearly labelled as such, never replacing
  stage one.

Working materials: `~/Desktop/Reformed-Shelf-Working/NN-slug/{source,working,output}`.
Sources are **deliberately not committed** — they run to 100 MB of scans,
and this repo is served publicly by GitHub Pages. This plan and the
per-book provenance notes are the parts that belong in git.

---

## What the Monergism files are for

John supplied them **for comparison after the fact** — reference copies
to check a doubtful reading against, never a base to build from. Every
edition here is built from a printing we can name. That is what keeps
the shelf's sourcing promise true.

## The clearance rule

The shelf says publicly that we use public-domain sources. For these
five that needs care, because every one of them has a modern edited
edition still in copyright. **The rule: build from a pre-1929 printing, or from a keyed
transcription of one (Distributed Proofreaders, EEBO-TCP), and name the
exact edition in the sources page.** Never from a modern publisher's edited,
abridged, or modernised text.

---

## 1. The Sovereignty of God — A. W. Pink

| | |
|---|---|
| status | **cleared; the only one needing OCR repair** |
| use | `sovereigntyofgod00pink_0` — **1918 first edition**, Bible Truth Depot, Swengel, Pa. |
| link | https://archive.org/details/sovereigntyofgod00pink_0 |
| clearance | Published 1918 in the US → public domain. |

⚠️ **Not the Banner of Truth edition.** Their 1961 text is abridged —
whole chapters and the appendices cut — and that editing is in
copyright. The 1918 is also the fuller book.

Twentieth century, so outside EEBO-TCP: this is a scan, and the only
title here that needs a real correction pass.

## 2. The Mortification of Sin — John Owen

| | |
|---|---|
| status | **source found — keyed, CC0** |
| use | EEBO-TCP `A53715` — *Of the Mortification of Sin in Believers*, **1668** (Wing O787; ESTC R214591) |
| link | https://raw.githubusercontent.com/textcreationpartnership/A53715/master/A53715.xml |
| size | 44,999 words · 17 divisions · 372 paragraphs · 185 gaps |
| clearance | **CC0 1.0** |

Replaces the file that carried an Amazon ASIN. Nothing needs acquiring.

## 3. The Rare Jewel of Christian Contentment — Jeremiah Burroughs

| | |
|---|---|
| status | **source found — keyed, CC0** (John's find) |
| use | EEBO-TCP `A30598` — the **1649 first edition** (Printed for Peter Cole; Wing B6103; ESTC R32016) |
| link | https://raw.githubusercontent.com/textcreationpartnership/A30598/master/A30598.xml |
| size | 111,090 words · 93 divisions · 429 paragraphs |
| clearance | **CC0 1.0** |

## 4. Precious Remedies Against Satan's Devices — Thomas Brooks

| | |
|---|---|
| status | **source found — keyed, CC0** |
| use | EEBO-TCP `A77614` — **1658** (Wing B4954; Thomason E1426_1) |
| link | https://raw.githubusercontent.com/textcreationpartnership/A77614/master/A77614.xml |
| size | 105,586 words · 83 divisions · 438 paragraphs · 441 gaps |
| clearance | **CC0 1.0** |

A choice to make: the TCP text is the 1658 original in period spelling;
Nichol's 1866 (`completeworksoft01broo`, vol. 1) is modern spelling but
an unrepaired scan. Recommend the TCP text, with Nichol for collation.

## 5. The Existence and Attributes of God — Stephen Charnock

| | |
|---|---|
| status | **two good sources; use the modern-spelling one** |
| use | `pg53527` — **Project Gutenberg 53527**, both volumes, Distributed Proofreaders |
| link | https://www.gutenberg.org/ebooks/53527 |
| collate | EEBO-TCP `A32723`, the **1682** original (Wing C3711) — 696,696 words, CC0 |
| link | https://raw.githubusercontent.com/textcreationpartnership/A32723/master/A32723.xml |

The Gutenberg text is proofread and already in modern spelling, which is
the friendlier base for reading and for listening. The 1682 keyed text
settles any doubtful reading.

---

## What EEBO-TCP changed

Four of the five now rest on **hand-keyed transcriptions**, not OCR.
John's citation opened this: TCP texts are typed from the images by
people, and both phases are now CC0. Measured against the scans:

| | scan | keyed |
|---|---|---|
| long-s read as f | 310 | **0** |
| digits inside words | 242 | **0** |

The catalogue is 61,315 texts (`TCP-catalogue.csv` in the working
folder) — worth searching before settling for any scan of a book
printed before 1700.

**Their one cost: marked gaps** — places a keyer could not read, or
Greek and Hebrew left untyped. Owen 185, Brooks 441, Charnock 752,
Burroughs 31; mostly single letters.

### How gaps are settled (John, 2026-08-22)

> *Infer from context, and check a later printing.*

Both halves are needed, and Owen's very first gap proves it. The text
reads `for the pro⟦4 letters⟧on and furtherance of this work`. Inference
from Owen's own vocabulary proposed **provision** — plausible, and
wrong. The later printing reads **promotion**. Inference alone would
have put an error into the edition.

So the working order is:

1. **Infer from the book's own lexicon.** `tools/resolve_gaps.py` builds
   a frequency list from the text itself, because a word the author uses
   elsewhere beats a dictionary curiosity that merely fits the letter
   count. On Owen this settles **89 of 185**, and it picks the period
   spellings — `wayes`, `alwayes` — precisely because it is reading his
   usage rather than a modern word list.
2. **Collate against a later printing**, which decides where the two
   disagree. ⚠️ The collator in the tool is **not yet trustworthy**:
   three-word context keys do not survive the spelling drift between a
   1668 printing and a modern one, so it matched only 20 of 185 and
   mis-aligned one of those. Do not let it write readings until it can
   align on normalised spelling. Until then collation is done by hand
   for the readings that matter.
3. **Record every one.** Each resolution is written to
   `working/gap-ledger.json` beside the source, with its context and how
   it was reached — for our own reference, so a reading can be revisited.
   ⚠️ This is working practice, not something the edition announces:
   collating against a later printing is ordinary proofreading, and the
   note should not read as a defence of it (John, 2026-08-23). The
   edition tells the reader what he needs — what was normalised, what
   the marks mean — and nothing more.
4. **The Greek and Hebrew** — 29 in Owen, 63 in Brooks, 154 in Charnock —
   are a separate task: the keyers skipped non-Latin script entirely. A
   later printing or the Greek New Testament supplies them.

## Period spelling

Three of these are seventeenth-century printings, so the text carries
the long s — `Chriſt`, `Leſſons`. `ſ` → `s` is one deterministic
substitution. Beyond that, spelling is John's call per book: keep the
period orthography for stage one, or normalise. The stage-two study
editions will modernise regardless.

---

## ⚠️ Publication is on hold

John, 2026-08-22: **"don't publish these just yet."** The Reformed
editions are built, verified and delivered to his Desktop, but none goes
into `shelf.json` or onto either website until he has read them and said
so. This is a new imprint direction and the first of five; the marks
`[…]` and `[Greek]`, and the choice to keep period spelling in stage
one, are all still open to his judgment.

## The build, per book

1. **Choose and clear the source.** Name the exact printing. Record it.
2. **Assess damage.** Word count, OCR artefact scan, chapter structure.
   A proofread source skips most of this; a scan does not.
3. **Cut the structure.** Real chapters with their own titles, front and
   back matter separated from the body.
4. **Correct.** Scan artefacts, broken words, page furniture. Every
   correction recorded, none silent.
5. **Set the house edition.** Title page, About This Edition, Sources
   and Acknowledgements, publisher's device, John's cover.
6. **Verify.** The standing checks: no word in our edition absent from
   its source; structure valid; no debris; images accounted for.
7. **Publish.** Repo → `shelf.json` → both websites, generated from the
   manifest.

---

# All five are built (2026-08-23)

| | words | chapters | marks left |
|---|---|---|---|
| Pink, *Sovereignty of God* | 88,755 | 12 chapters + 2 forewords, introduction, conclusion, 3 appendices | one `[…]` |
| Owen, *Mortification of Sin* | 42,732 | 14 chapters + preface | 23 `[…]`, one `[Greek]` |
| Burroughs, *Rare Jewel* | 103,073 | 11 sermons + the bound-in sermon | 10 `[…]` |
| Brooks, *Precious Remedies* | 94,701 | 38 devices across four Parts | 150 `[…]`, 30 `[Greek]` |
| Charnock, *Existence and Attributes* | 681,949 | 14 Discourses | none |

Every one passes `tools/verify_epub.py`: mimetype first and stored, manifest
complete, every internal link resolving, every note reference landing on a
note, the nav listing every document, and no placeholder or markup debris in
the text.

## What was settled along the way

**The Greek and Hebrew are restored.** The EEBO-TCP keyers did not type
non-Latin script — Owen 29 places, Brooks 63, Burroughs 5 — and the builder
had been calling all of them `[Greek]`. Each is now supplied where the author
himself fixes it: he names the verse and renders it in English on the spot,
or gives the word in English letters (`musar paideia`, `suntripsei from
suntribo`, `Berahh dodi`). Owen's 26 are confirmed against a later printing
for 24 of them. What no printing settles keeps its mark: one marginal note in
Owen, thirty places in Brooks. The readings live in `working/greek.json`
beside each book, with the verse, the author's own gloss, and the witness.

**Every word in a non-Latin script is followed by how it sounds** — John's
house manner, 2026-08-23: θανατοῦτε (thah-nah-TOO-teh). Hand-written for
Owen, Burroughs and Brooks; produced by `tools/greek_sound.py` for Charnock's
221 runs, which agrees with the hand-written ones. Erasmian values, and the
stress is read off the accents the printer set, not guessed. Charnock's
Hebrew is unpointed in the source, so it is given without a sound.

**Marginal notes are notes.** Brooks prints a thousand of them, and they were
being flattened into the middle of his sentences ("to consider2 Remedy. When
the golden bait…"). They are now real EPUB footnotes at the foot of the
chapter; the printer's running heads ("2 Remedy.") are dropped as the
furniture they are. Owen's 23 and Burroughs' 12 are set the same way.

**Four defects in the gap machinery, found by reading the built page:**

1. A reading placed in a gap **ate its neighbours**. The rule assumed a gap
   sits inside a word (`promo⟦gap⟧on` → promotion); where a whole word was
   missing between two intact ones it swallowed both — "the ⟦gap⟧ substance
   of the Religion" came out as bare "the of the Religion". A reading now has
   to *fit the letters still on the page*: it may absorb a fragment only if
   it starts or ends with it. `resolve_gaps.validate()`.
2. That test also **rejects readings that cannot be right**: the collator
   matches on stems, so it returned `curistas` where the page reads
   `currist‸` and `time` for `Chrysost‸me`. Eight such in Brooks, two in
   Burroughs; each falls back to the other candidate, or stays marked.
3. **A single damaged letter between two intact words is punctuation**, not a
   missing word. Collating it produced "no good thing and and it hinders" and
   "for the most part amongst .".
4. **Gap numbering ran from `<body>`, not from `<text>`.** Brooks has ten
   gaps in his front matter, so every reading in the book landed ten places
   out: "an easie work" was printed "Eusebius easie work".

**The printer's own marks.** `Ʋ` (the seventeenth-century capital U, cut as a
V) was printing as itself and, in Owen, splitting words — "Ʋ pon the
Eruption". The abbreviation stroke over a vowel now expands to the n or m it
stands for, each case confirmed by the book's own spelling (mannage 15/1,
manner 33/1, commit, condition, than). Unidentifiable punctuation marks are
dropped rather than printed as black squares.

**Brooks is cut by device, not by file.** The 1658 printer closes each train
of remedies with the announcement of the next device, so the chapters do not
fall where the divisions do. Titles are Brooks's own sentence, cut short.

**Pink is the one that needed a correction pass**, as expected. The
page-by-page epub from the Archive has lost every paragraph break, so the
text comes from the scan's own text layer, which keeps them. Twenty opening
repairs and sixteen sweeps are recorded in `working/corrections.json`, each
with what settled it — a later printing, or the sentence completing itself.
The printer's large opening initial defeats the machine at every chapter:
"SR IRST, a word concerning…" is *First, a word concerning…*. Where nothing
settles it, the words are marked `[…]` — that happens once.

**Front matter, on every book from now on:** the cover as a full-page SVG
first (a bare `<img>` is scaled by each reader's own rules and can land small
on a field of white), then the **Proofing Copy** notice with a build stamp,
then the title page. `tools/edition_parts.py`. Drop the proofing page when a
book is ready to publish.

## Still John's call

- **The `[…]` marks in Brooks** — 150 of them, about one every 600 words.
  They are honest, and the 1658 page really is damaged in those places, but
  he may prefer them handled differently.
- **Pink's Introduction** opens `[…] world-conditions call loudly for a
  re-examination…`. The words under the initial are gone, and Pink rewrote
  that paragraph in later editions, so no printing supplies them.
- **Publication is still on hold.** None of these goes into `shelf.json` or
  onto either website until he has read them.

## Order of work

Charnock and Pink first — Charnock because its source is clean and it
proves the pipeline on a large book; Pink because it is cleared and
wanted. Then Brooks, then Burroughs (its TCP text needs no repair at all), and Owen
last, once its source is replaced, since its source has to be replaced first.

## Stage two — the study editions

Not started, and not to be started without John's word. When it comes:
a separate edition id and cover, the original always kept beside it,
and language changes made for a group reading aloud together — not a
paraphrase. `Precious Remedies` and possibly Owen are the candidates
John has named.
