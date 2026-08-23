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
edition still in copyright. **The rule: build from a pre-1929 printing
or a Distributed-Proofreaders transcription of one, and name the exact
edition in the sources page.** Never from a modern publisher's edited,
abridged, or modernised text.

---

## 1. The Sovereignty of God — A. W. Pink

| | |
|---|---|
| status | **source in hand, cleared** |
| use | `sovereigntyofgod00pink_0.epub` — **1918 first edition**, Bible Truth Depot, Swengel, Pa. |
| link | https://archive.org/details/sovereigntyofgod00pink_0 |
| clearance | Published 1918 in the US → public domain. |

⚠️ **Do not use the Banner of Truth edition.** Their 1961 text is
abridged and edited — whole chapters and the appendices were cut — and
that editing is under copyright. The 1918 text is also the fuller book,
which is the one worth having.

Quality note: this is an archive.org scan, so expect OCR damage of the
kind found in Pollok. Budget for a real correction pass.

## 2. The Mortification of Sin — John Owen

| | |
|---|---|
| status | **source needs replacing** |
| have | a calibre-made epub carrying an Amazon ASIN (B003ZSHP3E) — provenance unknown, possibly a modern edition |
| use instead | Owen's *Works*, ed. Goold — Mortification is in **volume 6** |
| link | https://archive.org/details/ontemptationmort00owenuoft (Presbyterian Board of Publication) |
| alt | https://archive.org/details/worksofjohnowe185011owen (Goold set) |
| clearance | Owen d. 1683; the Goold edition 1850–55 → public domain. |

⚠️ The file on hand cannot be used: an ASIN means it was made from a
Kindle edition, and we cannot show which text that was. Replace it
before any work starts.

## 3. The Rare Jewel of Christian Contentment — Jeremiah Burroughs

| | |
|---|---|
| status | **blocked — no usable public-domain base** |
| clearance | Burroughs d. 1646; the text is public domain. The problem is not rights, it is that no clean printing exists to build from. |

What the search found: every public-domain copy is a seventeenth-century
printing — 1649, 1650, 1651, 1652, 1655, 1659 — and every one is an EEBO
scan in period type. The OCR is not repairable prose:

> *afuhifsof honow^ and ejieemmththe teB of Men*

310 long-s-as-f errors, 729 stray letters, 242 digits inside words, in
94,000 words. That is a transcription project, not a correction pass.
**There is no printing at all between 1659 and the modern editions**,
and those (Banner of Truth 1964, Reformation Heritage 2013) are in
copyright. HathiTrust and CCEL add nothing.

Options, in the order I would take them:

1. **Defer.** Build the other four. Burroughs waits for a better base —
   Distributed Proofreaders may yet do one.
2. **Ask Monergism for permission** to use their text, naming them in the
   sources page. Different from building on their file unasked, and it
   is the only clean route to this book today.
3. **Transcribe from the 1651** ourselves. Honest, and expensive.

## 4. Precious Remedies Against Satan's Devices — Thomas Brooks

| | |
|---|---|
| status | **sources in hand; pick the base** |
| best base | *Complete Works*, ed. Nichol, Edinburgh 1866 — **Precious Remedies is in volume 1** |
| have | `completeworksoft01broo.epub` (vol 1), `preciousremedies00broo.epub` (standalone), Monergism *Works*, two raw OCR texts |
| link | https://archive.org/details/completeworksoft01broo |
| clearance | Brooks d. 1680; Nichol edition 1866 → public domain. |

Recommendation: build **Precious Remedies alone** first, from the Nichol
volume 1. The complete works is six volumes and a different undertaking.
The two `.txt` files are unproofread OCR — useful only for comparison.

## 5. The Existence and Attributes of God — Stephen Charnock

| | |
|---|---|
| status | **best source of the five, in hand** |
| use | `pg53527-images-3.epub` — **Project Gutenberg 53527, both volumes**, transcribed and proofread by Distributed Proofreaders |
| link | https://www.gutenberg.org/ebooks/53527 · mirror: https://openchapter.io |
| clearance | Charnock d. 1680; PG text public domain in the US. |

This one needs no OCR repair — a proofread transcription is worth more
than any scan. The Princeton `.txt` files and the archive PDFs stay as
collation copies only.

---

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

## Order of work

Charnock and Pink first — Charnock because its source is clean and it
proves the pipeline on a large book; Pink because it is cleared and
wanted. Then Brooks, then Owen once its source is replaced.
Burroughs is blocked and waits, since its source has to be replaced first.

## Stage two — the study editions

Not started, and not to be started without John's word. When it comes:
a separate edition id and cover, the original always kept beside it,
and language changes made for a group reading aloud together — not a
paraphrase. `Precious Remedies` and possibly Owen are the candidates
John has named.
